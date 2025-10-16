import hashlib
import json
import os
import time
from datetime import datetime, timedelta

from flask import jsonify, render_template, request, session, make_response, redirect
from flask_login import login_required

from app.models.database_models import SessionLocal
from app.services.lineup_escrow_service import LineupEscrowService
from app.services.session_service import get_session_data_for_user
from utils.ai import client, get_or_create_assistant
from utils.auth import login_required
from utils.db import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
from utils.series_mapping_service import get_display_name

# Simple in-memory cache for lineup suggestions
LINEUP_CACHE = {}
CACHE_DURATION = timedelta(minutes=15)  # Cache for 15 minutes


def get_cache_key(players, instructions, series):
    """Generate a cache key for lineup requests"""
    data = {
        "players": sorted(players),  # Sort for consistent cache keys
        "instructions": sorted(instructions) if instructions else [],
        "series": series,
    }
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()


def get_cached_lineup(cache_key):
    """Get cached lineup if available and not expired"""
    if cache_key in LINEUP_CACHE:
        cached_data = LINEUP_CACHE[cache_key]
        if datetime.now() - cached_data["timestamp"] < CACHE_DURATION:
            return cached_data["lineup"]
    return None


def cache_lineup(cache_key, lineup):
    """Cache a lineup suggestion"""
    LINEUP_CACHE[cache_key] = {"lineup": lineup, "timestamp": datetime.now()}

    # Clean old cache entries (keep cache size manageable)
    if len(LINEUP_CACHE) > 100:
        oldest_key = min(
            LINEUP_CACHE.keys(), key=lambda k: LINEUP_CACHE[k]["timestamp"]
        )
        del LINEUP_CACHE[oldest_key]


def get_user_instructions(user_email, team_id=None):
    """Get lineup instructions for a user"""
    try:
        # Don't filter by team_id since we're storing it as NULL for now
        # Get all instructions for the user regardless of team
        query = """
            SELECT id, instruction 
            FROM user_instructions 
            WHERE user_email = %(user_email)s AND is_active = true
            ORDER BY created_at DESC
        """
        params = {"user_email": user_email}

        # Note: Not filtering by team_id since we're storing it as NULL
        # In the future, if we implement a teams table with proper IDs, we can add filtering back

        instructions = execute_query(query, params)
        return [
            {"id": instr["id"], "instruction": instr["instruction"]}
            for instr in instructions
        ]
    except Exception as e:
        print(f"Error getting user instructions: {str(e)}")
        return []


def add_user_instruction(user_email, instruction, team_id=None):
    """Add a new lineup instruction"""
    try:
        # Handle team_id - if it's a string (team name), set to NULL since DB expects integer
        # In the future, we could look up actual team IDs from a teams table
        db_team_id = None
        if team_id and isinstance(team_id, (int, str)):
            try:
                # Try to convert to int, if it fails, set to None
                db_team_id = int(team_id) if str(team_id).isdigit() else None
            except (ValueError, TypeError):
                db_team_id = None

        success = execute_update(
            """
            INSERT INTO user_instructions (user_email, instruction, team_id, is_active)
            VALUES (%(user_email)s, %(instruction)s, %(team_id)s, true)
            """,
            {
                "user_email": user_email,
                "instruction": instruction,
                "team_id": db_team_id,
            },
        )
        return success
    except Exception as e:
        print(f"Error adding instruction: {str(e)}")
        return False


def delete_user_instruction(user_email, instruction, team_id=None):
    """Delete a lineup instruction"""
    try:
        # For deletion, we'll match by user and instruction only, ignoring team_id
        # since team_id might be stored as NULL but passed as string
        query = """
            UPDATE user_instructions 
            SET is_active = false 
            WHERE user_email = %(user_email)s AND instruction = %(instruction)s
        """
        params = {"user_email": user_email, "instruction": instruction}

        # Don't filter by team_id since it's likely NULL in DB but string from frontend
        # If we need team-specific instructions in the future, we can add a teams table

        success = execute_update(query, params)
        return success
    except Exception as e:
        print(f"Error deleting instruction: {str(e)}")
        return False


