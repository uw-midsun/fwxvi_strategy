import os
import sys
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simulation.mock_data import load_mock_yaml, load_mock_csv
from simulation.simulation import simulate, VehicleParams



def test_mock_csv_runs_and_outputs():
    path = os.path.join(os.path.dirname(__file__), "test1.csv")
    theta_deg, ghi, meta = load_mock_csv(path)

    params = VehicleParams()
    dt = meta.get("dt", 1800)
    d0 = meta.get("d0", 0.0)

    # create a trivial constant speed profile
    v = np.full(theta_deg.size, 15.0)

    # Build position-based lookup functions from test arrays
    N_steps = theta_deg.size
    avg_v = 15.0
    total_dist = N_steps * dt * avg_v
    dist_points = np.linspace(0, total_dist, N_steps)

    def theta_fn(d):
        return np.interp(d, dist_points, theta_deg)

    def ghi_fn(d):
        return np.interp(d, dist_points, ghi)

    res = simulate(v, dt, d0, theta_fn, ghi_fn, params)

    # Print useful simulation results
    print(f"\n{'='*60}")
    print(f"Mock CSV Test Results")
    print(f"{'='*60}")
    print(f"Simulation timestep:     {dt:.1f} s")
    print(f"Number of steps:         {theta_deg.size}")
    print(f"Average speed:           {np.mean(v):.2f} m/s")
    print(f"Final distance:          {res.final_distance_m / 1000:.2f} km")
    print(f"Final SOC:               {res.final_soc_J / 3600:.2f} Wh")
    print(f"Initial battery energy:  {params.bat_max_energy / 3600:.2f} Wh")
    print(
        f"Energy consumed:         {(params.bat_max_energy - res.final_soc_J) / 3600:.2f} Wh"
    )
    print(f"Average GHI:             {np.mean(ghi):.1f} W/m²")
    print(f"Average grade:           {np.mean(theta_deg):.2f}°")
    print(f"{'=' * 60}\n")

    # Basic assertions: arrays have expected lengths and final distance non-negative
    assert res.traces["v"].shape[0] == theta_deg.size
    assert res.traces["ghi"].shape[0] == theta_deg.size
    assert res.final_distance_m >= 0.0
