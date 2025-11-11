## @file    optimizer.py
#  @date    2025-11-09
#  @author  Midnight Sun Team #24 - MSXVI
#  @brief   Main file for strategy XVI
#  @ingroup Strategy_XVI

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Tuple
from scipy.optimize import minimize
from simulation import simulate, VehicleParams

@dataclass
class OptimizeConfig:
    """
    @brief A configuration dataclass for the optimizer
    """
    dt: float = 10.0            # Time step (s)
    horizon: int = 600          # How many minutes we want to simulate?(s)
    d0: float = 0.0             # Starting distance (m)
    vmin: float = 10.0          # Minimum allowed speed (m/s)
    vmax: float = 20.0          # Maximum allowed speed (m/s)
    method: str = "Nelder-Mead" # Optimization method from scipy #TODO Experiment with different optimization methods
    max_iter: int = 2000        # Maximum itterations (regardless of if we reach convergence or not)

def objective(vs: np.ndarray, 
              dt: float, d0: float,
              theta_deg: np.ndarray, ghi: np.ndarray,
              params: VehicleParams) -> float:
    """
    @brief  Objective for SciPy minimize
    @param  vs the speed profile (m/s)
    @param  theta_deg road angles (from gpx files)
    @param  ghi Global horizontal index (w/m^2)
    @param  params for simulation
    @return Negative distance (so minimizing → maximize distance)
    """
    res = simulate(vs, dt, d0, theta_deg, ghi, params)
    # penalize running out of battery early
    penalty = 0.0
    if res.final_soc_J <= 0:
        penalty = 1e6
    return -res.final_distance_m + penalty


def optimize_velocity(cfg: OptimizeConfig,
                      theta_deg: np.ndarray,
                      ghi: np.ndarray,
                      params: VehicleParams) -> Tuple[np.ndarray, float]:
    """
    @brief  Runs the optimizer given slope and irradiance arrays
    @param  cfg Optimizer configuration data (see OptimizeConfig dataclass) 
    @param  theta_deg Numpy array of elevation in degrees
    @param  ghi Global horizontal index
    @return Best velocity array and objective value.
    """
    N = int(cfg.horizon / cfg.dt)
    vs0 = np.full(N, (cfg.vmin + cfg.vmax) / 2.0)

    bounds = [(cfg.vmin, cfg.vmax)] * N

    result = minimize(
        objective,
        vs0,
        args=(cfg.dt, cfg.d0, theta_deg, ghi, params),
        method=cfg.method,
        bounds=bounds if cfg.method != "Nelder-Mead" else None,
        options={"maxiter": cfg.max_iter, "disp": True},
    )

    best_vs = result.x
    best_obj = result.fun
    return best_vs, best_obj
