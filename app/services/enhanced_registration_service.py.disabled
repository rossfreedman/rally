"""
Enhanced Registration Service
============================

This service provides comprehensive registration functionality that:
1. Creates ALL possible user-player associations (not just one)
2. Handles multi-league and multi-team scenarios
3. Sets up appropriate context for first-time users
4. Ensures team assignments for all associations
5. Provides bulletproof error handling and fallbacks

Key Features:
- Multi-league registration support
- Automatic discovery of all user's player records
- Comprehensive association creation
- Team assignment validation
- Context setup for immediate use
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from app.models.database_models import (
    User, Player, UserPlayerAssociation, UserContext, Team, League, Club, Series
)
from app.services.auth_service_refactored import (
    find_player_matches, assign_player_to_team, get_or_create_league,
    get_or_create_club, get_or_create_series, hash_password
)
from app.services.context_service import ContextService
from core.database import get_db_session
from database_utils import execute_query
from utils.logging import log_activity

logger = logging.getLogger(__name__)

class EnhancedRegistrationService:
    """Service for comprehensive user registration with multi-league/team support"""
    
    @staticmethod
    def register_user_comprehensive(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        league_name: str = None,
        club_name: str = None,
        series_name: str = None,
        ad_deuce_preference: str = None,
        dominant_hand: str = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive user registration that finds and creates ALL possible associations
        """
        db_session = get_db_session()
        
        try:
            # 1. Check if user already exists
            existing_user = db_session.query(User).filter(User.email.ilike(email)).first()
            if existing_user:
                return {"success": False, "error": "Email already registered"}
            
            # 2. Create user record
            hashed_password = hash_password(password)
            new_user = User(
                email=email,
                password_hash=hashed_password,
                first_name=first_name,
                last_name=last_name,
                ad_deuce_preference=ad_deuce_preference,
                dominant_hand=dominant_hand,
                is_admin=False
            )
            
            db_session.add(new_user)
            db_session.flush()  # Get user ID
            
            logger.info(f"Created user record for {email} (ID: {new_user.id})")
            
            # 3. Find ALL possible player matches across all leagues
            all_player_matches = EnhancedRegistrationService._find_all_player_matches(
                first_name, last_name, db_session
            )
            
            logger.info(f"Found {len(all_player_matches)} potential player matches for {first_name} {last_name}")
            
            # 4. Create associations for all high-confidence matches
            associations_created = []
            teams_assigned = []
            
            for player in all_player_matches:
                try:
                    # Check if association already exists (shouldn't happen but be safe)
                    existing = db_session.query(UserPlayerAssociation).filter(
                        UserPlayerAssociation.user_id == new_user.id,
                        UserPlayerAssociation.tenniscores_player_id == player.tenniscores_player_id
                    ).first()
                    
                    if not existing:
                        # Create association
                        association = UserPlayerAssociation(
                            user_id=new_user.id,
                            tenniscores_player_id=player.tenniscores_player_id
                        )
                        db_session.add(association)
                        
                        # Ensure player has team assignment
                        if assign_player_to_team(player, db_session):
                            teams_assigned.append(player.id)
                        
                        associations_created.append({
                            "player_id": player.id,
                            "tenniscores_player_id": player.tenniscores_player_id,
                            "league": player.league.league_name if player.league else "Unknown",
                            "club": player.club.name if player.club else "Unknown",
                            "series": player.series.name if player.series else "Unknown",
                            "team_assigned": player.id in teams_assigned
                        })
                        
                        logger.info(f"Created association for player {player.full_name} "
                                  f"in {player.league.league_name if player.league else 'Unknown League'}")
                    
                except Exception as e:
                    logger.error(f"Error creating association for player {player.id}: {e}")
                    continue
            
            # 5. If no matches found and league/club/series provided, create minimal context
            if not associations_created and league_name and club_name and series_name:
                logger.info(f"No player matches found, but league/club/series provided. "
                           f"Setting up basic context for {email}")
                
                try:
                    # Create/get league, club, series for basic context
                    league = get_or_create_league(league_name, db_session)
                    club = get_or_create_club(club_name, db_session)
                    series = get_or_create_series(series_name, db_session)
                    
                    # Create basic context (no team since no player found)
                    context = UserContext(
                        user_id=new_user.id,
                        active_league_id=league.id
                    )
                    db_session.add(context)
                    
                except Exception as e:
                    logger.error(f"Error creating basic context: {e}")
            
            # 6. Set up user context automatically
            context_result = ContextService.auto_detect_context(new_user.id)
            
            # 7. Commit all changes
            db_session.commit()
            
            # 8. Log comprehensive activity
            try:
                log_activity(
                    action_type="comprehensive_registration",
                    action_description=f"User {first_name} {last_name} registered with comprehensive association discovery",
                    user_id=new_user.id,
                    extra_data={
                        "associations_created_count": len(associations_created),
                        "teams_assigned_count": len(teams_assigned),
                        "provided_league": league_name,
                        "provided_club": club_name,
                        "provided_series": series_name,
                        "context_auto_detected": context_result.get("success", False),
                        "associations_details": associations_created
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log comprehensive activity: {e}")
            
            # 9. Prepare response
            user_data = {
                "id": new_user.id,
                "email": new_user.email,
                "first_name": new_user.first_name,
                "last_name": new_user.last_name,
                "is_admin": new_user.is_admin,
                "ad_deuce_preference": new_user.ad_deuce_preference,
                "dominant_hand": new_user.dominant_hand,
                "associations_created": associations_created,
                "teams_assigned": teams_assigned
            }
            
            return {
                "success": True,
                "user": user_data,
                "associations_count": len(associations_created),
                "teams_assigned_count": len(teams_assigned),
                "context_set": context_result.get("success", False),
                "message": f"Registration successful! Created {len(associations_created)} player associations."
            }
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Comprehensive registration error for {email}: {e}")
            return {"success": False, "error": f"Registration failed: {str(e)}"}
        
        finally:
            db_session.close()
    
    @staticmethod
    def _find_all_player_matches(first_name: str, last_name: str, db_session) -> List[Player]:
        """
        Find ALL possible player matches across all leagues using various matching strategies
        """
        all_matches = []
        
        # Strategy 1: Exact name match across all leagues
        exact_matches = db_session.query(Player).filter(
            Player.first_name.ilike(first_name),
            Player.last_name.ilike(last_name),
            Player.is_active == True
        ).all()
        
        all_matches.extend(exact_matches)
        logger.info(f"Found {len(exact_matches)} exact name matches")
        
        # Strategy 2: Handle common name variations
        name_variations = EnhancedRegistrationService._get_name_variations(first_name, last_name)
        
        for var_first, var_last in name_variations:
            variation_matches = db_session.query(Player).filter(
                Player.first_name.ilike(var_first),
                Player.last_name.ilike(var_last),
                Player.is_active == True
            ).all()
            
            # Only add if not already in matches
            for match in variation_matches:
                if not any(m.id == match.id for m in all_matches):
                    all_matches.append(match)
        
        logger.info(f"Found {len(all_matches)} total matches after name variations")
        
        # Strategy 3: Filter for high-confidence matches
        # Remove duplicates and apply confidence scoring
        high_confidence_matches = EnhancedRegistrationService._filter_high_confidence_matches(
            all_matches, first_name, last_name
        )
        
        logger.info(f"Filtered to {len(high_confidence_matches)} high-confidence matches")
        
        return high_confidence_matches
    
    @staticmethod
    def _get_name_variations(first_name: str, last_name: str) -> List[Tuple[str, str]]:
        """
        Get common name variations for better matching
        """
        variations = []
        
        # Common nickname mappings
        nickname_map = {
            "william": ["bill", "billy", "will"],
            "robert": ["rob", "bob", "bobby"],
            "michael": ["mike", "mick"],
            "christopher": ["chris"],
            "matthew": ["matt"],
            "anthony": ["tony"],
            "elizabeth": ["liz", "beth", "betty"],
            "katherine": ["kate", "kathy", "katie"],
            "margaret": ["meg", "maggie", "peggy"],
            "patricia": ["pat", "patty", "tricia"],
            "peter": ["pete"],  # Added from memories
            "pete": ["peter"],  # Bidirectional mapping
        }
        
        first_lower = first_name.lower()
        last_lower = last_name.lower()
        
        # Check if first name has common variations
        for full_name, nicknames in nickname_map.items():
            if first_lower == full_name:
                for nickname in nicknames:
                    variations.append((nickname, last_name))
            elif first_lower in nicknames:
                variations.append((full_name, last_name))
                # Also add other nicknames for the same full name
                for other_nickname in nicknames:
                    if other_nickname != first_lower:
                        variations.append((other_nickname, last_name))
        
        return variations
    
    @staticmethod
    def _filter_high_confidence_matches(
        matches: List[Player], first_name: str, last_name: str
    ) -> List[Player]:
        """
        Filter matches to only include high-confidence ones
        """
        high_confidence = []
        
        for player in matches:
            confidence_score = 0
            
            # Exact name match (highest confidence)
            if (player.first_name.lower() == first_name.lower() and 
                player.last_name.lower() == last_name.lower()):
                confidence_score += 100
            
            # Known nickname variations
            elif EnhancedRegistrationService._is_known_variation(
                player.first_name, first_name, player.last_name, last_name
            ):
                confidence_score += 80
            
            # Has team assignment (indicates active player)
            if player.team_id:
                confidence_score += 20
            
            # Recent activity (has matches)
            if hasattr(player, 'matches_count') and player.matches_count > 0:
                confidence_score += 10
            
            # Accept if confidence score is high enough
            if confidence_score >= 80:  # Threshold for auto-association
                high_confidence.append(player)
                logger.debug(f"High confidence match: {player.full_name} "
                           f"(score: {confidence_score})")
            else:
                logger.debug(f"Low confidence match rejected: {player.full_name} "
                           f"(score: {confidence_score})")
        
        return high_confidence
    
    @staticmethod
    def _is_known_variation(player_first: str, provided_first: str, 
                          player_last: str, provided_last: str) -> bool:
        """
        Check if names are known variations of each other
        """
        # This could be expanded with more sophisticated matching logic
        return (player_last.lower() == provided_last.lower() and
                EnhancedRegistrationService._are_first_names_variations(
                    player_first, provided_first
                ))
    
    @staticmethod
    def _are_first_names_variations(name1: str, name2: str) -> bool:
        """
        Check if two first names are likely variations of each other
        """
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        # Exact match
        if name1_lower == name2_lower:
            return True
        
        # Check against known nickname patterns
        nickname_groups = [
            ["william", "bill", "billy", "will"],
            ["robert", "rob", "bob", "bobby"],
            ["michael", "mike", "mick"],
            ["christopher", "chris"],
            ["matthew", "matt"],
            ["anthony", "tony"],
            ["elizabeth", "liz", "beth", "betty"],
            ["katherine", "kate", "kathy", "katie"],
            ["margaret", "meg", "maggie", "peggy"],
            ["patricia", "pat", "patty", "tricia"],
            ["peter", "pete"],  # From memories
        ]
        
        for group in nickname_groups:
            if name1_lower in group and name2_lower in group:
                return True
        
        return False
    
    @staticmethod
    def get_registration_summary(user_id: int) -> Dict[str, Any]:
        """
        Get a summary of user's registration and associations
        """
        try:
            # Get user info
            user_leagues = ContextService.get_user_leagues(user_id)
            user_teams = ContextService.get_user_teams(user_id)
            context_info = ContextService.get_context_info(user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "leagues_count": len(user_leagues),
                "teams_count": len(user_teams),
                "leagues": user_leagues,
                "teams": user_teams,
                "current_context": context_info,
                "is_multi_league": len(user_leagues) > 1,
                "is_multi_team": len(user_teams) > 1,
                "needs_context_selection": len(user_teams) > 1
            }
            
        except Exception as e:
            logger.error(f"Error getting registration summary for user {user_id}: {e}")
            return {"success": False, "error": str(e)} 