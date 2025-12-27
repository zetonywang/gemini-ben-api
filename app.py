"""
Gemini + BEN Bridge Analysis API with PBN Support
Generates detailed game reports with key moment analysis
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai
import requests
import os
import re

app = Flask(__name__, template_folder='templates')
CORS(app)

# ============== CONFIGURATION ==============

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BEN_API_URL = os.environ.get("BEN_API_URL")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ============== PBN PARSER ==============

def parse_pbn(pbn_content: str) -> dict:
    """Parse PBN format into board data"""
    
    result = {
        "dealer": None,
        "vuln": [False, False],  # [NS, EW]
        "hands": ["", "", "", ""],  # [N, E, S, W]
        "auction": [],
        "play": [],
        "event": "",
        "site": "",
        "date": "",
        "north": "",
        "south": "",
        "east": "",
        "west": "",
        "contract": "",
        "declarer": "",
        "result": ""
    }
    
    lines = pbn_content.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Parse tag-value pairs like [Event "..."]
        match = re.match(r'\[(\w+)\s+"(.*)"\]', line)
        if match:
            tag, value = match.groups()
            tag_lower = tag.lower()
            
            if tag_lower == "dealer":
                result["dealer"] = value.upper()
                
            elif tag_lower == "vulnerable":
                vuln = value.lower()
                if vuln in ["all", "both"]:
                    result["vuln"] = [True, True]
                elif vuln == "ns":
                    result["vuln"] = [True, False]
                elif vuln == "ew":
                    result["vuln"] = [False, True]
                else:  # None, Love, -
                    result["vuln"] = [False, False]
                    
            elif tag_lower == "deal":
                # Format: N:AKQ.JT9.876.5432 E:... S:... W:...
                # Or: N:AKQ.JT9.876.5432 ... ... ...
                result["hands"] = parse_deal(value)
                
            elif tag_lower == "auction":
                result["auction_dealer"] = value.upper()
                
            elif tag_lower == "contract":
                result["contract"] = value
                
            elif tag_lower == "declarer":
                result["declarer"] = value.upper()
                
            elif tag_lower == "result":
                result["result"] = value
                
            elif tag_lower == "event":
                result["event"] = value
                
            elif tag_lower == "site":
                result["site"] = value
                
            elif tag_lower == "date":
                result["date"] = value
                
            elif tag_lower == "north":
                result["north"] = value
                
            elif tag_lower == "south":
                result["south"] = value
                
            elif tag_lower == "east":
                result["east"] = value
                
            elif tag_lower == "west":
                result["west"] = value
        
        # Parse auction (lines after [Auction "..."])
        elif not line.startswith('[') and line and result.get("auction_dealer"):
            # Auction bids on this line
            bids = line.split()
            for bid in bids:
                bid = bid.upper().replace("PASS", "PASS").replace("P", "PASS")
                bid = bid.replace("DBL", "X").replace("DOUBLE", "X")
                bid = bid.replace("RDBL", "XX").replace("REDOUBLE", "XX")
                if bid in ["PASS", "X", "XX"] or re.match(r'[1-7][CDHSN]', bid):
                    result["auction"].append(bid)
    
    # Parse play section if exists
    play_section = re.search(r'\[Play\s+"[^"]*"\](.*?)(?=\[|$)', pbn_content, re.DOTALL)
    if play_section:
        play_lines = play_section.group(1).strip().split('\n')
        for line in play_lines:
            cards = line.strip().split()
            for card in cards:
                card = card.upper()
                # Convert card format: SA -> SA, S2 -> S2, etc.
                if len(card) == 2 and card[0] in 'SHDC' and card[1] in '23456789TJQKA':
                    result["play"].append(card)
    
    return result


def parse_deal(deal_str: str) -> list:
    """Parse deal string into [N, E, S, W] hands"""
    hands = ["", "", "", ""]  # N, E, S, W
    seat_map = {"N": 0, "E": 1, "S": 2, "W": 3}
    
    # Remove the starting seat indicator if present
    deal_str = deal_str.strip()
    
    # Format 1: "N:xxx.xxx.xxx.xxx E:xxx.xxx.xxx.xxx S:xxx.xxx.xxx.xxx W:xxx.xxx.xxx.xxx"
    if ":" in deal_str:
        parts = re.findall(r'([NESW]):([^\s]+)', deal_str)
        for seat, hand in parts:
            hands[seat_map[seat]] = hand
    
    # Format 2: "N:hand1 hand2 hand3 hand4" (space separated, order is N E S W from dealer)
    else:
        match = re.match(r'([NESW]):(.*)', deal_str)
        if match:
            start_seat = match.group(1)
            hand_strs = match.group(2).strip().split()
            
            start_idx = seat_map[start_seat]
            for i, hand in enumerate(hand_strs):
                seat_idx = (start_idx + i) % 4
                hands[seat_idx] = hand
    
    return hands


# ============== BEN API ==============

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
            timeout=180
        )
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============== KEY MOMENTS ANALYSIS ==============

def find_key_moments(ben_result: dict) -> list:
    """Extract key moments (mistakes, critical decisions) from BEN analysis"""
    
    key_moments = []
    
    if not ben_result.get("success"):
        return key_moments
    
    # Analyze bidding mistakes
    for i, bid_info in enumerate(ben_result.get("bid_analysis", [])):
        bid = bid_info.get("bid", "?")
        quality = float(bid_info.get("quality", 1))
        candidates = bid_info.get("candidates", [])
        
        if candidates:
            best = candidates[0]
            recommended = best.get("call", bid)
            
            # If actual bid differs from recommended
            if bid != recommended:
                key_moments.append({
                    "type": "bidding",
                    "trick": 0,
                    "position": i + 1,
                    "played": bid,
                    "recommended": recommended,
                    "quality": quality,
                    "explanation": best.get("explanation", ""),
                    "severity": "major" if quality < 0.8 else "minor",
                    "imp_cost": 0  # Bidding IMP cost harder to quantify
                })
    
    # Analyze card play mistakes
    card_analysis = ben_result.get("card_analysis", {})
    trick_num = 0
    card_count = 0
    
    for card_key, analysis in card_analysis.items():
        card_count += 1
        if card_count % 4 == 1:
            trick_num += 1
            
        played = card_key
        recommended = analysis.get("card", played)
        who = analysis.get("who", "")
        
        # Skip forced plays
        if who in ["Forced", "Follow"]:
            continue
        
        if played != recommended:
            candidates = analysis.get("candidates", [])
            
            # Calculate IMP cost
            imp_cost = 0
            played_imp = 0
            recommended_imp = 0
            
            for cand in candidates:
                if cand.get("card") == recommended:
                    recommended_imp = cand.get("expected_score_imp", 0)
                if cand.get("card") == played:
                    played_imp = cand.get("expected_score_imp", 0)
            
            imp_cost = recommended_imp - played_imp
            
            # Only include significant mistakes (> 0.5 IMP)
            if imp_cost > 0.5:
                key_moments.append({
                    "type": "card_play",
                    "trick": trick_num,
                    "position": card_count,
                    "played": played,
                    "recommended": recommended,
                    "imp_cost": round(imp_cost, 2),
                    "severity": "major" if imp_cost > 2 else "minor",
                    "candidates": [
                        {
                            "card": c.get("card"),
                            "imp": round(c.get("expected_score_imp", 0), 2)
                        }
                        for c in candidates[:4]
                    ]
                })
    
    # Sort by IMP cost (most costly first)
    key_moments.sort(key=lambda x: x.get("imp_cost", 0), reverse=True)
    
    return key_moments


# ============== REPORT GENERATION ==============

def generate_report(board_data: dict, ben_result: dict, key_moments: list) -> str:
    """Use Gemini to generate a detailed game report"""
    
    if not GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not configured"
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Format key moments for the prompt
    moments_text = ""
    if key_moments:
        moments_text = "\n### KEY MOMENTS IDENTIFIED BY BEN ENGINE:\n\n"
        
        total_imp_cost = 0
        for i, moment in enumerate(key_moments, 1):
            if moment["type"] == "bidding":
                moments_text += f"""**Moment {i}: Bidding (Position {moment['position']})**
