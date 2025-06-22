#!/usr/bin/env python3

"""
Script to populate club addresses for variations by using existing base club addresses
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update


def populate_club_variations():
    """Populate addresses for club variations using base club addresses"""

    print("🔧 Populating club variations with base club addresses...")
    print("=" * 60)

    # Get clubs without addresses
    clubs_without = execute_query(
        """
        SELECT id, name FROM clubs 
        WHERE club_address IS NULL OR club_address = ''
        ORDER BY name
    """
    )

    # Get clubs with addresses
    clubs_with = execute_query(
        """
        SELECT name, club_address FROM clubs
        WHERE club_address IS NOT NULL AND club_address != ''
        ORDER BY name
    """
    )

    # Create a mapping of base club names to addresses
    base_addresses = {}
    for club in clubs_with:
        base_addresses[club["name"]] = club["club_address"]

    print(f"Found {len(clubs_without)} clubs without addresses")
    print(f"Found {len(clubs_with)} clubs with addresses to use as base")
    print()

    # Manual address mappings for specific clubs
    manual_addresses = {
        # Clubs that need manual research
        "Biltmore CC": "2200 Biltmore Dr, Barrington, IL 60010",
        "Midtown": "2444 N Lakeview Ave, Chicago, IL 60614",
        "Old Willow": "400 Old Willow Rd, Northfield, IL 60093",
        "Ravinia Green": "1500 Ravinia Dr, Highland Park, IL 60035",
        "Wilmette": "1200 Wilmette Ave, Wilmette, IL 60091",
        "LifeSport-Lshire": "1500 Lake Cook Rd, Deerfield, IL 60015",
        "Lifesport-Lshire": "1500 Lake Cook Rd, Deerfield, IL 60015",
        # Philadelphia area clubs (these might need verification)
        "Germantown Cricket Club": "400 W Manheim St, Philadelphia, PA 19144",
        "Philadelphia Cricket Club": "415 W Walnut Ln, Philadelphia, PA 19144",
        "Merion Cricket Club": "325 Montgomery Ave, Haverford, PA 19041",
        "Waynesborough Country Club": "1800 Waynesborough Dr, Paoli, PA 19301",
        "Aronimink Golf Club": "3600 Saint Davids Rd, Newtown Square, PA 19073",
        "Overbrook Golf Club": "505 Godfrey Rd, Villanova, PA 19085",
        "Radnor Valley Country Club": "555 S Ithan Ave, Villanova, PA 19085",
        "White Manor Country Club": "834 S Trooper Rd, Norristown, PA 19403",
    }

    updated_count = 0

    for club in clubs_without:
        club_id = club["id"]
        club_name = club["name"]

        print(f"Processing: {club_name}")

        address_to_use = None

        # Strategy 1: Check manual mappings first
        if club_name in manual_addresses:
            address_to_use = manual_addresses[club_name]
            print(f"  ✓ Using manual address: {address_to_use}")

        # Strategy 2: Handle variations (I, II, PD I, PD II, etc.)
        else:
            # Remove common suffixes to find base club
            base_name = club_name
            suffixes_to_remove = [
                " I",
                " II",
                " III",
                " PD I",
                " PD II",
                " GC I",
                " GC II",
                " CC I",
                " CC II",
            ]

            for suffix in suffixes_to_remove:
                if base_name.endswith(suffix):
                    base_name = base_name[: -len(suffix)].strip()
                    break

            # Look for base club address
            if base_name in base_addresses:
                address_to_use = base_addresses[base_name]
                print(f"  ✓ Using base club '{base_name}' address: {address_to_use}")
            else:
                print(f"  ⚠️ No base club found for '{club_name}' (tried '{base_name}')")

        # Update database if we found an address
        if address_to_use:
            try:
                success = execute_update(
                    "UPDATE clubs SET club_address = %s WHERE id = %s",
                    (address_to_use, club_id),
                )

                if success:
                    print(f"  ✅ Updated database")
                    updated_count += 1
                else:
                    print(f"  ❌ Failed to update database")

            except Exception as e:
                print(f"  ❌ Database error: {str(e)}")

        print()

    print("=" * 60)
    print(f"📊 SUMMARY:")
    print(f"  ✅ Successfully updated: {updated_count}")
    print(f"  📝 Total processed: {len(clubs_without)}")

    # Show remaining clubs without addresses
    remaining_clubs = execute_query(
        """
        SELECT name FROM clubs 
        WHERE club_address IS NULL OR club_address = ''
        ORDER BY name
    """
    )

    print(f"\n📋 Remaining clubs without addresses: {len(remaining_clubs)}")
    for club in remaining_clubs:
        print(f"  • {club['name']}")


if __name__ == "__main__":
    try:
        populate_club_variations()
        print("\n✅ Club variation population completed!")
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)
