## @file    plots.py
#  @date    2025-11-25
#  @author  Midnight Sun Team #24 - MSXVI
#  @brief   Generate plots for results
#  @ingroup Strategy_XVI

import numpy as np
import matplotlib.pyplot as plt

def generate_plots(dist_km, res, soc_wh): 
  """
  @brief  Generates speed and battery plots from simulation results
  @param  dist_km Distance array in kilometers
  @param  res SimResult object containing simulation traces
  @param  soc_wh Battery state of charge array in Watt-hours
  """
  fig, ax = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
    
  ax[0].plot(dist_km, res.traces["v"])
  ax[0].set_ylabel("Speed (m/s)")
  ax[0].grid(True, alpha=0.3)
  
  ax[1].plot(dist_km, soc_wh)
  ax[1].set_ylabel("Battery (Wh)")
  ax[1].grid(True, alpha=0.3)
  
  plt.tight_layout()
  plt.show()