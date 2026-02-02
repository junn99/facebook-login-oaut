"""Scheduled job for collecting Instagram insights."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import init_db
from src.insights_collector import collect_all_users


def run_collection():
    """Run the insights collection job."""
    print("Starting insights collection...")

    # Ensure database is initialized
    init_db()

    # Run collection
    results = collect_all_users()

    # Print summary
    print(f"\n=== Collection Summary ===")
    print(f"Total users: {results['total_users']}")
    print(f"Insights: {results['insights_success']} success, {results['insights_failed']} failed")
    print(f"Audience: {results['audience_success']} success, {results['audience_failed']} failed")

    if results["errors"]:
        print(f"\nErrors:")
        for error in results["errors"]:
            print(f"  - {error}")

    return results


if __name__ == "__main__":
    run_collection()
