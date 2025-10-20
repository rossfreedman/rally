from datetime import datetime

from flask import jsonify, request, session

from database_utils import execute_query, execute_query_one
from utils.auth import login_required
from utils.logging import log_user_activity


def get_matches_for_user_club(user):
    """Get upcoming matches and practices for a user's club from the database - ENHANCED with team_id support"""
    try:
        # Get user's club and series
        user_club = user.get("club")
        user_series = user.get("series")
        user_team_id = user.get("team_id")  # NEW: Get team_id from priority-based team detection
        
        if not user_club or not user_series:
            print("Missing club or series in user data")
            return []

        print(f"Looking for matches for club: {user_club}, series: {user_series}, team_id: {user_team_id}")

        # ENHANCED: Use team_id-based queries when available (much more reliable)
        if user_team_id:
            print(f"Using team_id-based query for team_id: {user_team_id}")
            
            # Get user's league_id for filtering
            user_league_id = user.get("league_id")
            print(f"Filtering by league_id: {user_league_id}")
            
            # Query using team_id (more reliable than string matching)
            # FIXED: Add league filtering to prevent cross-league practice contamination
            # FIXED: Add DISTINCT to prevent duplicate practice records
            # ENHANCED: Include team IDs for opponent lookup
            matches_query = """
                SELECT DISTINCT
                    s.match_date,
                    s.match_time,
                    s.home_team,
                    s.away_team,
                    s.home_team_id,
                    s.away_team_id,
                    s.location,
                    c.club_address,
                    l.league_id,
                    CASE 
                        WHEN s.home_team ILIKE %s THEN 'practice'
                        ELSE 'match'
                    END as type
                FROM schedule s
                LEFT JOIN leagues l ON s.league_id = l.id
                LEFT JOIN clubs c ON s.location = c.name
                WHERE (s.home_team_id = %s OR s.away_team_id = %s OR s.home_team ILIKE %s)
                AND (s.league_id = %s OR (s.league_id IS NULL AND s.home_team_id = %s))
                ORDER BY s.match_date, s.match_time
            """
            
            # Practice pattern for ILIKE search (fallback for practices not using team_id)
            # FIXED: Use specific series pattern instead of broad club pattern
            # Handle different series name formats to match practice patterns in database
            if "Division" in user_series:
                division_num = user_series.replace("Division ", "")
                practice_pattern = f"{user_club} Practice - Series {division_num}"
            elif "Series" in user_series:
                # User series already has "Series" prefix, use as-is
                practice_pattern = f"{user_club} Practice - {user_series}"
            else:
                # User series is just a number/letter, add "Series" prefix for practice pattern
                practice_pattern = f"{user_club} Practice - Series {user_series}"
            
            practice_search = f"%{practice_pattern}%"
            print(f"Practice pattern search: {practice_search}")
            
            matches = execute_query(
                matches_query, [practice_search, user_team_id, user_team_id, practice_search, user_league_id, user_team_id]
            )
            
            print(f"Found {len(matches)} matches using team_id {user_team_id}")
            
            # Debug: Log the types of matches found
            practice_count = sum(1 for match in matches if match.get('type') == 'practice')
            match_count = sum(1 for match in matches if match.get('type') == 'match')
            print(f"Debug: Found {practice_count} practices and {match_count} matches")
            
            # FALLBACK: If no matches found with team_id, try string pattern matching
            # This handles cases where schedule records exist with string names but no team_id foreign keys
            if not matches:
                print(f"No matches found with team_id {user_team_id}, trying string pattern fallback...")
                
                # Build string patterns like the legacy method
                if "Series" in user_series:
                    series_code = user_series.replace("Series ", "S")
                    user_team_pattern = f"{user_club} {series_code} - {user_series}"
                elif "Division" in user_series:
                    division_num = user_series.replace("Division ", "")
                    user_team_pattern = f"{user_club} {division_num} - Series {division_num}"
                else:
                    series_num = user_series.split()[-1] if user_series else ""
                    user_team_pattern = f"{user_club} - {series_num}"
                
                print(f"Trying string pattern: {user_team_pattern}")
                
                # Try legacy string pattern matching
                # FIXED: Add league filtering to prevent cross-league practice contamination
                # FIXED: Add DISTINCT to prevent duplicate practice records
                # ENHANCED: Include team IDs for opponent lookup
                legacy_matches_query = """
                    SELECT DISTINCT
                        s.match_date,
                        s.match_time,
                        s.home_team,
                        s.away_team,
                        s.home_team_id,
                        s.away_team_id,
                        s.location,
                        c.club_address,
                        l.league_id,
                        CASE 
                            WHEN s.home_team ILIKE %s THEN 'practice'
                            ELSE 'match'
                        END as type
                    FROM schedule s
                    LEFT JOIN leagues l ON s.league_id = l.id
                    LEFT JOIN clubs c ON s.location = c.name
                    WHERE (s.home_team ILIKE %s OR s.away_team ILIKE %s OR s.home_team ILIKE %s)
                    AND (s.league_id = %s OR (s.league_id IS NULL AND s.home_team_id = %s))
                    ORDER BY s.match_date, s.match_time
                """
                
                # Use the same practice pattern logic as the main query
                if "Division" in user_series:
                    division_num = user_series.replace("Division ", "")
                    practice_pattern = f"{user_club} Practice - Series {division_num}"
                elif "Series" in user_series:
                    # User series already has "Series" prefix, use as-is
                    practice_pattern = f"{user_club} Practice - {user_series}"
                else:
                    # User series is just a number/letter, add "Series" prefix for practice pattern
                    practice_pattern = f"{user_club} Practice - Series {user_series}"
                
                practice_search_legacy = f"%{practice_pattern}%"
                team_search = f"%{user_team_pattern}%"
                
                matches = execute_query(
                    legacy_matches_query, [practice_search_legacy, practice_search_legacy, team_search, team_search, user_league_id, user_team_id]
                )
                
                if matches:
                    print(f"Found {len(matches)} matches using string pattern fallback")
            
        else:
            # FALLBACK: Use legacy string pattern matching when team_id not available
            print(f"No team_id available, falling back to pattern matching")
            
            # Get user's league_id for filtering
            user_league_id = user.get("league_id")
            print(f"Filtering by league_id: {user_league_id}")
            
            # Handle different series name formats
            # For NSTF: "Series 2B" -> "Tennaqua S2B - Series 2B"
    
            # For APTA: "Chicago 22" -> "Tennaqua - 22"

            if "Series" in user_series:
                # NSTF format: "Series 2B" -> "S2B"
                series_code = user_series.replace("Series ", "S")
                user_team_pattern = f"{user_club} {series_code} - {user_series}"
            elif "Division" in user_series:
        
                # FIXED: Schedule uses "Series 16" format, not "Division 16"
                division_num = user_series.replace("Division ", "")
                user_team_pattern = f"{user_club} {division_num} - Series {division_num}"
            else:
                # APTA format: "Chicago 22" -> extract number
                series_num = user_series.split()[-1] if user_series else ""
                user_team_pattern = f"{user_club} - {series_num}"

            print(f"Looking for team pattern: {user_team_pattern}")

            # Create practice pattern for this user's club and series
    
            if "Division" in user_series:
                division_num = user_series.replace("Division ", "")
                practice_pattern = f"{user_club} Practice - Series {division_num}"
            else:
                practice_pattern = f"{user_club} Practice - {user_series}"
            print(f"Looking for practice pattern: {practice_pattern}")

            # Query the database for matches where user's team is playing
            # Include both regular matches and practice entries
            # JOIN with clubs table to get club address for Google Maps links
            # FIXED: Add league filtering to prevent cross-league practice contamination
            # FIXED: Add DISTINCT to prevent duplicate practice records
            # ENHANCED: Include team IDs for opponent lookup
            matches_query = """
                SELECT DISTINCT
                    s.match_date,
                    s.match_time,
                    s.home_team,
                    s.away_team,
                    s.home_team_id,
                    s.away_team_id,
                    s.location,
                    c.club_address,
                    l.league_id,
                    CASE 
                        WHEN s.home_team ILIKE %s THEN 'practice'
                        ELSE 'match'
                    END as type
                FROM schedule s
                LEFT JOIN leagues l ON s.league_id = l.id
                LEFT JOIN clubs c ON s.location = c.name
                WHERE (s.home_team ILIKE %s OR s.away_team ILIKE %s OR s.home_team ILIKE %s)
                AND (s.league_id = %s OR (s.league_id IS NULL AND s.home_team_id = %s))
                ORDER BY s.match_date, s.match_time
            """

            # Search patterns:
            # 1. Practice pattern: "Tennaqua Practice - Chicago 22"
            # 2. Team pattern for regular matches: "Tennaqua - 22"
            practice_search = f"%{practice_pattern}%"
            team_search = f"%{user_team_pattern}%"

            matches = execute_query(
                matches_query, [practice_search, practice_search, team_search, team_search, user_league_id, user_team_id]
            )
            
            # Debug: Log the types of matches found
            practice_count = sum(1 for match in matches if match.get('type') == 'practice')
            match_count = sum(1 for match in matches if match.get('type') == 'match')
            print(f"Debug: Found {practice_count} practices and {match_count} matches")

        filtered_matches = []
        for match in matches:
            try:
                # Format date and time to match the original JSON format
                match_date = (
                    match["match_date"].strftime("%m/%d/%Y")
                    if match["match_date"]
                    else ""
                )
                match_time = (
                    match["match_time"].strftime("%I:%M %p").lstrip("0")
                    if match["match_time"]
                    else ""
                )

                # Determine if this is a practice or match
                is_practice = "Practice" in (match["home_team"] or "")

                # Normalize match data to consistent format
                normalized_match = {
                    "date": match_date,
                    "time": match_time,
                    "location": match["location"] or "",
                    "club_address": match["club_address"] or "",  # Include club address
                    "home_team": match["home_team"] or "",
                    "away_team": match["away_team"] or "",
                    "home_team_id": match.get("home_team_id"),
                    "away_team_id": match.get("away_team_id"),
                    "type": "practice" if is_practice else "match",
                }

                # Add practice-specific fields
                if is_practice:
                    normalized_match["description"] = match["home_team"]

                filtered_matches.append(normalized_match)

                if is_practice:
                    print(
                        f"Found practice: {match['home_team']} on {match_date} at {match_time}"
                    )
                else:
                    print(
                        f"Found match: {match['home_team']} vs {match['away_team']} on {match_date}"
                    )

            except Exception as e:
                print(f"Warning: Skipping invalid match record: {e}")
                continue

        # Sort matches by date and time (same logic as reference)
        def sort_key(match):
            try:
                date_obj = datetime.strptime(match["date"], "%m/%d/%Y")
                time_obj = datetime.strptime(match["time"], "%I:%M %p")
                return (date_obj, time_obj)
            except ValueError:
                # If parsing fails, put it at the end
                return (datetime.max, datetime.max)

        filtered_matches.sort(key=sort_key)

        print(
            f"Found {len(filtered_matches)} total entries (matches + practices) for team"
        )
        return filtered_matches

    except Exception as e:
        print(f"Error getting matches for user club: {str(e)}")
        return []


