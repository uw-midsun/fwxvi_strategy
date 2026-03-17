"""Mock data loader for YAML-based test scenarios.

Date: 2025-11-23
Author: Midnight Sun Team #24 - MSXVI
Group: Strategy_XVI
"""

from __future__ import annotations

from typing import Tuple, Dict, Any
import numpy as np
import csv
import os
try:
    import yaml
except ImportError:
    yaml = None



def load_mock_csv(path: str) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Load a CSV mock profile for testing.

    Args:
        path: Path to CSV file containing mock scenario data.

    Returns:
        Tuple of (theta_deg, ghi, meta) where meta contains dt and d0.
    """
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    if not rows:
        raise ValueError("CSV file is empty or invalid format.")
    # Assume all rows have the same dt and d0
    dt = float(rows[0].get("dt", 1800))
    d0 = float(rows[0].get("d0", 0.0))
    ghi = np.array([float(r["ghi"]) for r in rows], dtype=float)
    theta_deg = np.array([float(r["theta_deg"]) for r in rows], dtype=float)
    meta = {"dt": dt, "d0": d0}
    return theta_deg, ghi, meta

def load_mock_yaml(path: str) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """Load a YAML mock profile for testing (legacy)."""
    if yaml is None:
        raise ImportError("PyYAML is not installed.")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    ghi = np.asarray(data.get("ghi", []), dtype=float)
    theta_deg = np.asarray(data.get("theta_deg", []), dtype=float)
    meta = {
        "dt": float(data.get("dt", 1800)),
        "d0": float(data.get("d0", 0.0)),
    }
    return theta_deg, ghi, meta
