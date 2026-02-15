from typing import List, Optional, Tuple, Any, Callable
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox, QLineEdit, QGridLayout
from core.data_contracts import SubStat


class EchoTabWidget(QWidget):
    """
    Widget representing a single Echo input tab (Main Stat + 5 Substats).
    Encapsulates UI construction and data binding.
    """

    def __init__(self, cost: str, main_opts: List[str], sub_opts: List[str], tr_func: Callable[[str, Any], str]):
        super().__init__()
        self.cost = cost
        self.tr = tr_func
        self._sub_opts = sub_opts  # Store for retranslation
        self._main_opts = main_opts  # Store for retranslation

        self.main_combo: QComboBox = None
        self.grp_main: QGroupBox = None
        self.grp_sub: QGroupBox = None
        self.sub_entries: List[Tuple[QComboBox, QLineEdit]] = []

        self._init_ui(main_opts, sub_opts)

    def _init_ui(self, main_opts: List[str], sub_opts: List[str]):
        layout = QVBoxLayout(self)

        # Main Stat Section
        self.grp_main = QGroupBox(self.tr("main_stat"))
        main_layout = QVBoxLayout(self.grp_main)
        self.main_combo = QComboBox()
        self._populate_main_combo(main_opts)
        main_layout.addWidget(self.main_combo)
        layout.addWidget(self.grp_main)

        # Substat Section
        self.grp_sub = QGroupBox(self.tr("substats"))
        sub_layout = QGridLayout(self.grp_sub)

        for i in range(5):
            row = i // 2
            col = i % 2

            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0, 0, 0, 0)

            stat_combo = QComboBox()
            self._populate_sub_combo(stat_combo, sub_opts)

            val_entry = QLineEdit()
            val_entry.setFixedWidth(60)

            cell_layout.addWidget(stat_combo)
            cell_layout.addWidget(val_entry)

            sub_layout.addWidget(cell_widget, row, col)
            self.sub_entries.append((stat_combo, val_entry))

        layout.addWidget(self.grp_sub)
        layout.addStretch()

    def _populate_main_combo(self, opts: List[str]):
        current = self.main_combo.currentData()
        self.main_combo.blockSignals(True)
        self.main_combo.clear()

        # Default empty item if needed, but usually we just list options
        # Based on TabManager logic, sometimes it adds "---"
        # We will assume opts are raw keys.

        for k in opts:
            self.main_combo.addItem(self.tr(k), userData=k)

        if current:
            idx = self.main_combo.findData(current)
            if idx >= 0:
                self.main_combo.setCurrentIndex(idx)
        self.main_combo.blockSignals(False)

    def _populate_sub_combo(self, combo: QComboBox, opts: List[str]):
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("", userData="")  # Empty option
        for k in opts:
            combo.addItem(self.tr(k), userData=k)

        if current:
            idx = combo.findData(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def set_data(self, main_stat: Optional[str], substats: List[Tuple[str, str]]):
        """Sets the UI values."""
        self.block_signals(True)

        # Main Stat
        if main_stat:
            idx = self.main_combo.findData(main_stat)
            if idx >= 0:
                self.main_combo.setCurrentIndex(idx)
        else:
            self.main_combo.setCurrentIndex(-1)

        # Substats
        # Clear first
        for cb, le in self.sub_entries:
            cb.setCurrentIndex(0)
            le.clear()

        for i, (stat, val) in enumerate(substats):
            if i < len(self.sub_entries):
                cb, le = self.sub_entries[i]
                idx = cb.findData(stat)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
                le.setText(str(val))

        self.block_signals(False)

    def get_data(self) -> Tuple[str, List[SubStat]]:
        """Returns (main_stat, [SubStats])."""
        main = self.main_combo.currentData()
        subs = []
        for cb, le in self.sub_entries:
            k = cb.currentData()
            v = le.text()
            if k and v:
                subs.append(SubStat(k, v))
        return main, subs

    def clear_data(self):
        """Resets inputs."""
        self.block_signals(True)
        self.main_combo.setCurrentIndex(-1)
        for cb, le in self.sub_entries:
            cb.setCurrentIndex(0)
            le.clear()
        self.block_signals(False)

    def is_empty(self) -> bool:
        """Returns True if no data is entered."""
        if self.main_combo.currentIndex() > 0:
            return False
        return not self.has_substats()

    def has_substats(self) -> bool:
        """Returns True if at least one substat has both a type and a value."""
        for cb, le in self.sub_entries:
            if cb.currentIndex() > 0 and le.text().strip():
                return True
        return False

    def block_signals(self, block: bool):
        self.main_combo.blockSignals(block)
        for cb, _ in self.sub_entries:
            cb.blockSignals(block)

    def update_main_options(self, options: List[str], preferred: List[str] = None):
        """Updates main stat options, optionally selecting a preferred one."""
        self.main_combo.blockSignals(True)
        current = self.main_combo.currentData()
        self.main_combo.clear()

        self.main_combo.addItem("---", userData="")
        for k in options:
            self.main_combo.addItem(self.tr(k), userData=k)

        if preferred and preferred[0]:
            # Try to select preferred
            target = preferred[0]
            idx = self.main_combo.findData(target)
            if idx >= 0:
                self.main_combo.setCurrentIndex(idx)
        elif current:
            # Keep current if possible
            idx = self.main_combo.findData(current)
            if idx >= 0:
                self.main_combo.setCurrentIndex(idx)

        self.main_combo.blockSignals(False)

    def retranslate(self):
        self.grp_main.setTitle(self.tr("main_stat"))
        self.grp_sub.setTitle(self.tr("substats"))

        # Refresh combo items text
        self._populate_main_combo(self._main_opts)  # Note: this resets main options to initial list, careful if dynamic
        # Actually Main options are dynamic based on character.
        # So we should probably just re-set the text of existing items?
        # QComboBox item text update is tricky without clearing.
        # Ideally the parent calls `update_main_options` again with the correct list.

        # For sub stats, options are static (all stats)
        for cb, _ in self.sub_entries:
            self._populate_sub_combo(cb, self._sub_opts)
