## @file    map_demo.py
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

GPX_PATH = "../data/asc_24_(temp)/0_FullBaseRoute.gpx" #! Adjust when main.py is moved outside of simulation/

if __name__ == "__main__":
    print("Loading GPX points")
    pts = load_gpx_points(GPX_PATH, AscTrack.NashvilleToPaducah)       

    dist_m, theta_deg = compute_segments(pts)
    N = len(pts)

    # Not tryna do figure out this stuff rn, so mock data! #TODO Setup Solcast :)
    ghi = np.linspace(700, 900, N) 
    
    # Optimize!
    print("Optimizing...")
    dt = 1800 # every 30 mins                       
    horizon = N * dt              
    params = VehicleParams()
    cfg = OptimizeConfig(dt=dt, horizon=horizon,
                         vmin=10.0, vmax=20.0,
                         method="Powell", max_iter=2000)
    best_vs, best_obj = optimize_velocity(cfg, theta_deg, ghi, params)
    print(f"Optimization done. Best objective (negative distance) = {best_obj:.2f}")

    # Simulate!
    print("Simulataing....")
    d0 = 0.0
    res = simulate(best_vs, dt, d0, theta_deg, ghi, params)

    # Plots (will be changed)
    soc_wh = wh_from_joules(res.traces["Ebat_J"])
    dist_km = res.traces["distance_m"] / 1000

    fig, ax = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
    ax[0].plot(dist_km, res.traces["v"])
    ax[0].set_ylabel("Speed (m/s)")
    ax[1].plot(dist_km, soc_wh)
    ax[1].set_ylabel("Battery (Wh)")
    ax[2].plot(dist_km, res.traces["P_net_W"])
    ax[2].set_ylabel("Net Power (W)")
    ax[2].set_xlabel("Distance (km)")
    plt.tight_layout()
    plt.show()

    print(f"Final distance: {res.final_distance_m/1000:.2f} km")
    print(f"Final SOC: {wh_from_joules(res.final_soc_J):.2f} Wh")