- Bid made: {moment['played']}
- BEN recommends: {moment['recommended']}
- Severity: {moment['severity'].upper()}

"""
            else:
                total_imp_cost += moment.get("imp_cost", 0)
                moments_text += f"""**Moment {i}: Trick {moment['trick']} Card Play**
- Card played: {moment['played']}
- BEN recommends: {moment['recommended']}
- IMP Cost: {moment['imp_cost']:+.1f}
- Alternatives: {', '.join([f"{c['card']}({c['imp']:+.1f})" for c in moment.get('candidates', [])])}
- Severity: {moment['severity'].upper()}

"""
        
        moments_text += f"\n**Total Estimated IMP Cost: {total_imp_cost:.1f} IMPs**\n"
    else:
        moments_text = "\n### No significant mistakes found! Well played!\n"
    
    # Build the prompt
    prompt = f"""You are an expert bridge analyst and coach. Generate a detailed, educational game report.

## BOARD INFORMATION

**Dealer:** {board_data.get('dealer', '?')}
**Vulnerability:** NS={'Vul' if board_data['vuln'][0] else 'NV'}, EW={'Vul' if board_data['vuln'][1] else 'NV'}
**Contract:** {board_data.get('contract', 'Unknown')}
**Declarer:** {board_data.get('declarer', 'Unknown')}
**Result:** {board_data.get('result', 'Unknown')}

