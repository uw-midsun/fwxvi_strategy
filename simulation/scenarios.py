## @file    scenarios.py
#  @date    2025-11-25
#  @author  Midnight Sun Team #24 - MSXVI
#  @brief   Scenario runners for test and race day simulations
#  @ingroup Strategy_XVI

from __future__ import annotations
import os
import numpy as np
from pathlib import Path
from typing import Tuple, Optional

from simulation import simulate, VehicleParams, wh_from_joules, SimResult
from optimizer import optimize_velocity, OptimizeConfig
from map_visualization import load_gpx_points, compute_segments, AscTrack
from mock_data import load_mock_yaml
from config import SimConfig
from plots import generate_plots

SOLCAST_AVAILABLE = False


def run_test_scenario(yaml_path: str, config: SimConfig) -> SimResult:
    """
    @brief  Run a test scenario using mock YAML data
    @param  yaml_path Path to YAML test file
    @param  config Simulation configuration
    @return Simulation result
    """
    print(f"\nLoading test scenario: {yaml_path}")
    theta_deg, ghi, meta = load_mock_yaml(yaml_path)
    
    dt = meta.get("dt", config.dt)
    d0 = meta.get("d0", 0.0)
    N_steps = theta_deg.size
    horizon = N_steps * dt
    
    params = VehicleParams()
    
    # Build optimizer config
    opt_cfg = OptimizeConfig(
        dt=dt,
        horizon=horizon,
        d0=d0,
        vmin=config.vmin,
        vmax=config.vmax,
        method=config.method,
        max_iter=config.max_iter,
        energy_penalty=config.energy_penalty,
    )
    
    print("Optimizing velocity profile...")
    best_vs, best_obj = optimize_velocity(opt_cfg, theta_deg, ghi, params)
    print(f"Optimization complete. Objective: {best_obj:.2f}")
    
    print("Simulating...")
    res = simulate(best_vs, dt, d0, theta_deg, ghi, params)
    
    _print_results(res, best_vs, params)
    
    # Ask if user wants to see plots
    plot_choice = input("\nGenerate plots? (y/n): ").strip().lower()
    if plot_choice in ('y', 'yes'):
        dist_km = res.traces["distance_m"] / 1000
        soc_wh = wh_from_joules(res.traces["Ebat_J"])
        generate_plots(dist_km, res, soc_wh)
    
    return res


def run_raceday_scenario(config: SimConfig) -> SimResult:
    """
    @brief  Run a race day scenario using GPX data and optionally Solcast
    @param  config Simulation configuration
    @return Simulation result
    """
    print(f"\nLoading race day scenario...")
    
    # Load GPX data
    data_dir = Path(__file__).parent.parent / "data" / "asc_24_(temp)"
    gpx_path = data_dir / config.gpx_file
    
    if not gpx_path.exists():
        raise FileNotFoundError(f"GPX file not found: {gpx_path}")
    
    print(f"Loading GPX: {gpx_path.name}")
    pts = load_gpx_points(str(gpx_path), AscTrack.NashvilleToPaducah)
    dist_m, theta_deg = compute_segments(pts)
    N_gps = len(pts)
    
    # Get GHI data
    if config.use_solcast and SOLCAST_AVAILABLE and config.solcast_api_key:
        print("Fetching GHI data from Solcast...")
        # TODO
    else:
        print("Using mock GHI data (Solcast disabled or unavailable)")
        ghi = np.linspace(700, 900, N_gps)
    
    # Setup simulation
    dt = config.dt
    N_steps = N_gps
    horizon = N_steps * dt
    
    # Use default vehicle params from VehicleParams dataclass
    params = VehicleParams()
    
    opt_cfg = OptimizeConfig(
        dt=dt,
        horizon=horizon,
        d0=0.0,
        vmin=config.vmin,
        vmax=config.vmax,
        method=config.method,
        max_iter=config.max_iter,
        energy_penalty=config.energy_penalty,
    )
    
    print("Optimizing velocity profile (may take a while)...")
    best_vs, best_obj = optimize_velocity(opt_cfg, theta_deg, ghi, params)
    print(f"Optimization complete. Objective: {best_obj:.2f}")
    
    print("Simulating...")
    res = simulate(best_vs, dt, 0.0, theta_deg, ghi, params)
    
    _print_results(res, best_vs, params)
    
    # Ask if user wants to see plots
    plot_choice = input("\nGenerate plots? (y/n): ").strip().lower()
    if plot_choice in ('y', 'yes'):
        dist_km = res.traces["distance_m"] / 1000
        soc_wh = wh_from_joules(res.traces["Ebat_J"])
        generate_plots(dist_km, res, soc_wh)
    
    return res


def _print_results(res: SimResult, best_vs: np.ndarray, params: VehicleParams) -> None:
    """
    @brief  Print formatted simulation results
    @param  res Simulation result
    @param  best_vs Optimized velocity profile
    @param  params Vehicle parameters
    """
    print(f"\n{'-'*50}")
    print("Simulation Results")
    print(f"{'-'*50}")
    print(f"Final distance:        {res.final_distance_m/1000:.2f} km")
    print(f"Final SOC:             {wh_from_joules(res.final_soc_J):.2f} Wh")
    print(f"Initial battery:       {wh_from_joules(params.bat_max_energy):.2f} Wh")
    print(f"Energy consumed:       {wh_from_joules(params.bat_max_energy - res.final_soc_J):.2f} Wh")
    print(f"Average speed:         {np.mean(best_vs):.2f} m/s ({np.mean(best_vs)*3.6:.2f} km/h)")
    print(f"Min speed:             {np.min(best_vs):.2f} m/s")
    print(f"Max speed:             {np.max(best_vs):.2f} m/s")
    print(f"Number of steps:       {len(best_vs)}")
    print(f"{'-'*50}\n")
