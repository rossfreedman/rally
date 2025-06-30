"""
PTI Calculator Service v5.0 - REALISTIC ADJUSTMENTS

Fixed the v4 algorithm by using a realistic K-factor that produces 
normal PTI adjustments (0.5-3.0 points) instead of the unrealistic
14+ point adjustments from v4.

Key Changes from v4:
- Base K-factor: 2.0 (instead of 31.5) - realistic for rating systems  
- Same formula structure as v4 but with proper scaling
- Produces normal PTI adjustments in expected range
"""

import math
from typing import Dict, Any, Tuple


class PTICalculatorV5:
    """Corrected PTI calculator with realistic adjustments"""
    
    def __init__(self):
        # Realistic base K-factor (much smaller than v4's 31.5)
        self.base_k_factor = 2.0
        
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
        """Calculate expected win probability using ELO formula"""
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
        """Calculate PTI changes using corrected realistic algorithm"""
        
        # Step 1: Calculate team averages
        team1_avg = (player_pti + partner_pti) / 2
        team2_avg = (opp1_pti + opp2_pti) / 2
        
        # Step 2: Calculate spread (absolute difference)
        spread = abs(team1_avg - team2_avg)
        
        # Step 3: Calculate expected probability using ELO formula
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
        
        # Step 6: Calculate K-factor with realistic base
        k_factor = self.base_k_factor * experience_multiplier
        
        # Step 7: Calculate adjustment using same formula but realistic K
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
                "adjustment": round(adjustment, 6),  # Should now be realistic (0.5-3.0)
                "before": {
                    "player": {"pti": player_pti, "mu": "", "sigma": ""},
                    "partner": {"pti": partner_pti, "mu": "", "sigma": ""},
                    "opp1": {"pti": opp1_pti, "mu": "", "sigma": ""},
                    "opp2": {"pti": opp2_pti, "mu": "", "sigma": ""}
                },
                "after": {
                    "player": {"pti": round(new_player_pti, 6), "mu": "", "sigma": ""},
                    "partner": {"pti": round(new_partner_pti, 6), "mu": "", "sigma": ""},
                    "opp1": {"pti": round(new_opp1_pti, 6), "mu": "", "sigma": ""},
                    "opp2": {"pti": round(new_opp2_pti, 6), "mu": "", "sigma": ""}
                },
                "details": {
                    "team1_avg": round(team1_avg, 2),
                    "team2_avg": round(team2_avg, 2),
                    "expected_prob": round(expected_prob, 10),
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
pti_calculator_v5 = PTICalculatorV5()


def calculate_pti_v5(
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
    Calculate PTI changes using the corrected v5 algorithm with realistic adjustments
    
    Returns the same format as the original API for compatibility
    """
    return pti_calculator_v5.calculate_pti_changes(
        player_pti, partner_pti, opp1_pti, opp2_pti,
        player_exp, partner_exp, opp1_exp, opp2_exp, match_score
    ) 