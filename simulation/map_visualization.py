## @file    map_demo.py
#  @date    2025-11-10
#  @author  Midnight Sun Team #24 - MSXVI
#  @brief   GPX utilities + mapping for strategy XVI 
#  @note    This is mainly for ASC. For FSGP elevation data isn't AS important since it's a grand prix
#           However, would be cool to have lap by lap coloured map gradients for best speeds for FSGP
#  @ingroup Strategy_XVI

from __future__ import annotations
from typing import List, Dict, Tuple, Optional
import json
import numpy as np
import folium
import gpxpy, gpxpy.gpx
from enum import IntEnum 

#! Not tested yet, plan is to connect this to telemetry

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
    """Great-circle distance in meters between two WGS84 points."""
    R = 6371000.0
    lat1, lon1, lat2, lon2 = np.radians([lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2.0)**2
    return float(2.0 * R * np.arcsin(np.sqrt(a)))

def load_gpx_points(path: str, track: IntEnum) -> np.ndarray:
    """
    @brief  Loads gpx points (woah!)
    @param  path File path to gpx files
    @param  track Specific track along the route (ex: GeringToCasper)
    @return np.ndarray of shape [N, 3] as (lat, lon, elevation)
    """
    with open(path, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)
        
    pts = []
    track_idx = int(track)
    trk = gpx.tracks[track_idx]
    
    for seg in trk.segments:
        for p in seg.points:
            pts.append((p.latitude, p.longitude, p.elevation))
                
    if not pts:
        raise ValueError("No GPX points found.")
    return np.asarray(pts, dtype=float)

def compute_segments(pts: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    @brief  Computes the distances between the various GPS points
    @param  pts [N,3] (lat, lon, ele)
    @return distance, grade_deg
    """
    lat, lon, ele = pts[:, 0], pts[:, 1], pts[:, 2]
    N = len(pts)
    dist = np.zeros(N, dtype=float)
    for i in range(1, N):
        dist[i] = dist[i-1] + haversine(lat[i-1], lon[i-1], lat[i], lon[i])

    # np.diff calculates the difference between consecutive values
    d_ele = np.diff(ele, prepend=ele[0])
    d_dist = np.diff(dist, prepend=dist[0])
    d_dist[d_dist == 0.0] = 1e-9
    grade_deg = np.degrees(np.arctan(d_ele / d_dist))
    return dist, grade_deg

# ----------------------------
# Visualization helpers
# ----------------------------
def color_for_speed(v: float, vmin: float = 10.0, vmax: float = 20.0) -> str:
    """
    @brief  Colour gradient for speeds
    @param  v Speed
    @param  vmin Minimum speed set
    @param  vmax Maximum speed set
    @return Hex code of colour
    """
    t = float((v - vmin) / max(vmax - vmin, 1e-9))
    t = min(max(t, 0.0), 1.0)
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
def export_grafana_json(gpx_path: str,
                        speed: np.ndarray,
                        theta_deg: Optional[np.ndarray] = None,
                        ghi: Optional[np.ndarray] = None,
                        vmin: float = 10.0,
                        vmax: float = 20.0,
                        outfile: Optional[str] = None) -> Dict:
    """
    @brief   Builds a JSON object suitable for Grafana map visualization
    @details Each entry includes lat/lon, segment info, and color-coded speed
    @param   gpx_path GPX files file path
    @param   speed Numpy array of target speeds
    @param   ghi Global horizontal irradiance
    @param   vmin Minimum speed
    @param   vmax Maximum speed
    @param   outfile If you want to save the outputted JSON in a file
             ^ Mainly for testing right now
    @return  A list of dicts
    """
    v, th, ghi, seg_n = _align_inputs_for_segments(pts, speed, theta_deg, ghi)

    data: List[Dict] = []
    for i in range(seg_n):
        entry = {
            "segment": int(i),
            "lat_start": float(pts[i, 0]),
            "lon_start": float(pts[i, 1]),
            "lat_end": float(pts[i + 1, 0]),
            "lon_end": float(pts[i + 1, 1]),
            "grade_deg": float(th[i]),
            "ghi_wm2": float(ghi[i]),
            "speed_mps": float(v[i]),
            "color": color_for_speed(v[i], vmin, vmax),
        }
        data.append(entry)

    json_obj = {"segments": data, "meta": {"vmin": vmin, "vmax": vmax}}

    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(json_obj, f, indent=2)
        print(f"Saved Grafana JSON to {outfile}")

    return json_obj
