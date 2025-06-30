#!/usr/bin/env python3
"""
Network Analysis for PTI Calculator

This script analyzes the original PTI calculator to find API endpoints
and reverse engineer the direct HTTP calls.
"""

import requests
import re
import json
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse

def analyze_original_site():
    """Analyze the original PTI calculator site"""
    print("🔍 Analyzing original PTI calculator site...")
    
    base_url = "https://calc.platform.tennis/calculator2.html"
    
    try:
        response = requests.get(base_url)
        html_content = response.text
        
        print(f"✅ Successfully fetched site (HTTP {response.status_code})")
        
        # Look for JavaScript functions and API endpoints
        print("\n📋 Analyzing JavaScript...")
        
        # Search for function definitions
        function_patterns = [
            r'function\s+(\w+)\s*\([^)]*\)\s*{',
            r'(\w+)\s*=\s*function\s*\([^)]*\)\s*{',
            r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*{',
        ]
        
        functions_found = []
        for pattern in function_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            functions_found.extend(matches)
        
        print(f"Found {len(functions_found)} JavaScript functions:")
        for func in sorted(set(functions_found))[:10]:  # Show first 10
            print(f"  - {func}")
        
        # Look for form submission patterns
        print("\n📡 Looking for form submission patterns...")
        
        form_patterns = [
            r'action\s*=\s*["\']([^"\']+)["\']',
            r'method\s*=\s*["\']([^"\']+)["\']',
            r'fetch\s*\(\s*["\']([^"\']+)["\']',
            r'axios\.\w+\s*\(\s*["\']([^"\']+)["\']',
            r'XMLHttpRequest.*open\s*\(\s*["\'](\w+)["\'],\s*["\']([^"\']+)["\']',
        ]
        
        endpoints_found = []
        for pattern in form_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            endpoints_found.extend(matches)
        
        if endpoints_found:
            print("Found potential endpoints:")
            for endpoint in endpoints_found:
                print(f"  - {endpoint}")
        else:
            print("No obvious form submissions found - likely client-side calculation")
        
        # Look for calculation functions
        print("\n🧮 Looking for calculation functions...")
        
        calc_patterns = [
            r'(ratingsigmaTOPerfvolatility.*?)function',
            r'(update_pti2_ratings.*?)function',
            r'(PerfvolatityTOpti2rating.*?)function',
            r'(calculatePTI.*?)function',
            r'(pti.*calc.*?)function',
        ]
        
        calc_functions = []
        for pattern in calc_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            calc_functions.extend(matches)
        
        if calc_functions:
            print("Found calculation function patterns:")
            for func in calc_functions[:3]:  # Show first 3
                preview = func[:100].replace('\n', ' ')
                print(f"  - {preview}...")
        
        # Extract the full JavaScript code for analysis
        script_tags = re.findall(r'<script[^>]*>(.*?)</script>', html_content, re.DOTALL | re.IGNORECASE)
        
        print(f"\n📄 Found {len(script_tags)} script tags")
        
        # Save the HTML and JavaScript for manual inspection
        with open("original_site_analysis.html", "w") as f:
            f.write(html_content)
        
        print("✅ Saved original site HTML to original_site_analysis.html")
        
        return {
            "success": True,
            "functions": functions_found,
            "endpoints": endpoints_found,
            "calc_functions": calc_functions,
            "script_tags": len(script_tags),
            "html_content": html_content
        }
        
    except Exception as e:
        print(f"❌ Error analyzing site: {e}")
        return {"success": False, "error": str(e)}

def extract_javascript_calculator(html_content: str) -> Optional[str]:
    """Extract the JavaScript calculator code"""
    print("\n🔧 Extracting JavaScript calculator...")
    
    # Look for the main calculation functions
    key_functions = [
        "ratingsigmaTOPerfvolatility",
        "update_pti2_ratings", 
        "PerfvolatityTOpti2rating"
    ]
    
    extracted_code = []
    
    for func_name in key_functions:
        pattern = rf'function\s+{func_name}\s*\([^)]*\)\s*{{[^}}]*}}'
        matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        if matches:
            print(f"✅ Found {func_name}")
            extracted_code.extend(matches)
        else:
            print(f"❌ Could not find {func_name}")
    
    if extracted_code:
        full_code = "\n\n".join(extracted_code)
        with open("extracted_calculator.js", "w") as f:
            f.write(full_code)
        print("✅ Saved extracted JavaScript to extracted_calculator.js")
        return full_code
    
    return None

def create_direct_api_caller():
    """Create a direct API caller based on analysis"""
    print("\n🚀 Creating direct API caller...")
    
    api_code = '''#!/usr/bin/env python3
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
    spread_match = re.search(r'Spread:?\\s*([0-9.]+)', html)
    adjustment_match = re.search(r'Adjustment:?\\s*([0-9.]+)', html)
    
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
'''
    
    with open("direct_api_caller.py", "w") as f:
        f.write(api_code)
    
    print("✅ Created direct_api_caller.py")

def main():
    """Main analysis function"""
    print("🕵️ PTI Calculator Network Analysis")
    print("=" * 50)
    
    # Step 1: Analyze the original site
    analysis = analyze_original_site()
    
    if not analysis["success"]:
        print("❌ Site analysis failed")
        return
    
    # Step 2: Extract JavaScript calculator
    js_code = extract_javascript_calculator(analysis["html_content"])
    
    # Step 3: Create direct API caller
    create_direct_api_caller()
    
    print("\n🎯 Analysis Complete!")
    print("=" * 30)
    print("Files created:")
    print("- original_site_analysis.html (full site HTML)")
    print("- extracted_calculator.js (JavaScript functions)")
    print("- direct_api_caller.py (direct API caller)")
    
    print("\nNext steps:")
    print("1. Run: python direct_api_caller.py")
    print("2. If that fails, we'll try JavaScript execution")
    print("3. If that fails, we'll use Playwright automation")

if __name__ == "__main__":
    main() 