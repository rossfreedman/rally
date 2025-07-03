"""
Simplified Data-Driven Match Simulation Service

This module provides match simulation between two platform tennis pairings
using real, available player data and statistics from the database.
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from database_utils import execute_query, execute_query_one


class AdvancedMatchupSimulator:
    """
    Data-driven matchup simulator using real player statistics and performance data.
    Focuses on individual player metrics that are actually available in the database.
    """

    def __init__(self):
        # Simplified metric weights focused on available data
        self.metric_weights = {
            # Individual Player Metrics (70% total weight)
            "average_pti": 0.25,  # Team average PTI - strongest predictor
            "individual_win_rates": 0.20,  # Individual player win percentages
            "recent_individual_form": 0.15,  # Recent match performance per player
            "head_to_head_record": 0.15,  # Direct matchups between players
            "experience_level": 0.15,  # Total matches played by players (increased to balance)
            # Head-to-Head & Comparative (30% total weight)
            "consistency_factor": 0.05,  # PTI consistency/volatility
            "pti_advantage": 0.05,  # PTI difference between teams
        }

        # Validate weights sum to 1.0
        total_weight = sum(self.metric_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Metric weights must sum to 1.0, got {total_weight}")

    def simulate_matchup(
        self,
        team_a_players: List[int],
        team_b_players: List[int],
        user_league_id: Optional[str] = None,
    ) -> Dict:
        """
        Generate a matchup simulation using real player data and statistics.

        Args:
            team_a_players: List of 2 player IDs for Team A
            team_b_players: List of 2 player IDs for Team B
            user_league_id: Optional league filter for data

        Returns:
            Dictionary containing simulation results and detailed analysis
        """
        try:
            print(
                f"[DEBUG] Starting simulation: Team A {team_a_players} vs Team B {team_b_players}"
            )

            # Convert string league_id to integer foreign key if needed
            league_id_int = None
            if isinstance(user_league_id, str) and user_league_id != "":
                try:
                    league_record = execute_query_one(
                        "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                    )
                    if league_record:
                        league_id_int = league_record["id"]
                        print(
                            f"[DEBUG] Converted league_id '{user_league_id}' to integer: {league_id_int}"
                        )
                except Exception as e:
                    print(f"[DEBUG] Could not convert league ID: {e}")
            elif isinstance(user_league_id, int):
                league_id_int = user_league_id

            # Validate input
            if len(team_a_players) != 2 or len(team_b_players) != 2:
                return {"error": "Each team must have exactly 2 players"}

            # Get player data for both teams
            team_a_data = self._get_team_data(team_a_players, league_id_int)
            team_b_data = self._get_team_data(team_b_players, league_id_int)

            if not team_a_data["valid"] or not team_b_data["valid"]:
                return {"error": "Could not find all player data"}

            # Calculate metrics for both teams using real data
            team_a_metrics = self._calculate_real_metrics(
                team_a_players, league_id_int, team_b_players
            )
            team_b_metrics = self._calculate_real_metrics(
                team_b_players, league_id_int, team_a_players
            )

            # Calculate PTI advantage for each team (15% weight)
            team_a_avg_pti = team_a_metrics.get("average_pti", 25.0)
            team_b_avg_pti = team_b_metrics.get("average_pti", 25.0)

            # Team A's PTI advantage = their PTI - opponent's PTI
            team_a_metrics["pti_advantage"] = team_a_avg_pti - team_b_avg_pti
            # Team B's PTI advantage = their PTI - opponent's PTI
            team_b_metrics["pti_advantage"] = team_b_avg_pti - team_a_avg_pti

            print(f"[DEBUG] Team A metrics: {team_a_metrics}")
            print(f"[DEBUG] Team B metrics: {team_b_metrics}")
            print(
                f"[DEBUG] PTI advantage: Team A = {team_a_metrics['pti_advantage']:.1f}, Team B = {team_b_metrics['pti_advantage']:.1f}"
            )

            # Calculate composite scores
            team_a_score = self._calculate_composite_score(team_a_metrics)
            team_b_score = self._calculate_composite_score(team_b_metrics)

            print(
                f"[DEBUG] Composite scores: Team A = {team_a_score:.3f}, Team B = {team_b_score:.3f}"
            )

            # Calculate win probability
            win_probability = self._calculate_win_probability(
                team_a_score, team_b_score
            )

            # Generate analysis
            advantages = self._analyze_advantages(
                team_a_metrics, team_b_metrics, team_a_data, team_b_data
            )
            confidence = self._determine_confidence(
                team_a_metrics, team_b_metrics, win_probability
            )

            return {
                "success": True,
                "team_a": {
                    "players": team_a_data["players"],
                    "metrics": team_a_metrics,
                    "composite_score": team_a_score,
                },
                "team_b": {
                    "players": team_b_data["players"],
                    "metrics": team_b_metrics,
                    "composite_score": team_b_score,
                },
                "prediction": {
                    "team_a_probability": round(win_probability, 1),
                    "team_b_probability": round(100 - win_probability, 1),
                    "predicted_winner": "Team A" if win_probability > 50 else "Team B",
                    "confidence": confidence,
                },
                "advantages": advantages,
                "metric_breakdown": self._get_metric_breakdown(
                    team_a_metrics, team_b_metrics
                ),
            }

        except Exception as e:
            print(f"Error in simulate_matchup: {str(e)}")
            import traceback

            traceback.print_exc()
            return {"error": f"Simulation failed: {str(e)}"}

    def _get_team_data(
        self, player_ids: List[int], league_id: Optional[int] = None
    ) -> Dict:
        """Get basic player information for a team."""
        try:
            players = []

            for player_id in player_ids:
                query = """
                    SELECT id, first_name, last_name, pti, wins, losses, win_percentage
                    FROM players 
                    WHERE id = %s
                """
                params = [player_id]

                if league_id:
                    query += " AND league_id = %s"
                    params.append(league_id)

                player_data = execute_query_one(query, params)

                if not player_data:
                    print(f"[DEBUG] Player {player_id} not found")
                    return {"valid": False, "players": []}

                players.append(
                    {
                        "id": player_data["id"],
                        "name": f"{player_data['first_name']} {player_data['last_name']}",
                        "pti": (
                            float(player_data["pti"]) if player_data["pti"] else 25.0
                        ),  # Default PTI
                        "wins": player_data["wins"] or 0,
                        "losses": player_data["losses"] or 0,
                        "win_percentage": (
                            float(player_data["win_percentage"])
                            if player_data["win_percentage"]
                            else 0.0
                        ),
                    }
                )

            return {"valid": True, "players": players}

        except Exception as e:
            print(f"Error getting team data: {str(e)}")
            return {"valid": False, "players": []}

    def _calculate_real_metrics(
        self,
        player_ids: List[int],
        league_id: Optional[int] = None,
        opponent_player_ids: Optional[List[int]] = None,
    ) -> Dict:
        """Calculate metrics using real, available player data."""
        try:
            metrics = {}

            # Get player data
            players_data = []
            for player_id in player_ids:
                query = """
                    SELECT id, first_name, last_name, pti, wins, losses, win_percentage, 
                           tenniscores_player_id
                    FROM players 
                    WHERE id = %s
                """
                params = [player_id]
                if league_id:
                    query += " AND league_id = %s"
                    params.append(league_id)

                player_data = execute_query_one(query, params)
                if player_data:
                    players_data.append(player_data)

            if len(players_data) != 2:
                return self._get_default_metrics()

            # 1. Average PTI (25% weight) - Most important metric
            ptis = []
            for player in players_data:
                pti = float(player["pti"]) if player["pti"] else 25.0
                ptis.append(pti)
            metrics["average_pti"] = statistics.mean(ptis)

            # 2. Individual Win Rates (20% weight)
            win_rates = []
            for player in players_data:
                if player["win_percentage"]:
                    win_rates.append(float(player["win_percentage"]))
                elif (player["wins"] or 0) + (player["losses"] or 0) > 0:
                    total_matches = (player["wins"] or 0) + (player["losses"] or 0)
                    win_rate = ((player["wins"] or 0) / total_matches) * 100
                    win_rates.append(win_rate)
                else:
                    win_rates.append(50.0)  # Default for no data
            metrics["individual_win_rates"] = statistics.mean(win_rates)

            # 3. Recent Individual Form (15% weight)
            recent_form_scores = []
            for player in players_data:
                recent_form = self._get_player_recent_form(
                    player["tenniscores_player_id"], league_id
                )
                recent_form_scores.append(recent_form)
            metrics["recent_individual_form"] = statistics.mean(recent_form_scores)

            # 4. Experience Level (10% weight)
            experience_scores = []
            for player in players_data:
                total_matches = (player["wins"] or 0) + (player["losses"] or 0)
                experience_scores.append(total_matches)
            metrics["experience_level"] = statistics.mean(experience_scores)

            # 5. PTI Advantage (15% weight) - calculated in main simulation after both teams are processed
            metrics["pti_advantage"] = (
                0.0  # Temporary placeholder, will be overwritten with actual calculation
            )

            # 6. Head-to-Head Record (10% weight)
            if opponent_player_ids and len(opponent_player_ids) == 2:
                # Get opponent player data
                opponent_players_data = []
                for opponent_id in opponent_player_ids:
                    query = """
                        SELECT id, first_name, last_name, pti, wins, losses, win_percentage, 
                               tenniscores_player_id
                        FROM players 
                        WHERE id = %s
                    """
                    params = [opponent_id]
                    if league_id:
                        query += " AND league_id = %s"
                        params.append(league_id)

                    opponent_data = execute_query_one(query, params)
                    if opponent_data:
                        opponent_players_data.append(opponent_data)

                if len(opponent_players_data) == 2:
                    h2h_score = self._calculate_head_to_head(
                        players_data, opponent_players_data, league_id
                    )
                else:
                    h2h_score = 50.0  # Default if opponent data not found
            else:
                h2h_score = 50.0  # Default if no opponent provided

            metrics["head_to_head_record"] = h2h_score

            # 7. Consistency Factor (5% weight)
            consistency_scores = []
            for player in players_data:
                consistency = self._get_player_consistency(player["id"])
                consistency_scores.append(consistency)
            metrics["consistency_factor"] = statistics.mean(consistency_scores)

            return metrics

        except Exception as e:
            print(f"Error calculating real metrics: {str(e)}")
            return self._get_default_metrics()

    def _get_player_recent_form(
        self, tenniscores_player_id: str, league_id: Optional[int] = None
    ) -> float:
        """Get player's recent performance based on last 5 matches."""
        try:
            if not tenniscores_player_id:
                return 50.0

            # Get recent matches for this player
            query = """
                SELECT winner, match_date,
                       home_player_1_id, home_player_2_id, 
                       away_player_1_id, away_player_2_id
                FROM match_scores 
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR 
                       away_player_1_id = %s OR away_player_2_id = %s)
            """
            params = [
                tenniscores_player_id,
                tenniscores_player_id,
                tenniscores_player_id,
                tenniscores_player_id,
            ]

            if league_id:
                query += " AND league_id = %s"
                params.append(league_id)

            query += " ORDER BY match_date DESC LIMIT 5"

            recent_matches = execute_query(query, params)

            if not recent_matches:
                return 50.0  # Default if no recent matches

            wins = 0
            for match in recent_matches:
                is_home = tenniscores_player_id in [
                    match["home_player_1_id"],
                    match["home_player_2_id"],
                ]
                won = (is_home and match["winner"] == "home") or (
                    not is_home and match["winner"] == "away"
                )
                if won:
                    wins += 1

            return (wins / len(recent_matches)) * 100

        except Exception as e:
            print(f"Error getting recent performance: {str(e)}")
            return 50.0

    def _calculate_head_to_head(
        self,
        team_a_players: List[Dict],
        team_b_players: List[Dict],
        league_id: Optional[int] = None,
    ) -> float:
        """Calculate head-to-head performance between these specific team pairings."""
        try:
            if len(team_a_players) != 2 or len(team_b_players) != 2:
                print(
                    f"[DEBUG H2H] Invalid team sizes: Team A={len(team_a_players)}, Team B={len(team_b_players)}"
                )
                return 50.0

            # Get ALL TennisScores IDs for both teams (including duplicates)
            team_a_ids = []
            team_b_ids = []

            # For each player, find ALL their TennisScores IDs in case of duplicates
            for player in team_a_players:
                if player["tenniscores_player_id"]:
                    team_a_ids.append(player["tenniscores_player_id"])
                # Also look for other records with same name
                name_query = """
                    SELECT DISTINCT tenniscores_player_id 
                    FROM players 
                    WHERE first_name = %s AND last_name = %s AND tenniscores_player_id IS NOT NULL
                """
                alt_ids = execute_query(
                    name_query, [player["first_name"], player["last_name"]]
                )
                for alt_id in alt_ids:
                    if alt_id["tenniscores_player_id"] not in team_a_ids:
                        team_a_ids.append(alt_id["tenniscores_player_id"])

            for player in team_b_players:
                if player["tenniscores_player_id"]:
                    team_b_ids.append(player["tenniscores_player_id"])
                # Also look for other records with same name
                name_query = """
                    SELECT DISTINCT tenniscores_player_id 
                    FROM players 
                    WHERE first_name = %s AND last_name = %s AND tenniscores_player_id IS NOT NULL
                """
                alt_ids = execute_query(
                    name_query, [player["first_name"], player["last_name"]]
                )
                for alt_id in alt_ids:
                    if alt_id["tenniscores_player_id"] not in team_b_ids:
                        team_b_ids.append(alt_id["tenniscores_player_id"])

            print(
                f"[DEBUG H2H] Team A players: {[(p.get('first_name', ''), p.get('last_name', ''), p.get('tenniscores_player_id', 'None')) for p in team_a_players]}"
            )
            print(
                f"[DEBUG H2H] Team B players: {[(p.get('first_name', ''), p.get('last_name', ''), p.get('tenniscores_player_id', 'None')) for p in team_b_players]}"
            )
            print(f"[DEBUG H2H] Team A TennisScores IDs: {team_a_ids}")
            print(f"[DEBUG H2H] Team B TennisScores IDs: {team_b_ids}")

            if len(team_a_ids) == 0 or len(team_b_ids) == 0:
                print(
                    f"[DEBUG H2H] Missing TennisScores IDs: Team A has {len(team_a_ids)}, Team B has {len(team_b_ids)}"
                )
                return 50.0

            # Build dynamic query to handle variable number of player IDs
            team_a_placeholders = ", ".join(["%s"] * len(team_a_ids))
            team_b_placeholders = ", ".join(["%s"] * len(team_b_ids))

            query = f"""
                SELECT winner, match_date,
                       home_player_1_id, home_player_2_id, 
                       away_player_1_id, away_player_2_id
                FROM match_scores 
                WHERE (
                    -- Team A was home, Team B was away
                    (home_player_1_id IN ({team_a_placeholders}) AND home_player_2_id IN ({team_a_placeholders}) AND
                     away_player_1_id IN ({team_b_placeholders}) AND away_player_2_id IN ({team_b_placeholders}))
                ) OR (
                    -- Team A was away, Team B was home
                    (away_player_1_id IN ({team_a_placeholders}) AND away_player_2_id IN ({team_a_placeholders}) AND
                     home_player_1_id IN ({team_b_placeholders}) AND home_player_2_id IN ({team_b_placeholders}))
                )
            """

            # Use team IDs for each condition
            params = (
                team_a_ids
                + team_a_ids
                + team_b_ids
                + team_b_ids
                + team_a_ids
                + team_a_ids
                + team_b_ids
                + team_b_ids
            )

            if league_id:
                query += " AND league_id = %s"
                params.append(league_id)

            query += " ORDER BY match_date DESC"

            print(f"[DEBUG H2H] Query: {query}")
            print(f"[DEBUG H2H] Params: {params}")

            head_to_head_matches = execute_query(query, params)

            print(
                f"[DEBUG H2H] Found {len(head_to_head_matches) if head_to_head_matches else 0} head-to-head matches"
            )
            if head_to_head_matches:
                for i, match in enumerate(head_to_head_matches):
                    print(
                        f"[DEBUG H2H] Match {i+1}: Date={match.get('match_date')}, Winner={match.get('winner')}"
                    )
                    print(
                        f"[DEBUG H2H]   Home: {match.get('home_player_1_id')} & {match.get('home_player_2_id')}"
                    )
                    print(
                        f"[DEBUG H2H]   Away: {match.get('away_player_1_id')} & {match.get('away_player_2_id')}"
                    )

            if not head_to_head_matches:
                print(f"[DEBUG H2H] No head-to-head matches found - returning 50.0")
                return 50.0  # No head-to-head history, neutral score

            # Count wins for Team A
            team_a_wins = 0
            total_matches = len(head_to_head_matches)

            for match in head_to_head_matches:
                # Determine if Team A was home or away in this match
                team_a_was_home = (
                    match["home_player_1_id"] in team_a_ids
                    and match["home_player_2_id"] in team_a_ids
                )
                team_a_was_away = (
                    match["away_player_1_id"] in team_a_ids
                    and match["away_player_2_id"] in team_a_ids
                )

                # Team A wins if: (they were home and winner='home') or (they were away and winner='away')
                if (team_a_was_home and match["winner"] == "home") or (
                    team_a_was_away and match["winner"] == "away"
                ):
                    team_a_wins += 1

            # Calculate win percentage for Team A
            team_a_win_percentage = (team_a_wins / total_matches) * 100

            # Give more weight to recent matches (last 3 matches get 2x weight)
            if total_matches >= 3:
                recent_matches = head_to_head_matches[:3]
                recent_team_a_wins = 0

                for match in recent_matches:
                    team_a_was_home = (
                        match["home_player_1_id"] in team_a_ids
                        and match["home_player_2_id"] in team_a_ids
                    )
                    team_a_was_away = (
                        match["away_player_1_id"] in team_a_ids
                        and match["away_player_2_id"] in team_a_ids
                    )
                    if (team_a_was_home and match["winner"] == "home") or (
                        team_a_was_away and match["winner"] == "away"
                    ):
                        recent_team_a_wins += 1

                recent_win_percentage = (recent_team_a_wins / len(recent_matches)) * 100

                # Weighted average: 60% recent, 40% overall
                team_a_win_percentage = (recent_win_percentage * 0.6) + (
                    team_a_win_percentage * 0.4
                )

            print(
                f"[DEBUG] Head-to-head: Team A won {team_a_wins}/{total_matches} matches ({team_a_win_percentage:.1f}%)"
            )
            return team_a_win_percentage

        except Exception as e:
            print(f"Error calculating head-to-head: {str(e)}")
            return 50.0

    def _get_player_consistency(self, player_id: int) -> float:
        """Get player's PTI consistency from player_history."""
        try:
            query = """
                SELECT end_pti
                FROM player_history 
                WHERE player_id = %s AND end_pti IS NOT NULL
                ORDER BY date DESC
                LIMIT 10
            """
            history = execute_query(query, [player_id])

            if not history or len(history) < 3:
                return 50.0  # Default for insufficient data

            ptis = [float(h["end_pti"]) for h in history]
            std_dev = statistics.stdev(ptis)

            # Convert standard deviation to a 0-100 scale (lower std_dev = higher consistency)
            # Assume std_dev of 0-10 maps to consistency of 100-0
            consistency = max(0, 100 - (std_dev * 10))
            return consistency

        except Exception as e:
            print(f"Error getting player consistency: {str(e)}")
            return 50.0

    def _get_default_metrics(self) -> Dict:
        """Return default metrics when data is unavailable."""
        return {
            "average_pti": 25.0,
            "individual_win_rates": 50.0,
            "recent_individual_form": 50.0,
            "experience_level": 0,
            "pti_advantage": 0.0,
            "head_to_head_record": 50.0,
            "consistency_factor": 50.0,
        }

    def _normalize_metrics(self, metrics: Dict) -> Dict:
        """Normalize metrics to 0-1 scale."""
        normalized = {}

        # Normalization parameters based on realistic competitive ranges
        normalization_params = {
            "average_pti": {
                "min": 18.0,
                "max": 38.0,
                "higher_better": False,
            },  # Lower PTI = stronger player
            "individual_win_rates": {
                "min": 20.0,
                "max": 80.0,
                "higher_better": True,
            },  # Realistic competitive range
            "recent_individual_form": {"min": 0.0, "max": 100.0, "higher_better": True},
            "experience_level": {
                "min": 0,
                "max": 40,
                "higher_better": True,
            },  # More realistic max experience
            "pti_advantage": {
                "min": -8.0,
                "max": 8.0,
                "higher_better": True,
            },  # Tighter range for more impact
            "head_to_head_record": {"min": 0.0, "max": 100.0, "higher_better": True},
            "consistency_factor": {"min": 0.0, "max": 100.0, "higher_better": True},
        }

        for metric_name, value in metrics.items():
            if metric_name in normalization_params:
                params = normalization_params[metric_name]

                # Clamp value to min/max range
                clamped_value = max(params["min"], min(params["max"], value))

                # Normalize to 0-1
                if params["max"] != params["min"]:
                    normalized_value = (clamped_value - params["min"]) / (
                        params["max"] - params["min"]
                    )
                    
                    # Invert if lower values are better (like PTI)
                    if not params.get("higher_better", True):
                        normalized_value = 1.0 - normalized_value
                else:
                    normalized_value = 0.5

                normalized[metric_name] = normalized_value
            else:
                normalized[metric_name] = min(
                    1.0, max(0.0, value / 100.0)
                )  # Default normalization

        return normalized

    def _calculate_composite_score(self, raw_metrics: Dict) -> float:
        """Calculate weighted composite score from normalized metrics."""
        try:
            # Normalize metrics first
            normalized_metrics = self._normalize_metrics(raw_metrics)

            print(f"[DEBUG] Normalized metrics: {normalized_metrics}")

            # Calculate weighted score
            composite_score = 0.0
            total_weight_used = 0.0

            for metric_name, weight in self.metric_weights.items():
                if metric_name in normalized_metrics:
                    metric_value = normalized_metrics[metric_name]
                    weighted_contribution = metric_value * weight
                    composite_score += weighted_contribution
                    total_weight_used += weight

                    print(
                        f"[DEBUG] {metric_name}: {metric_value:.3f} * {weight:.3f} = {weighted_contribution:.3f}"
                    )

            # Don't divide by total_weight_used - the weights already sum to 1.0
            # If some metrics are missing, we want the score to reflect the actual weighted sum
            # Only normalize if we have less than 80% of the total weight
            if total_weight_used < 0.8:
                composite_score = composite_score / total_weight_used
                print(
                    f"[DEBUG] Normalized due to missing data: {total_weight_used:.3f} weight used"
                )

            print(
                f"[DEBUG] Final composite score: {composite_score:.3f} (total weight used: {total_weight_used:.3f})"
            )

            return composite_score

        except Exception as e:
            print(f"Error calculating composite score: {str(e)}")
            return 0.5

    def _calculate_win_probability(self, score_a: float, score_b: float) -> float:
        """Calculate win probability using logistic function."""
        try:
            # Calculate score difference for Team A
            score_diff = score_a - score_b

            print(f"[DEBUG] Score difference: {score_diff:.3f}")

            # Apply logistic function with moderate scaling
            # Balanced scaling factor for reasonable but not extreme predictions
            scaling_factor = 5.0  # Moderate sensitivity to differences
            win_probability = 1 / (1 + math.exp(-scaling_factor * score_diff))

            # Convert to percentage and apply reasonable bounds
            win_probability_pct = win_probability * 100
            win_probability_pct = max(
                30.0, min(70.0, win_probability_pct)
            )  # Keep between 30-70% for balanced predictions

            print(f"[DEBUG] Win probability: {win_probability_pct:.1f}%")

            return win_probability_pct

        except Exception as e:
            print(f"Error calculating win probability: {str(e)}")
            return 50.0

    def _analyze_advantages(
        self,
        team_a_metrics: Dict,
        team_b_metrics: Dict,
        team_a_data: Dict,
        team_b_data: Dict,
    ) -> Dict:
        """Analyze advantages based on real metrics."""
        try:
            advantages = {
                "team_a_advantages": [],
                "team_b_advantages": [],
                "key_factors": [],
            }

            # Compare PTI (lower PTI = stronger player)
            pti_diff = team_a_metrics.get("average_pti", 0) - team_b_metrics.get(
                "average_pti", 0
            )
            if pti_diff < -2:  # Team A has lower PTI (stronger)
                advantages["team_a_advantages"].append(
                    f'Lower average PTI ({team_a_metrics["average_pti"]:.1f} vs {team_b_metrics["average_pti"]:.1f})'
                )
            elif pti_diff > 2:  # Team B has lower PTI (stronger)
                advantages["team_b_advantages"].append(
                    f'Lower average PTI ({team_b_metrics["average_pti"]:.1f} vs {team_a_metrics["average_pti"]:.1f})'
                )

            # Compare win rates
            wr_diff = team_a_metrics.get(
                "individual_win_rates", 0
            ) - team_b_metrics.get("individual_win_rates", 0)
            if wr_diff > 10:
                advantages["team_a_advantages"].append(
                    f'Better individual win rates ({team_a_metrics["individual_win_rates"]:.1f}% vs {team_b_metrics["individual_win_rates"]:.1f}%)'
                )
            elif wr_diff < -10:
                advantages["team_b_advantages"].append(
                    f'Better individual win rates ({team_b_metrics["individual_win_rates"]:.1f}% vs {team_a_metrics["individual_win_rates"]:.1f}%)'
                )

            # Compare recent performance
            form_diff = team_a_metrics.get(
                "recent_individual_form", 0
            ) - team_b_metrics.get("recent_individual_form", 0)
            if form_diff > 15:
                advantages["team_a_advantages"].append("Better recent performance")
            elif form_diff < -15:
                advantages["team_b_advantages"].append("Better recent performance")

            # Compare experience
            exp_diff = team_a_metrics.get("experience_level", 0) - team_b_metrics.get(
                "experience_level", 0
            )
            if exp_diff > 10:
                advantages["team_a_advantages"].append("More experienced players")
            elif exp_diff < -10:
                advantages["team_b_advantages"].append("More experienced players")

            return advantages

        except Exception as e:
            print(f"Error analyzing advantages: {str(e)}")
            return {"team_a_advantages": [], "team_b_advantages": [], "key_factors": []}

    def _determine_confidence(
        self, team_a_metrics: Dict, team_b_metrics: Dict, win_probability: float
    ) -> str:
        """Determine confidence based on data quality and prediction margin."""
        try:
            confidence_factors = 0

            # Data quality factors
            avg_experience = (
                team_a_metrics.get("experience_level", 0)
                + team_b_metrics.get("experience_level", 0)
            ) / 2
            if avg_experience >= 10:
                confidence_factors += 2
            elif avg_experience >= 5:
                confidence_factors += 1

            # Prediction margin
            margin = abs(win_probability - 50)
            if margin > 15:
                confidence_factors += 2
            elif margin > 8:
                confidence_factors += 1

            # PTI data availability
            if (
                team_a_metrics.get("average_pti", 0) > 15
                and team_b_metrics.get("average_pti", 0) > 15
            ):
                confidence_factors += 1

            # Determine confidence level
            if confidence_factors >= 4:
                return "high"
            elif confidence_factors >= 2:
                return "medium"
            else:
                return "low"

        except Exception as e:
            print(f"Error determining confidence: {str(e)}")
            return "low"

    def _get_metric_breakdown(self, team_a_metrics: Dict, team_b_metrics: Dict) -> Dict:
        """Get detailed breakdown of metric contributions."""
        try:
            breakdown = {}

            team_a_normalized = self._normalize_metrics(team_a_metrics)
            team_b_normalized = self._normalize_metrics(team_b_metrics)

            for metric_name, weight in self.metric_weights.items():
                team_a_value = team_a_normalized.get(metric_name, 0.0)
                team_b_value = team_b_normalized.get(metric_name, 0.0)

                breakdown[metric_name] = {
                    "team_a_normalized": team_a_value,
                    "team_b_normalized": team_b_value,
                    "weight": weight,
                    "advantage": (
                        "Team A"
                        if team_a_value > team_b_value
                        else "Team B" if team_b_value > team_a_value else "Even"
                    ),
                }

            return breakdown

        except Exception as e:
            print(f"Error getting metric breakdown: {str(e)}")
            return {}


