#!/usr/bin/env python3
"""
Development tool to check routes and detect conflicts

Usage:
    python dev_tools/check_routes.py
    python dev_tools/check_routes.py --conflicts-only
    python dev_tools/check_routes.py --export routes.md
"""

import argparse
import os
import sys

# Add the parent directory to the path so we can import from the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(description="Check Flask routes for conflicts")
    parser.add_argument(
        "--conflicts-only",
        action="store_true",
        help="Only show conflicts, not full route list",
    )
    parser.add_argument(
        "--export", type=str, metavar="FILE", help="Export route documentation to file"
    )
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    args = parser.parse_args()

    # Import and create the Flask app (without running it)
    print("Loading Flask application...")

    try:
        # Import all necessary components
        from server import app
        from utils.route_validation import (
            RouteConflictDetector,
            get_routes_documentation,
        )

        print("Analyzing routes...")

        # Create detector and analyze routes
        detector = RouteConflictDetector()
        analysis = detector.analyze_app_routes(app)

        if args.json:
            # Output JSON format
            import json

            print(json.dumps(analysis, indent=2))
            return

        if args.export:
            # Export documentation to file
            docs = get_routes_documentation(app)
            with open(args.export, "w") as f:
                f.write(docs)
            print(f"Documentation exported to {args.export}")
            return

        if args.conflicts_only:
            # Show only conflicts
            if analysis["conflicts"]:
                print(f"\n⚠️  Found {len(analysis['conflicts'])} route conflicts:")
                for i, conflict in enumerate(analysis["conflicts"], 1):
                    print(f"\n  Conflict #{i}: {conflict['route']}")
                    for endpoint_info in conflict["conflicting_endpoints"]:
                        blueprint = endpoint_info["blueprint"]
                        endpoint = endpoint_info["endpoint"]
                        print(
                            f"    - {blueprint}.{endpoint} ({endpoint_info['methods']})"
                        )
            else:
                print("✅ No route conflicts detected!")
            return

        # Show full summary
        detector.print_route_summary()

        # Show conflicts if any
        if analysis["conflicts"]:
            print(f"\n⚠️  Found {len(analysis['conflicts'])} route conflicts:")
            for i, conflict in enumerate(analysis["conflicts"], 1):
                print(f"\n  Conflict #{i}: {conflict['route']}")
                for endpoint_info in conflict["conflicting_endpoints"]:
                    blueprint = endpoint_info["blueprint"]
                    endpoint = endpoint_info["endpoint"]
                    print(f"    - {blueprint}.{endpoint} ({endpoint_info['methods']})")
        else:
            print("\n✅ No route conflicts detected!")

    except Exception as e:
        print(f"Error analyzing routes: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
