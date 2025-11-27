## @file    map_visualization.py
#  @date    2025-11-10
#  @author  Midnight Sun Team #24 - MSXVI
#  @brief   GPX utilities + mapping for strategy XVI 
#  @note    This is mainly for ASC. For FSGP elevation data isn't AS important since it's a grand prix
#           However, would be cool to have lap by lap coloured map gradients for best speeds for FSGP
#  @ingroup Strategy_XVI

#! Not tested
# TODO  

from __future__ import annotations
from typing import List, Dict, Tuple, Optional
import json
import numpy as np
import gpxpy, gpxpy.gpx
from enum import IntEnum 

# ----------------------------
# Core GPX helpers
# ----------------------------

class AscTrack(IntEnum): 
    """
    @brief To store track indices
    @note  This is not fully listed out since this repo still uses asc2024 track data
           Will be updated when we get asc2026 track data
    """
    NashvilleToPaducah = 0 
    # And then the rest...
    
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    @brief Distance in meters between two points using GPS data
    """
    R = 6371000.0
    lat1, lon1, lat2, lon2 = np.radians([lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
    return float(2.0 * R * np.arcsin(np.sqrt(a)))

def load_gpx_points(path: str, track: IntEnum) -> np.ndarray:
    """
    @brief  Loads GPX points from file
    @param  path File path to GPX file
    @param  track Specific track along the route (e.g., NashvilleToPaducah)
    @return np.ndarray of shape [N, 3] as (lat, lon, elevation)
    """
    with open(path, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)
        
    pts = []
    track_idx = int(track)
    
    if track_idx >= len(gpx.tracks):
        raise ValueError(f"Track index {track_idx} not found in GPX file")
    
    trk = gpx.tracks[track_idx]
    
    for seg in trk.segments:
        for p in seg.points:
            pts.append((p.latitude, p.longitude, p.elevation))
                
    if not pts:
        raise ValueError("No GPX points found in the specified track.")
    
    return np.asarray(pts, dtype=float)

def compute_segments(pts: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    @brief  Computes cumulative distances and grade angles between GPS points
    @param  pts [N,3] array of (lat, lon, elevation)
    @return (distance, grade_deg) - cumulative distance and grade in degrees
    """
    lat, lon, ele = pts[:, 0], pts[:, 1], pts[:, 2]
    N = len(pts)
    dist = np.zeros(N, dtype=float)
    for i in range(1, N):
        dist[i] = dist[i-1] + haversine(lat[i-1], lon[i-1], lat[i], lon[i])

    # Compute grade 
    d_ele = np.diff(ele, prepend=ele[0])
    d_dist = np.diff(dist, prepend=0.0)
    
    grade_deg = np.zeros(N, dtype=float)
    mask = d_dist > 1e-6  # Only compute where there's meaningful distance
    grade_deg[mask] = np.degrees(np.arctan(d_ele[mask] / d_dist[mask]))
    
    return dist, grade_deg

def interpolate_to_time_grid(
    theta_deg: np.ndarray, 
    ghi: np.ndarray, 
    dist_m: np.ndarray,
    dt: float,
    avg_speed: float = 15.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    @brief  Interpolates GPS-based data to match simulation timesteps
    @param  theta_deg Grade angles at GPS points
    @param  ghi Global horizontal irradiance at GPS points
    @param  dist_m Cumulative distance at GPS points
    @param  dt Time step for simulation (seconds)
    @param  avg_speed Estimated average speed for calculating time grid (m/s)
    @return (theta_interp, ghi_interp) - interpolated arrays matching simulation steps
    """
    # TODO
    return theta_deg, ghi

# ----------------------------
# Visualization helpers
# ----------------------------
def color_for_speed(v: float, vmin: float = 10.0, vmax: float = 20.0) -> str:
    """
    @brief  Returns color gradient hex code based on speed
    @param  v Current speed (m/s)
    @param  vmin Minimum speed in range
    @param  vmax Maximum speed in range
    @return Hex color code (e.g., '#ff0000')
    """
    t = float((v - vmin) / max(vmax - vmin, 1e-9))
    t = min(max(t, 0.0), 1.0)
    
    # Color gradient: blue -> cyan -> green -> yellow -> red
    stops = [
        (0.00, (0, 0, 255)),
        (0.25, (0, 255, 255)),
        (0.50, (0, 255, 0)),
        (0.75, (255, 255, 0)),
        (1.00, (255, 0, 0)),
    ]
    
    for i in range(1, len(stops)):
        if t <= stops[i][0]:
            t0, c0 = stops[i - 1]
            t1, c1 = stops[i]
            u = (t - t0) / max(t1 - t0, 1e-9)
            r = int(c0[0] + u * (c1[0] - c0[0]))
            g = int(c0[1] + u * (c1[1] - c0[1]))
            b = int(c0[2] + u * (c1[2] - c0[2]))
            return f"#{r:02x}{g:02x}{b:02x}"
    
    return "#ff0000"

# ----------------------------
# Public API 
# ----------------------------
def export_grafana_json(
    gpx_path: str,
    track: AscTrack,
    speed: np.ndarray,
    theta_deg: Optional[np.ndarray] = None,
    ghi: Optional[np.ndarray] = None,
    vmin: float = 10.0,
    vmax: float = 20.0,
    outfile: Optional[str] = None
) -> Dict:
    """
    @brief   Builds a JSON object suitable for Grafana map visualization
    @details Each entry includes lat/lon, segment info, and color-coded speed
    @param   gpx_path Path to GPX file
    @param   track Track index to load
    @param   speed Numpy array of target speeds (m/s)
    @param   theta_deg Grade angles 
    @param   ghi Global horizontal irradiance 
    @param   vmin Minimum speed for color scaling
    @param   vmax Maximum speed for color scaling
    @param   outfile Optional output file path for JSON
    @return  Dictionary containing segment data for Grafana
    """
    # Load GPS points
    pts = load_gpx_points(gpx_path, track)
    
    # Align array lengths
    n_segments = min(len(pts) - 1, len(speed), len(theta_deg), len(ghi))
    
    # Build segment data
    data: List[Dict] = []
    for i in range(n_segments):
        entry = {
            "segment": int(i),
            "lat_start": float(pts[i, 0]),
            "lon_start": float(pts[i, 1]),
            "lat_end": float(pts[i + 1, 0]),
            "lon_end": float(pts[i + 1, 1]),
            "grade_deg": float(theta_deg[i]),
            "ghi_wm2": float(ghi[i]),
            "speed_mps": float(speed[i]),
            "color": color_for_speed(speed[i], vmin, vmax),
        }
        data.append(entry)

    json_obj = {
        "segments": data, 
        "meta": {
            "vmin": vmin, 
            "vmax": vmax,
            "total_segments": n_segments
        }
    }

    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(json_obj, f, indent=2)
        print(f"Saved Grafana JSON to {outfile}")

    return json_obj