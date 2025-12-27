"""
Gemini + BEN Bridge Analysis API
Deployed on Railway
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import requests
import os

app = Flask(__name__)
CORS(app)

# ============== CONFIGURATION ==============

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BEN_API_URL = os.environ.get("BEN_API_URL")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ============== HELPER FUNCTIONS ==============

def call_ben_api(board_data: dict) -> dict:
    """Call BEN API for analysis"""
    try:
        response = requests.post(
            f"{BEN_API_URL}/api/analyze/manual",
            json=board_data,
            headers={
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            },
            timeout=120
        )
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_ben_analysis(ben_result: dict) -> str:
    """Format BEN analysis into readable text"""
    if not ben_result or not ben_result.get("success"):
        return "BEN analysis unavailable"
    
    output = []
    output.append("=" * 50)
    output.append("BEN ENGINE ANALYSIS")
    output.append("=" * 50)
    
    # Bid Analysis
    output.append("\n### BIDDING ANALYSIS ###\n")
    for i, bid_info in enumerate(ben_result.get("bid_analysis", [])):
        bid = bid_info.get("bid", "?")
        quality = bid_info.get("quality", "?")
        
        candidates = bid_info.get("candidates", [])
        if candidates:
            best = candidates[0]
            recommended = best.get("call", bid)
            explanation = best.get("explanation", "")
        else:
            recommended = bid
            explanation = bid_info.get("explanation", "")
        
        output.append(f"Bid #{i+1}: {bid}")
        output.append(f"  Quality: {quality}")
        if bid != recommended:
            output.append(f"  ⚠️ BEN recommends: {recommended}")
        output.append(f"  Explanation: {explanation}")
        output.append("")
    
    # Card Play Analysis
    output.append("\n### CARD PLAY ANALYSIS ###\n")
    card_analysis = ben_result.get("card_analysis", {})
    
    mistakes = []
    for card_key, analysis in card_analysis.items():
        played = card_key
        recommended = analysis.get("card", played)
        who = analysis.get("who", "")
        
        # Skip forced plays
        if who in ["Forced", "Follow"]:
            continue
            
        if played != recommended:
            candidates = analysis.get("candidates", [])
            
            output.append(f"❌ {played} played, BEN recommends {recommended}")
            for cand in candidates[:3]:
                card = cand.get("card", "?")
                imp = cand.get("expected_score_imp", 0)
                output.append(f"   - {card}: {imp:+.2f} IMPs")
            output.append("")
            mistakes.append(played)
    
    if not mistakes:
        output.append("✅ No significant mistakes found in card play")
    else:
        output.append(f"\nTotal mistakes found: {len(mistakes)}")
    
    return "\n".join(output)


def analyze_with_gemini(board_data: dict, ben_analysis: str = None) -> str:
    """Analyze with Gemini, optionally with BEN data"""
    
    if not GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not configured"
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    base_info = f"""**Dealer:** {board_data['dealer']}
**Vulnerability:** NS={'Vul' if board_data['vuln'][0] else 'NV'}, EW={'Vul' if board_data['vuln'][1] else 'NV'}

**Hands (Spades.Hearts.Diamonds.Clubs):**
- North: {board_data['hands'][0]}
- East:  {board_data['hands'][1]}
- South: {board_data['hands'][2]}
- West:  {board_data['hands'][3]}

**Auction:** {' - '.join(board_data['auction'])}

**Play:** {' '.join(board_data['play'])}
"""
    
    if ben_analysis:
        prompt = f"""You are an expert bridge analyst with access to BEN, a world-class bridge AI.

{base_info}

{ben_analysis}

Using BEN's analysis, provide:
1. Summary of bidding mistakes (if any)
2. Explain WHY BEN's card play recommendations are better
3. Calculate total IMP cost of mistakes
4. Key lessons from this hand
5. Rate declarer's play 1-10

Explain BEN's insights in simple, human-understandable terms.
"""
    else:
        prompt = f"""You are an expert bridge analyst. Analyze this board:

{base_info}

Provide:
1. Bidding analysis - any mistakes?
2. Card play analysis - any errors?
3. Optimal line of play
4. Expected tricks for declarer
5. Overall assessment

