#!/usr/bin/env python3

"""
Association Discovery Service

This service finds and creates missing user-player associations.
It's designed to fix cases like Victor's where users have player records
in multiple leagues but only some are linked to their user account.
"""

import logging
from typing import Dict, List, Optional, Any
from database_utils import execute_query, execute_query_one, execute_update
import traceback

logger = logging.getLogger(__name__)

class AssociationDiscoveryService:
    """Service for discovering and creating missing user-player associations"""
    
    @staticmethod
    def discover_missing_associations(user_id: int, email: str = None) -> Dict[str, Any]:
        """
        Discover and create missing player associations for a user
        
        Args:
            user_id: User's database ID
            email: User's email (optional, for better matching)
            
        Returns:
            Dict with discovery results
        """
        try:
            logger.info(f"🔍 DISCOVERY START: User {user_id} ({email})")
            
            # 1. Get user info
            user_info = execute_query_one("""
                SELECT id, email, first_name, last_name 
                FROM users 
                WHERE id = %s
            """, [user_id])
            
            if not user_info:
                logger.error(f"❌ DISCOVERY ERROR: User {user_id} not found in database")
                return {"success": False, "error": f"User {user_id} not found"}
            
            user_email = email or user_info['email']
            first_name = user_info['first_name']
            last_name = user_info['last_name']
            
            logger.info(f"🔍 DISCOVERY DETAILS: {first_name} {last_name} ({user_email})")
            
            # 2. Get existing associations
            existing_associations = execute_query("""
                SELECT tenniscores_player_id 
                FROM user_player_associations 
                WHERE user_id = %s
            """, [user_id])
            
            existing_player_ids = [assoc['tenniscores_player_id'] for assoc in existing_associations]
            logger.info(f"🔗 EXISTING ASSOCIATIONS: {len(existing_player_ids)} found")
            for i, player_id in enumerate(existing_player_ids):
                logger.info(f"   [{i+1}] {player_id}")
            
            # 3. Find potential unlinked players
            logger.info(f"🔍 SEARCHING FOR POTENTIAL PLAYERS...")
            potential_players = AssociationDiscoveryService._find_potential_players(
                first_name, last_name, user_email
            )
            
            logger.info(f"🔍 POTENTIAL PLAYERS FOUND: {len(potential_players)}")
            for i, player in enumerate(potential_players):
                logger.info(f"   [{i+1}] {player['tenniscores_player_id']} - {player['league_name']} ({player['confidence']}% confidence)")
            
            # 4. Filter out already linked players
            unlinked_players = [
                player for player in potential_players 
                if player['tenniscores_player_id'] not in existing_player_ids
            ]
            
            logger.info(f"🎯 UNLINKED PLAYERS: {len(unlinked_players)} need to be linked")
            for i, player in enumerate(unlinked_players):
                logger.info(f"   [{i+1}] {player['tenniscores_player_id']} - {player['league_name']} ({player['club_name']}, {player['series_name']})")
            
            # 5. Create associations for high-confidence matches
            associations_created = []
            errors = []
            
            for player in unlinked_players:
                try:
                    player_id = player['tenniscores_player_id']
                    logger.info(f"🔗 ATTEMPTING TO CREATE ASSOCIATION: {player_id}")
                    
                    # Double-check association doesn't exist
                    existing_check = execute_query_one("""
                        SELECT user_id FROM user_player_associations 
                        WHERE user_id = %s AND tenniscores_player_id = %s
                    """, [user_id, player_id])
                    
                    if existing_check:
                        logger.warning(f"⚠️  ASSOCIATION ALREADY EXISTS: {player_id} - skipping")
                        continue  # Already exists
                    
                    # Create the association
                    logger.info(f"🔗 CREATING ASSOCIATION: user_id={user_id}, tenniscores_player_id={player_id}")
                    execute_update("""
                        INSERT INTO user_player_associations (user_id, tenniscores_player_id) 
                        VALUES (%s, %s)
                    """, [user_id, player_id])
                    
                    associations_created.append({
                        "tenniscores_player_id": player_id,
                        "league_name": player['league_name'],
                        "club_name": player['club_name'],
                        "series_name": player['series_name'],
                        "confidence": player['confidence']
                    })
                    
                    logger.info(f"✅ ASSOCIATION CREATED: {player_id} ({player['league_name']})")
                    
                except Exception as e:
                    error_msg = f"Error creating association for {player['tenniscores_player_id']}: {e}"
                    logger.error(f"❌ ASSOCIATION ERROR: {error_msg}")
                    logger.error(f"❌ ASSOCIATION ERROR TRACEBACK: {traceback.format_exc()}")
                    errors.append(error_msg)
            
            # 6. Update user's league_context if they got their first association
            if associations_created and not existing_associations:
                try:
                    logger.info(f"🔧 UPDATING LEAGUE CONTEXT for first-time association")
                    # Set league_context to the first new association's league
                    first_association = associations_created[0]
                    league_lookup = execute_query_one("""
                        SELECT l.id FROM leagues l WHERE l.league_name = %s
                    """, [first_association['league_name']])
                    
                    if league_lookup:
                        execute_update("""
                            UPDATE users SET league_context = %s WHERE id = %s
                        """, [league_lookup['id'], user_id])
                        logger.info(f"✅ LEAGUE CONTEXT UPDATED: {first_association['league_name']}")
                    else:
                        logger.warning(f"⚠️  LEAGUE NOT FOUND: {first_association['league_name']}")
                except Exception as e:
                    logger.warning(f"⚠️  LEAGUE CONTEXT UPDATE ERROR: {e}")
            
            result = {
                "success": True,
                "user_id": user_id,
                "existing_associations": len(existing_associations),
                "associations_created": len(associations_created),
                "new_associations": associations_created,
                "errors": errors,
                "summary": f"Created {len(associations_created)} new associations for {first_name} {last_name}"
            }
            
            logger.info(f"🏁 DISCOVERY COMPLETE: {result['summary']}")
            if associations_created:
                logger.info(f"🎉 NEW ASSOCIATIONS CREATED: {len(associations_created)}")
                for assoc in associations_created:
                    logger.info(f"   • {assoc['tenniscores_player_id']} - {assoc['league_name']} ({assoc['club_name']}, {assoc['series_name']})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ DISCOVERY FAILED: Error discovering associations for user {user_id}: {e}")
            logger.error(f"❌ DISCOVERY FAILED TRACEBACK: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _find_potential_players(first_name: str, last_name: str, email: str) -> List[Dict[str, Any]]:
        """
        Find potential player records that could belong to this user
        """
        logger.info(f"🔍 FINDING POTENTIAL PLAYERS for {first_name} {last_name} ({email})")
        potential_players = []
        
        # Strategy 1: Exact name match
        logger.info(f"🔍 STRATEGY 1: Exact name match")
        exact_matches = execute_query("""
            SELECT p.tenniscores_player_id, p.first_name, p.last_name, p.email, p.is_active,
                   l.league_name, c.name as club_name, s.name as series_name
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE LOWER(TRIM(p.first_name)) = LOWER(TRIM(%s))
            AND LOWER(TRIM(p.last_name)) = LOWER(TRIM(%s))
            AND p.is_active = true
        """, [first_name, last_name])
        
        logger.info(f"🔍 EXACT NAME MATCHES: {len(exact_matches)} found")
        for match in exact_matches:
            confidence = 90  # High confidence for exact name match
            
            # Boost confidence if email matches
            if match['email'] and match['email'].lower() == email.lower():
                confidence = 100
                logger.info(f"   🎯 EXACT NAME + EMAIL MATCH: {match['tenniscores_player_id']} - {match['league_name']} (100% confidence)")
            else:
                logger.info(f"   🎯 EXACT NAME MATCH: {match['tenniscores_player_id']} - {match['league_name']} (90% confidence)")
            
            potential_players.append({
                "tenniscores_player_id": match['tenniscores_player_id'],
                "first_name": match['first_name'],
                "last_name": match['last_name'],
                "email": match['email'],
                "league_name": match['league_name'],
                "club_name": match['club_name'],
                "series_name": match['series_name'],
                "confidence": confidence,
                "match_type": "exact_name"
            })
        
        # Strategy 2: Email match (even with different names - handles name changes)
        logger.info(f"🔍 STRATEGY 2: Email match")
        if email:
            email_matches = execute_query("""
                SELECT p.tenniscores_player_id, p.first_name, p.last_name, p.email, p.is_active,
                       l.league_name, c.name as club_name, s.name as series_name
                FROM players p
                JOIN leagues l ON p.league_id = l.id
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                WHERE LOWER(TRIM(p.email)) = LOWER(TRIM(%s))
                AND p.is_active = true
            """, [email])
            
            logger.info(f"🔍 EMAIL MATCHES: {len(email_matches)} found")
            for match in email_matches:
                # Don't duplicate if already found by name
                if any(p['tenniscores_player_id'] == match['tenniscores_player_id'] for p in potential_players):
                    logger.info(f"   ⚠️  EMAIL MATCH DUPLICATE: {match['tenniscores_player_id']} - already found by name")
                    continue
                
                logger.info(f"   📧 EMAIL MATCH: {match['tenniscores_player_id']} - {match['league_name']} (95% confidence)")
                potential_players.append({
                    "tenniscores_player_id": match['tenniscores_player_id'],
                    "first_name": match['first_name'],
                    "last_name": match['last_name'],
                    "email": match['email'],
                    "league_name": match['league_name'],
                    "club_name": match['club_name'],
                    "series_name": match['series_name'],
                    "confidence": 95,  # High confidence for email match
                    "match_type": "email"
                })
        else:
            logger.info(f"   📧 NO EMAIL PROVIDED - skipping email matching")
        
        # Strategy 3: Known name variations (like Pete/Peter)
        logger.info(f"🔍 STRATEGY 3: Name variations")
        name_variations = AssociationDiscoveryService._get_name_variations(first_name)
        logger.info(f"   🔤 NAME VARIATIONS for '{first_name}': {name_variations}")
        
        for variant_name in name_variations:
            logger.info(f"   🔍 CHECKING VARIANT: {variant_name} {last_name}")
            variant_matches = execute_query("""
                SELECT p.tenniscores_player_id, p.first_name, p.last_name, p.email, p.is_active,
                       l.league_name, c.name as club_name, s.name as series_name
                FROM players p
                JOIN leagues l ON p.league_id = l.id
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                WHERE LOWER(TRIM(p.first_name)) = LOWER(TRIM(%s))
                AND LOWER(TRIM(p.last_name)) = LOWER(TRIM(%s))
                AND p.is_active = true
            """, [variant_name, last_name])
            
            logger.info(f"   🔍 VARIANT MATCHES for '{variant_name}': {len(variant_matches)} found")
            for match in variant_matches:
                # Don't duplicate if already found
                if any(p['tenniscores_player_id'] == match['tenniscores_player_id'] for p in potential_players):
                    logger.info(f"     ⚠️  VARIANT DUPLICATE: {match['tenniscores_player_id']} - already found")
                    continue
                
                confidence = 85  # Good confidence for known variations
                if match['email'] and match['email'].lower() == email.lower():
                    confidence = 95
                    logger.info(f"     🎯 VARIANT + EMAIL MATCH: {match['tenniscores_player_id']} - {match['league_name']} (95% confidence)")
                else:
                    logger.info(f"     🎯 VARIANT MATCH: {match['tenniscores_player_id']} - {match['league_name']} (85% confidence)")
                
                potential_players.append({
                    "tenniscores_player_id": match['tenniscores_player_id'],
                    "first_name": match['first_name'],
                    "last_name": match['last_name'],
                    "email": match['email'],
                    "league_name": match['league_name'],
                    "club_name": match['club_name'],
                    "series_name": match['series_name'],
                    "confidence": confidence,
                    "match_type": "name_variation"
                })
        
        # Filter to only high-confidence matches (80% or higher)
        high_confidence = [p for p in potential_players if p['confidence'] >= 80]
        
        logger.info(f"🔍 POTENTIAL PLAYERS SUMMARY: {len(potential_players)} total, {len(high_confidence)} high-confidence (≥80%)")
        
        return high_confidence
    
    @staticmethod
    def _get_name_variations(first_name: str) -> List[str]:
        """
        Get known variations of a first name
        """
        name_variations_map = {
            "william": ["bill", "billy", "will"],
            "bill": ["william", "billy", "will"],
            "billy": ["william", "bill", "will"],
            "will": ["william", "bill", "billy"],
            
            "robert": ["rob", "bob", "bobby", "ross"],
            "rob": ["robert", "bob", "bobby"],
            "bob": ["robert", "rob", "bobby"],
            "bobby": ["robert", "rob", "bob"],
            
            "ross": ["robert", "rob"],
            
            "michael": ["mike", "mick"],
            "mike": ["michael", "mick"],
            "mick": ["michael", "mike"],
            
            "peter": ["pete"],
            "pete": ["peter"],  # From Victor's case
            
            "christopher": ["chris"],
            "chris": ["christopher"],
            
            "matthew": ["matt"],
            "matt": ["matthew"],
            
            "anthony": ["tony"],
            "tony": ["anthony"],
            
            "elizabeth": ["liz", "beth", "betty"],
            "liz": ["elizabeth", "beth", "betty"],
            "beth": ["elizabeth", "liz", "betty"],
            "betty": ["elizabeth", "liz", "beth"],
            
            "katherine": ["kate", "kathy", "katie"],
            "kate": ["katherine", "kathy", "katie"],
            "kathy": ["katherine", "kate", "katie"],
            "katie": ["katherine", "kate", "kathy"],
            
            # Add Eric and Jim variations to test
            "eric": ["erik"],
            "erik": ["eric"],
            "james": ["jim", "jimmy"],
            "jim": ["james", "jimmy"],
            "jimmy": ["james", "jim"],
            "gregory": ["greg", "gregg"],
            "greg": ["gregory", "gregg"],
            "gregg": ["gregory", "greg"],
        }
        
        first_lower = first_name.lower()
        variations = name_variations_map.get(first_lower, [])
        
        return variations
    
    @staticmethod
    def discover_for_all_users(limit: int = 100) -> Dict[str, Any]:
        """
        Run discovery for all users (maintenance function)
        
        Args:
            limit: Maximum number of users to process (to avoid timeouts)
            
        Returns:
            Summary of discovery results
        """
        logger.info(f"🔍 Running association discovery for up to {limit} users")
        
        # Get users who might benefit from discovery
        users_query = """
            SELECT u.id, u.email, u.first_name, u.last_name,
                   COUNT(upa.tenniscores_player_id) as association_count
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            WHERE u.first_name IS NOT NULL AND u.last_name IS NOT NULL
            GROUP BY u.id, u.email, u.first_name, u.last_name
            HAVING COUNT(upa.tenniscores_player_id) < 2  -- Users with 0 or 1 associations
            ORDER BY association_count ASC, u.created_at DESC
            LIMIT %s
        """
        
        users_to_check = execute_query(users_query, [limit])
        
        results = {
            "users_processed": 0,
            "users_with_new_associations": 0,
            "total_associations_created": 0,
            "errors": [],
            "details": []
        }
        
        for user in users_to_check:
            try:
                discovery_result = AssociationDiscoveryService.discover_missing_associations(
                    user['id'], user['email']
                )
                
                results["users_processed"] += 1
                
                if discovery_result.get("success") and discovery_result.get("associations_created", 0) > 0:
                    results["users_with_new_associations"] += 1
                    results["total_associations_created"] += discovery_result["associations_created"]
                    
                    results["details"].append({
                        "user_id": user['id'],
                        "email": user['email'],
                        "name": f"{user['first_name']} {user['last_name']}",
                        "new_associations": discovery_result["associations_created"],
                        "associations_details": discovery_result.get("new_associations", [])
                    })
                
                if not discovery_result.get("success"):
                    results["errors"].append(f"User {user['id']}: {discovery_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                error_msg = f"Error processing user {user['id']}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        logger.info(f"🏁 Discovery complete: {results['users_with_new_associations']}/{results['users_processed']} users gained associations")
        
        return results 