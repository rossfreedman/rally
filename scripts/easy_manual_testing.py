#!/usr/bin/env python3
"""
Easy Manual PTI Testing Helper

If automation fails, this makes manual testing super easy.
Just copy/paste results from the original site.
"""

import json
import webbrowser
from typing import Dict, List, Any

# Same test cases as automation
STRATEGIC_TEST_CASES = [
    {
        "id": 1,
        "player_pti": 50, "partner_pti": 40, "opp1_pti": 30, "opp2_pti": 23,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-2,2-6,6-3",
        "description": "Your Original Case (Known Result)"
    },
    {
        "id": 2,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 30, "opp2_pti": 30,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Equal Teams, Player Wins"
    },
    {
        "id": 3,
        "player_pti": 40, "partner_pti": 40, "opp1_pti": 25, "opp2_pti": 25,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-3,6-4",
        "description": "Big Underdogs Win (Upset)"
    },
    {
        "id": 4,
        "player_pti": 25, "partner_pti": 25, "opp1_pti": 40, "opp2_pti": 40,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-3,6-4",
        "description": "Big Favorites Win (Expected)"
    },
    {
        "id": 5,
        "player_pti": 28, "partner_pti": 32, "opp1_pti": 30, "opp2_pti": 35,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "7-5,6-4",
        "description": "Close Match, Favorites Win"
    },
    {
        "id": 6,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 30, "opp2_pti": 30,
        "player_exp": "New Player", "partner_exp": "New Player", "opp1_exp": "30+ matches", "opp2_exp": "30+ matches",
        "score": "6-4,6-4",
        "description": "Different Experience Levels"
    },
    {
        "id": 7,
        "player_pti": 25, "partner_pti": 25, "opp1_pti": 40, "opp2_pti": 40,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-1,6-2",
        "description": "Blowout Win by Favorites"
    },
    {
        "id": 8,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 32, "opp2_pti": 32,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "7-6,4-6,7-6",
        "description": "Very Close 3-Set Match"
    },
    {
        "id": 9,
        "player_pti": 20, "partner_pti": 20, "opp1_pti": 50, "opp2_pti": 50,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "High PTI vs Low PTI"
    },
    {
        "id": 10,
        "player_pti": 50, "partner_pti": 20, "opp1_pti": 35, "opp2_pti": 35,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-3,6-4",
        "description": "Mixed Team vs Balanced Team"
    },
    {
        "id": 11,
        "player_pti": 50, "partner_pti": 40, "opp1_pti": 30, "opp2_pti": 23,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "2-6,6-2,3-6",
        "description": "Player Loses (Same as Case 1 but Reversed Score)"
    },
    {
        "id": 12,
        "player_pti": 30, "partner_pti": 30, "opp1_pti": 30, "opp2_pti": 30,
        "player_exp": "10-30 Matches", "partner_exp": "10-30 Matches", "opp1_exp": "30+ matches", "opp2_exp": "30+ matches",
        "score": "6-4,6-4",
        "description": "Moderate Experience vs Experienced"
    },
    {
        "id": 13,
        "player_pti": 45, "partner_pti": 45, "opp1_pti": 25, "opp2_pti": 25,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-2,6-3",
        "description": "Large Spread, Underdogs Win"
    },
    {
        "id": 14,
        "player_pti": 29, "partner_pti": 31, "opp1_pti": 32, "opp2_pti": 32,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-4,6-4",
        "description": "Small Spread, Favorites Win"
    },
    {
        "id": 15,
        "player_pti": 35, "partner_pti": 35, "opp1_pti": 35, "opp2_pti": 35,
        "player_exp": "1-10 matches", "partner_exp": "1-10 matches", "opp1_exp": "30+ matches", "opp2_exp": "30+ matches",
        "score": "6-4,6-4",
        "description": "Same PTIs, Different Experience"
    }
]

def normalize_experience(exp: str) -> str:
    """Normalize experience to full dropdown text"""
    if exp == "30+":
        return "30+ matches"
    elif exp == "10-30":
        return "10-30 Matches"
    elif exp == "1-10":
        return "1-10 matches"
    elif exp == "New":
        return "New Player"
    else:
        return exp

