"""Mock data loader for test scenarios.

Date: 2025-11-23
Author: Midnight Sun Team #24 - MSXVI
Group: Strategy_XVI
"""

from __future__ import annotations

from typing import Tuple
import numpy as np
import csv

try:
    import yaml
except ImportError:
    yaml = None


def load_mock_csv(path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load a CSV mock profile for testing.

    Args:
        path: Path to CSV file with columns: distance_m, ghi, theta_deg.

    Returns:
        Tuple of (distance_m, theta_deg, ghi).
    """
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    if not rows:
        raise ValueError("CSV file is empty or invalid format.")
    distance_m = np.array([float(r["distance_m"]) for r in rows], dtype=float)
    theta_deg = np.array([float(r["theta_deg"]) for r in rows], dtype=float)
    ghi = np.array([float(r["ghi"]) for r in rows], dtype=float)
    return distance_m, theta_deg, ghi


def load_mock_yaml(path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load a YAML mock profile for testing.

    Args:
        path: Path to YAML file with keys: distance_m, ghi, theta_deg.

    Returns:
        Tuple of (distance_m, theta_deg, ghi).
    """
    if yaml is None:
        raise ImportError("PyYAML is not installed.")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    distance_m = np.asarray(data.get("distance_m", []), dtype=float)
    theta_deg = np.asarray(data.get("theta_deg", []), dtype=float)
    ghi = np.asarray(data.get("ghi", []), dtype=float)
    return distance_m, theta_deg, ghi
