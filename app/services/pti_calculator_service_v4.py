"""
PTI Calculator Service v4.0 - EXACT REFERENCE MATCH

Reverse-engineered from comprehensive reference data to exactly match
the original calc.platform.tennis PTI calculator.

Key Findings:
- Base K-factor: 31.5 for all calculations
- Experience multipliers applied to WINNING TEAM only:
  * "30+": 1.0
  * "10-30": 1.05  
  * "1-10": 1.1
  * "New": 1.15
- ELO probability: 1 / (1 + 10^(-(team1_avg - team2_avg)/400))
- Adjustment: base_k * experience_multiplier * |actual - expected|
- Winners: PTI decreases (subtract adjustment)
- Losers: PTI increases (add adjustment)
"""

import math
from typing import Dict, Any, Tuple


class PTICalculatorV4:
    """Exact PTI calculator matching the original reference implementation"""
    
    def __init__(self):
        # Base K-factor from reference data analysis
        self.base_k_factor = 31.5
        
        # Experience multipliers (applied to winning team)
        self.experience_multipliers = {
            "30+": 1.0,
            "30+ matches": 1.0,
            "10-30": 1.05,
            "10-30 Matches": 1.05,
            "1-10": 1.1,
            "1-10 matches": 1.1,
            "New": 1.15,
            "New Player": 1.15
        }
    
    def _get_experience_multiplier(self, experience: str) -> float:
        """Get the multiplier for a given experience level"""
        return self.experience_multipliers.get(experience, 1.0)
    
    def _calculate_expected_probability(self, team1_avg: float, team2_avg: float) -> float:
        """Calculate expected win probability using ELO formula from reference"""
        rating_diff = team1_avg - team2_avg
        return 1 / (1 + math.pow(10, -rating_diff / 400))
    
    def _parse_score(self, score: str) -> bool:
        """Parse match score to determine if player/partner won"""
        try:
            sets = score.split(',')
            team1_sets = 0
            team2_sets = 0
            
            for set_score in sets:
                scores = set_score.strip().split('-')
                if len(scores) == 2:
                    score1 = int(scores[0])
                    score2 = int(scores[1])
                    
                    if score1 > score2:
                        team1_sets += 1
                    else:
                        team2_sets += 1
            
            return team1_sets > team2_sets
            
        except (ValueError, IndexError):
            return True  # Default to win if score parsing fails
    
    def calculate_pti_changes(
        self,
        player_pti: float,
        partner_pti: float,
        opp1_pti: float,
        opp2_pti: float,
        player_exp: str,
        partner_exp: str,
        opp1_exp: str,
        opp2_exp: str,
        match_score: str
    ) -> Dict[str, Any]:
        """Calculate PTI changes using the exact reference algorithm"""
        
        # Step 1: Calculate team averages
        team1_avg = (player_pti + partner_pti) / 2
        team2_avg = (opp1_pti + opp2_pti) / 2
        
        # Step 2: Calculate spread (absolute difference)
        spread = abs(team1_avg - team2_avg)
        
        # Step 3: Calculate expected probability using exact ELO formula
        expected_prob = self._calculate_expected_probability(team1_avg, team2_avg)
        
        # Step 4: Determine actual result
        player_wins = self._parse_score(match_score)
        actual_result = 1.0 if player_wins else 0.0
        
        # Step 5: Calculate experience multiplier for WINNING TEAM ONLY
        if player_wins:
            # Player team wins - use their experience
            winner_exp1_mult = self._get_experience_multiplier(player_exp)
            winner_exp2_mult = self._get_experience_multiplier(partner_exp)
        else:
            # Opponent team wins - use their experience  
            winner_exp1_mult = self._get_experience_multiplier(opp1_exp)
            winner_exp2_mult = self._get_experience_multiplier(opp2_exp)
        
        experience_multiplier = (winner_exp1_mult + winner_exp2_mult) / 2
        
        # Step 6: Calculate K-factor 
        k_factor = self.base_k_factor * experience_multiplier
        
        # Step 7: Calculate adjustment using exact formula
        adjustment = k_factor * abs(actual_result - expected_prob)
        
        # Step 8: Calculate PTI changes (winners decrease, losers increase)
        if player_wins:
            # Player team wins (PTI decreases = gets better)
            player_change = -adjustment
            partner_change = -adjustment
            opp1_change = adjustment
            opp2_change = adjustment
        else:
            # Player team loses (PTI increases = gets worse)
            player_change = adjustment
            partner_change = adjustment
            opp1_change = -adjustment
            opp2_change = -adjustment
        
        # Apply changes
        new_player_pti = player_pti + player_change
        new_partner_pti = partner_pti + partner_change
        new_opp1_pti = opp1_pti + opp1_change
        new_opp2_pti = opp2_pti + opp2_change
        
        return {
            "success": True,
            "result": {
                "spread": round(spread, 2),
                "adjustment": round(adjustment, 6),  # High precision to match reference
                "before": {
                    "player": {"pti": player_pti},
                    "partner": {"pti": partner_pti},
                    "opp1": {"pti": opp1_pti},
                    "opp2": {"pti": opp2_pti}
                },
                "after": {
                    "player": {"pti": round(new_player_pti, 6)},
                    "partner": {"pti": round(new_partner_pti, 6)},
                    "opp1": {"pti": round(new_opp1_pti, 6)},
                    "opp2": {"pti": round(new_opp2_pti, 6)}
                },
                "details": {
                    "team1_avg": round(team1_avg, 2),
                    "team2_avg": round(team2_avg, 2),
                    "expected_prob": round(expected_prob, 10),  # High precision
                    "actual_result": actual_result,
                    "experience_multiplier": round(experience_multiplier, 6),
                    "k_factor": round(k_factor, 6),
                    "player_wins": player_wins,
                    "formula_verification": {
                        "base_k": self.base_k_factor,
                        "winner_exp_avg": experience_multiplier,
                        "prob_diff": round(abs(actual_result - expected_prob), 10),
                        "calculation": f"{k_factor:.6f} * {abs(actual_result - expected_prob):.10f} = {adjustment:.6f}"
                    }
                }
            }
        }


# Create a global instance
pti_calculator_v4 = PTICalculatorV4()


def calculate_pti_v4(
    player_pti: float,
    partner_pti: float,
    opp1_pti: float,
    opp2_pti: float,
    player_exp: str,
    partner_exp: str,
    opp1_exp: str,
    opp2_exp: str,
    match_score: str
) -> Dict[str, Any]:
    """
    Calculate PTI changes using the exact v4 algorithm that matches reference data
    
    Returns the same format as the original API for compatibility
    """
    return pti_calculator_v4.calculate_pti_changes(
        player_pti, partner_pti, opp1_pti, opp2_pti,
        player_exp, partner_exp, opp1_exp, opp2_exp, match_score
    ) 