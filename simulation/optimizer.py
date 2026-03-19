"""Optimizer

Date: 2025-11-09
Author: Midnight Sun Team #24 - MSXVI
Group: Strategy_XVI
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Callable
from scipy.optimize import minimize
from simulation import simulate, VehicleParams
import itertools


@dataclass
class OptimizeConfig:
    """A configuration dataclass for the optimizer."""

    # fmt: off
    dt: float = 10.0            # Time step (s)
    horizon: int = 100          # How many seconds we want to simulate (s)
    d0: float = 0.0             # Starting distance (m)
    vmin: float = 8.9           # Minimum allowed speed (m/s), default value as per ASC 2026 regs
    vmax: float = 29.0          # Maximum allowed speed (m/s), default value as per ASC 2026 regs
    method: str = "SLSQP"       # Optimization method from scipy
    max_iter: int = 1000        # Maximum itterations (regardless of if we reach convergence or not)
    min_soc: float = 0.2        # Minimum SOC threshold at the end of the simulation
    # fmt: on


def objective(
    vs: np.ndarray,
    dt: float,
    d0: float,
    theta_fn: Callable,
    ghi_fn: Callable,
    params: VehicleParams,
    cfg: OptimizeConfig,
) -> float:
    """Objective for SciPy minimize.

    Args:
        vs: The speed profile (m/s).
        theta_fn: Callable returning road grade (deg) at given distance(s).
        ghi_fn: Callable returning GHI (W/m^2) at given distance(s).
        params: For simulation.

    Returns:
        Negative distance (so minimizing -> maximize distance).
    """
    res = simulate(vs, dt, d0, theta_fn, ghi_fn, params)
    min_reserve = cfg.min_soc * params.bat_max_energy
    margin = np.min(res.traces["Ebat_raw_J"][1:] - min_reserve)

    if margin < 0:
        return 1e12 + 1e6 * (-margin)

    return -res.final_distance_m


def SLSQP_velocity(
    cfg: OptimizeConfig, theta_fn: Callable, ghi_fn: Callable, params: VehicleParams
) -> Tuple[np.ndarray, float]:
    """Runs an SLSQP optimization on given slope and irradiance callables.

    Args:
        cfg: Optimizer configuration data (see OptimizeConfig dataclass).
        theta_fn: Callable returning road grade (deg) at given distance(s).
        ghi_fn: Callable returning GHI (W/m^2) at given distance(s).

    Returns:
        Best velocity array and objective value.
    """
    N = int(cfg.horizon / cfg.dt)

    vs0 = np.full(N, cfg.vmin)

    bounds = [(cfg.vmin, cfg.vmax)] * N

    # Per timestep SOC >= cfg.min_soc constraints
    min_reserve = cfg.min_soc * params.bat_max_energy  # In Joules

    def soc_constraints(vs):
        """Return SOC - reserve for every timestep; each must be >= 0."""
        res = simulate(vs, cfg.dt, cfg.d0, theta_fn, ghi_fn, params)
        return res.traces["Ebat_raw_J"][1:] - min_reserve

    constraints = [{"type": "ineq", "fun": soc_constraints}]

    iteration_log = []

    def callback(xk):
        """Called by scipy's optimize function. Shows traces of each itteration"""
        res = simulate(xk, cfg.dt, cfg.d0, theta_fn, ghi_fn, params)
        obj = -res.final_distance_m
        soc_pct = res.final_soc_J / params.bat_max_energy * 100
        iteration_log.append(
            {
                "iter": len(iteration_log),
                "objective": obj,
                "distance_km": res.final_distance_m / 1000,
                "final_soc_pct": soc_pct,
                "mean_speed": float(np.mean(xk)),
            }
        )
        entry = iteration_log[-1]
        print(
            f"  Iter {entry['iter']:4d} | "
            f"dist={entry['distance_km']:.2f} km | "
            f"SOC={entry['final_soc_pct']:.1f}% | "
            f"avg_v={entry['mean_speed']:.2f} m/s"
        )

    # Pass cfg through to the objective so it can access tunable weights.
    result = minimize(
        objective,
        vs0,
        args=(cfg.dt, cfg.d0, theta_fn, ghi_fn, params, cfg),
        method=cfg.method,
        bounds=bounds,
        constraints=constraints,
        callback=callback,
        options={"maxiter": cfg.max_iter, "disp": True},
    )
    if not result.success:
        print(f"Warning: Optimization did not converge. Message: {result.message}")

    best_vs = result.x
    best_obj = result.fun
    return best_vs, best_obj


def exhaustive_search_velocity(
    cfg: OptimizeConfig, theta_fn: Callable, ghi_fn: Callable, params: VehicleParams
) -> Tuple[np.ndarray, float]:
    """Perform an exhaustive search (try every single velocity vector) to find optimized velocity

    Args:
        cfg: Optimizer configuration data (see OptimizeConfig dataclass).
        theta_fn: Callable that takes an array of indices or distances and returns road grade (deg) array.
        ghi_fn: Callable that takes an array of indices or distances and returns GHI (W/m^2) array.
        params: Vehicle parameters.

    Returns:
        Best velocity array and objective value.
    """

    # N = int(cfg.horizon / cfg.dt)
    N = 10  # For testing, set to 10. Change back to above for full search (warning: very slow!)
    v_grid = np.linspace(cfg.vmin, cfg.vmax, num=4)

    best_vs = None
    best_obj = float('inf')
    min_reserve = cfg.min_soc * params.bat_max_energy

    print(f"Starting exhaustive search for N={N}. Total permutations: {len(v_grid)**N}")

    for vs_tuple in itertools.product(v_grid, repeat=N):
        vs = np.array(vs_tuple)
        res = simulate(vs, cfg.dt, cfg.d0, theta_fn, ghi_fn, params)
        margin = np.min(res.traces["Ebat_raw_J"][1:] - min_reserve)
        if margin < 0:
            continue  # Battery died, skip this profile
        obj = -res.final_distance_m
        if obj < best_obj:
            best_obj = obj
            best_vs = vs.copy()
            print(f"New best: dist={res.final_distance_m / 1000:.2f} km | vs={vs}")

    if best_vs is None:
        best_vs = np.full(N, cfg.vmin)
        best_obj = 1e12

    return best_vs, best_obj