Be specific about mistakes and improvements.
"""
    
    response = model.generate_content(prompt)
    return response.text


# ============== API ENDPOINTS ==============

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "Gemini + BEN Bridge Analysis API",
        "status": "running",
        "endpoints": {
            "GET /": "This info page",
            "GET /health": "Health check",
            "POST /api/analyze/gemini": "Gemini-only analysis",
            "POST /api/analyze/ben": "BEN-only analysis",
            "POST /api/analyze/combined": "Gemini + BEN analysis",
            "POST /api/analyze/compare": "Compare all three"
        },
        "configuration": {
            "ben_configured": BEN_API_URL is not None,
            "gemini_configured": GEMINI_API_KEY is not None
        }
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "ben_url": BEN_API_URL is not None,
        "gemini_key": GEMINI_API_KEY is not None
    })


@app.route("/api/analyze/gemini", methods=["POST"])
def analyze_gemini_only():
    """Gemini analysis without BEN"""
    try:
        board_data = request.json
        
        if not GEMINI_API_KEY:
            return jsonify({
                "success": False,
                "error": "GEMINI_API_KEY not configured"
            }), 500
        
        analysis = analyze_with_gemini(board_data, ben_analysis=None)
        
        return jsonify({
            "success": True,
            "source": "gemini",
            "analysis": analysis
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze/ben", methods=["POST"])
def analyze_ben_only():
    """BEN analysis only"""
    try:
        board_data = request.json
        
        if not BEN_API_URL:
            return jsonify({
                "success": False,
                "error": "BEN_API_URL not configured"
            }), 500
        
        ben_result = call_ben_api(board_data)
        ben_formatted = format_ben_analysis(ben_result)
        
        return jsonify({
            "success": ben_result.get("success", False),
            "source": "ben",
            "raw": ben_result,
            "formatted": ben_formatted
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze/combined", methods=["POST"])
def analyze_combined():
    """Gemini analysis enhanced with BEN"""
    try:
        board_data = request.json
        
        if not GEMINI_API_KEY:
            return jsonify({
                "success": False,
                "error": "GEMINI_API_KEY not configured"
            }), 500
            
        if not BEN_API_URL:
            return jsonify({
                "success": False,
                "error": "BEN_API_URL not configured"
            }), 500
        
        # Get BEN analysis
        ben_result = call_ben_api(board_data)
        ben_formatted = format_ben_analysis(ben_result)
        
        # Get Gemini analysis with BEN context
        gemini_analysis = analyze_with_gemini(board_data, ben_analysis=ben_formatted)
        
        return jsonify({
            "success": True,
            "source": "gemini+ben",
            "ben_raw": ben_result,
            "ben_formatted": ben_formatted,
            "gemini_analysis": gemini_analysis
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze/compare", methods=["POST"])
def analyze_compare():
    """Compare Gemini alone vs Gemini + BEN"""
    try:
        board_data = request.json
        
        results = {
            "success": True,
            "board": board_data,
            "comparisons": {}
        }
        
        # 1. Gemini only
        if GEMINI_API_KEY:
            try:
                results["comparisons"]["gemini_only"] = {
                    "status": "success",
                    "analysis": analyze_with_gemini(board_data, ben_analysis=None)
                }
            except Exception as e:
                results["comparisons"]["gemini_only"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            results["comparisons"]["gemini_only"] = {
                "status": "not_configured",
                "error": "GEMINI_API_KEY not set"
            }
        
        # 2. BEN only
        if BEN_API_URL:
            ben_result = call_ben_api(board_data)
            ben_formatted = format_ben_analysis(ben_result)
            results["comparisons"]["ben_only"] = {
                "status": "success" if ben_result.get("success") else "error",
                "raw": ben_result,
                "formatted": ben_formatted
            }
        else:
            results["comparisons"]["ben_only"] = {
                "status": "not_configured",
                "error": "BEN_API_URL not set"
            }
            ben_result = None
            ben_formatted = None
        
        # 3. Gemini + BEN
        if GEMINI_API_KEY and BEN_API_URL and ben_result and ben_result.get("success"):
            try:
                results["comparisons"]["gemini_with_ben"] = {
                    "status": "success",
                    "analysis": analyze_with_gemini(board_data, ben_analysis=ben_formatted)
                }
            except Exception as e:
                results["comparisons"]["gemini_with_ben"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            results["comparisons"]["gemini_with_ben"] = {
                "status": "not_available",
                "error": "Requires both Gemini and BEN to be configured and working"
            }
        
        return jsonify(results)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============== RUN ==============

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting server on port {port}")
    print(f"GEMINI_API_KEY configured: {GEMINI_API_KEY is not None}")
    print(f"BEN_API_URL configured: {BEN_API_URL is not None}")
    app.run(host="0.0.0.0", port=port, debug=False)
