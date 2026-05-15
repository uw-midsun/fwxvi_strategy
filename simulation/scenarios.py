"""Scenario runners for test and race day simulations.

Date: 2025-11-25
Author: Midnight Sun Team #24 - MSXVI
Group: Strategy_XVI
"""

from __future__ import annotations
import numpy as np
from pathlib import Path
from mock_data import load_mock_csv

from simulation import simulate, VehicleParams, wh_from_joules, SimResult
from optimizer import SLSQP_velocity, exhaustive_search_velocity, OptimizeConfig
from map_visualization import load_gpx_points, compute_segments, AscTrack
from mock_data import load_mock_yaml
from config import SimConfig
from plots import generate_plots

SOLCAST_AVAILABLE = False


def run_test_scenario(
    test_path: str,
    config: SimConfig,
    method: str = "SLSQP",
    log_fn=None,
    iter_log_fn=None,
) -> SimResult:
    """Run a test scenario using mock YAML or CSV data.

    Args:
        test_path: Path to test file (YAML or CSV).
        config: Simulation configuration.
        method: Optimization method ("SLSQP" or "exhaustive").
        log_fn: Optional callback for log messages (e.g. GUI log). Falls back to print.
        iter_log_fn: Optional callback for per-iteration optimizer messages.

    Returns:
        Simulation result.
    """
    log = log_fn or print

    log(f"Loading test scenario: {test_path}")
    if test_path.lower().endswith(".csv"):
        dist_points, theta_deg_arr, ghi_arr = load_mock_csv(test_path)
    else:
        dist_points, theta_deg_arr, ghi_arr = load_mock_yaml(test_path)

    # Build position-based lookup functions directly from distance data
    def theta_fn(d):
        return np.interp(d, dist_points, theta_deg_arr)

    def ghi_fn(d):
        return np.interp(d, dist_points, ghi_arr)

    params = VehicleParams()
    dt = config.dt

    opt_cfg = OptimizeConfig(
        dt=dt,
        horizon=config.horizon,
        d0=0.0,
        vmin=config.vmin,
        vmax=config.vmax,
        method=method,
        max_iter=config.max_iter,
        min_soc=config.min_soc,
    )

    if method == "SLSQP":
        log("Optimizing velocity profile using SLSQP...")
        best_vs, best_obj = SLSQP_velocity(
            opt_cfg, theta_fn, ghi_fn, params, iter_log_fn=iter_log_fn
        )
    else:
        log("Optimizing velocity profile using Exhaustive Search...")
        best_vs, best_obj = exhaustive_search_velocity(
            opt_cfg, theta_fn, ghi_fn, params, iter_log_fn=iter_log_fn
        )

    log(f"Optimization complete. Objective: {best_obj:.2f}")
    log("Simulating...")
    res = simulate(best_vs, dt, 0.0, theta_fn, ghi_fn, params)

    _print_results(res, best_vs, params, log_fn=log)

    return res


def run_raceday_scenario(
    config: SimConfig, method: str = "SLSQP", log_fn=None, iter_log_fn=None
) -> SimResult:
    """Run a race day scenario using GPX data and optionally Solcast.

    Args:
        config: Simulation configuration.
        method: Optimization method ("SLSQP" or "exhaustive").
        log_fn: Optional callback for log messages (e.g. GUI log). Falls back to print.
        iter_log_fn: Optional callback for per-iteration optimizer messages.

    Returns:
        Simulation result.
    """
    log = log_fn or print

    log("Loading race day scenario...")

    # Load GPX data
    data_dir = Path(__file__).parent.parent / "data" / "asc_24_(temp)"
    gpx_path = data_dir / config.gpx_file

    if not gpx_path.exists():
        raise FileNotFoundError(f"GPX file not found: {gpx_path}")

    log(f"Loading GPX: {gpx_path.name}")
    pts = load_gpx_points(str(gpx_path), AscTrack.NashvilleToPaducah)
    dist_m, theta_deg_arr = compute_segments(pts)

    # Get GHI data
    if config.use_solcast and SOLCAST_AVAILABLE and config.solcast_api_key:
        log("Fetching GHI data from Solcast...")
        ghi_arr = np.linspace(700, 900, len(pts))
    else:
        log("Using mock GHI data (Solcast disabled or unavailable)")
        ghi_arr = np.linspace(700, 900, len(pts))

    # Build position-based lookup functions from GPS data
    def theta_fn(d):
        return np.interp(d, dist_m, theta_deg_arr)

    def ghi_fn(d):
        return np.interp(d, dist_m, ghi_arr)

    # Setup simulation
    dt = config.dt
    horizon = config.horizon

    # Use default vehicle params from VehicleParams dataclass
    params = VehicleParams()

    opt_cfg = OptimizeConfig(
        dt=dt,
        horizon=horizon,
        d0=0.0,
        vmin=config.vmin,
        vmax=config.vmax,
        method=method,
        max_iter=config.max_iter,
        min_soc=config.min_soc,
    )

    if method == "SLSQP":
        log("Optimizing velocity profile using SLSQP (may take a while)...")
        best_vs, best_obj = SLSQP_velocity(
            opt_cfg, theta_fn, ghi_fn, params, iter_log_fn=iter_log_fn
        )
    else:
        log("Optimizing velocity profile using Exhaustive Search (may take a while)...")
        best_vs, best_obj = exhaustive_search_velocity(
            opt_cfg, theta_fn, ghi_fn, params, iter_log_fn=iter_log_fn
        )

    log(f"Optimization complete. Objective: {best_obj:.2f}")
    log("Simulating...")
    res = simulate(best_vs, dt, 0.0, theta_fn, ghi_fn, params)

    _print_results(res, best_vs, params, log_fn=log)

    return res


def _print_results(
    res: SimResult, best_vs: np.ndarray, params: VehicleParams, log_fn=None
) -> None:
    """Print formatted simulation results.

    Args:
        res: Simulation result.
        best_vs: Optimized velocity profile.
        params: Vehicle parameters.
        log_fn: Optional callback for log messages. Falls back to print.
    """
    log = log_fn or print
    log(f"{'-' * 50}")
    log("Simulation Results")
    log(f"{'-' * 50}")
    log(f"Final distance:        {res.final_distance_m / 1000:.2f} km")
    log(f"Final SOC:             {wh_from_joules(res.final_soc_J):.2f} Wh")
    log(f"Initial battery:       {wh_from_joules(params.bat_max_energy):.2f} Wh")
    log(
        f"Energy consumed:       {wh_from_joules(params.bat_max_energy - res.final_soc_J):.2f} Wh"
    )
    log(
        f"Average speed:         {np.mean(best_vs):.2f} m/s ({np.mean(best_vs) * 3.6:.2f} km/h)"
    )
    log(f"Min speed:             {np.min(best_vs):.2f} m/s")
    log(f"Max speed:             {np.max(best_vs):.2f} m/s")
    log(f"Number of steps:       {len(best_vs)}")
    log(f"{'-' * 50}")