def init_schedule_routes(app):
    @app.route("/api/schedule")
    @login_required
    def serve_schedule():
        """Serve the schedule data from database"""
        try:
            # ✅ FIX: Return user-specific schedule data in expected format
            user = session.get("user")
            if not user:
                return jsonify({"error": "User not found in session"}), 401

            # Get user's matches using existing function
            user_matches = get_matches_for_user_club(user)
            
            # Convert to expected format
            schedule_data = {
                "matches": user_matches,
                "user": {
                    "club": user.get("club"),
                    "series": user.get("series")
                },
                "total_matches": len(user_matches)
            }
            
            return jsonify(schedule_data)
            
        except Exception as e:
            print(f"Error loading schedule from database: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/team-matches")
    @login_required
    def get_team_matches():
        """Get matches for a team from database"""
        try:
            # Query match history from the database instead of JSON file
            query = """
                SELECT 
                    ms.match_date as "Date",
                    ms.home_team as "Home Team",
                    ms.away_team as "Away Team",
                    ms.home_player_1_id as "Home Player 1 ID",
                    ms.home_player_2_id as "Home Player 2 ID", 
                    ms.away_player_1_id as "Away Player 1 ID",
                    ms.away_player_2_id as "Away Player 2 ID",
                    ms.scores as "Scores",
                    ms.winner as "Winner",
                    l.league_id
                FROM match_scores ms
                LEFT JOIN leagues l ON ms.league_id = l.id
                ORDER BY ms.match_date DESC
            """
            matches = execute_query(query)

            # Convert date objects to strings for JSON serialization
            for match in matches:
                if match.get("Date"):
                    match["Date"] = match["Date"].strftime("%d-%b-%y")

            return jsonify(matches)
        except Exception as e:
            print(f"Error getting team matches from database: {str(e)}")
            return jsonify({"error": str(e)}), 500