# Legacy function for backward compatibility - updated to use match_scores table
def get_teams_for_selection(
    user_league_id: Optional[str] = None,
    user_series: Optional[str] = None,
    user_club: Optional[str] = None,
) -> List[Dict]:
    """Get available teams (actual clubs/series) for matchup selection using new teams table."""
    try:
        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                )
                if league_record:
                    league_id_int = league_record["id"]
                    print(
                        f"[DEBUG] get_teams_for_selection: Converted league_id '{user_league_id}' to integer: {league_id_int}"
                    )
                else:
                    print(
                        f"[WARNING] get_teams_for_selection: League '{user_league_id}' not found in leagues table"
                    )
            except Exception as e:
                print(
                    f"[DEBUG] get_teams_for_selection: Could not convert league ID: {e}"
                )
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id
            print(
                f"[DEBUG] get_teams_for_selection: League_id already integer: {league_id_int}"
            )

        # Get teams from the new teams table with club and series info
        query = """
            SELECT DISTINCT 
                t.id as team_id,
                t.team_name,
                t.team_alias,
                c.name as club_name,
                s.name as series_name,
                -- Generate display name: use alias if exists, otherwise create from series
                COALESCE(
                    t.team_alias,
                    CASE 
                        WHEN s.name LIKE 'Chicago %' THEN 'Series ' || REPLACE(s.name, 'Chicago ', '')
                        WHEN s.name LIKE 'Division %' THEN 'Series ' || REPLACE(s.name, 'Division ', '')
                        ELSE s.name
                    END
                ) as display_name
            FROM teams t
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            WHERE t.is_active = TRUE
        """

        params = []
        if league_id_int:
            query += " AND t.league_id = %s"
            params.append(league_id_int)

        # Filter by user's series if provided (show all teams in series, not just user's club)
        if user_series:
            query += " AND s.name = %s"
            params.append(user_series)

        query += " ORDER BY c.name, s.name"

        results = execute_query(query, params)

        teams = []
        for row in results:
            # The SQL query already handles display_name generation
            display_name = row["display_name"]
            
            teams.append({
                "id": row["team_id"],
                "name": row["team_name"], 
                "display_name": display_name,
                "club_name": row["club_name"],
                "series_name": row["series_name"]
            })

        print(
            f"[DEBUG] get_teams_for_selection: Found {len(teams)} teams for league_id {league_id_int}, series '{user_series}' (all clubs in series)"
        )

        return teams

    except Exception as e:
        print(f"Error getting teams for selection: {str(e)}")
        return []