def get_player_data_for_lineup(players, series, players_with_preferences=None):
    """Get comprehensive player data from database for lineup generation"""
    try:
        if not players:
            return "No player data available."

        # Query for player stats using correct column names
        query = """
            SELECT DISTINCT ON (first_name || ' ' || last_name)
                first_name || ' ' || last_name AS name,
                pti,
                wins,
                losses,
                (wins + losses) as total_matches,
                win_percentage,
                series_id
            FROM players 
            WHERE (first_name || ' ' || last_name) = ANY(%s)
            ORDER BY first_name || ' ' || last_name, pti DESC NULLS LAST
        """

        player_records = execute_query(query, [players])

        # Get pairing consistency data from match_scores table - Show actual partnership history
        pairing_query = """
            WITH player_mappings AS (
                SELECT DISTINCT
                    p.tenniscores_player_id,
                    p.first_name || ' ' || p.last_name AS full_name
                FROM players p
                WHERE (p.first_name || ' ' || p.last_name) = ANY(%s)
            ),
            home_pairings AS (
                SELECT 
                    p1.full_name as player1,
                    p2.full_name as player2,
                    CASE WHEN ms.winner = 'home' THEN 1 ELSE 0 END as won,
                    ms.home_team as team_name
                FROM match_scores ms
                JOIN player_mappings p1 ON ms.home_player_1_id = p1.tenniscores_player_id
                JOIN player_mappings p2 ON ms.home_player_2_id = p2.tenniscores_player_id
                WHERE ms.home_player_1_id IS NOT NULL 
                AND ms.home_player_2_id IS NOT NULL
                AND ms.home_player_1_id != ms.home_player_2_id
                AND ms.winner IN ('home', 'away')
            ),
            away_pairings AS (
                SELECT 
                    p1.full_name as player1,
                    p2.full_name as player2,
                    CASE WHEN ms.winner = 'away' THEN 1 ELSE 0 END as won,
                    ms.away_team as team_name
                FROM match_scores ms
                JOIN player_mappings p1 ON ms.away_player_1_id = p1.tenniscores_player_id
                JOIN player_mappings p2 ON ms.away_player_2_id = p2.tenniscores_player_id
                WHERE ms.away_player_1_id IS NOT NULL 
                AND ms.away_player_2_id IS NOT NULL
                AND ms.away_player_1_id != ms.away_player_2_id
                AND ms.winner IN ('home', 'away')
            ),
            all_pairings AS (
                SELECT * FROM home_pairings
                UNION ALL
                SELECT * FROM away_pairings
            )
            SELECT 
                CASE 
                    WHEN player1 < player2 THEN player1 || '/' || player2
                    ELSE player2 || '/' || player1
                END as pairing,
                COUNT(*) as matches_together,
                SUM(won) as wins_together,
                ROUND(AVG(won) * 100, 1) as win_rate,
                STRING_AGG(DISTINCT team_name, ', ') as teams_played_for
            FROM all_pairings
            GROUP BY 
                CASE 
                    WHEN player1 < player2 THEN player1 || '/' || player2
                    ELSE player2 || '/' || player1
                END
            HAVING COUNT(*) >= 1  -- Show any partnerships, even single matches
            ORDER BY COUNT(*) DESC, AVG(won) DESC
        """

        try:
            pairing_records = execute_query(pairing_query, [players])
        except Exception as e:
            print(f"Error getting pairing data: {e}")
            pairing_records = []

        if not player_records:
            return f"No database records found for selected players in {series}. Cannot provide data-driven recommendations."

        # Format the comprehensive data for the AI
        data_lines = []
        data_lines.append(f"PLAYER DATA for {series}:")
        data_lines.append("=" * 40)

        # Create a map of player preferences for easy lookup
        preferences_map = {}
        if players_with_preferences:
            for player_pref in players_with_preferences:
                preferences_map[player_pref["name"]] = player_pref

        # Player individual stats
        data_lines.append("INDIVIDUAL PLAYER STATS:")
        for player in player_records:
            name = player["name"]
            pti = player["pti"] if player["pti"] else "No PTI"
            wins = player["wins"] if player["wins"] else 0
            losses = player["losses"] if player["losses"] else 0
            total_matches = player["total_matches"] if player["total_matches"] else 0
            win_pct = player["win_percentage"] if player["win_percentage"] else 0

            data_lines.append(f"• {name}:")
            data_lines.append(f"  - PTI: {pti}")
            data_lines.append(
                f"  - Overall Record: {wins}-{losses} ({win_pct}% win rate, {total_matches} matches)"
            )

            # Add preferences if available
            if name in preferences_map:
                player_prefs = preferences_map[name]
                ad_deuce_pref = player_prefs.get("position_preference")
                dominant_hand = player_prefs.get("hand_preference")

                if ad_deuce_pref:
                    data_lines.append(
                        f"  - Court Position Preference: {ad_deuce_pref} side"
                    )
                if dominant_hand:
                    data_lines.append(f"  - Dominant Hand: {dominant_hand}")

                if ad_deuce_pref or dominant_hand:
                    data_lines.append("")  # Add blank line for readability

        # Successful pairings
        if pairing_records:
            data_lines.append("\nSUCCESSFUL PAIRINGS (2+ matches together):")
            for pairing in pairing_records:
                pair_name = pairing["pairing"]
                matches = pairing["matches_together"]
                wins = pairing["wins_together"]
                losses = matches - wins
                win_rate = round((wins / matches) * 100, 1) if matches > 0 else 0

                data_lines.append(
                    f"• {pair_name}: {wins}-{losses} together ({win_rate}% win rate, {matches} matches)"
                )

        # Add any missing players
        found_names = {p["name"] for p in player_records}
        missing_players = [p for p in players if p not in found_names]

        if missing_players:
            data_lines.append("\nPLAYERS NOT FOUND IN DATABASE:")
            for player in missing_players:
                data_lines.append(
                    f"• {player}: No data available - use general strategy"
                )

        data_lines.append("\nDATA SUMMARY:")
        data_lines.append(
            f"• Found data for {len(player_records)} of {len(players)} selected players"
        )
        data_lines.append(f"• {len(pairing_records)} successful pairings identified")
        data_lines.append("• Recommendations should be based ONLY on this actual data")

        return "\n".join(data_lines)

    except Exception as e:
        print(f"Error getting comprehensive player data: {e}")
        import traceback

        print(f"Full traceback: {traceback.format_exc()}")
        return f"Error retrieving player data. Cannot provide data-driven recommendations for: {', '.join(players)}"


