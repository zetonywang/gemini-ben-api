"""
Test script for Bridge Game Analysis API with PBN Support
"""

import requests
import json

# ============== CONFIGURATION ==============
# Change this to your Railway URL
API_URL = "https://your-railway-url.up.railway.app"

# Sample PBN content
SAMPLE_PBN = """
[Event "Test Game"]
[Site "Online"]
[Date "2024.12.26"]
[Board "1"]
[North "Player N"]
[South "Player S"]
[East "Player E"]
[West "Player W"]
[Dealer "S"]
[Vulnerable "All"]
[Deal "N:AJ87632.J96.753. K9.Q8542.T6.AJ74 QT4.A.KJ94.KQ986 5.KT73.AQ82.T532"]
[Contract "4S"]
[Declarer "N"]
[Result "10"]
[Auction "S"]
1N Pass 4H Pass
4S Pass Pass Pass
[Play "E"]
C2 D3 CA C6
D6 DJ DQ D5
DA D7 DT D4
D8 H6 H2 D9
SQ S5 S2 SK
H4 HA H7 H9
S4 C3 SA S9
S3 C4 ST H3
CK C5 HJ C7
C8 CT S6 CJ
S7 H8 C9 D2
S8 H5 CQ HT
SJ HQ DK HK
"""


def test_health():
    """Test health endpoint"""
    print("\n" + "=" * 50)
    print("TEST: Health Check")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_parse_pbn():
    """Test PBN parsing only"""
    print("\n" + "=" * 50)
    print("TEST: Parse PBN")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{API_URL}/api/parse/pbn",
            json={"pbn": SAMPLE_PBN},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if data.get("success"):
            board = data.get("board", {})
            print(f"Dealer: {board.get('dealer')}")
            print(f"Vuln: {board.get('vuln')}")
            print(f"Hands: {board.get('hands')}")
            print(f"Auction: {board.get('auction')}")
            print(f"Play cards: {len(board.get('play', []))}")
        else:
            print(f"Error: {data.get('error')}")
            
        return data.get("success", False)
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_quick_analysis():
    """Test quick analysis (BEN only, no Gemini report)"""
    print("\n" + "=" * 50)
    print("TEST: Quick Analysis")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{API_URL}/api/analyze/quick",
            json={"pbn": SAMPLE_PBN},
            timeout=180
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if data.get("success"):
            print(f"Total mistakes: {data.get('total_mistakes')}")
            print(f"Total IMP cost: {data.get('total_imp_cost'):.1f}")
            
            print("\nKey Moments:")
            for i, moment in enumerate(data.get("key_moments", [])[:5], 1):
                print(f"  {i}. {moment['type']}: {moment['played']} -> {moment['recommended']} ({moment.get('imp_cost', 0):+.1f} IMP)")
        else:
            print(f"Error: {data.get('error')}")
            
        return data.get("success", False)
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_full_analysis():
    """Test full analysis with Gemini report"""
    print("\n" + "=" * 50)
    print("TEST: Full PBN Analysis with Report")
    print("=" * 50)
    
    try:
        response = requests.post(
            f"{API_URL}/api/analyze/pbn",
            json={"pbn": SAMPLE_PBN},
            timeout=300  # Longer timeout for full analysis
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if data.get("success"):
            print(f"\n✅ Analysis Complete!")
            print(f"Total mistakes: {data.get('total_mistakes')}")
            print(f"Total IMP cost: {data.get('total_imp_cost'):.1f}")
            print(f"BEN available: {data.get('ben_available')}")
            
            print("\n" + "-" * 50)
            print("KEY MOMENTS:")
            print("-" * 50)
            for i, moment in enumerate(data.get("key_moments", []), 1):
                if moment["type"] == "bidding":
                    print(f"{i}. BIDDING: {moment['played']} → {moment['recommended']}")
                else:
                    print(f"{i}. TRICK {moment['trick']}: {moment['played']} → {moment['recommended']} ({moment.get('imp_cost', 0):+.1f} IMP)")
            
            print("\n" + "-" * 50)
            print("GEMINI REPORT:")
            print("-" * 50)
            report = data.get("report", "No report generated")
            print(report[:2000] + "..." if len(report) > 2000 else report)
            
        else:
            print(f"Error: {data.get('error')}")
            
        return data.get("success", False)
    except Exception as e:
        print(f"Error: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("BRIDGE GAME ANALYSIS API - TEST SUITE")
    print(f"Testing: {API_URL}")
    print("=" * 60)
    
    results = {
        "health": test_health(),
        "parse_pbn": test_parse_pbn(),
        "quick_analysis": test_quick_analysis(),
        "full_analysis": test_full_analysis()
    }
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")


if __name__ == "__main__":
    print("=" * 60)
    print("Before running:")
    print("1. Update API_URL with your Railway URL")
    print("2. Ensure BEN is running locally with ngrok")
    print("=" * 60)
    
    confirm = input("\nReady to test? (y/n): ")
    if confirm.lower() == 'y':
        run_all_tests()
    else:
        print("Update API_URL first!")
