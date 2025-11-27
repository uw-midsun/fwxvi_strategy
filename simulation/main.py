## @file    main.py
#  @date    2025-11-25
#  @author  Midnight Sun Team #24 - MSXVI
#  @brief   Strategy XVI
#  @ingroup Strategy_XVI

import os
import sys
from pathlib import Path

from config import SimConfig
from scenarios import run_test_scenario, run_raceday_scenario

def list_yaml_tests() -> list:
    """
    @brief  List available YAML test files
    @return List of YAML file paths
    """
    test_dir = Path(__file__).parent.parent / "test"
    yaml_files = list(test_dir.glob("*.yaml"))
    return sorted([str(f) for f in yaml_files])


def configure_menu(config: SimConfig) -> None:
    """
    @brief  Interactive menu to configure simulation parameters
    @param  config Configuration object to modify
    """
    param_map = {
        1: "dt",
        2: "vmin",
        3: "vmax",
        4: "method",
        5: "max_iter",
        6: "energy_penalty",
        7: "use_solcast",
        8: "gpx_file",
    }
    
    while True:
        config.display()
        print("Options: [1-8] Change parameter | [r] Run | [q] Quit")
        choice = input("Select: ").strip().lower()
        
        if choice == 'q':
            sys.exit(0)
        elif choice == 'r':
            return
        elif choice.isdigit() and int(choice) in param_map:
            param_name = param_map[int(choice)]
            current_val = getattr(config, param_name)
            new_val = input(f"Enter new value for {param_name} (current: {current_val}): ").strip()
            if config.update_param(param_name, new_val):
                print(f"Updated {param_name} to {getattr(config, param_name)}")
            else:
                print(f"Failed to update {param_name}")
        else:
            print("Invalid choice.")


def main_menu() -> None:
    """
    @brief  Main interactive menu for testing suite
    """
    config = SimConfig()
    
    print('\n' + '-'*50)
    print("MSXVI Strategy Testing Suite")
    print('-'*50)
    
    while True:
        print("\nMain Menu:")
        print("  1. Configure parameters")
        print("  2. Run test scenario (YAML)")
        print("  3. Run race day scenario (GPX + Solcast)")
        print("  q. Quit")
        
        choice = input("\nSelect: ").strip().lower()
        
        if choice == 'q':
            print("Exiting...")
            sys.exit(0)
        elif choice == '1':
            configure_menu(config)
        elif choice == '2':
            yaml_files = list_yaml_tests()
            if not yaml_files:
                print("No YAML test files found in test/ directory.")
                continue
            
            print("\nAvailable test files:")
            for idx, path in enumerate(yaml_files, 1):
                print(f"  {idx}. {Path(path).name}")
            
            test_choice = input("Select test file (number): ").strip()
            if test_choice.isdigit() and 1 <= int(test_choice) <= len(yaml_files):
                try:
                    run_test_scenario(yaml_files[int(test_choice)-1], config)
                except Exception as e:
                    print(f"Error running test: {e}")
            else:
                print("Invalid selection.")
                
        elif choice == '3':
            try:
                # Check for Solcast API key if enabled
                if config.use_solcast and not config.solcast_api_key:
                    api_key = os.environ.get("SOLCAST_API_KEY")
                    if api_key:
                        config.solcast_api_key = api_key
                    else:
                        print("Warning: Solcast enabled but no API key found.")
                        print("Set SOLCAST_API_KEY environment variable or disable Solcast.")
                
                run_raceday_scenario(config)
            except Exception as e:
                print(f"Error running race day scenario: {e}")
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Exiting...")
        sys.exit(0)
        