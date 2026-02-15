from typing import Callable, Optional
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QGroupBox,
    QMessageBox,
)
from core.data_contracts import CharacterProfile
from utils.constants import DIALOG_CHAR_SETTING_WIDTH, DIALOG_CHAR_SETTING_HEIGHT


class CharSettingDialog(QDialog):
    """Character settings dialog."""

    def __init__(self, parent, on_register_char: Callable, profile: Optional[CharacterProfile] = None):
        super().__init__(parent)
        self.app = parent
        self.on_register_char = on_register_char
        self.profile = profile

        title_key = "char_setting_edit" if self.profile else "char_setting_new"
        # Fallback if keys don't exist yet
        title = self.app.tr(title_key)
        if title == title_key:
            title = self.app.tr("char_setting_title") + (" (Edit)" if self.profile else " (New)")

        self.setWindowTitle(title)
        self.resize(DIALOG_CHAR_SETTING_WIDTH, DIALOG_CHAR_SETTING_HEIGHT)

        # Definitions
        self.cost_presets = {"[4,3,3,1,1]": [4, 3, 3, 1, 1], "[4,4,1,1,1]": [4, 4, 1, 1, 1]}
        # Reverse map for loading: "43311" -> "[4,3,3,1,1]"
        self.cost_config_map = {"".join(map(str, v)): k for k, v in self.cost_presets.items()}
        # from constants import MAIN_STAT_OPTIONS, SUBSTAT_MAX_VALUES # Removed
        self.main_stats = self.app.data_manager.main_stat_options
        self.substat_candidates = list(self.app.data_manager.substat_max_values.keys())

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Row 1: Name and English Name
        row1 = QHBoxLayout()
        row1.addWidget(QLabel(self.app.tr("char_name")))
        self.entry_name = QLineEdit()
        row1.addWidget(self.entry_name)

        row1.addWidget(QLabel(self.app.tr("char_name_en")))
        self.entry_name_en = QLineEdit()
        self.entry_name_en.setPlaceholderText(self.app.tr("char_name_en_placeholder"))
        row1.addWidget(self.entry_name_en)
        layout.addLayout(row1)

        # Element Row
        row_element = QHBoxLayout()
        row_element.addWidget(QLabel(self.app.tr("element_label", "属性")))
        self.combo_element = QComboBox()
        self.combo_element.addItems(["焦熱", "凝縮", "回折", "消滅", "電導", "気動"])
        row_element.addWidget(self.combo_element)
        layout.addLayout(row_element)

        # Stat Offsets Group
        offset_group = QGroupBox(self.app.tr("base_stat_offsets"))
        offset_layout = QHBoxLayout(offset_group)
        layout.addWidget(offset_group)

        from utils.constants import STAT_ATK_PERCENT, STAT_CRIT_RATE, STAT_CRIT_DMG, STAT_ER

        self.offset_fields = {}
        for stat in [STAT_ATK_PERCENT, STAT_CRIT_RATE, STAT_CRIT_DMG, STAT_ER]:
            v_box = QVBoxLayout()
            v_box.addWidget(QLabel(self.app.tr(stat)))
            entry = QLineEdit("0.0")
            entry.setFixedWidth(60)
            self.offset_fields[stat] = entry
            v_box.addWidget(entry)
            offset_layout.addLayout(v_box)

        # Base and Ideal Stats Group
        calc_param_group = QGroupBox(self.app.tr("basic_settings"))
        calc_param_layout = QVBoxLayout(calc_param_group)
        layout.addWidget(calc_param_group)

        from utils.constants import STAT_ATK_FLAT, STAT_DEF_FLAT, STAT_HP_FLAT

        row_scaling = QHBoxLayout()
        row_scaling.addWidget(QLabel(self.app.tr("scaling_stat_label")))
        self.combo_scaling = QComboBox()
        self.combo_scaling.addItems([STAT_ATK_FLAT, STAT_DEF_FLAT, STAT_HP_FLAT])
        row_scaling.addWidget(self.combo_scaling)
        calc_param_layout.addLayout(row_scaling)

        self.base_stat_fields = {}
        self.ideal_stat_fields = {}
        for stat in [STAT_ATK_FLAT, STAT_DEF_FLAT, STAT_HP_FLAT]:
            row = QHBoxLayout()
            row.addWidget(QLabel(self.app.tr(stat)))

            row.addWidget(QLabel(self.app.tr("base_stat_label")))
            b_entry = QLineEdit("0")
            b_entry.setFixedWidth(80)
            self.base_stat_fields[stat] = b_entry
            row.addWidget(b_entry)

            row.addWidget(QLabel(self.app.tr("ideal_stat_label")))
            i_entry = QLineEdit("0")
            i_entry.setFixedWidth(80)
            self.ideal_stat_fields[stat] = i_entry
            row.addWidget(i_entry)

            calc_param_layout.addLayout(row)

        # Row 2: Preset
        row2 = QHBoxLayout()
        row2.addWidget(QLabel(self.app.tr("cost_config")))
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(list(self.cost_presets.keys()))
        self.combo_preset.currentTextChanged.connect(self.update_main_stat_options)
        row2.addWidget(self.combo_preset)
        layout.addLayout(row2)

        # Slot Config
        slot_group = QGroupBox(self.app.tr("echo_5_slot_config"))
        slot_layout = QVBoxLayout(slot_group)
        layout.addWidget(slot_group)

        self.slot_labels = []
        self.slot_combos = []

        for i in range(5):
            r_layout = QHBoxLayout()
            lbl = QLabel()
            lbl.setFixedWidth(120)
            self.slot_labels.append(lbl)
            r_layout.addWidget(lbl)

            cb = QComboBox()
            self.slot_combos.append(cb)
            r_layout.addWidget(cb)

            slot_layout.addLayout(r_layout)

        self.update_main_stat_options()

        # Effective Substats
        eff_group = QGroupBox(self.app.tr("effective_substats_weights"))
        eff_layout = QVBoxLayout(eff_group)
        layout.addWidget(eff_group)

        # Add Template ComboBox
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel(self.app.tr("weight_template")))
        self.combo_weight_template = QComboBox()

        # from constants import CHARACTER_STAT_WEIGHTS # Removed
        self.weight_templates = {
            k: v
            for k, v in self.app.data_manager.character_stat_weights.items()
            if k in ["General", "会心特化型", "バランス型", "スキル回転型"]
        }
        self.combo_weight_template.addItems([self.app.tr("custom")] + list(self.weight_templates.keys()))
        self.combo_weight_template.currentTextChanged.connect(self._apply_weight_template)
        template_layout.addWidget(self.combo_weight_template)
        eff_layout.addLayout(template_layout)

        self.eff_combos = []
        self.eff_weights = []

        for i in range(5):
            r_layout = QHBoxLayout()
            r_layout.addWidget(QLabel(self.app.tr("effective_substat_n", i + 1)))

            cb = QComboBox()
            cb.addItems([""] + self.substat_candidates)  # Add empty option
            self.eff_combos.append(cb)
            r_layout.addWidget(cb)

            r_layout.addWidget(QLabel(self.app.tr("weight")))
            entry = QLineEdit("1")
            entry.setFixedWidth(60)
            self.eff_weights.append(entry)
            r_layout.addWidget(entry)

            eff_layout.addLayout(r_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_save = QPushButton(self.app.tr("save"))
        btn_save.clicked.connect(self.on_save_char)
        btn_close = QPushButton(self.app.tr("close"))
        btn_close.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        if self.profile:
            self._load_profile_data()

    def _load_profile_data(self):
        """Pre-fills the dialog with data from the provided profile."""
        if not self.profile:
            return

        self.entry_name.setText(self.profile.jp_name)
        self.entry_name_en.setText(self.profile.internal_name)
        self.combo_element.setCurrentText(self.profile.element)

        # Load offsets
        for stat, entry in self.offset_fields.items():
            val = self.profile.stat_offsets.get(stat, 0.0)
            entry.setText(str(val))

        # Load base/ideal/scaling
        self.combo_scaling.setCurrentText(self.profile.scaling_stat)
        for stat, entry in self.base_stat_fields.items():
            entry.setText(str(self.profile.base_stats.get(stat, 0)))
        for stat, entry in self.ideal_stat_fields.items():
            entry.setText(str(self.profile.ideal_stats.get(stat, 0)))
        # Assuming internal name shouldn't be changed in edit mode, or make it readonly?
        # For now, let's leave it editable but maybe warn? Or just readonly.
        # self.entry_name_en.setReadOnly(True) # Safer

        # Preset
        preset_key = self.cost_config_map.get(self.profile.cost_config)
        if preset_key:
            self.combo_preset.setCurrentText(preset_key)
            self.update_main_stat_options()  # Force update slots

        # Slots
        # main_stats keys: "4", "3", "3_2", "1", "1_2" roughly or just indexed?
        # CharacterManager._load_character_profiles uses:
        # mainstats = {"4": "...", "3": "...", "3_2": "...", ...}
        # dialog on_save_char logic:
        # key = str(c) if single, else f"{c}_{occurrence}"

        # We need to replicate the key generation logic to match slots
        costs = self.cost_presets.get(self.combo_preset.currentText(), [])
        cost_occurrence = {}
        cost_total = {c: costs.count(c) for c in set(costs)}

        for i, cost in enumerate(costs):
            cost_occurrence[cost] = cost_occurrence.get(cost, 0) + 1
            if cost_total[cost] == 1:
                key = str(cost)
            else:
                key = f"{cost}_{cost_occurrence[cost]}"

            val = self.profile.main_stats.get(key, "")
            idx = self.slot_combos[i].findText(val)
            if idx >= 0:
                self.slot_combos[i].setCurrentIndex(idx)

        # Weights
        # Map back to UI slots. The logic is a bit flexible here since UI is 5 fixed slots.
        # We just fill as many as fit.
        sorted_weights = sorted(self.profile.weights.items(), key=lambda x: x[1], reverse=True)
        for i, (stat, weight) in enumerate(sorted_weights):
            if i < 5:
                idx = self.eff_combos[i].findText(stat)
                if idx >= 0:
                    self.eff_combos[i].setCurrentIndex(idx)
                    self.eff_weights[i].setText(str(weight))

    def update_main_stat_options(self, *args):
        preset_key = self.combo_preset.currentText()
        if not preset_key:
            return

        costs = self.cost_presets[preset_key]
        for i, cost in enumerate(costs):
            cb = self.slot_combos[i]
            cb.clear()
            vals = self.main_stats.get(str(cost), [""])
            # Add empty option at the beginning
            cb.addItems([""] + vals)

            self.slot_labels[i].setText(self.app.tr("cost_echo", cost))

        # Clear remaining
        for j in range(len(costs), 5):
            self.slot_combos[j].clear()
            self.slot_labels[j].setText("")

    def _apply_weight_template(self, template_name):
        if template_name == self.app.tr("custom") or template_name not in self.weight_templates:
            return

        weights = self.weight_templates[template_name]

        # Disable signals to prevent feedback loops while updating
        for combo in self.eff_combos:
            combo.blockSignals(True)
        for weight_entry in self.eff_weights:
            weight_entry.blockSignals(True)

        # Clear all entries first
        for i in range(5):
            self.eff_combos[i].setCurrentIndex(0)  # Set to empty
            self.eff_weights[i].setText("")

        # Apply template
        for i, (stat_name, weight_value) in enumerate(weights.items()):
            if i < 5:
                index = self.eff_combos[i].findText(stat_name)
                if index != -1:
                    self.eff_combos[i].setCurrentIndex(index)
                    self.eff_weights[i].setText(str(weight_value))

        # Re-enable signals
        for combo in self.eff_combos:
            combo.blockSignals(False)
        for weight_entry in self.eff_weights:
            weight_entry.blockSignals(False)

    def on_save_char(self):
        name = self.entry_name.text().strip()
        if not name:
            QMessageBox.critical(self, self.app.tr("error"), self.app.tr("enter_char_name"))
            return

        name_en = self.entry_name_en.text().strip()
        if not name_en:
            QMessageBox.critical(self, self.app.tr("error"), self.app.tr("enter_char_name_en"))
            return

        preset_key = self.combo_preset.currentText()
        costs = self.cost_presets[preset_key]
        mainstats = {}
        cost_occurrence = {}
        cost_total = {c: costs.count(c) for c in set(costs)}

        for i, c in enumerate(costs):
            cost_occurrence[c] = cost_occurrence.get(c, 0) + 1
            if cost_total[c] == 1:
                key = str(c)
            else:
                key = f"{c}_{cost_occurrence[c]}"

            mainstat = self.slot_combos[i].currentText()
            if not mainstat:
                QMessageBox.critical(self, self.app.tr("error"), self.app.tr("echo_main_stat_unselected", i + 1))
                return
            mainstats[key] = mainstat

        effweights = {}
        for cb, w_entry in zip(self.eff_combos, self.eff_weights):
            ename = cb.currentText()
            weight_s = w_entry.text()
            if ename:
                try:
                    effweights[ename] = float(weight_s)
                except ValueError:
                    effweights[ename] = 1.0

        stat_offsets = {}
        for stat, entry in self.offset_fields.items():
            try:
                stat_offsets[stat] = float(entry.text())
            except ValueError:
                stat_offsets[stat] = 0.0

        base_stats = {}
        for stat, entry in self.base_stat_fields.items():
            try:
                base_stats[stat] = float(entry.text())
            except ValueError:
                base_stats[stat] = 0.0

        ideal_stats = {}
        for stat, entry in self.ideal_stat_fields.items():
            try:
                ideal_stats[stat] = float(entry.text())
            except ValueError:
                ideal_stats[stat] = 0.0

        scaling_stat = self.combo_scaling.currentText()
        element = self.combo_element.currentText()

        if self.on_register_char:
            success = self.on_register_char(
                name,
                name_en,
                preset_key,
                mainstats,
                effweights,
                stat_offsets=stat_offsets,
                base_stats=base_stats,
                ideal_stats=ideal_stats,
                scaling_stat=scaling_stat,
                element=element,
            )
            if not success:
                QMessageBox.critical(
                    self,
                    self.app.tr("error"),
                    f"Failed to save character profile for '{name}'.\nCheck log for details.",
                )
                return

        QMessageBox.information(self, self.app.tr("save_complete"), self.app.tr("save_msg", name))
        self.accept()