**Hands:**
- North: {board_data['hands'][0]}
- East:  {board_data['hands'][1]}
- South: {board_data['hands'][2]}
- West:  {board_data['hands'][3]}

**Auction:** {' - '.join(board_data.get('auction', []))}

**Play:** {' '.join(board_data.get('play', [])[:20])}{'...' if len(board_data.get('play', [])) > 20 else ''}

{moments_text}

## YOUR TASK

Generate a comprehensive game report with these sections:

### 1. BOARD OVERVIEW
- Briefly describe the hand distributions
- Note any interesting features (voids, long suits, etc.)

### 2. BIDDING ANALYSIS
- Evaluate the auction
- Explain the meaning of each bid
- Suggest improvements if any

### 3. KEY MOMENTS ANALYSIS
For each key moment identified above:
- Explain WHY the recommended play is better
- What was the thinking error?
- How to recognize similar situations

### 4. DECLARER'S LINE OF PLAY
- Describe the overall strategy
- What went well?
- What could be improved?

### 5. DEFENSIVE ANALYSIS (if applicable)
- How did the defense perform?
- Any missed opportunities?

### 6. LESSONS LEARNED
- 3-5 key takeaways from this hand
- Tips for improvement

### 7. OVERALL RATING
- Rate declarer's play: X/10
- Rate defense: X/10

