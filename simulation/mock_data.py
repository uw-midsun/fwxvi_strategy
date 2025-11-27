## @file    mock_data.py
#  @date    2025-11-23
#  @author  Midnight Sun Team #24 - MSXVI
#  @brief   Mock data loader for YAML-based test scenarios
#  @ingroup Strategy_XVI

from __future__ import annotations
from typing import Tuple, Dict, Any
import yaml
import numpy as np

def load_mock_yaml(path: str) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    @brief  Load a YAML mock profile for testing
    @param  path Path to YAML file containing mock scenario data
    @return Tuple of (theta_deg, ghi, meta) where meta contains dt and d0
    """
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    ghi = np.asarray(data.get("ghi", []), dtype=float)
    theta_deg = np.asarray(data.get("theta_deg", []), dtype=float)

    meta = {
        "dt": float(data.get("dt", 1800)),
        "d0": float(data.get("d0", 0.0)),
    }

    return theta_deg, ghi, meta
