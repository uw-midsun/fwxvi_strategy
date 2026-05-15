"""PyQt5 GUI for FWXVI Strategy Testing Suite.

Date: 2026-04-01
Author: Midnight Sun Team #24 - MSXVI
Group: Strategy_XVI
"""

import sys
import os
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
    QTextEdit,
    QTabWidget,
    QFileDialog,
    QSplitter,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

import matplotlib

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from config import SimConfig
from simulation import VehicleParams, wh_from_joules
from scenarios import run_test_scenario, run_raceday_scenario
from plots import generate_plots


class SimulationWorker(QThread):
    """Runs a simulation scenario in a background thread."""

    log_signal = pyqtSignal(str)
    iter_signal = pyqtSignal(str)  # per-iteration optimizer output
    finished_signal = pyqtSignal(object)  # SimResult or None
    error_signal = pyqtSignal(str)

    def __init__(self, scenario, config, method, test_path=None):
        super().__init__()
        self.scenario = scenario  # "test" or "raceday"
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

        self._build_ui()

    # UI construction 
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)

        # Left panel: config + controls
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self._build_config_group())
        left_layout.addWidget(self._build_scenario_group())
        left_layout.addWidget(self._build_run_group())
        left_layout.addStretch()

        # Right panel: plots + log
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

        self.dt_edit = QLineEdit(str(self.config.dt))
        self.horizon_edit = QLineEdit(str(self.config.horizon))
        self.vmin_edit = QLineEdit(str(self.config.vmin))
        self.vmax_edit = QLineEdit(str(self.config.vmax))
        self.max_iter_edit = QLineEdit(str(self.config.max_iter))
        self.min_soc_edit = QLineEdit(str(self.config.min_soc))
        self.solcast_check = QCheckBox()
        self.solcast_check.setChecked(self.config.use_solcast)

        form.addRow("Timestep (s):", self.dt_edit)
        form.addRow("Horizon (s):", self.horizon_edit)
        form.addRow("V min (m/s):", self.vmin_edit)
        form.addRow("V max (m/s):", self.vmax_edit)
        form.addRow("Max iterations:", self.max_iter_edit)
        form.addRow("Min SOC fraction:", self.min_soc_edit)
        form.addRow("Use Solcast:", self.solcast_check)

        return grp

    # Scenario panel 
    def _build_scenario_group(self) -> QGroupBox:
        grp = QGroupBox("Scenario")
        layout = QVBoxLayout(grp)

        # Scenario type
        self.scenario_tabs = QTabWidget()

        # Test scenario tab
        test_tab = QWidget()
        test_layout = QVBoxLayout(test_tab)
        self.test_file_combo = QComboBox()
        self._populate_test_files()
        test_layout.addWidget(QLabel("Test file:"))
        test_layout.addWidget(self.test_file_combo)
        test_layout.addStretch()
        self.scenario_tabs.addTab(test_tab, "Test (CSV/YAML)")

        # Race day tab
        race_tab = QWidget()
        race_layout = QVBoxLayout(race_tab)
        self.gpx_combo = QComboBox()
        self._populate_gpx_files()
        race_layout.addWidget(QLabel("GPX file:"))
        race_layout.addWidget(self.gpx_combo)
        race_layout.addStretch()
        self.scenario_tabs.addTab(race_tab, "Race Day (GPX)")

        layout.addWidget(self.scenario_tabs)

        # Optimization method (shared)
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
        layout = QHBoxLayout(grp)

        self.run_btn = QPushButton("Run Optimization")
        self.run_btn.setMinimumHeight(36)
        self.run_btn.clicked.connect(self._on_run)
        layout.addWidget(self.run_btn)

        return grp

    # Plot area 
    def _build_plot_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(9, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, container)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        return container

    # Log area (Results / Iterations) 
    def _build_log_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.log_tabs = QTabWidget()

        # Results tab (high-level status messages)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.log_tabs.addTab(self.results_text, "Results")

        # Iterations tab (per-iteration output)
        self.iter_text = QTextEdit()
        self.iter_text.setReadOnly(True)
        self.iter_text.setFontFamily("Consolas")
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

    def _log(self, msg: str):
        self.results_text.append(msg)

    def _iter_log(self, msg: str):
        self.iter_text.append(msg)
        # Auto-switch to iterations tab on first iteration message
        if self.log_tabs.currentIndex() != 1:
            self.log_tabs.setCurrentIndex(1)

    #  Run handler 
    def _on_run(self):
        if self.worker and self.worker.isRunning():
            self._log("Simulation already running...")
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

        self.run_btn.setEnabled(False)
        self.run_btn.setText("Running...")
        self.results_text.clear()
        self.iter_text.clear()
        self.log_tabs.setCurrentIndex(1)  # Show Iterations tab while running

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

    def _on_finished(self, res):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Optimization")
        self.last_result = res
        self.log_tabs.setCurrentIndex(0)  # Switch to Results tab

        if res is None:
            self._log("No result returned.")
            return

        # Draw plots
        self.figure.clear()
        params = VehicleParams()
        dist_km = res.traces["distance_m"] / 1000
        soc_wh = wh_from_joules(res.traces["Ebat_J"])
        bat_max_wh = wh_from_joules(params.bat_max_energy)

        v = res.traces["v"]
        n = min(len(dist_km), len(v), len(soc_wh))
        dist_km = dist_km[:n]
        v = v[:n]
        soc_wh = soc_wh[:n]

        ax1 = self.figure.add_subplot(2, 1, 1)
        ax1.step(dist_km, v, where="post", linewidth=1.5)
        ax1.plot(dist_km, v, "o", markersize=4)
        ax1.set_ylabel("Speed (m/s)")
        ax1.grid(True, alpha=0.3)

        ax2 = self.figure.add_subplot(2, 1, 2, sharex=ax1)
        ax2.plot(dist_km, soc_wh, marker="o", markersize=4, label="Battery SOC")
        threshold_wh = self.config.min_soc * bat_max_wh
        ax2.axhline(
            y=threshold_wh,
            color="r",
            linestyle="--",
            linewidth=1.5,
            label=f"{self.config.min_soc * 100:.0f}% minimum",
        )
        ax2.legend()
        ax2.set_ylabel("Battery (Wh)")
        ax2.set_xlabel("Distance (km)")
        ax2.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw()

    def _on_error(self, msg):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Run Optimization")
        self._log(f"ERROR: {msg}")

# Entry point
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
