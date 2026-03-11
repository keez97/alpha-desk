#!/usr/bin/env python3
"""
Validation script for Features 8 & 10 implementation.
Checks all files exist, imports work, and basic functionality is correct.
"""
import sys
import os
from pathlib import Path

def check_file_exists(path: str) -> bool:
    """Check if file exists."""
    exists = Path(path).exists()
    status = "✓" if exists else "✗"
    print(f"{status} {path}")
    return exists

def check_import(module_path: str, class_name: str = None) -> bool:
    """Check if module can be imported."""
    try:
        parts = module_path.split('.')
        exec(f"from {'.'.join(parts[:-1])} import {parts[-1]}")
        status = "✓"
        print(f"{status} {module_path}")
        return True
    except Exception as e:
        print(f"✗ {module_path}: {e}")
        return False

def main():
    print("=" * 60)
    print("AlphaDesk Features 8 & 10 Validation Check")
    print("=" * 60)

    all_good = True

    # Check backend services
    print("\n[Backend Services]")
    all_good &= check_file_exists("backend/services/sector_transitions.py")
    all_good &= check_file_exists("backend/services/scenario_risk.py")

    # Check backend routers
    print("\n[Backend Routers]")
    all_good &= check_file_exists("backend/routers/sector_transitions.py")
    all_good &= check_file_exists("backend/routers/scenario_risk.py")

    # Check frontend hooks
    print("\n[Frontend Hooks]")
    all_good &= check_file_exists("frontend/src/hooks/useSectorTransitions.ts")
    all_good &= check_file_exists("frontend/src/hooks/useScenarioRisk.ts")

    # Check frontend components
    print("\n[Frontend Components]")
    all_good &= check_file_exists("frontend/src/components/morning-brief/SectorTransitionsPanel.tsx")
    all_good &= check_file_exists("frontend/src/components/morning-brief/ScenarioRiskPanel.tsx")

    # Check backend imports
    print("\n[Backend Imports]")
    all_good &= check_import("backend.services.sector_transitions.get_sector_transitions")
    all_good &= check_import("backend.services.scenario_risk.get_scenario_risk_data")
    all_good &= check_import("backend.routers.sector_transitions.router")
    all_good &= check_import("backend.routers.scenario_risk.router")

    # Check main.py registration
    print("\n[Main.py Registration]")
    try:
        with open("backend/main.py", "r") as f:
            content = f.read()
            has_imports = "sector_transitions" in content and "scenario_risk" in content
            has_routers = "app.include_router(sector_transitions.router)" in content
            has_routers &= "app.include_router(scenario_risk.router)" in content

            status = "✓" if has_imports and has_routers else "✗"
            print(f"{status} Sector transitions imports: {has_imports}")
            print(f"{status} Scenario risk imports: {has_imports}")
            print(f"{status} Router registration: {has_routers}")
            all_good &= has_imports and has_routers
    except Exception as e:
        print(f"✗ Error reading main.py: {e}")
        all_good = False

    # Check API functions added
    print("\n[API Client Functions]")
    try:
        with open("frontend/src/lib/api.ts", "r") as f:
            content = f.read()
            has_fetch_st = "fetchSectorTransitions" in content
            has_fetch_sr = "fetchScenarioRisk" in content

            status_st = "✓" if has_fetch_st else "✗"
            status_sr = "✓" if has_fetch_sr else "✗"
            print(f"{status_st} fetchSectorTransitions function")
            print(f"{status_sr} fetchScenarioRisk function")
            all_good &= has_fetch_st and has_fetch_sr
    except Exception as e:
        print(f"✗ Error reading api.ts: {e}")
        all_good = False

    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print("✓ All validation checks passed!")
        print("\nNext steps:")
        print("1. Start backend: python backend/main.py")
        print("2. Start frontend: npm run dev")
        print("3. Test endpoints: curl http://localhost:8000/api/sector-transitions")
        print("4. Add panels to MorningBriefPage component")
        return 0
    else:
        print("✗ Some validation checks failed")
        print("Review the errors above and fix issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
