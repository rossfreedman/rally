#!/usr/bin/env python3
"""
Team Name Resolver - Enhanced name matching for import process

This utility helps resolve team name variations during data import by providing
fuzzy matching and normalization rules to map scraped team names to canonical
team names in the database.
"""

import re
from typing import Optional, List, Dict, Tuple
from database_utils import execute_query_one, execute_query


class TeamNameResolver:
    """
    Resolves team name variations to canonical team IDs in the database.
    """
    
    def __init__(self, league_id: int):
        self.league_id = league_id
        self._team_cache = None
        self._name_variations = {
            # Common name variations for different clubs
            'midt': ['midt-bannockburn', 'midt bannockburn', 'midt - bannockburn'],
            'bannockburn': ['midt-bannockburn', 'midt bannockburn', 'midt - bannockburn'],
            'winnetka': ['winnetka gc', 'winnetka country club'],
            'willow': ['old willow', 'old willow cc'],
            'forest': ['lake forest', 'lake forest cc'],
            'ridge': ['sunset ridge', 'sunset ridge cc'],
            'bluff': ['lake bluff', 'lake bluff cc'],
        }
    
    def _load_teams_cache(self) -> Dict[str, Dict]:
        """Load all teams for the league into cache for fast lookup."""
        if self._team_cache is not None:
            return self._team_cache
            
        teams_query = """
            SELECT 
                id,
                team_name,
                club_id,
                series_id,
                LOWER(team_name) as normalized_name
            FROM teams 
            WHERE league_id = %s
            AND is_active = true
        """
        
        teams = execute_query(teams_query, [self.league_id])
        self._team_cache = {}
        
        for team in teams:
            # Index by normalized name for fast lookup
            normalized = team['normalized_name']
            self._team_cache[normalized] = team
            
            # Also index by variations
            for variation in self._generate_name_variations(team['team_name']):
                self._team_cache[variation.lower()] = team
                
        return self._team_cache
    
    def _generate_name_variations(self, team_name: str) -> List[str]:
        """Generate possible variations of a team name."""
        variations = [team_name]
        base_name = team_name.lower()
        
        # Remove/add hyphens and spaces
        variations.extend([
            base_name.replace('-', ' '),
            base_name.replace(' ', '-'),
            base_name.replace(' - ', '-'),
            base_name.replace('-', ' - '),
        ])
        
        # Handle series number variations
        series_match = re.search(r'(\d+)$', base_name)
        if series_match:
            series_num = series_match.group(1)
            base_without_series = base_name.replace(f' - {series_num}', '').replace(f'-{series_num}', '').replace(f' {series_num}', '')
            
            # Add variations with different series formatting
            variations.extend([
                f"{base_without_series} - {series_num}",
                f"{base_without_series}-{series_num}",
                f"{base_without_series} {series_num}",
            ])
        
        # Apply club-specific variations
        for short_name, long_names in self._name_variations.items():
            if short_name in base_name:
                for long_name in long_names:
                    variations.append(base_name.replace(short_name, long_name))
                    
        return list(set(variations))
    
    def resolve_team_name(self, scraped_name: str) -> Optional[Tuple[int, str, Dict]]:
        """
        Resolve a scraped team name to a canonical team ID.
        
        Args:
            scraped_name: The team name as scraped from source
            
        Returns:
            Tuple of (team_id, canonical_name, team_info) or None if not found
        """
        teams_cache = self._load_teams_cache()
        
        # 1. Exact match (case insensitive)
        exact_match = teams_cache.get(scraped_name.lower())
        if exact_match:
            return (exact_match['id'], exact_match['team_name'], exact_match)
        
        # 2. Try variations of the scraped name
        for variation in self._generate_name_variations(scraped_name):
            match = teams_cache.get(variation.lower())
            if match:
                return (match['id'], match['team_name'], match)
        
        # 3. Fuzzy matching - find best partial match
        best_match = self._fuzzy_match(scraped_name, teams_cache)
        if best_match:
            return best_match
            
        return None
    
    def _fuzzy_match(self, scraped_name: str, teams_cache: Dict) -> Optional[Tuple[int, str, Dict]]:
        """
        Perform fuzzy matching to find the best candidate team.
        
        This looks for teams that contain key components of the scraped name.
        """
        scraped_lower = scraped_name.lower()
        scraped_parts = set(re.findall(r'\w+', scraped_lower))
        
        best_score = 0
        best_match = None
        
        for team_name, team_info in teams_cache.items():
            team_parts = set(re.findall(r'\w+', team_name))
            
            # Calculate similarity score
            common_parts = scraped_parts.intersection(team_parts)
            if len(common_parts) == 0:
                continue
                
            # Score based on proportion of matching parts
            score = len(common_parts) / max(len(scraped_parts), len(team_parts))
            
            # Boost score for exact club name matches
            for short_name, long_names in self._name_variations.items():
                if short_name in scraped_lower:
                    for long_name in long_names:
                        if long_name.replace(' ', '').replace('-', '') in team_name.replace(' ', '').replace('-', ''):
                            score += 0.5
                            break
            
            if score > best_score and score >= 0.6:  # Minimum threshold
                best_score = score
                best_match = (team_info['id'], team_info['team_name'], team_info)
        
        return best_match
    
    def validate_and_suggest_fixes(self, scraped_matches: List[Dict]) -> Dict:
        """
        Analyze scraped matches and suggest fixes for unresolved team names.
        
        Args:
            scraped_matches: List of match dictionaries with team names
            
        Returns:
            Dictionary with analysis and suggested fixes
        """
        unresolved_teams = set()
        resolved_count = 0
        suggestions = []
        
        for match in scraped_matches:
            home_team = match.get('home_team')
            away_team = match.get('away_team')
            
            for team_name in [home_team, away_team]:
                if team_name:
                    resolution = self.resolve_team_name(team_name)
                    if resolution:
                        resolved_count += 1
                    else:
                        unresolved_teams.add(team_name)
                        
                        # Try to suggest a fix
                        suggestion = self._suggest_team_fix(team_name)
                        if suggestion:
                            suggestions.append({
                                'scraped_name': team_name,
                                'suggested_id': suggestion[0],
                                'suggested_name': suggestion[1],
                                'confidence': 'medium'
                            })
        
        return {
            'total_teams_processed': resolved_count + len(unresolved_teams),
            'resolved_teams': resolved_count,
            'unresolved_teams': list(unresolved_teams),
            'resolution_rate': resolved_count / (resolved_count + len(unresolved_teams)) if (resolved_count + len(unresolved_teams)) > 0 else 0,
            'suggestions': suggestions
        }
    
    def _suggest_team_fix(self, team_name: str) -> Optional[Tuple[int, str]]:
        """Suggest a possible fix for an unresolved team name."""
        # This is where we'd implement more sophisticated matching
        # For now, return the fuzzy match result
        teams_cache = self._load_teams_cache()
        result = self._fuzzy_match(team_name, teams_cache)
        return (result[0], result[1]) if result else None


