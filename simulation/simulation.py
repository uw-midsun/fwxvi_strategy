## @file    simulation.py
#  @date    2025-11-07
#  @author  Midnight Sun Team #24 - MSXVI
#  @brief   Simulation for MSXVI
#  @ingroup Strategy_XVI

from dataclasses import dataclass
from typing import NamedTuple, Optional, Dict
import numpy as np

# ! Some Values NEED to be verified for vehicle params 

@dataclass
class VehicleParams:
  """
  @brief A data class to store parameters for the model
  """
  mass: float = 450.0                               # mass
  drag_coeff: float = 0.18                          # drag coefficient
  front_area: float = 1.357                         # frontal area 
  C_RR: float = 0.004                               # rolling resistance 
  solar_area: float = 4.0                           # Solar array area
  panel_eff: float = 0.243                          # electrical panel efficiency (fraction)
  bat_max_energy: float = 40 * 3.63 * 36 * 3600     # battery energy capacity, Joules
  air_density: float = 1.293                        # air density
  gravity_const: float = 9.81                       # gravity
  # regen_eff: float = 0.0                            # TODO
  drive_eff: float = 0.94                           # drivetrain efficiency on traction losses in the set [0, 1] 


class SimResult(NamedTuple):
  """
  @brief The expected output values 
  """
  final_distance_m: float
  final_soc_J: float
  traces: Dict[str, np.ndarray]  

# ------------------------------------------------------------
# Power calculations (Check confluence page for more details)
# ------------------------------------------------------------
def rolling_power(v: np.ndarray, M: float, g: float, C_RR: float) -> np.ndarray:
    """
    @brief Calculates rolling resistance power loss
    @param v Velocity (m/s)
    @param M Vehicle mass (kg)
    @param g Gravitational acceleration (m/s²)
    @param C_RR Rolling resistance coefficient
    @return Power loss due to rolling resistance (W)
    """
    return (M * g * C_RR) * v


def drag_power(v: np.ndarray, rho: float, Cd: float, A: float) -> np.ndarray:
    """
    @brief Calculates aerodynamic drag power loss
    @param v Velocity (m/s)
    @param rho Air density (kg/m³)
    @param Cd Drag coefficient
    @param A Frontal area (m²)
    @return Power loss due to aerodynamic drag (W)
    """
    return 0.5 * rho * Cd * A * v**3


def grade_power(v: np.ndarray, theta_rad: np.ndarray, M: float, g: float) -> np.ndarray:
    """
    @brief Calculates gravitational power (positive uphill, negative downhill)
    @param v Velocity (m/s)
    @param theta_rad Road grade angle (radians)
    @param M Vehicle mass (kg)
    @param g Gravitational acceleration (m/s²)
    @return Power required to overcome grade (W), negative when descending
    """
    return M * g * np.sin(theta_rad) * v


def solar_power(G_wm2: np.ndarray, A_solar: float, panel_eff: float) -> np.ndarray:
    """
    @brief Calculates solar power generation
    @param G_wm2 Global horizontal irradiance (W/m²)
    @param A_solar Solar panel area (m²)
    @param panel_eff Panel efficiency (fraction)
    @return Electrical power generated (W)
    """
    return A_solar * panel_eff * G_wm2

# ----------------------------
# Simulation
# ----------------------------
def simulate(
  v: np.ndarray,
  dt: float,
  d0: float,
  theta_deg: np.ndarray,
  ghi: np.ndarray,
  params: VehicleParams = VehicleParams(), 
  stop_on_empty: bool = True,
) -> SimResult:
  """
  @brief Vectorized simulation over a fixed horizon
  @param v speed profile (m/s)
  @param dt timestep (s)
  @param d0 starting distance (m) 
  @param theta_deg road angle (from gpx files)
  @param ghi Global Horizontal Irradiance, we assume the panels lay flat (room for improvement here)
  @param params vehicle parameters (see dataclass)
  @param stop_on_empty if True, freeze distance once battery empties
  @returns SimResult(final_distance_m, final_soc_J, traces)
  """
  v = np.asarray(v, dtype=float)
  N = v.size
  p = params

  # Distance timeline (Euler)
  d = np.empty(N, dtype=float)
  d[0] = d0
  if N > 1:
    d[1:] = d0 + np.cumsum(v[:-1] * dt)

  theta_rad = np.deg2rad(theta_deg)

  P_rr = rolling_power(v, p.mass, p.gravity_const, p.C_RR)
  P_drag = drag_power(v, p.air_density, p.drag_coeff, p.front_area)
  P_grade_raw = grade_power(v, theta_rad, p.mass, p.gravity_const)
  P_solar = solar_power(ghi, p.solar_area, p.panel_eff)

  # Apply drivetrain efficiency
  P_grade_loss_pos = np.maximum(P_grade_raw, 0.0) / max(p.drive_eff, 1e-9)
  P_rr_drive = P_rr / max(p.drive_eff, 1e-9)
  P_drag_drive = P_drag / max(p.drive_eff, 1e-9)

  # Net battery power draw 
  # (+ Means drawing from battery)
  # (Losses (positive) minus solar)
  P_net = (P_rr_drive + P_drag_drive + P_grade_loss_pos) - P_solar 

  E_rr = P_rr * dt
  E_drag = P_drag * dt
  E_grade = P_grade_raw * dt
  E_solar = P_solar * dt
  E_net = P_net * dt 

  # Battery integration 
  Ebat = np.empty(N, dtype=float)
  Ebat[0] = p.bat_max_energy
  if N > 1:
    # Battery decreases by E_net (if E_net>0), increases if E_net<0
    Ebat[1:] = np.clip(Ebat[0] - np.cumsum(E_net[:-1]), 0.0, p.bat_max_energy)
  final_soc_J = float(Ebat[-1])

  if stop_on_empty:
    empty_idx = np.argmax(Ebat <= 0.0)  # 0 if never empty
    if Ebat[-1] <= 0.0 and empty_idx > 0:
      d[empty_idx:] = d[empty_idx]

  # debugging purposes in case numbers look funky
  traces = {
    "distance_m": d,
    "Ebat_J": Ebat,
    "P_rr_W": P_rr,
    "P_drag_W": P_drag,
    "P_grade_W": P_grade_raw,
    "P_solar_W": P_solar,
    "P_net_W": P_net,
    "E_rr_J": E_rr,
    "E_drag_J": E_drag,
    "E_grade_J": E_grade,
    "E_solar_J": E_solar,
    "E_net_J": E_net,
    "theta_deg": theta_deg,
    "ghi": ghi,
    "v": v,
  }
  return SimResult(final_distance_m=float(d[-1]), final_soc_J=final_soc_J, traces=traces)


# ----------------------------
# Helpers
# ----------------------------
def distance_trajectory(v: np.ndarray, dt: float, d0: float) -> np.ndarray:
  """
  @brief Euler-integrate distance from a speed profile
  @param v Velocity profile (m/s)
  @param dt Timestep (seconds)
  @param d0 Initial distance (meters)
  @return Cumulative distance array (meters)
  """
  v = np.asarray(v, dtype=float)
  d = np.empty_like(v)
  d[0] = d0
  if v.size > 1:
    d[1:] = d0 + np.cumsum(v[:-1] * dt)
  return d

def wh_from_joules(E_J: np.ndarray | float) -> np.ndarray | float:
  """
  @brief Convert energy from Joules to Watt-hours
  @param E_J Energy in Joules
  @return Energy in Watt-hours
  """
  return np.asarray(E_J) / 3600.0
