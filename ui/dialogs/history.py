from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QLabel,
    QPushButton,
    QDateEdit,
    QFrame,
    QComboBox,
    QCheckBox,
)
from PySide6.QtCore import QDate


class HistoryDialog(QDialog):
    """Dialog for viewing application history with character and cost filters."""

    def __init__(self, parent, history_mgr):
        super().__init__(parent)
        self.app = parent
        self.history_mgr = history_mgr

        self.setWindowTitle(self.app.tr("history_title") if hasattr(self.app, "tr") else "History")
        self.resize(900, 600)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Filter Area
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)

        # Keyword
        filter_layout.addWidget(QLabel(self.app.tr("history_search")))
        self.kw_input = QLineEdit()
        self.kw_input.setPlaceholderText("Action, Result, Character...")
        self.kw_input.textChanged.connect(self.load_data)
        filter_layout.addWidget(self.kw_input)

        # Character Filter
        filter_layout.addWidget(QLabel(self.app.tr("history_char")))
        self.char_filter = QComboBox()
        self.char_filter.addItem("All", "")
        # Get all unique characters in history
        chars = sorted(list(set(h.character for h in self.history_mgr._history if h.character)))
        for c in chars:
            jp_name = self.app.character_manager.get_display_name(c)
            display_text = f"{jp_name} ({c})" if jp_name != c else c
            self.char_filter.addItem(display_text, c)
        self.char_filter.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.char_filter)

        # Cost Filter
        filter_layout.addWidget(QLabel(self.app.tr("history_cost")))
        self.cost_filter = QComboBox()
        self.cost_filter.addItems(["All", "4", "3", "1"])
        self.cost_filter.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.cost_filter)

        # Rating Filter
        filter_layout.addWidget(QLabel(self.app.tr("history_rating")))
        self.rating_filter = QComboBox()
        self.rating_filter.addItems(["All", "SSS", "SS", "S", "A", "B", "C"])
        self.rating_filter.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.rating_filter)

        # Date Filters
        self.date_filter_cb = QCheckBox(self.app.tr("history_filter_date"))
        self.date_filter_cb.setChecked(False)
        self.date_filter_cb.stateChanged.connect(self.load_data)
        filter_layout.addWidget(self.date_filter_cb)

        filter_layout.addWidget(QLabel(self.app.tr("history_from")))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.dateChanged.connect(self.load_data)
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel(self.app.tr("history_to")))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self.load_data)
        filter_layout.addWidget(self.date_to)

        btn_reset = QPushButton(self.app.tr("history_reset"))
        btn_reset.clicked.connect(self.reset_filters)
        filter_layout.addWidget(btn_reset)

        layout.addWidget(filter_frame)

        # Stats Area
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        layout.addWidget(self.stats_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [
                self.app.tr("history_col_time"),
                self.app.tr("history_col_char"),
                self.app.tr("history_col_cost"),
                self.app.tr("history_col_action"),
                self.app.tr("history_col_result"),
            ]
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # Bottom Buttons
        btn_layout = QHBoxLayout()

        # Duplicate Setting (Left side)
        dup_layout = QHBoxLayout()
        dup_layout.addWidget(QLabel(self.app.tr("history_duplicate_mode")))

        self.combo_history_dup = QComboBox()
        self.dup_mode_map = {
            self.app.tr("history_dup_all"): "all",
            self.app.tr("history_dup_latest"): "latest",
            self.app.tr("history_dup_oldest"): "oldest",
        }
        self.dup_mode_map_inv = {v: k for k, v in self.dup_mode_map.items()}

        self.combo_history_dup.addItems(list(self.dup_mode_map.keys()))
        current_mode = self.app.app_config.history_duplicate_mode
        if current_mode in self.dup_mode_map_inv:
            self.combo_history_dup.setCurrentText(self.dup_mode_map_inv[current_mode])

        self.combo_history_dup.setToolTip(self.app.tr("history_duplicate_tooltip"))
        self.combo_history_dup.currentTextChanged.connect(self._update_history_dup_mode)

        dup_layout.addWidget(self.combo_history_dup)
        btn_layout.addLayout(dup_layout)

        btn_layout.addStretch()

        btn_clear = QPushButton(self.app.tr("history_clear"))
        btn_clear.clicked.connect(self.clear_history)
        btn_close = QPushButton(self.app.tr("close"))
        btn_close.clicked.connect(self.accept)

        btn_layout.addWidget(btn_clear)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _update_history_dup_mode(self, text):
        if text in self.dup_mode_map:
            new_mode = self.dup_mode_map[text]
            self.app.app_config.history_duplicate_mode = new_mode
            self.app.config_manager.save()

    def load_data(self):
        kw = self.kw_input.text()
        char = self.char_filter.currentData()
        cost = self.cost_filter.currentText()
        if cost == "All":
            cost = ""

        rating = self.rating_filter.currentText()
        if rating == "All":
            rating = ""

        d_from = ""
        d_to = ""
        if self.date_filter_cb.isChecked():
            d_from = self.date_from.date().toString("yyyy-MM-dd")
            d_to = self.date_to.date().toString("yyyy-MM-dd")

        # Pass name map for bilingual search
        name_map = self.app.character_manager._name_map_en_to_jp
        entries = self.history_mgr.get_entries(kw, char, cost, d_from, d_to, name_map=name_map, rating=rating)

        self.table.setRowCount(0)
        scores = []
        for i, h in enumerate(entries):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(h.timestamp))

            jp_name = self.app.character_manager.get_display_name(h.character)
            char_display = f"{jp_name} ({h.character})" if jp_name != h.character else h.character
            self.table.setItem(i, 1, QTableWidgetItem(char_display))

            self.table.setItem(i, 2, QTableWidgetItem(h.cost))
            self.table.setItem(i, 3, QTableWidgetItem(h.action))
            self.table.setItem(i, 4, QTableWidgetItem(h.result))

            # Extract score for stats
            score = h.details.get("score")
            if score is None:
                # Try to parse from result string "Score: 85.50 ..."
                try:
                    if "Score:" in h.result:
                        parts = h.result.split("Score:")[1].strip().split(" ")
                        score = float(parts[0])
                except (ValueError, IndexError):
                    pass

            if score is not None:
                scores.append(score)

        # Update stats label
        if scores:
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            self.stats_label.setText(self.app.tr("history_stats").format(len(scores), avg_score, max_score))
        else:
            self.stats_label.setText(self.app.tr("history_no_data"))

    def reset_filters(self):
        self.kw_input.clear()
        self.char_filter.setCurrentIndex(0)
        self.cost_filter.setCurrentIndex(0)
        self.rating_filter.setCurrentIndex(0)
        self.date_filter_cb.setChecked(False)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        self.load_data()

    def clear_history(self):
        self.history_mgr.clear()
        self.load_data()