def interactive_testing():
    """Interactive testing with prompts"""
    print("🎯 Interactive Manual Testing")
    print("=" * 40)
    
    # Open the calculator
    print("Opening PTI calculator in your browser...")
    webbrowser.open("https://calc.platform.tennis/calculator2.html")
    
    results = []
    
    for case in STRATEGIC_TEST_CASES:
        print(f"\n📋 Test Case {case['id']}: {case['description']}")
        print("-" * 50)
        
        # Show what to enter
        print("Enter these values:")
        print(f"Player PTI: {case['player_pti']}")
        print(f"Player Exp: {normalize_experience(case['player_exp'])}")
        print(f"Partner PTI: {case['partner_pti']}")
        print(f"Partner Exp: {normalize_experience(case['partner_exp'])}")
        print(f"Score: {case['score']}")
        print(f"Opp PTI: {case['opp1_pti']}")
        print(f"Opp Exp: {normalize_experience(case['opp1_exp'])}")
        print(f"Opp PTI: {case['opp2_pti']}")
        print(f"Opp Exp: {normalize_experience(case['opp2_exp'])}")
        
        # Get results
        input("\nPress Enter after filling in the form...")
        
        print("\nNow enter the results:")
        try:
            spread = float(input("Spread: "))
            adjustment = float(input("Adjustment: "))
            
            player_after = float(input("Player PTI After: "))
            partner_after = float(input("Partner PTI After: "))
            opp1_after = float(input("Opp1 PTI After: "))
            opp2_after = float(input("Opp2 PTI After: "))
            
            result = {
                "id": case["id"],
                "description": case["description"],
                "spread": spread,
                "adjustment": adjustment,
                "player_before": case["player_pti"],
                "player_after": player_after,
                "partner_before": case["partner_pti"],
                "partner_after": partner_after,
                "opp1_before": case["opp1_pti"],
                "opp1_after": opp1_after,
                "opp2_before": case["opp2_pti"],
                "opp2_after": opp2_after,
                "success": True
            }
            
            results.append(result)
            print(f"✅ Case {case['id']} recorded!")
            
        except ValueError:
            print("❌ Invalid input, skipping case")
            continue
    
    # Save results
    with open("manual_focused_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n🎉 Completed! Saved {len(results)} results to manual_focused_results.json")
    
    # Copy to analysis filename
    with open("focused_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("📊 Running analysis...")
    import subprocess
    subprocess.run(["python", "analyze_focused_results.py"])

def batch_entry():
    """Batch entry mode - paste all results at once"""
    print("📝 Batch Entry Mode")
    print("=" * 30)
    
    print("Go to https://calc.platform.tennis/calculator2.html")
    print("Test all 15 cases and collect results.")
    print("Then enter results in this format:")
    print("Case ID, Spread, Adjustment, Player After, Partner After, Opp1 After, Opp2 After")
    print("Example: 1, 37.0, 2.30, 47.70, 37.70, 32.39, 25.39")
    print("\nEnter 'done' when finished:")
    
    results = []
    case_lookup = {case["id"]: case for case in STRATEGIC_TEST_CASES}
    
    while True:
        line = input("Result: ").strip()
        if line.lower() == 'done':
            break
            
        try:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) != 7:
                print("❌ Need exactly 7 values: Case ID, Spread, Adjustment, Player After, Partner After, Opp1 After, Opp2 After")
                continue
            
            case_id = int(parts[0])
            spread = float(parts[1])
            adjustment = float(parts[2])
            player_after = float(parts[3])
            partner_after = float(parts[4])
            opp1_after = float(parts[5])
            opp2_after = float(parts[6])
            
            if case_id not in case_lookup:
                print(f"❌ Unknown case ID: {case_id}")
                continue
            
            case = case_lookup[case_id]
            result = {
                "id": case_id,
                "description": case["description"],
                "spread": spread,
                "adjustment": adjustment,
                "player_before": case["player_pti"],
                "player_after": player_after,
                "partner_before": case["partner_pti"],
                "partner_after": partner_after,
                "opp1_before": case["opp1_pti"],
                "opp1_after": opp1_after,
                "opp2_before": case["opp2_pti"],
                "opp2_after": opp2_after,
                "success": True
            }
            
            results.append(result)
            print(f"✅ Case {case_id} recorded!")
            
        except ValueError as e:
            print(f"❌ Error parsing: {e}")
            continue
    
    # Save results
    with open("batch_focused_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n🎉 Completed! Saved {len(results)} results to batch_focused_results.json")
    
    # Copy to analysis filename
    with open("focused_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("📊 Running analysis...")
    import subprocess
    subprocess.run(["python", "analyze_focused_results.py"])

def main():
    """Main function"""
    print("🎯 Easy Manual PTI Testing")
    print("=" * 40)
    print("Choose your testing method:")
    print("1. Interactive (step-by-step prompts)")
    print("2. Batch (paste all results at once)")
    print("3. Show test cases only")
    
    choice = input("\nChoice (1-3): ").strip()
    
    if choice == "1":
        interactive_testing()
    elif choice == "2":
        batch_entry()
    elif choice == "3":
        print("\nTest Cases:")
        for case in STRATEGIC_TEST_CASES:
            print(f"\nCase {case['id']}: {case['description']}")
            print(f"Player: {case['player_pti']} ({normalize_experience(case['player_exp'])})")
            print(f"Partner: {case['partner_pti']} ({normalize_experience(case['partner_exp'])})")
            print(f"Opp1: {case['opp1_pti']} ({normalize_experience(case['opp1_exp'])})")
            print(f"Opp2: {case['opp2_pti']} ({normalize_experience(case['opp2_exp'])})")
            print(f"Score: {case['score']}")
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main() 