def get_players_by_team(
    team_name: str, user_league_id: Optional[str] = None
) -> List[Dict]:
    """Get players for a specific team using the new team structure."""
    try:
        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                )
                if league_record:
                    league_id_int = league_record["id"]
                    print(
                        f"[DEBUG] get_players_by_team: Converted league_id '{user_league_id}' to integer: {league_id_int}"
                    )
                else:
                    print(
                        f"[WARNING] get_players_by_team: League '{user_league_id}' not found in leagues table"
                    )
            except Exception as e:
                print(f"[DEBUG] get_players_by_team: Could not convert league ID: {e}")
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id
            print(
                f"[DEBUG] get_players_by_team: League_id already integer: {league_id_int}"
            )

        # Try to parse team_name as either "Club - Series" format or exact team name
        club_name = None
        series_name = None
        
        if " - " in team_name:
            # Format: "Club - Series"
            parts = team_name.split(" - ")
            if len(parts) == 2:
                club_name = parts[0].strip()
                series_name = parts[1].strip()
        
        # Get players using the new team structure
        if club_name and series_name:
            # Query by club and series combination
            query = """
                SELECT DISTINCT 
                    p.id, 
                    p.first_name, 
                    p.last_name, 
                    p.pti
                FROM players p
                JOIN teams t ON p.team_id = t.id
                JOIN clubs c ON t.club_id = c.id
                JOIN series s ON t.series_id = s.id
                WHERE c.name = %s AND s.name = %s AND p.is_active = TRUE
            """
            params = [club_name, series_name]
            
            if league_id_int:
                query += " AND p.league_id = %s"
                params.append(league_id_int)
        else:
            # Query by exact team name
            query = """
                SELECT DISTINCT 
                    p.id, 
                    p.first_name, 
                    p.last_name, 
                    p.pti
                FROM players p
                JOIN teams t ON p.team_id = t.id
                WHERE t.team_name = %s AND p.is_active = TRUE
            """
            params = [team_name]
            
            if league_id_int:
                query += " AND p.league_id = %s"
                params.append(league_id_int)

        query += " ORDER BY p.first_name, p.last_name"
        players = execute_query(query, params)

        print(
            f"[DEBUG] get_players_by_team: Found {len(players)} players for team '{team_name}'"
        )

        if not players:
            return []

        return [
            {
                "id": player["id"],
                "name": f"{player['first_name']} {player['last_name']}",
                "pti": player.get("pti", 0),
            }
            for player in players
        ]

    except Exception as e:
        print(f"Error getting players by team: {str(e)}")
        return []


