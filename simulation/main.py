## @file    main.py
#  @date    2025-11-09
#  @author  Midnight Sun Team #24 - MSXVI
#  @brief   Main file for strategy XVI
#  @ingroup Strategy_XVI

# TODO Either add to existing doxygen documentation or make a new one or no doxygen documentation 😨

import numpy as np
import matplotlib.pyplot as plt

from simulation import simulate, VehicleParams, wh_from_joules
from optimizer import optimize_velocity, OptimizeConfig
from map_visualization import load_gpx_points, compute_segments, export_grafana_json, AscTrack
from pathlib import Path

GPX_PATH = Path(__file__).parent.parent / "data" / "asc_24_(temp)" / "0_FullBaseRoute.gpx"
OPTIMIZATION_TIMESTEP = 1800    # seconds (30 minutes per step)
MIN_SPEED_MPS = 10.0            # m/s minimum safe speed
MAX_SPEED_MPS = 30.0            # m/s maximum allowable speed
MAX_ITERATIONS = 2000           # optimization iteration limit
OPTIMIZATION_METHOD = "Powell"  # scipy optimization method

if __name__ == "__main__":
    print("Loading GPX points...")
    pts = load_gpx_points(str(GPX_PATH), AscTrack.NashvilleToPaducah)       

    dist_m, theta_deg = compute_segments(pts)
    N_gps = len(pts)

    # Not tryna do figure out this stuff rn, so mock data! #TODO Setup Solcast :)
    ghi = np.linspace(700, 900, N_gps) 
    
    # Setup optimization parameters
    dt = OPTIMIZATION_TIMESTEP                       
    N_steps = N_gps  # Match number of GPS points for now
    horizon = N_steps * dt
    
    params = VehicleParams()
    cfg = OptimizeConfig(
        dt=dt, 
        horizon=horizon,
        vmin=MIN_SPEED_MPS, 
        vmax=MAX_SPEED_MPS,
        method=OPTIMIZATION_METHOD,  # Powell method handles bounds well
        max_iter=MAX_ITERATIONS
    )
    
    # Optimize velocity profile
    print("Optimizing velocity profile...")
    best_vs, best_obj = optimize_velocity(cfg, theta_deg, ghi, params)
    print(f"Optimization complete. Best objective: {best_obj:.2f}")

    # Simulate with optimized speeds
    print("Simulating...")
    d0 = 0.0
    res = simulate(best_vs, dt, d0, theta_deg, ghi, params)

    # Generate plots
    soc_wh = wh_from_joules(res.traces["Ebat_J"])
    dist_km = res.traces["distance_m"] / 1000

    fig, ax = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
    
    ax[0].plot(dist_km, res.traces["v"])
    ax[0].set_ylabel("Speed (m/s)")
    ax[0].grid(True, alpha=0.3)
    
    ax[1].plot(dist_km, soc_wh)
    ax[1].set_ylabel("Battery (Wh)")
    ax[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

    # Print final capacity 
    print(f"Final distance: {res.final_distance_m/1000:.2f} km")
    print(f"Final SOC: {wh_from_joules(res.final_soc_J):.2f} Wh")
    print(f"Average speed: {np.mean(best_vs):.2f} m/s")
    
# Notes:
# Plots look a little funky
# Average speed isn't average speed?? Is numpy lying to me...
        