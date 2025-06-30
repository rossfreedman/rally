#!/usr/bin/env python3
"""
Direct PTI Calculator API Caller

This script makes direct HTTP requests to calculate PTI values
without browser automation.
"""

import requests
import json
from typing import Dict, Any

def calculate_pti_direct(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate PTI using direct API calls"""
    
    # Try different approaches based on analysis
    
    # Approach 1: Check if there's a direct API endpoint
    try:
        api_url = "https://calc.platform.tennis/api/calculate"  # Guess
        payload = {
            "player_pti": test_case["player_pti"],
            "partner_pti": test_case["partner_pti"],
            "opp1_pti": test_case["opp1_pti"],
            "opp2_pti": test_case["opp2_pti"],
            "player_exp": test_case["player_exp"],
            "partner_exp": test_case["partner_exp"],
            "opp1_exp": test_case["opp1_exp"],
            "opp2_exp": test_case["opp2_exp"],
            "score": test_case["score"]
        }
        
        response = requests.post(api_url, json=payload, timeout=10)
        if response.status_code == 200:
            return {"success": True, "result": response.json()}
    except:
        pass
    
    # Approach 2: Form submission
    try:
        form_url = "https://calc.platform.tennis/calculator2.html"
        form_data = {
            "player_pti": test_case["player_pti"],
            "partner_pti": test_case["partner_pti"],
            "opp1_pti": test_case["opp1_pti"], 
            "opp2_pti": test_case["opp2_pti"],
            "player_exp": test_case["player_exp"],
            "partner_exp": test_case["partner_exp"],
            "opp1_exp": test_case["opp1_exp"],
            "opp2_exp": test_case["opp2_exp"],
            "score": test_case["score"]
        }
        
        response = requests.post(form_url, data=form_data, timeout=10)
        if response.status_code == 200:
            # Parse HTML response for results
            return parse_html_results(response.text)
    except:
        pass
    
    return {"success": False, "error": "No direct API found"}

def parse_html_results(html: str) -> Dict[str, Any]:
    """Parse PTI results from HTML response"""
    import re
    
    # Look for result patterns in HTML
    spread_match = re.search(r'Spread:?\s*([0-9.]+)', html)
    adjustment_match = re.search(r'Adjustment:?\s*([0-9.]+)', html)
    
    if spread_match and adjustment_match:
        return {
            "success": True,
            "result": {
                "spread": float(spread_match.group(1)),
                "adjustment": float(adjustment_match.group(1))
            }
        }
    
    return {"success": False, "error": "Could not parse results"}

# Test with a simple case
if __name__ == "__main__":
    test_case = {
        "player_pti": 50, "partner_pti": 40, "opp1_pti": 30, "opp2_pti": 23,
        "player_exp": "30+", "partner_exp": "30+", "opp1_exp": "30+", "opp2_exp": "30+",
        "score": "6-2,2-6,6-3"
    }
    
    result = calculate_pti_direct(test_case)
    print(json.dumps(result, indent=2))
