"""Generate plots for results.

Date: 2025-11-25
Author: Midnight Sun Team #24 - MSXVI
Group: Strategy_XVI
"""

import numpy as np
import matplotlib.pyplot as plt


def generate_plots(dist_km, res, soc_wh, bat_max_wh=None, ele_m=None, dist_m_gps=None):
    """Generates speed and battery plots from simulation results.

  Args:
      dist_km: Distance array in kilometers.
      res: SimResult object containing simulation traces.
      soc_wh: Battery state of charge array in Watt-hours.
      bat_max_wh: Maximum battery capacity in Wh (used to draw 20% threshold).
      ele_m: Raw GPS elevation array in meters (optional).
      dist_m_gps: Cumulative GPS distance array in meters matching ele_m (optional).
  """
    fig, ax = plt.subplots(3, 1, figsize=(9, 11), sharex=True)

    # Align arrays — traces may differ in length by 1 (e.g. Ebat has N+1 entries)
    v = res.traces["v"]
    n = min(len(dist_km), len(v), len(soc_wh))
    dist_km = dist_km[:n]
    v = v[:n]
    soc_wh = soc_wh[:n]

    # Elevation: use raw GPS data if available, otherwise reconstruct from grade angles
    if ele_m is not None and dist_m_gps is not None:
        elevation_m = np.interp(dist_km * 1000, dist_m_gps, ele_m)
    else:
        theta_rad = np.deg2rad(res.traces["theta_deg"][:n])
        d_dist_m = np.diff(dist_km * 1000, prepend=0.0)
        elevation_m = np.cumsum(np.sin(theta_rad) * d_dist_m)

    ax[0].fill_between(dist_km, elevation_m, alpha=0.3)
    ax[0].plot(dist_km, elevation_m, linewidth=1.5)
    ax[0].set_ylabel("Elevation (m)")
    ax[0].grid(True, alpha=0.3)

    ax[1].step(dist_km, v, where='post', linewidth=1.5)
    ax[1].plot(dist_km, v, 'o', markersize=4)
    ax[1].set_ylabel("Speed (m/s)")
    ax[1].grid(True, alpha=0.3)

    ax[2].plot(dist_km, soc_wh, marker='o', markersize=4, label="Battery SOC")
    if bat_max_wh is not None:
        threshold_wh = 0.2 * bat_max_wh
        ax[2].axhline(y=threshold_wh,
                      color='r',
                      linestyle='--',
                      linewidth=1.5,
                      label="20% minimum")
        ax[2].legend()
    ax[2].set_ylabel("Battery (Wh)")
    ax[2].set_xlabel("Distance (km)")
    ax[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()
