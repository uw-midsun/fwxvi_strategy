## @file    map_demo.py
#  @date    2025-11-09
#  @author  Midnight Sun Team #24 - MSXVI
#  @brief   Main file for strategy XVI
#  @ingroup Strategy_XVI

# TODO Either add to existing doxygen documentation or make a new one or no doxygen documentation at all 😨

import numpy as np
import matplotlib.pyplot as plt

from simulation.simulation import simulate, VehicleParams, wh_from_joules
from simulation.optimizer import optimize_velocity, OptimizeConfig
from simulation.map_demo import load_gpx_points, compute_segments, save_map_with_speeds

GPX_PATH = "data/asc_24_(temp)/0_FullBaseRoute.gpx" 

if __name__ == "__main__":
    pts = load_gpx_points(GPX_PATH)        # shape [N,3] -> (lat, lon, ele)
    MAX_POINTS = 1000
    if len(pts) > MAX_POINTS:
        stride = max(1, len(pts) // MAX_POINTS)
        pts = pts[::stride]
    print(f"Using {len(pts)} points after downsampling.")

    dist_m, theta_deg = compute_segments(pts)
    N = len(pts)

    # Not tryna do figure out this stuff rn, so mock data ftw! #TODO Figure out :)
    ghi = np.linspace(700, 900, N) 
    
    # Optimize!
    dt = 1.0                       
    horizon = N * dt              
    params = VehicleParams()
    cfg = OptimizeConfig(dt=dt, horizon=horizon,
                         vmin=10.0, vmax=20.0,
                         method="Nelder-Mead", max_iter=2000)
    best_vs, best_obj = optimize_velocity(cfg, theta_deg, ghi, params)
    print(f"Optimization done. Best objective (negative distance) = {best_obj:.2f}")

    # Simulate!
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

    # This saves: route_recommended_speed.html (open in a browser)
    save_map_with_speeds(GPX_PATH, best_vs, theta_deg=theta_deg, ghi=ghi,
                         vmin=cfg.vmin, vmax=cfg.vmax)
