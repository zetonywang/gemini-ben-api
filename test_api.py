"""
Test script for Gemini + BEN API
Run this after deploying to Railway to verify everything works
"""

import requests
import json

# ============== CONFIGURATION ==============
# Change this to your Railway URL after deployment
API_URL = "https://your-app-name.up.railway.app"

# Sample board data
SAMPLE_BOARD = {
    "dealer": "S",
    "vuln": [True, True],
    "hands": [
        "AJ87632.J96.753.",    # North
        "K9.Q8542.T6.AJ74",    # East  
        "QT4.A.KJ94.KQ986",    # South
        "5.KT73.AQ82.T532"     # West
    ],
    "auction": ["1N", "PASS", "4H", "PASS", "4S", "PASS", "PASS", "PASS"],
    "play": [
        "C2", "D3", "CA", "C6", "D6", "DJ", "DQ", "D5",
        "DA", "D7", "DT", "D4", "D8", "H6", "H2", "D9",
        "SQ", "S5", "S2", "SK", "H4", "HA", "H7", "H9",
        "S4", "C3", "SA", "S9", "S3", "C4", "ST", "H3",
        "CK", "C5", "HJ", "C7", "C8", "CT", "S6", "CJ",
        "S7", "H8", "C9", "D2", "S8", "H5", "CQ", "HT",
        "SJ", "HQ", "DK", "HK"
    ]
}


def test_health():
    """Test health endpoint"""
    print("\n" + "=" * 50)
    print("TEST: Health Check")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_home():
    """Test home endpoint"""
    print("\n" + "=" * 50)
    print("TEST: Home Page")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_URL}/", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_gemini_only():
    """Test Gemini-only analysis"""
    print("\n" + "=" * 50)
    print("TEST: Gemini Only Analysis")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{API_URL}/api/analyze/gemini",
            json=SAMPLE_BOARD,
            timeout=60
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        if data.get('success'):
            print(f"Analysis preview: {data.get('analysis', '')[:500]}...")
        else:
            print(f"Error: {data.get('error')}")
        return data.get('success', False)
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_ben_only():
    """Test BEN-only analysis"""
    print("\n" + "=" * 50)
    print("TEST: BEN Only Analysis")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{API_URL}/api/analyze/ben",
            json=SAMPLE_BOARD,
            timeout=120
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        if data.get('success'):
            print(f"Formatted analysis preview:\n{data.get('formatted', '')[:500]}...")
        else:
            print(f"Error: {data.get('error')}")
        return data.get('success', False)
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_combined():
    """Test combined Gemini + BEN analysis"""
    print("\n" + "=" * 50)
    print("TEST: Combined Gemini + BEN Analysis")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{API_URL}/api/analyze/combined",
            json=SAMPLE_BOARD,
            timeout=180
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        if data.get('success'):
            print(f"Gemini analysis preview:\n{data.get('gemini_analysis', '')[:500]}...")
        else:
            print(f"Error: {data.get('error')}")
        return data.get('success', False)
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_compare():
    """Test comparison endpoint"""
    print("\n" + "=" * 50)
    print("TEST: Compare All Three")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{API_URL}/api/analyze/compare",
            json=SAMPLE_BOARD,
            timeout=180
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        
        comparisons = data.get('comparisons', {})
        for key, value in comparisons.items():
            print(f"\n{key}: {value.get('status')}")
            
        return data.get('success', False)
    except Exception as e:
        print(f"Error: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("GEMINI + BEN API TEST SUITE")
    print(f"Testing: {API_URL}")
    print("=" * 60)
    
    results = {
        "health": test_health(),
        "home": test_home(),
        "gemini_only": test_gemini_only(),
        "ben_only": test_ben_only(),
        "combined": test_combined(),
        "compare": test_compare()
    }
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} tests passed")


if __name__ == "__main__":
    print("=" * 60)
    print("Before running, make sure to:")
    print("1. Update API_URL with your Railway URL")
    print("2. Ensure BEN is running locally with ngrok")
    print("=" * 60)
    
    confirm = input("\nHave you updated the API_URL? (y/n): ")
    if confirm.lower() == 'y':
        run_all_tests()
    else:
        print("Please update API_URL in this script first!")