def get_pairing_data_for_frontend(players):
    """Get pairing data in a format suitable for frontend display"""
    try:
        if not players or len(players) < 2:
            print(
                f"[DEBUG] get_pairing_data_for_frontend: Not enough players ({len(players) if players else 0})"
            )
            return {}

        print(
            f"[DEBUG] get_pairing_data_for_frontend: Processing {len(players)} players: {players}"
        )

        # Get pairing consistency data from match_scores table - Show actual partnership history
        pairing_query = """
            WITH player_mappings AS (
                SELECT DISTINCT
                    p.tenniscores_player_id,
                    p.first_name || ' ' || p.last_name AS full_name
                FROM players p
                WHERE (p.first_name || ' ' || p.last_name) = ANY(%s)
            ),
            home_pairings AS (
                SELECT 
                    p1.full_name as player1,
                    p2.full_name as player2,
                    CASE WHEN ms.winner = 'home' THEN 1 ELSE 0 END as won,
                    ms.home_team as team_name
                FROM match_scores ms
                JOIN player_mappings p1 ON ms.home_player_1_id = p1.tenniscores_player_id
                JOIN player_mappings p2 ON ms.home_player_2_id = p2.tenniscores_player_id
                WHERE ms.home_player_1_id IS NOT NULL 
                AND ms.home_player_2_id IS NOT NULL
                AND ms.home_player_1_id != ms.home_player_2_id
                AND ms.winner IN ('home', 'away')
            ),
            away_pairings AS (
                SELECT 
                    p1.full_name as player1,
                    p2.full_name as player2,
                    CASE WHEN ms.winner = 'away' THEN 1 ELSE 0 END as won,
                    ms.away_team as team_name
                FROM match_scores ms
                JOIN player_mappings p1 ON ms.away_player_1_id = p1.tenniscores_player_id
                JOIN player_mappings p2 ON ms.away_player_2_id = p2.tenniscores_player_id
                WHERE ms.away_player_1_id IS NOT NULL 
                AND ms.away_player_2_id IS NOT NULL
                AND ms.away_player_1_id != ms.away_player_2_id
                AND ms.winner IN ('home', 'away')
            ),
            all_pairings AS (
                SELECT * FROM home_pairings
                UNION ALL
                SELECT * FROM away_pairings
            )
            SELECT 
                CASE 
                    WHEN player1 < player2 THEN player1 || '/' || player2
                    ELSE player2 || '/' || player1
                END as pairing,
                COUNT(*) as matches_together,
                SUM(won) as wins_together,
                ROUND(AVG(won) * 100, 1) as win_rate,
                STRING_AGG(DISTINCT team_name, ', ') as teams_played_for
            FROM all_pairings
            GROUP BY 
                CASE 
                    WHEN player1 < player2 THEN player1 || '/' || player2
                    ELSE player2 || '/' || player1
                END
            ORDER BY COUNT(*) DESC, AVG(won) DESC
        """

        pairing_records = execute_query(pairing_query, [players])

        print(f"[DEBUG] Found {len(pairing_records)} pairing records")
        for record in pairing_records:
            print(
                f"[DEBUG] - {record['pairing']}: {record['wins_together']}-{record['matches_together'] - record['wins_together']} ({record['matches_together']} matches)"
            )

        # Convert to dict for easy lookup by pairing name
        pairing_data = {}
        for pairing in pairing_records:
            pairing_data[pairing["pairing"]] = {
                "wins": pairing["wins_together"],
                "losses": pairing["matches_together"] - pairing["wins_together"],
                "total_games": pairing["matches_together"],
                "win_rate": pairing["win_rate"],
            }

        print(
            f"[DEBUG] Returning pairing_data with {len(pairing_data)} entries: {list(pairing_data.keys())}"
        )
        return pairing_data

    except Exception as e:
        print(f"Error getting pairing data for frontend: {e}")
        return {}


def generate_fast_lineup(players, instructions, series, players_with_preferences=None):
    """Generate lineup using optimized Chat Completions API with real player data"""

    # Get real player data from database
    player_data = get_player_data_for_lineup(players, series, players_with_preferences)

    # Build data-driven prompt with sophisticated analysis rules
    prompt = f"""Create a strategic lineup for {series} using ONLY the actual player data provided below and following advanced tennis strategy principles.

{player_data}

**STRATEGIC ANALYSIS FRAMEWORK:**

Prioritize instructions for your analysis in this specific order and weighting:

1. **Special Instructions** (50% weighted in analysis) - User-provided instructions take absolute priority
2. **Most Skilled Players First** (25% weighted in analysis) - Players with LOWEST PTI numbers are most skilled and should play on lower-numbered courts
3. **Consistency & Success Rate** (25% weighted in analysis) - Prioritize pairings that have played together frequently AND have high win rates together

**COURT ASSIGNMENT RULES (CRITICAL):**
PTI INTERPRETATION: Lower PTI numbers = More skilled players, Higher PTI numbers = Less skilled players

- Court 1 = MOST SKILLED players (LOWEST PTI numbers: e.g., 44.10, 45.60)
- Court 2 = NEXT MOST SKILLED players (NEXT LOWEST PTI numbers: e.g., 50.40, 50.90)  
- Court 3 = LESS SKILLED players (HIGHER PTI numbers: e.g., 55.90, 56.30)
- Court 4 = LEAST SKILLED players (HIGHEST PTI numbers: e.g., 58.90, 59.90)

CRITICAL PAIRING RULE: Do NOT mix skill levels! Pair players with similar PTI scores together (within 3-5 points maximum). 

**ADDITIONAL CONSIDERATIONS:**
- **Partnership Consistency**: Look for pairings with 60%+ win rates and multiple matches played
- **Ad/Deuce Court Positioning**: Ad players should be paired with Deuce players when possible
- **Win Percentage Override**: Players with exceptionally high individual win rates can play lower courts even if their PTI is higher

**REASONING REQUIREMENTS:**
- Reference specific PTI numbers, win/loss records, and partnership statistics
- Mention successful pairing history with actual win rates when relevant
- Explain court assignment logic based on the weighted priority system above
- Note any strategic positioning considerations (Ad/Deuce when known)

**Required Format:**
Court 1: Player1/Player2 - [PTI: X/Y, reasoning: specific data-driven explanation]
Court 2: Player3/Player4 - [PTI: X/Y, reasoning: specific data-driven explanation]
Court 3: Player5/Player6 - [PTI: X/Y, reasoning: specific data-driven explanation]
Court 4: Player7/Player8 - [PTI: X/Y, reasoning: specific data-driven explanation]

**FORBIDDEN** - Do NOT use vague phrases like:
- "Strong net play" / "baseline consistency" / "tactical awareness"
- "Experience" / "communication" / "strategic play"
- Any playing style characteristics not shown in the data"""

    # Add instructions if provided
    if instructions:
        prompt += f"\n\nSpecial instructions:\n" + "\n".join(
            f"• {inst}" for inst in instructions
        )

    # Use Chat Completions API - much faster than Assistant API
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Faster and cheaper than gpt-4
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert paddle tennis coach. Create concise, strategic lineups quickly.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,  # Limit response length for speed
            temperature=0.7,
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error with Chat Completions API: {e}")
        # Fallback to a simple algorithmic approach if API fails
        return generate_algorithmic_lineup(players, instructions)