Write in a friendly, educational tone. Be specific with card references.
"""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating report: {str(e)}"


# ============== API ENDPOINTS ==============

@app.route("/", methods=["GET"])
def home():
    """Serve the HTML frontend"""
    try:
        return render_template('index.html')
    except:
        # Fallback to JSON if template not found
        return jsonify({
            "service": "Bridge Game Analysis API",
            "version": "2.0",
            "description": "Upload PBN files to get detailed game reports",
            "endpoints": {
                "GET /": "Web interface (or this JSON)",
                "GET /api/info": "API information",
                "GET /health": "Health check",
                "POST /api/analyze/pbn": "Upload PBN and get full report",
                "POST /api/parse/pbn": "Parse PBN only (no analysis)",
                "POST /api/analyze/manual": "Analyze with manual input",
                "POST /api/analyze/quick": "Quick analysis without report"
            },
            "configuration": {
                "ben_configured": BEN_API_URL is not None,
                "gemini_configured": GEMINI_API_KEY is not None
            }
        })


@app.route("/api/info", methods=["GET"])
def api_info():
    """Return API information"""
    return jsonify({
        "service": "Bridge Game Analysis API",
        "version": "2.0",
        "description": "Upload PBN files to get detailed game reports",
        "endpoints": {
            "GET /": "Web interface",
            "GET /api/info": "This info",
            "GET /health": "Health check",
            "POST /api/analyze/pbn": "Upload PBN and get full report",
            "POST /api/parse/pbn": "Parse PBN only (no analysis)",
            "POST /api/analyze/manual": "Analyze with manual input",
            "POST /api/analyze/quick": "Quick analysis without report"
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


@app.route("/api/parse/pbn", methods=["POST"])
def parse_pbn_endpoint():
    """Parse PBN without analysis"""
    try:
        if request.is_json:
            pbn_content = request.json.get("pbn", "")
        else:
            pbn_content = request.data.decode("utf-8")
        
        board_data = parse_pbn(pbn_content)
        
        return jsonify({
            "success": True,
            "board": board_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/analyze/pbn", methods=["POST"])
def analyze_pbn():
    """Full PBN analysis with report generation"""
    try:
        # Get PBN content
        if request.is_json:
            pbn_content = request.json.get("pbn", "")
        else:
            pbn_content = request.data.decode("utf-8")
        
        if not pbn_content:
            return jsonify({"success": False, "error": "No PBN content provided"}), 400
        
        # Parse PBN
        board_data = parse_pbn(pbn_content)
        
        if not board_data["hands"][0]:
            return jsonify({"success": False, "error": "Could not parse hands from PBN"}), 400
        
        # Call BEN for analysis
        ben_result = {"success": False}
        if BEN_API_URL:
            ben_input = {
                "dealer": board_data["dealer"] or "N",
                "vuln": board_data["vuln"],
                "hands": board_data["hands"],
                "auction": board_data["auction"],
                "play": board_data["play"]
            }
            ben_result = call_ben_api(ben_input)
        
        # Find key moments
        key_moments = find_key_moments(ben_result) if ben_result.get("success") else []
        
        # Generate report
        report = ""
        if GEMINI_API_KEY:
            report = generate_report(board_data, ben_result, key_moments)
        
        return jsonify({
            "success": True,
            "board": board_data,
            "key_moments": key_moments,
            "report": report,
            "ben_available": ben_result.get("success", False),
            "total_mistakes": len(key_moments),
            "total_imp_cost": sum(m.get("imp_cost", 0) for m in key_moments)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze/quick", methods=["POST"])
def analyze_quick():
    """Quick analysis - key moments only, no detailed report"""
    try:
        if request.is_json:
            pbn_content = request.json.get("pbn", "")
        else:
            pbn_content = request.data.decode("utf-8")
        
        board_data = parse_pbn(pbn_content)
        
        ben_input = {
            "dealer": board_data["dealer"] or "N",
            "vuln": board_data["vuln"],
            "hands": board_data["hands"],
            "auction": board_data["auction"],
            "play": board_data["play"]
        }
        
        ben_result = call_ben_api(ben_input) if BEN_API_URL else {"success": False}
        key_moments = find_key_moments(ben_result) if ben_result.get("success") else []
        
        return jsonify({
            "success": True,
            "board": board_data,
            "key_moments": key_moments,
            "total_mistakes": len(key_moments),
            "total_imp_cost": sum(m.get("imp_cost", 0) for m in key_moments)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze/manual", methods=["POST"])
def analyze_manual():
    """Analyze with manual input (same as before)"""
    try:
        board_data = request.json
        
        ben_result = call_ben_api(board_data) if BEN_API_URL else {"success": False}
        key_moments = find_key_moments(ben_result) if ben_result.get("success") else []
        
        report = ""
        if GEMINI_API_KEY and ben_result.get("success"):
            report = generate_report(board_data, ben_result, key_moments)
        
        return jsonify({
            "success": True,
            "board": board_data,
            "key_moments": key_moments,
            "report": report,
            "ben_raw": ben_result if ben_result.get("success") else None,
            "total_mistakes": len(key_moments),
            "total_imp_cost": sum(m.get("imp_cost", 0) for m in key_moments)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============== RUN ==============

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Bridge Analysis API on port {port}")
    print(f"GEMINI_API_KEY configured: {GEMINI_API_KEY is not None}")
    print(f"BEN_API_URL configured: {BEN_API_URL}")
    app.run(host="0.0.0.0", port=port, debug=False)
