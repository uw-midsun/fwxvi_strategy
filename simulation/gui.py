"""PyQt5 GUI for FWXVI Strategy Testing Suite.

Date: 2026-04-01
Author: Midnight Sun Team #24 - MSXVI
Group: Strategy_XVI
"""

import ctypes
import re
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QToolButton,
    QTextEdit,
    QTabWidget,
    QSplitter,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon, QPainter, QPixmap

import matplotlib

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from config import SimConfig
from simulation import VehicleParams, wh_from_joules
from scenarios import run_test_scenario, run_raceday_scenario

# Theme definitions
_DARK_PLOT = {
    "fig_bg": "#2b2b2b",
    "ax_bg": "#1e1e1e",
    "text": "#dcdcdc",
    "grid": "#4a4a4a",
    "speed_line": "#5b9bd5",
    "soc_line": "#70b870",
    "threshold": "#e06c75",
    "iter_label": "color: #aaa; font-size: 11px;",
}
_LIGHT_PLOT = {
    "fig_bg": "white",
    "ax_bg": "white",
    "text": "black",
    "grid": "#cccccc",
    "speed_line": "#1f77b4",
    "soc_line": "#2ca02c",
    "threshold": "red",
    "iter_label": "color: #555; font-size: 11px;",
}

_DARK_QSS = """
QWidget {
    background-color: #2b2b2b;
    color: #dcdcdc;
}
QGroupBox {
    border: 1px solid #555;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 4px;
    color: #dcdcdc;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    color: #bbb;
}
QLineEdit {
    background-color: #3c3f41;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 2px 4px;
    color: #dcdcdc;
}
QLineEdit:focus {
    border: 1px solid #4a9eff;
}
QComboBox {
    background-color: #3c3f41;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 2px 4px;
    color: #dcdcdc;
}
QComboBox QAbstractItemView {
    background-color: #3c3f41;
    border: 1px solid #555;
    color: #dcdcdc;
    selection-background-color: #4a9eff;
    selection-color: #000;
}
QPushButton {
    background-color: #3c3f41;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 4px 12px;
    color: #dcdcdc;
}
QPushButton:hover {
    background-color: #4c5052;
    border-color: #777;
}
QPushButton:pressed {
    background-color: #2b2b2b;
}
QPushButton:disabled {
    color: #666;
    background-color: #333;
    border-color: #444;
}
QTabWidget::pane {
    border: 1px solid #555;
}
QTabBar::tab {
    background-color: #3c3f41;
    border: 1px solid #555;
    padding: 4px 12px;
    color: #aaa;
}
QTabBar::tab:selected {
    background-color: #2b2b2b;
    color: #dcdcdc;
    border-bottom-color: #2b2b2b;
}
QTextEdit {
    background-color: #1e1e1e;
    border: 1px solid #555;
    color: #dcdcdc;
    padding: 6px;
}
QCheckBox {
    color: #dcdcdc;
    background: transparent;
}
QCheckBox::indicator {
    border: 1px solid #555;
    background-color: #3c3f41;
    width: 13px;
    height: 13px;
}
QCheckBox::indicator:checked {
    background-color: #4a9eff;
    border-color: #4a9eff;
}
QLabel {
    background: transparent;
    color: #dcdcdc;
}
QSplitter::handle {
    background-color: #444;
}
QScrollBar:vertical {
    background-color: #2b2b2b;
    width: 12px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #555;
    border-radius: 6px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QMenuBar {
    background-color: #2b2b2b;
    color: #dcdcdc;
    border-bottom: 1px solid #444;
}
QMenuBar::item:selected {
    background-color: #3c3f41;
}
QMenu {
    background-color: #3c3f41;
    border: 1px solid #555;
    color: #dcdcdc;
}
QMenu::item:selected {
    background-color: #4a9eff;
    color: #000;
}
QMenu::indicator {
    width: 13px;
    height: 13px;
}
"""


class SimulationWorker(QThread):
    """Runs a simulation scenario in a background thread."""

    log_signal = pyqtSignal(str)
    iter_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self, scenario, config, method, test_path=None):
        super().__init__()
        self.scenario = scenario
        self.config = config
        self.method = method
        self.test_path = test_path

    def run(self):
        try:
            if self.scenario == "test":
                res = run_test_scenario(
                    self.test_path,
                    self.config,
                    method=self.method,
                    log_fn=self.log_signal.emit,
                    iter_log_fn=self.iter_signal.emit,
                )
            else:
                res = run_raceday_scenario(
                    self.config,
                    method=self.method,
                    log_fn=self.log_signal.emit,
                    iter_log_fn=self.iter_signal.emit,
                )
            self.finished_signal.emit(res)
        except Exception as e:
            self.error_signal.emit(str(e))


