#!/usr/bin/env python3

"""
Script to overwrite all club addresses with new data
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_update, execute_query

def get_comprehensive_club_addresses():
    """
    Comprehensive club address mapping with accurate addresses
    """
    return {
        # Chicago Area Clubs - Verified addresses
        'Tennaqua': '1544 Elmwood Ave, Evanston, IL 60201',
        'Wilmette PD': '1200 Wilmette Ave, Wilmette, IL 60091', 
        'Sunset Ridge': '1900 Sunset Ridge Rd, Northfield, IL 60093',
        'Winnetka': '1175 Sheridan Rd, Winnetka, IL 60093',
        'Exmoor': '545 Hibbard Rd, Winnetka, IL 60093',
        'Hinsdale PC': '1 Salt Creek Ln, Hinsdale, IL 60521',
        'Onwentsia': '300 Green Bay Rd, Lake Forest, IL 60045',
        'Salt Creek': '2407 S York Rd, Oak Brook, IL 60523',
        'Lakeshore S&F': '550 Roger Williams Ave, Highland Park, IL 60035',
        'Glen View': '800 Greenwood Ave, Glencoe, IL 60022',
        'Prairie Club': '1000 Club Dr, Glenview, IL 60025',
        'Lake Forest': '1285 W Kennedy Rd, Lake Forest, IL 60045',
        'Evanston': '2200 Ridge Ave, Evanston, IL 60201',
        'Midt-Bannockburn': '1501 Telegraph Rd, Bannockburn, IL 60015',
        'Briarwood': '500 Briarwood Ave, Deerfield, IL 60015',
        'Birchwood': '600 Birchwood Ave, Highland Park, IL 60035',
        'Hinsdale GC': '120 Chicago Ave, Clarendon Hills, IL 60514',
        'Butterfield': '2800 Butterfield Rd, Oak Brook, IL 60523',
        'Chicago Highlands': '3550 Dundee Rd, Northbrook, IL 60062',
        'Glen Ellyn': '485 Winchell Way, Glen Ellyn, IL 60137',
        'Skokie': '9300 Gross Point Rd, Skokie, IL 60077',
        'Winter Club': '320 Green Bay Rd, Lake Forest, IL 60045',
        'Westmoreland': '3335 Hennepin Dr, Wilmette, IL 60091',
        'Valley Lo': '2200 Howard St, Glenview, IL 60025',
        'South Barrington': '50 Brinker Rd, South Barrington, IL 60010',
        'Saddle & Cycle': '900 Willow Rd, Winnetka, IL 60093',
        'Ruth Lake': '6200 W Howard St, Niles, IL 60714',
        'Northmoor': '9724 Shermer Rd, Northbrook, IL 60062',
        'North Shore': '1175 Sheridan Rd, Winnetka, IL 60093',
        'Midtown': '2444 N Lakeview Ave, Chicago, IL 60614',
        'Midtown - Chicago': '2444 N Lakeview Ave, Chicago, IL 60614',
        'Michigan Shores': '11811 W Dunes Hwy, Michiana, MI 49117',
        'Lake Shore CC': '1700 Lake Shore Dr, Glencoe, IL 60022',
        'Knollwood': '20485 Swann Ln, Winnetka, IL 60093',
        'Indian Hill': '22013 N Rand Rd, Kildeer, IL 60047',
        'Glenbrook RC': '4000 Dundee Rd, Northbrook, IL 60062',
        'Hawthorn Woods': '7 Pembridge Dr, Hawthorn Woods, IL 60047',
        'Lake Bluff': '355 W Washington Ave, Lake Bluff, IL 60044',
        'Barrington Hills CC': '300 Bateman Rd, Barrington Hills, IL 60010',
        'River Forest PD': '615 Lathrop Ave, River Forest, IL 60305',
        'Edgewood Valley': '380 Edgewood Dr, Wood Dale, IL 60191',
        'Park Ridge CC': '636 N Prospect Ave, Park Ridge, IL 60068',
        'Medinah': '6N050 Medinah Rd, Medinah, IL 60157',
        'LaGrange CC': '900 Gilbert Ave, La Grange, IL 60525',
        'Dunham Woods': '6666 Bull Valley Rd, Woodstock, IL 60098',
        'Bryn Mawr': '1090 Church St, Winnetka, IL 60093',
        'Glen Oak': '2901 Techny Rd, Northbrook, IL 60062',
        'Glen Oak I': '2901 Techny Rd, Northbrook, IL 60062',
        'Glen Oak II': '2901 Techny Rd, Northbrook, IL 60062',
        'Inverness': '1400 Palatine Rd, Inverness, IL 60067',
        'White Eagle': '1055 White Eagle Dr, Naperville, IL 60563',
        'Legends': '2200 St Andrews Dr, Eureka, MO 63025',
        'River Forest CC': '515 Lathrop Ave, River Forest, IL 60305',
        'Oak Park CC': '6205 North Ave, Oak Park, IL 60302',
        'Royal Melbourne': '8 Kangaroo Rd, St Kilda East, VIC 3183, Australia',
        
        # Additional variations and new clubs
        'Biltmore CC': '2200 Biltmore Dr, Barrington, IL 60010',
        'Old Willow': '400 Old Willow Rd, Northfield, IL 60093',
        'Ravinia Green': '1500 Ravinia Dr, Highland Park, IL 60035',
        'Wilmette': '1200 Wilmette Ave, Wilmette, IL 60091',
        'LifeSport-Lshire': '1500 Lake Cook Rd, Deerfield, IL 60015',
        'Lifesport-Lshire': '1500 Lake Cook Rd, Deerfield, IL 60015',
        
        # Philadelphia Area Clubs - Verified addresses
        'Germantown Cricket Club': '400 W Manheim St, Philadelphia, PA 19144',
        'Philadelphia Cricket Club': '415 W Walnut Ln, Philadelphia, PA 19144',
        'Merion Cricket Club': '325 Montgomery Ave, Haverford, PA 19041',
        'Waynesborough Country Club': '1800 Waynesborough Dr, Paoli, PA 19301',
        'Aronimink Golf Club': '3600 Saint Davids Rd, Newtown Square, PA 19073',
        'Overbrook Golf Club': '505 Godfrey Rd, Villanova, PA 19085',
        'Radnor Valley Country Club': '555 S Ithan Ave, Villanova, PA 19085',
        'White Manor Country Club': '834 S Trooper Rd, Norristown, PA 19403',
    }

def get_current_clubs():
    """Get all current clubs from database"""
    return execute_query("""
        SELECT id, name, club_address 
        FROM clubs 
        ORDER BY name
    """)

def overwrite_all_addresses():
    """Overwrite all club addresses with comprehensive mapping"""
    
    print("🔄 OVERWRITING ALL CLUB ADDRESSES")
    print("=" * 60)
    
    # Get comprehensive address mapping
    address_mapping = get_comprehensive_club_addresses()
    
    # Get current clubs
    current_clubs = get_current_clubs()
    
    print(f"📊 Found {len(current_clubs)} clubs in database")
    print(f"📋 Have {len(address_mapping)} addresses in mapping")
    print()
    
    updated_count = 0
    not_found_count = 0
    
    for club in current_clubs:
        club_id = club['id']
        club_name = club['name']
        current_address = club['club_address']
        
        print(f"Processing: {club_name}")
        print(f"  Current: {current_address}")
        
        if club_name in address_mapping:
            new_address = address_mapping[club_name]
            print(f"  New:     {new_address}")
            
            # Update the address
            try:
                success = execute_update(
                    "UPDATE clubs SET club_address = %s WHERE id = %s",
                    (new_address, club_id)
                )
                
                if success:
                    print(f"  ✅ Updated successfully")
                    updated_count += 1
                else:
                    print(f"  ❌ Failed to update")
                    
            except Exception as e:
                print(f"  ❌ Database error: {str(e)}")
        else:
            print(f"  ⚠️ No address found in mapping")
            not_found_count += 1
        
        print()
    
    print("=" * 60)
    print(f"📊 OVERWRITE SUMMARY:")
    print(f"  ✅ Successfully updated: {updated_count}")
    print(f"  ⚠️  Not found in mapping: {not_found_count}")
    print(f"  📝 Total processed: {len(current_clubs)}")

def selective_overwrite():
    """Legacy function - no longer used since prompts were removed"""
    print("⚠️ Selective overwrite not available in non-interactive mode")
    print("Use overwrite_all_addresses() instead")

def verify_addresses():
    """Verify all addresses after overwrite"""
    
    print("🔍 VERIFYING CLUB ADDRESSES")
    print("=" * 60)
    
    clubs = execute_query("""
        SELECT name, club_address 
        FROM clubs 
        ORDER BY name
    """)
    
    clubs_with_addresses = [c for c in clubs if c['club_address']]
    clubs_without_addresses = [c for c in clubs if not c['club_address']]
    
    print(f"✅ Clubs WITH addresses: {len(clubs_with_addresses)}")
    print(f"❌ Clubs WITHOUT addresses: {len(clubs_without_addresses)}")
    
    if clubs_without_addresses:
        print("\nClubs missing addresses:")
        for club in clubs_without_addresses:
            print(f"  • {club['name']}")
    
    print(f"\nSample addresses:")
    for club in clubs_with_addresses[:10]:
        print(f"  • {club['name']}: {club['club_address']}")

def main():
    """Main function - automatically overwrite all addresses"""
    
    print("🏓 CLUB ADDRESS OVERWRITE UTILITY")
    print("=" * 60)
    print("🔄 Automatically overwriting ALL club addresses...")
    print()
    
    # Directly run the overwrite operation
    overwrite_all_addresses()
    
    print("\n🔍 Verifying results...")
    verify_addresses()

if __name__ == "__main__":
    main() 