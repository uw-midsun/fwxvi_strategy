## @file    config.py
#  @date    2025-11-25
#  @author  Midnight Sun Team #24 - MSXVI
#  @brief   Configuration management for strategy simulations
#  @ingroup Strategy_XVI

from dataclasses import dataclass, field
from typing import Optional
import json

@dataclass
class SimConfig:
    """
    @brief Configuration parameters for simulation and optimization
    """
    # Optimization parameters
    dt: float = 1800.0                      # Timestep 
    vmin: float = 10.0                      # Minimum speed 
    vmax: float = 15                        # Maximum speed 
    method: str = "Powell"                  # Optimization method
    max_iter: int = 2000                    # Maximum iterations
    energy_penalty: float = 0.0             # Energy penalty weight
    
    # Data sources
    use_solcast: bool = False               # Use Solcast API for GHI data
    solcast_api_key: Optional[str] = None   # Solcast API key
    gpx_file: str = "0_FullBaseRoute.gpx"   # GPX filename
    
    def display(self) -> None:
        """
        @brief Display all configuration parameters with indices
        """
        params = [
            ("dt", self.dt, "s", "Timestep"),
            ("vmin", self.vmin, "m/s", "Minimum speed"),
            ("vmax", self.vmax, "m/s", "Maximum speed"),
            ("method", self.method, "", "Optimization method"),
            ("max_iter", self.max_iter, "", "Max iterations"),
            ("energy_penalty", self.energy_penalty, "", "Energy penalty weight"),
            ("use_solcast", self.use_solcast, "", "Use Solcast API"),
            ("gpx_file", self.gpx_file, "", "GPX filename"),
        ]
        
        print(f"\n{'-'*50}")
        print("Current Configuration")
        print(f"{'-'*50}")
        for idx, (name, value, unit, description) in enumerate(params, 1):
            unit_str = f" {unit}" if unit else ""
            print(f"{idx:2d}. {description:25s} = {value}{unit_str}")
        print(f"{'-'*50}\n")
    
    def update_param(self, param_name: str, value: any) -> bool:
        """
        @brief  Update a configuration parameter
        @param  param_name Name of the parameter to update
        @param  value New value for the parameter
        @return True if successful, False otherwise
        """
        if hasattr(self, param_name):
            # Type conversion based on current type
            current_val = getattr(self, param_name)
            try:
                if isinstance(current_val, bool):
                    new_val = value.lower() in ('true', '1', 'yes', 'y') if isinstance(value, str) else bool(value)
                elif isinstance(current_val, int):
                    new_val = int(value)
                elif isinstance(current_val, float):
                    new_val = float(value)
                else:
                    new_val = value
                setattr(self, param_name, new_val)
                return True
            except (ValueError, AttributeError):
                return False
        return False