# Main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FWXVI Strategy Testing Suite")
        self.setMinimumSize(1100, 750)

        self.config = SimConfig()
        self.worker = None
        self.last_result = None
        self._dark_mode = False

        self._build_ui()
        self._apply_theme(dark=False)

    # UI construction
    def _build_ui(self):
        self.menuBar().hide()

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self._build_config_group())
        left_layout.addWidget(self._build_scenario_group())
        left_layout.addWidget(self._build_run_group())
        left_layout.addStretch()

        right = QSplitter(Qt.Vertical)
        right.addWidget(self._build_plot_area())
        right.addWidget(self._build_log_area())
        right.setStretchFactor(0, 3)
        right.setStretchFactor(1, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 760])

        root_layout.addWidget(splitter)

    # Config panel
    def _build_config_group(self) -> QGroupBox:
        grp = QGroupBox("Configuration")
        form = QFormLayout(grp)
        form.setVerticalSpacing(6)

        self.dt_edit = QLineEdit(str(self.config.dt))
        self.horizon_edit = QLineEdit(str(self.config.horizon))
        form.addRow("Timestep (s):", self.dt_edit)
        form.addRow("Horizon (s):", self.horizon_edit)

        # Vmin / Vmax on one row
        v_row = QHBoxLayout()
        self.vmin_edit = QLineEdit(str(self.config.vmin))
        self.vmax_edit = QLineEdit(str(self.config.vmax))
        v_row.addWidget(QLabel("Min:"))
        v_row.addWidget(self.vmin_edit)
        v_row.addSpacing(8)
        v_row.addWidget(QLabel("Max:"))
        v_row.addWidget(self.vmax_edit)
        form.addRow("Speed (m/s):", v_row)

        # Max iterations / Min SOC on one row
        opt_row = QHBoxLayout()
        self.max_iter_edit = QLineEdit(str(self.config.max_iter))
        self.min_soc_edit = QLineEdit(str(self.config.min_soc))
        opt_row.addWidget(QLabel("Iter:"))
        opt_row.addWidget(self.max_iter_edit)
        opt_row.addSpacing(8)
        opt_row.addWidget(QLabel("Min SOC:"))
        opt_row.addWidget(self.min_soc_edit)
        form.addRow("Optimizer:", opt_row)

        self.solcast_check = QCheckBox()
        self.solcast_check.setChecked(self.config.use_solcast)
        form.addRow("Use Solcast:", self.solcast_check)

        return grp

    # Scenario panel
    def _build_scenario_group(self) -> QGroupBox:
        grp = QGroupBox("Scenario")
        layout = QVBoxLayout(grp)

        self.scenario_tabs = QTabWidget()

        test_tab = QWidget()
        test_layout = QVBoxLayout(test_tab)
        self.test_file_combo = QComboBox()
        self._populate_test_files()
        test_layout.addWidget(QLabel("Test file:"))
        test_layout.addWidget(self.test_file_combo)
        test_layout.addStretch()
        self.scenario_tabs.addTab(test_tab, "Test (CSV/YAML)")

        race_tab = QWidget()
        race_layout = QVBoxLayout(race_tab)
        self.gpx_combo = QComboBox()
        self._populate_gpx_files()
        race_layout.addWidget(QLabel("GPX file:"))
        race_layout.addWidget(self.gpx_combo)
        race_layout.addStretch()
        self.scenario_tabs.addTab(race_tab, "Race Day (GPX)")

        layout.addWidget(self.scenario_tabs)

        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Method:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["SLSQP", "Exhaustive"])
        method_row.addWidget(self.method_combo)
        layout.addLayout(method_row)

        return grp

    # Run button
    def _build_run_group(self) -> QGroupBox:
        grp = QGroupBox("Actions")
        layout = QVBoxLayout(grp)

        btn_row = QHBoxLayout()

        self.run_btn = QPushButton("Run Optimization")
        self.run_btn.setMinimumHeight(36)
        self.run_btn.clicked.connect(self._on_run)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setMinimumHeight(36)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(
            "QPushButton:enabled { color: #c0392b; font-weight: bold; }"
        )
        self.stop_btn.clicked.connect(self._on_stop)

        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.stop_btn)
        layout.addLayout(btn_row)

        self.iter_label = QLabel("")
        self.iter_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.iter_label)

        return grp

    # Plot area
    def _build_plot_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(9, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, container)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        self.theme_btn = QToolButton()
        self.theme_btn.setText("☽")
        self.theme_btn.setToolTip("Switch to dark mode")
        self.theme_btn.setAutoRaise(True)
        self.theme_btn.setFont(QFont("Segoe UI", 14))
        self.theme_btn.setFixedSize(40, 40)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.toolbar.addWidget(self.theme_btn)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        return container

    # Log area (Results / Iterations)
    def _build_log_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.log_tabs = QTabWidget()

        log_font = QFont("Consolas", 9)
        log_style = "QTextEdit { padding: 6px; }"

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(log_font)
        self.results_text.setStyleSheet(log_style)
        self.log_tabs.addTab(self.results_text, "Results")

        self.iter_text = QTextEdit()
        self.iter_text.setReadOnly(True)
        self.iter_text.setFont(log_font)
        self.iter_text.setStyleSheet(log_style)
        self.log_tabs.addTab(self.iter_text, "Iterations")

        layout.addWidget(self.log_tabs)
        return container

    # Helpers
    def _populate_test_files(self):
        test_dir = Path(__file__).parent.parent / "test"
        files = sorted(test_dir.glob("*.csv")) + sorted(test_dir.glob("*.yaml"))
        for f in files:
            self.test_file_combo.addItem(f.name, str(f))

    def _populate_gpx_files(self):
        gpx_dir = Path(__file__).parent.parent / "data" / "asc_24_(temp)"
        files = sorted(gpx_dir.glob("*.gpx"))
        for f in files:
            self.gpx_combo.addItem(f.name, f.name)

    def _apply_config(self):
        """Read GUI fields back into the SimConfig."""
        self.config.dt = float(self.dt_edit.text())
        self.config.horizon = float(self.horizon_edit.text())
        self.config.vmin = float(self.vmin_edit.text())
        self.config.vmax = float(self.vmax_edit.text())
        self.config.max_iter = int(self.max_iter_edit.text())
        self.config.min_soc = float(self.min_soc_edit.text())
        self.config.use_solcast = self.solcast_check.isChecked()
        self.config.gpx_file = self.gpx_combo.currentData() or self.config.gpx_file

    def _toggle_theme(self):
        self._apply_theme(dark=not self._dark_mode)

    def _invert_toolbar_icons(self, dark: bool):
        size = self.toolbar.iconSize()
        for action in self.toolbar.actions():
            icon = action.icon()
            if icon.isNull():
                continue
            if not hasattr(action, "_original_icon"):
                action._original_icon = icon
            if dark:
                src = action._original_icon.pixmap(size)
                result = QPixmap(src.size())
                result.fill(Qt.transparent)
                painter = QPainter(result)
                painter.drawPixmap(0, 0, src)
                painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
                painter.fillRect(result.rect(), QColor("#dcdcdc"))
                painter.end()
                action.setIcon(QIcon(result))
            else:
                action.setIcon(action._original_icon)

    def _set_titlebar_dark(self, dark: bool):
        try:
            hwnd = int(self.winId())
            value = ctypes.c_int(1 if dark else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception:
            pass

    def _apply_theme(self, dark: bool):
        self._dark_mode = dark
        app = QApplication.instance()
        app.setStyleSheet(_DARK_QSS if dark else "")

        colors = _DARK_PLOT if dark else _LIGHT_PLOT
        self.iter_label.setStyleSheet(colors["iter_label"])

        # Title bar
        self._set_titlebar_dark(dark)

        # Theme toggle button
        if dark:
            self.theme_btn.setText("☼")
            self.theme_btn.setToolTip("Switch to light mode")
        else:
            self.theme_btn.setText("☽")
            self.theme_btn.setToolTip("Switch to dark mode")

        # Matplotlib toolbar icons
        self._invert_toolbar_icons(dark)

        # Always update figure background (even before a result is drawn)
        self.figure.patch.set_facecolor(colors["fig_bg"])
        self.canvas.setStyleSheet(f"background-color: {colors['fig_bg']};")
        self.canvas.draw()

        if self.last_result is not None:
            self._redraw_plots(self.last_result)

    def _set_running(self, running: bool):
        self.run_btn.setEnabled(not running)
        self.run_btn.setText("Running..." if running else "Run Optimization")
        self.stop_btn.setEnabled(running)
        if not running:
            self.iter_label.setText("")

    def _log(self, msg: str):
        stripped = msg.strip()
        if stripped and all(c == "-" for c in stripped) and len(stripped) > 5:
            self.results_text.append(
                '<span style="color: #aaa;">──────────────────────────────────────────────────</span>'
            )
        elif stripped == "Simulation Results":
            self.results_text.append(f"<b>{stripped}</b>")
        else:
            self.results_text.append(msg)

    def _iter_log(self, msg: str):
        self.iter_text.append(msg)
        m = re.search(r"Iter\s+(\d+)", msg)
        if m:
            self.iter_label.setText(f"Iter {int(m.group(1))} / {self.config.max_iter}")
        if self.log_tabs.currentIndex() != 1:
            self.log_tabs.setCurrentIndex(1)

    def _redraw_plots(self, res):
        colors = _DARK_PLOT if self._dark_mode else _LIGHT_PLOT

        params = VehicleParams()
        dist_km = res.traces["distance_m"] / 1000
        soc_wh = wh_from_joules(res.traces["Ebat_J"])
        bat_max_wh = wh_from_joules(params.bat_max_energy)

        v = res.traces["v"]
        n = min(len(dist_km), len(v), len(soc_wh))
        dist_km = dist_km[:n]
        v = v[:n]
        soc_wh = soc_wh[:n]

        self.figure.clear()
        self.figure.patch.set_facecolor(colors["fig_bg"])

        ax1 = self.figure.add_subplot(2, 1, 1)
        ax1.set_facecolor(colors["ax_bg"])
        ax1.set_title("Optimized Velocity Profile", color=colors["text"])
        ax1.step(dist_km, v, where="post", linewidth=1.5, color=colors["speed_line"])
        ax1.plot(dist_km, v, "o", markersize=4, color=colors["speed_line"])
        ax1.set_ylabel("Speed (m/s)", color=colors["text"])
        ax1.tick_params(colors=colors["text"])
        ax1.grid(True, alpha=0.3, color=colors["grid"])
        for spine in ax1.spines.values():
            spine.set_edgecolor(colors["grid"])

        ax2 = self.figure.add_subplot(2, 1, 2, sharex=ax1)
        ax2.set_facecolor(colors["ax_bg"])
        ax2.set_title("Battery State of Charge", color=colors["text"])
        ax2.plot(
            dist_km,
            soc_wh,
            marker="o",
            markersize=4,
            label="Battery SOC",
            color=colors["soc_line"],
        )
        threshold_wh = self.config.min_soc * bat_max_wh
        ax2.axhline(
            y=threshold_wh,
            color=colors["threshold"],
            linestyle="--",
            linewidth=1.5,
            label=f"{self.config.min_soc * 100:.0f}% minimum",
        )
        ax2.legend(facecolor=colors["ax_bg"], labelcolor=colors["text"])
        ax2.set_ylabel("Battery (Wh)", color=colors["text"])
        ax2.set_xlabel("Distance (km)", color=colors["text"])
        ax2.tick_params(colors=colors["text"])
        ax2.grid(True, alpha=0.3, color=colors["grid"])
        for spine in ax2.spines.values():
            spine.set_edgecolor(colors["grid"])

        self.figure.tight_layout()
        self.canvas.draw()

    # Run handler
    def _on_run(self):
        if self.worker and self.worker.isRunning():
            return

        try:
            self._apply_config()
        except ValueError as e:
            self._log(f"Invalid config value: {e}")
            return

        method_map = {"SLSQP": "SLSQP", "Exhaustive": "exhaustive"}
        method = method_map[self.method_combo.currentText()]

        is_test = self.scenario_tabs.currentIndex() == 0
        test_path = self.test_file_combo.currentData() if is_test else None

        self._set_running(True)
        self.results_text.clear()
        self.iter_text.clear()
        self.log_tabs.setCurrentIndex(1)

        self.worker = SimulationWorker(
            scenario="test" if is_test else "raceday",
            config=self.config,
            method=method,
            test_path=test_path,
        )
        self.worker.log_signal.connect(self._log)
        self.worker.iter_signal.connect(self._iter_log)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _on_stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self._log("Optimization stopped by user.")
        self._set_running(False)

    def _on_finished(self, res):
        self._set_running(False)
        self.last_result = res
        self.log_tabs.setCurrentIndex(0)

        if res is None:
            self._log("No result returned.")
            return

        self._redraw_plots(res)

    def _on_error(self, msg):
        self._set_running(False)
        self._log(f"ERROR: {msg}")


# Entry point
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