def fix_orphaned_team_references(league_id: int = 4783, dry_run: bool = True) -> Dict:  # Fixed: was 4930, should be 4783 (APTA Chicago)
    """
    Find and fix orphaned team references in match_scores table.
    
    Args:
        league_id: League to process
        dry_run: If True, only analyze without making changes
        
    Returns:
        Dictionary with results of the operation
    """
    resolver = TeamNameResolver(league_id)
    
    # Find matches with NULL team references
    orphaned_query = """
        SELECT 
            id,
            home_team,
            away_team,
            home_team_id,
            away_team_id,
            match_date
        FROM match_scores 
        WHERE league_id = %s
        AND (home_team_id IS NULL OR away_team_id IS NULL)
        ORDER BY match_date DESC
    """
    
    orphaned_matches = execute_query(orphaned_query, [league_id])
    
    fixes_applied = []
    fixes_suggested = []
    
    for match in orphaned_matches:
        match_id = match['id']
        
        # Try to resolve home team
        if match['home_team_id'] is None and match['home_team']:
            resolution = resolver.resolve_team_name(match['home_team'])
            if resolution:
                team_id, canonical_name, team_info = resolution
                
                fix_info = {
                    'match_id': match_id,
                    'field': 'home_team_id',
                    'scraped_name': match['home_team'],
                    'resolved_id': team_id,
                    'canonical_name': canonical_name,
                    'club_id': team_info['club_id'],
                    'series_id': team_info['series_id']
                }
                
                if not dry_run:
                    # Apply the fix
                    update_query = "UPDATE match_scores SET home_team_id = %s WHERE id = %s"
                    execute_query_one(update_query, [team_id, match_id])
                    fixes_applied.append(fix_info)
                else:
                    fixes_suggested.append(fix_info)
        
        # Try to resolve away team
        if match['away_team_id'] is None and match['away_team']:
            resolution = resolver.resolve_team_name(match['away_team'])
            if resolution:
                team_id, canonical_name, team_info = resolution
                
                fix_info = {
                    'match_id': match_id,
                    'field': 'away_team_id',
                    'scraped_name': match['away_team'],
                    'resolved_id': team_id,
                    'canonical_name': canonical_name,
                    'club_id': team_info['club_id'],
                    'series_id': team_info['series_id']
                }
                
                if not dry_run:
                    # Apply the fix
                    update_query = "UPDATE match_scores SET away_team_id = %s WHERE id = %s"
                    execute_query_one(update_query, [team_id, match_id])
                    fixes_applied.append(fix_info)
                else:
                    fixes_suggested.append(fix_info)
    
    return {
        'total_orphaned_matches': len(orphaned_matches),
        'fixes_applied': fixes_applied,
        'fixes_suggested': fixes_suggested,
        'dry_run': dry_run
    }


if __name__ == "__main__":
    # Test the resolver
    resolver = TeamNameResolver(4783)  # APTA Chicago (Fixed: was 4930, should be 4783)
    
    # Test cases
    test_names = [
        "Midt - 18",
        "Birchwood - 18", 
        "Tennaqua - 13",
        "Winnetka - 15",
        "Old Willow - 12"
    ]
    
    print("=== TESTING TEAM NAME RESOLVER ===")
    for name in test_names:
        result = resolver.resolve_team_name(name)
        if result:
            team_id, canonical_name, info = result
            print(f"✅ '{name}' → ID {team_id}: '{canonical_name}' (club: {info['club_id']})")
        else:
            print(f"❌ '{name}' → No match found")
    
    # Test orphaned fixes
    print("\n=== TESTING ORPHANED FIXES (DRY RUN) ===")
    fixes_result = fix_orphaned_team_references(4783, dry_run=True)  # Fixed: was 4930, should be 4783
    print(f"Found {fixes_result['total_orphaned_matches']} orphaned matches")
    print(f"Can fix {len(fixes_result['fixes_suggested'])} matches")
    
    for fix in fixes_result['fixes_suggested'][:5]:  # Show first 5
        print(f"  Match {fix['match_id']}: '{fix['scraped_name']}' → '{fix['canonical_name']}' (ID: {fix['resolved_id']})")