def get_players_for_selection(user_league_id: Optional[str] = None) -> List[Dict]:
    """Get players available for selection."""
    try:
        # Convert string league_id to integer foreign key if needed
        league_id_int = None
        if isinstance(user_league_id, str) and user_league_id != "":
            try:
                league_record = execute_query_one(
                    "SELECT id FROM leagues WHERE league_id = %s", [user_league_id]
                )
                if league_record:
                    league_id_int = league_record["id"]
                    print(
                        f"[DEBUG] get_players_for_selection: Converted league_id '{user_league_id}' to integer: {league_id_int}"
                    )
                else:
                    print(
                        f"[WARNING] get_players_for_selection: League '{user_league_id}' not found in leagues table"
                    )
            except Exception as e:
                print(
                    f"[DEBUG] get_players_for_selection: Could not convert league ID: {e}"
                )
        elif isinstance(user_league_id, int):
            league_id_int = user_league_id
            print(
                f"[DEBUG] get_players_for_selection: League_id already integer: {league_id_int}"
            )

        query = """
            SELECT id, first_name, last_name, pti
            FROM players
        """
        params = []

        if league_id_int:
            query += " WHERE league_id = %s"
            params.append(league_id_int)

        query += " ORDER BY first_name, last_name LIMIT 100"

        players = execute_query(query, params)

        return [
            {
                "id": player["id"],
                "name": f"{player['first_name']} {player['last_name']}",
                "pti": player["pti"],
            }
            for player in players or []
        ]

    except Exception as e:
        print(f"Error getting players for selection: {str(e)}")
        return []