def generate_algorithmic_lineup(players, instructions):
    """Fallback algorithmic lineup generation using available data"""
    if len(players) < 4:
        return f"Need at least 4 players. You selected: {', '.join(players)}"

    # Try to get player data for smarter pairing
    try:
        # Quick query for PTI ratings to do skill-based pairing
        query = """
            SELECT 
                first_name || ' ' || last_name AS name,
                COALESCE(pti, 40) as pti
            FROM players 
            WHERE (first_name || ' ' || last_name) = ANY(%s)
            ORDER BY pti DESC
        """

        player_records = execute_query(query, [players])
        player_ptis = {p["name"]: p["pti"] for p in player_records}

        # Sort players by PTI (lowest first for proper court assignment), use default PTI for unknown players
        sorted_players = sorted(
            players, key=lambda p: player_ptis.get(p, 40), reverse=False
        )

        # Assign courts following PTI rule: lower PTI = lower court number
        courts = []
        used_players = set()

        for court_num in range(1, 5):  # Up to 4 courts
            if len(used_players) >= len(sorted_players):
                break

            # Get available players (sorted lowest PTI first)
            available = [p for p in sorted_players if p not in used_players]
            if len(available) < 2:
                break

            # For Court 1: use lowest PTI players
            # For higher courts: use progressively higher PTI players
            base_index = (court_num - 1) * 2
            if base_index < len(available):
                player1 = (
                    available[base_index]
                    if base_index < len(available)
                    else available[0]
                )
                player2 = (
                    available[base_index + 1]
                    if base_index + 1 < len(available)
                    else available[-1]
                )

            p1_pti = player_ptis.get(player1, 40)
            p2_pti = player_ptis.get(player2, 40)

            courts.append(
                f"Court {court_num}: {player1}/{player2} - PTI-based pairing (PTI: {p1_pti}/{p2_pti})"
            )
            used_players.add(player1)
            used_players.add(player2)

        # Add remaining players as substitutes
        remaining = [p for p in players if p not in used_players]
        if remaining:
            courts.append(f"Substitutes: {'/'.join(remaining)}")

        result = "\n".join(courts)
        result += (
            "\n\nNote: PTI-based court assignment (lower PTI = lower court number)."
        )

    except Exception as e:
        # Ultimate fallback - simple pairing
        print(f"Error in algorithmic lineup: {e}")
        courts = []
        for i in range(0, min(len(players), 8), 2):
            if i + 1 < len(players):
                court_num = (i // 2) + 1
                courts.append(
                    f"Court {court_num}: {players[i]}/{players[i+1]} - General pairing"
                )

        result = "\n".join(courts)
        result += "\n\nNote: Basic pairing (data unavailable)."

    if instructions:
        result += f"\n\nInstructions to consider: {', '.join(instructions)}"

    return result


def init_lineup_routes(app):
    @app.route("/mobile/lineup-selection")
    @login_required
    def serve_mobile_lineup_selection():
        """Serve the lineup selection landing page"""
        try:
            session_data = {"user": session["user"], "authenticated": True}
            log_user_activity(
                session["user"]["email"], "page_visit", page="mobile_lineup_selection"
            )
            return render_template(
                "mobile/lineup_selection.html", session_data=session_data
            )
        except Exception as e:
            print(f"Error serving lineup selection page: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/mobile/lineup")
    @login_required
    def serve_mobile_lineup():
        """Serve the mobile lineup page"""
        try:
            session_data = {"user": session["user"], "authenticated": True}
            log_user_activity(
                session["user"]["email"], "page_visit", page="mobile_lineup"
            )
            return render_template("mobile/lineup.html", session_data=session_data)
        except Exception as e:
            print(f"Error serving lineup page: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/mobile/lineup-ai")
    @login_required
    def serve_mobile_lineup_ai():
        """Serve the AI-driven lineup creation page"""
        try:
            session_data = {"user": session["user"], "authenticated": True}
            log_user_activity(
                session["user"]["email"], "page_visit", page="mobile_lineup_ai"
            )
            return render_template("mobile/lineup_ai.html", session_data=session_data)
        except Exception as e:
            print(f"Error serving AI lineup page: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/mobile/lineup-confirmation")
    @login_required
    def serve_mobile_lineup_confirmation():
        """Serve the mobile lineup confirmation page"""
        try:
            session_data = {"user": session["user"], "authenticated": True}
            log_user_activity(
                session["user"]["email"],
                "page_visit",
                page="mobile_lineup_confirmation",
            )
            return render_template(
                "mobile/lineup_confirmation.html", session_data=session_data
            )
        except Exception as e:
            print(f"Error serving lineup confirmation page: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/mobile/create-lineup")
    @login_required
    def serve_mobile_create_lineup():
        """Serve the mobile Create Lineup page"""
        session_data = {"user": session["user"], "authenticated": True}
        log_user_activity(
            session["user"]["email"],
            "page_visit",
            page="mobile_create_lineup",
            details="Accessed mobile create lineup page",
        )
        
        # Enhanced cache-busting with timestamp and aggressive headers
        response = make_response(render_template("mobile/create_lineup.html", session_data=session_data))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        response.headers['ETag'] = f'"{int(time.time())}"'
        return response

    @app.route("/mobile/lineup-escrow")
    @login_required
    def serve_mobile_lineup_escrow():
        """Serve the mobile Lineup Escrow page with captain selection"""
        session_data = {"user": session["user"], "authenticated": True}
        log_user_activity(
            session["user"]["email"],
            "page_visit",
            page="mobile_lineup_escrow",
            details="Accessed mobile lineup escrow page",
        )
        
        # Add cache-busting headers to prevent caching issues
        response = make_response(render_template("mobile/lineup_escrow.html", session_data=session_data))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route("/mobile/lineup-messaging")
    @login_required
    def serve_mobile_lineup_messaging():
        """Serve the mobile lineup messaging page for sending lineups via SMS/email"""
        try:
            session_data = {"user": session["user"], "authenticated": True}
            log_user_activity(
                session["user"]["email"], "page_visit", page="mobile_lineup_messaging"
            )
            return render_template(
                "mobile/lineup_messaging.html", session_data=session_data
            )
        except Exception as e:
            print(f"Error serving lineup messaging page: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/lineup-instructions", methods=["GET", "POST", "DELETE"])
    @login_required
    def lineup_instructions():
        """Handle lineup instructions"""
        if request.method == "GET":
            try:
                user_email = session["user"]["email"]
                team_id = request.args.get("team_id")
                instructions = get_user_instructions(user_email, team_id=team_id)
                return jsonify(
                    {"instructions": [i["instruction"] for i in instructions]}
                )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        elif request.method == "POST":
            try:
                user_email = session["user"]["email"]
                data = request.json
                instruction = data.get("instruction")
                team_id = data.get("team_id")

                if not instruction:
                    return jsonify({"error": "Instruction is required"}), 400

                success = add_user_instruction(user_email, instruction, team_id=team_id)
                if not success:
                    return jsonify({"error": "Failed to add instruction"}), 500

                return jsonify({"status": "success"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        elif request.method == "DELETE":
            try:
                user_email = session["user"]["email"]
                data = request.json
                instruction = data.get("instruction")
                team_id = data.get("team_id")

                if not instruction:
                    return jsonify({"error": "Instruction is required"}), 400

                success = delete_user_instruction(
                    user_email, instruction, team_id=team_id
                )
                if not success:
                    return jsonify({"error": "Failed to delete instruction"}), 500

                return jsonify({"status": "success"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    @app.route("/api/generate-lineup", methods=["POST"])
    @login_required
    def generate_lineup():
        """Generate lineup using optimized AI - MUCH FASTER!"""
        try:
            data = request.json
            selected_players = data.get("players", [])
            instructions = data.get("instructions", [])
            players_with_preferences = data.get("players_with_preferences", None)

            if not selected_players:
                return jsonify({"error": "No players selected"}), 400

            user_series = session["user"].get("series", "")
            display_series = get_display_name(user_series)

            start_time = time.time()

            # Check cache first (include preferences in cache key for future enhancement)
            cache_key = get_cache_key(selected_players, instructions, display_series)
            cached_lineup = get_cached_lineup(cache_key)

            if cached_lineup:
                # Also get pairing data for cached responses
                pairing_data = get_pairing_data_for_frontend(selected_players)
                return jsonify(
                    {"suggestion": cached_lineup, "pairing_data": pairing_data}
                )

            # Generate new lineup using fast Chat Completions API with preferences
            suggestion = generate_fast_lineup(
                selected_players, instructions, display_series, players_with_preferences
            )

            # Get actual pairing data from database
            pairing_data = get_pairing_data_for_frontend(selected_players)

            # Cache the result
            cache_lineup(cache_key, suggestion)

            processing_time = time.time() - start_time

            if instructions:
                print(
                    f"✅ Used {len(instructions)} user instructions in lineup generation"
                )

            return jsonify({"suggestion": suggestion, "pairing_data": pairing_data})

        except Exception as e:
            print(f"Error generating lineup: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # Lineup Escrow API Endpoints
    @app.route("/api/lineup-escrow/create", methods=["POST"])
    @login_required
    def create_lineup_escrow():
        """Create a new lineup escrow session"""
        try:
            data = request.json
            user = session["user"]
            
            # Validate required fields
            required_fields = ["recipient_name", "recipient_contact", "contact_type", "initiator_lineup", "message_body"]
            for field in required_fields:
                if not data.get(field):
                    return jsonify({"error": f"{field} is required"}), 400
            
            # Validate contact type
            if data["contact_type"] not in ["email", "sms"]:
                return jsonify({"error": "contact_type must be 'email' or 'sms'"}), 400
            
            with SessionLocal() as db_session:
                escrow_service = LineupEscrowService(db_session)
                
                result = escrow_service.create_escrow_session(
                    initiator_user_id=user["id"],
                    recipient_name=data["recipient_name"],
                    recipient_contact=data["recipient_contact"],
                    contact_type=data["contact_type"],
                    initiator_lineup=data["initiator_lineup"],
                    subject=data.get("subject", "Lineup Escrow™"),
                    message_body=data["message_body"],
                    initiator_team_id=data.get("initiator_team_id"),
                    recipient_team_id=data.get("recipient_team_id"),
                    expires_in_hours=data.get("expires_in_hours", 48)
                )
                
                if result["success"]:
                    # Send notification to recipient
                    if data["contact_type"] == "email":
                        escrow_service.notify_recipient_team(
                            escrow_id=result["escrow_id"],
                            recipient_team_name=data["recipient_name"],
                            recipient_captain_email=data["recipient_contact"]
                        )
                    
                    return jsonify(result)
                else:
                    return jsonify(result), 400
                    
        except Exception as e:
            print(f"Error creating lineup escrow: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/lineup-escrow/submit", methods=["POST"])
    def submit_recipient_lineup():
        """Submit recipient lineup to complete escrow (no login required)"""
        try:
            data = request.json
            
            # Validate required fields
            required_fields = ["escrow_token", "recipient_contact", "recipient_lineup"]
            for field in required_fields:
                if not data.get(field):
                    return jsonify({"error": f"{field} is required"}), 400
            
            with SessionLocal() as db_session:
                escrow_service = LineupEscrowService(db_session)
                
                result = escrow_service.submit_recipient_lineup(
                    escrow_token=data["escrow_token"],
                    recipient_contact=data["recipient_contact"],
                    recipient_lineup=data["recipient_lineup"]
                )
                
                if result["success"]:
                    # Check if escrow is now complete and send completion notification
                    escrow_details = escrow_service.get_escrow_details(data["escrow_token"], data["recipient_contact"])
                    if escrow_details["success"] and escrow_details["both_lineups_visible"]:
                        escrow_service.notify_escrow_completion(result["escrow_id"])
                    
                    return jsonify(result)
                else:
                    return jsonify(result), 400
                    
        except Exception as e:
            print(f"Error submitting recipient lineup: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/lineup-escrow/view/<escrow_token>", methods=["GET"])
    def view_lineup_escrow(escrow_token):
        """View lineup escrow details (no login required)"""
        try:
            viewer_contact = request.args.get("contact", "")
            
            # Allow access without contact parameter for originating captains
            # The service will handle this case gracefully
            
            with SessionLocal() as db_session:
                escrow_service = LineupEscrowService(db_session)
                
                result = escrow_service.get_escrow_details(escrow_token, viewer_contact)
                
                if result["success"]:
                    return jsonify(result)
                else:
                    return jsonify(result), 400
                    
        except Exception as e:
            print(f"Error viewing lineup escrow: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/lineup-escrow/search-player", methods=["POST"])
    @login_required
    def search_player_for_escrow():
        """Search for a player by name to get their teams for escrow"""
        try:
            data = request.json
            player_name = data.get("player_name", "").strip()
            
            if not player_name:
                return jsonify({"error": "player_name is required"}), 400
            
            # Get current user's league ID for filtering
            current_user_league_id = session["user"].get("league_id")
            if not current_user_league_id:
                return jsonify({"error": "User league not found"}), 400
            
            with SessionLocal() as db_session:
                # Search for players by name (first name, last name, or full name)
                from app.models.database_models import Player, Team, League, Club, Series
                import re
                
                # Split name into parts for flexible search
                name_parts = player_name.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = name_parts[-1]
                    # Search for exact matches first, but only in the user's league
                    players = db_session.query(Player).join(Team).filter(
                        Team.league_id == current_user_league_id,
                        ((Player.first_name.ilike(f"%{first_name}%") & Player.last_name.ilike(f"%{last_name}%")) |
                        (Player.first_name.ilike(f"%{last_name}%") & Player.last_name.ilike(f"%{first_name}%")))
                    ).all()
                else:
                    # Single name search, but only in the user's league
                    players = db_session.query(Player).join(Team).filter(
                        Team.league_id == current_user_league_id,
                        ((Player.first_name.ilike(f"%{player_name}%")) |
                        (Player.last_name.ilike(f"%{player_name}%")))
                    ).all()
                if not players:
                    return jsonify({"error": "No players found with that name"}), 404
                # Get unique teams for these players
                team_data = []
                seen_teams = set()
                for player in players:
                    if player.team_id and player.team_id not in seen_teams:
                        team = db_session.query(Team).filter(Team.id == player.team_id).first()
                        if team and team.league_id == current_user_league_id:  # Double-check league filtering
                            league = db_session.query(League).filter(League.id == team.league_id).first()
                            club = db_session.query(Club).filter(Club.id == team.club_id).first()
                            series = db_session.query(Series).filter(Series.id == team.series_id).first()
                            # Always show 'Series X' format
                            series_name = series.name if series else "Unknown Series"
                            series_number = None
                            if series_name:
                                match = re.search(r'(\d+)', series_name)
                                if match:
                                    series_number = match.group(1)
                            series_display = f"Series {series_number}" if series_number else series_name
                            # Look up phone number using our CSV fallback system
                            from app.routes.api_routes import _load_directory_contact_from_csv
                            phone_number = ""
                            try:
                                contact_info = _load_directory_contact_from_csv(session["user"], player.first_name, player.last_name)
                                phone_number = contact_info.get("phone", "").strip()
                            except Exception as e:
                                print(f"Error looking up phone for {player.first_name} {player.last_name}: {e}")
                                phone_number = ""
                            
                            team_data.append({
                                "team_id": team.id,
                                "team_name": team.display_name,
                                "league_name": league.league_name if league else "Unknown League",
                                "club_name": club.name if club else "Unknown Club",
                                "series_name": series_display,  # Fixed: was series_display, should be series_name
                                "player_name": f"{player.first_name} {player.last_name}",
                                "player_id": player.id,
                                "phone_number": phone_number
                            })
                            seen_teams.add(team.id)
                return jsonify({
                    "success": True,
                    "teams": team_data
                })
        except Exception as e:
            print(f"Error searching for player: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/opposing-team-players/<int:team_id>", methods=["GET"])
    def get_opposing_team_players(team_id):
        """Get players for the opposing team in lineup escrow (no login required)"""
        try:
            with SessionLocal() as db_session:
                from app.models.database_models import Player, Team, Club, Series
                
                # Get team information
                team = db_session.query(Team).filter(Team.id == team_id).first()
                if not team:
                    return jsonify({"error": "Team not found"}), 404
                
                # Get all players for this team
                players = db_session.query(Player).filter(Player.team_id == team_id).all()
                
                if not players:
                    return jsonify({"error": "No players found for this team"}), 404
                
                # Format player data
                player_data = []
                for player in players:
                    # Get position preference (Ad, Deuce, Either)
                    position_preference = None
                    if player.pti:
                        pti = float(player.pti)
                        if pti >= 60:
                            position_preference = 'Either'  # High-rated players can play both sides
                        elif pti >= 50:
                            position_preference = 'Ad'      # Mid-high rated players typically play Ad
                        elif pti >= 45:
                            position_preference = 'Deuce'   # Mid-rated players typically play Deuce
                        elif pti >= 40:
                            position_preference = 'Either'  # Lower rated players might need flexibility
                    
                    player_data.append({
                        "id": player.id,
                        "name": f"{player.first_name} {player.last_name}",
                        "first_name": player.first_name,
                        "last_name": player.last_name,
                        "pti": player.pti or 0,  # Add PTI field for frontend compatibility
                        "rating": player.pti or 0,  # Keep rating for backward compatibility
                        "position_preference": position_preference,
                        "tenniscores_player_id": player.tenniscores_player_id
                    })
                
                return jsonify({
                    "success": True,
                    "team_id": team_id,
                    "team_name": team.display_name,
                    "players": player_data
                })
                
        except Exception as e:
            print(f"Error getting opposing team players: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/saved-lineups", methods=["GET", "POST", "DELETE", "PUT"])
    @login_required
    def saved_lineups():
        """Handle saved lineups"""
        try:
            user = session["user"]
            team_id = request.args.get("team_id") or request.json.get("team_id")
            
            print(f"🔍 Saved Lineups API Debug:")
            print(f"   User ID: {user.get('id')}")
            print(f"   User Email: {user.get('email')}")
            print(f"   Team ID from request: {team_id}")
            print(f"   Request method: {request.method}")
            
            if not team_id:
                return jsonify({"error": "team_id is required"}), 400
            
            with SessionLocal() as db_session:
                escrow_service = LineupEscrowService(db_session)
                
                if request.method == "GET":
                    result = escrow_service.get_saved_lineups(user["id"], int(team_id))
                    print(f"   API Result: {result}")
                    return jsonify(result)
                    
                elif request.method == "POST":
                    data = request.json
                    required_fields = ["lineup_name", "lineup_data"]
                    for field in required_fields:
                        if not data.get(field):
                            return jsonify({"error": f"{field} is required"}), 400
                    
                    result = escrow_service.save_lineup(
                        user_id=user["id"],
                        team_id=int(team_id),
                        lineup_name=data["lineup_name"],
                        lineup_data=data["lineup_data"]
                    )
                    
                    if result["success"]:
                        return jsonify(result)
                    else:
                        return jsonify(result), 400
                        
                elif request.method == "DELETE":
                    data = request.json
                    lineup_id = data.get("lineup_id")
                    
                    if not lineup_id:
                        return jsonify({"error": "lineup_id is required"}), 400
                    
                    result = escrow_service.delete_saved_lineup(int(lineup_id), user["id"])
                    
                    if result["success"]:
                        return jsonify(result)
                    else:
                        return jsonify(result), 400
                        
                elif request.method == "PUT":
                    data = request.json
                    lineup_id = data.get("lineup_id")
                    
                    if not lineup_id:
                        return jsonify({"error": "lineup_id is required"}), 400
                        
                    result = escrow_service.update_saved_lineup(
                        lineup_id=int(lineup_id),
                        user_id=user["id"],
                        lineup_name=data.get("lineup_name"),
                        lineup_data=data.get("lineup_data")
                    )
                    
                    if result["success"]:
                        return jsonify(result)
                    else:
                        return jsonify(result), 400
                        
        except Exception as e:
            print(f"Error handling saved lineups: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/mobile/saved-lineups")
    @login_required 
    def serve_saved_lineups_page():
        """Serve the saved lineups page"""
        try:
            # Get session data for context (using same pattern as other routes)
            session_data = {"user": session["user"], "authenticated": True}
            return render_template("mobile/saved_lineups.html", session_data=session_data)
        except Exception as e:
            print(f"Error serving saved lineups page: {str(e)}")
            # Create basic session data for error template
            session_data = {"user": session.get("user", {}), "authenticated": True}
            return render_template("mobile/error.html", error="Unable to load saved lineups page", session_data=session_data), 500

    @app.route("/mobile/view-lineup-escrows")
    @login_required
    def serve_view_lineup_escrows():
        """Serve the view previous lineup escrows page"""
        try:
            session_data = {"user": session["user"], "authenticated": True}
            log_user_activity(
                session["user"]["email"],
                "page_visit",
                page="mobile_view_lineup_escrows",
                details="Accessed previous lineup escrows page"
            )
            return render_template("mobile/view_lineup_escrows.html", session_data=session_data)
        except Exception as e:
            print(f"Error serving view lineup escrows page: {str(e)}")
            session_data = {"user": session.get("user", {}), "authenticated": True}
            return render_template("mobile/error.html", error="Unable to load lineup escrows page", session_data=session_data), 500

    @app.route("/api/lineup-escrow/user-previous", methods=["GET"])
    @login_required
    def get_user_previous_escrows():
        """Get all previous lineup escrows created by the current user"""
        try:
            user = session["user"]
            limit = request.args.get("limit", 50, type=int)
            
            with SessionLocal() as db_session:
                escrow_service = LineupEscrowService(db_session)
                
                result = escrow_service.get_user_previous_escrows(
                    user_id=user["id"],
                    limit=limit
                )
                
                if result["success"]:
                    return jsonify(result)
                else:
                    return jsonify(result), 400
                    
        except Exception as e:
            print(f"Error getting user previous escrows: {str(e)}")
            return jsonify({"error": str(e)}), 500

    def _create_minimal_session_data():
        """Create minimal session data for non-authenticated users"""
        return {
            "user": {
                "is_admin": False,
                "tenniscores_player_id": None
            }, 
            "authenticated": False
        }

    @app.route("/mobile/lineup-escrow-view/<escrow_token>")
    def serve_lineup_escrow_view(escrow_token):
        """Serve the lineup escrow view page"""
        try:
            # Get viewer contact from query parameter (optional for originating captains)
            viewer_contact = request.args.get("contact", "")
            
            # Allow access without contact parameter for originating captains
            # The service will handle this case gracefully
            
            try:
                with SessionLocal() as db_session:
                    escrow_service = LineupEscrowService(db_session)
                    # Pass viewer_contact (might be empty for originating captains)
                    result = escrow_service.get_escrow_details(escrow_token, viewer_contact)
                    
                    if not result["success"]:
                        # Create minimal session data for error template
                        session_data = _create_minimal_session_data()
                        return render_template("mobile/lineup_escrow_error.html", 
                                             error=result.get("error", "Escrow session not found."),
                                             session_data=session_data)
                    
                    # Validate that escrow_data exists
                    if "escrow_data" not in result:
                        print(f"Missing escrow_data in result: {result}")
                        # Create minimal session data for error template
                        session_data = _create_minimal_session_data()
                        return render_template("mobile/lineup_escrow_error.html", 
                                             error="Invalid escrow data format.",
                                             session_data=session_data)
                    
                    # Validate required fields
                    required_fields = ["id", "status", "initiator_lineup", "message_body"]
                    missing_fields = [field for field in required_fields if field not in result["escrow_data"]]
                    if missing_fields:
                        print(f"Missing required fields in escrow_data: {missing_fields}")
                        # Create minimal session data for error template
                        session_data = _create_minimal_session_data()
                        return render_template("mobile/lineup_escrow_error.html", 
                                             error="Incomplete escrow data.",
                                             session_data=session_data)
                    
                    # Validate both_lineups_visible field
                    if "both_lineups_visible" not in result:
                        print(f"Missing both_lineups_visible in result: {result}")
                        # Create minimal session data for error template
                        session_data = _create_minimal_session_data()
                        return render_template("mobile/lineup_escrow_error.html", 
                                             error="Invalid escrow data format.",
                                             session_data=session_data)
                    
                    # Pass escrow data to template
                    # Create minimal session data for non-authenticated users
                    session_data = _create_minimal_session_data()  # No login required
                    # Add cache-busting headers to prevent caching issues
                    try:
                        response = make_response(render_template("mobile/lineup_escrow_view.html", 
                                         session_data=session_data,
                                         escrow_data=result["escrow_data"],
                                         both_lineups_visible=result["both_lineups_visible"]))
                        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                        response.headers['Pragma'] = 'no-cache'
                        response.headers['Expires'] = '0'
                        return response
                    except Exception as template_error:
                        print(f"Error rendering template: {str(template_error)}")
                        import traceback
                        traceback.print_exc()
                        # Create minimal session data for error template
                        session_data = _create_minimal_session_data()
                        return render_template("mobile/lineup_escrow_error.html", 
                                             error="An error occurred while rendering the lineup escrow view.",
                                             session_data=session_data)
            except Exception as db_error:
                print(f"Database error in lineup escrow view: {str(db_error)}")
                import traceback
                traceback.print_exc()
                # Create minimal session data for error template
                session_data = _create_minimal_session_data()
                return render_template("mobile/lineup_escrow_error.html", 
                                     error="Database error occurred while loading the lineup escrow.",
                                     session_data=session_data)
                                     
        except Exception as e:
            print(f"Error serving lineup escrow view: {str(e)}")
            import traceback
            traceback.print_exc()
            # Create minimal session data for error template
            session_data = _create_minimal_session_data()
            return render_template("mobile/lineup_escrow_error.html", 
                                 error="An error occurred while loading the lineup escrow.",
                                 session_data=session_data)

    @app.route("/mobile/lineup-escrow-opposing/<escrow_token>", methods=["GET"])
    def serve_mobile_lineup_escrow_opposing(escrow_token):
        """Serve the mobile Lineup Escrow opposing captain page with drag and drop interface"""
        try:
            viewer_contact = request.args.get("contact", "")
            
            # Allow access without contact parameter for originating captains
            # The service will handle this case gracefully
            
            with SessionLocal() as db_session:
                escrow_service = LineupEscrowService(db_session)
                
                result = escrow_service.get_escrow_details(escrow_token, viewer_contact)
                
                if result["success"]:
                    escrow_data = result["escrow_data"]
                    both_lineups_visible = result["both_lineups_visible"]
                    
                    # If both lineups are already visible, redirect to view page
                    if both_lineups_visible:
                        # Only include contact parameter if it exists
                        if viewer_contact and viewer_contact.strip():
                            from urllib.parse import quote
                            encoded_contact = quote(viewer_contact.strip(), safe='')
                            return redirect(f"/mobile/lineup-escrow-view/{escrow_token}?contact={encoded_contact}")
                        else:
                            return redirect(f"/mobile/lineup-escrow-view/{escrow_token}")
                    
                    # Render the opposing captain template
                    # Create minimal session data for non-authenticated users
                    session_data = _create_minimal_session_data()
                    # Add cache-busting headers to prevent caching issues
                    response = make_response(render_template(
                        "mobile/lineup_escrow_opposing_captain.html",
                        escrow_data=escrow_data,
                        both_lineups_visible=both_lineups_visible,
                        session_data=session_data
                    ))
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    return response
                else:
                    return jsonify({"error": result.get("error", "Unknown error")}), 400
                    
        except Exception as e:
            print(f"Error serving lineup escrow opposing page: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
