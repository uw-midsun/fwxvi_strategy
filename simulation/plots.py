"""Generate plots for results.

Date: 2025-11-25
Author: Midnight Sun Team #24 - MSXVI
Group: Strategy_XVI
"""

import numpy as np
import matplotlib.pyplot as plt


def generate_plots(dist_km, res, soc_wh, bat_max_wh=None):
    """Generates speed and battery plots from simulation results.

  Args:
      dist_km: Distance array in kilometers.
      res: SimResult object containing simulation traces.
      soc_wh: Battery state of charge array in Watt-hours.
      bat_max_wh: Maximum battery capacity in Wh (used to draw 20% threshold).
  """
    fig, ax = plt.subplots(2, 1, figsize=(9, 8), sharex=True)

    # Align arrays — traces may differ in length by 1 (e.g. Ebat has N+1 entries)
    v = res.traces["v"]
    n = min(len(dist_km), len(v), len(soc_wh))
    dist_km = dist_km[:n]
    v = v[:n]
    soc_wh = soc_wh[:n]

    ax[0].step(dist_km, v, where='post', linewidth=1.5)
    ax[0].plot(dist_km, v, 'o', markersize=4)
    ax[0].set_ylabel("Speed (m/s)")
    ax[0].grid(True, alpha=0.3)

    ax[1].plot(dist_km, soc_wh, marker='o', markersize=4, label="Battery SOC")
    if bat_max_wh is not None:
        threshold_wh = 0.2 * bat_max_wh
        ax[1].axhline(y=threshold_wh,
                      color='r',
                      linestyle='--',
                      linewidth=1.5,
                      label="20% minimum")
        ax[1].legend()
    ax[1].set_ylabel("Battery (Wh)")
    ax[1].set_xlabel("Distance (km)")
    ax[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()
