import json
from datetime import datetime

def parse_date(date_str):
    """Convert date string to datetime object"""
    try:
        return datetime.strptime(date_str, "%d-%b-%y")
    except:
        return None

def get_most_recent_matches(matches):
    """Get matches from the most recent date"""
    # Convert dates and find the latest date
    dated_matches = [(parse_date(m['Date']), m) for m in matches if parse_date(m['Date'])]
    if not dated_matches:
        return []
    
    latest_date = max(date for date, _ in dated_matches)
    
    # Get matches from the latest date only
    latest_matches = [
        match for date, match in dated_matches 
        if date == latest_date
    ]
    
    return latest_matches

def calculate_match_score(matches, target_date, target_team):
    """
    Calculate the total score for a team on a specific date across all courts.
    
    Args:
        matches: List of match dictionaries from match_history.json
        target_date: Date to analyze in format "DD-MMM-YY" 
        target_team: Team name to calculate score for
        
    Returns:
        Tuple of (team_points, opponent_points)
    """
    team_points = 0
    opponent_points = 0
    
    # Filter matches for target date and team
    date_matches = [m for m in matches if m['Date'] == target_date and 
                   (m['Home Team'] == target_team or m['Away Team'] == target_team)]
    
    for match in date_matches:
        is_home = match['Home Team'] == target_team
        scores = match['Scores'].split(', ')
        
        # Calculate points for each set
        for set_score in scores:
            our_score, their_score = map(int, set_score.split('-'))
            
            # Flip scores if we're the away team
            if not is_home:
                our_score, their_score = their_score, our_score
                
            if our_score > their_score:
                team_points += 1
            else:
                opponent_points += 1
                
        # Add bonus point for winning the match
        if (is_home and match['Winner'] == 'home') or \
           (not is_home and match['Winner'] == 'away'):
            team_points += 1
        else:
            opponent_points += 1
            
    return team_points, opponent_points

def show_latest_tennaqua_scores():
    """Show Tennaqua match scores from the most recent date only"""
    with open('data/match_history.json', 'r') as f:
        all_matches = json.load(f)
    
    latest_matches = get_most_recent_matches(all_matches)
    if not latest_matches:
        print("No matches found")
        return
    
    latest_date = latest_matches[0]['Date']
    print(f"\nShowing Tennaqua scores for {latest_date}:")
    print("=" * 80)
    
    # Group matches by teams playing
    teams_seen = set()
    
    for match in latest_matches:
        # Only include matches where Tennaqua is playing
        if not ('Tennaqua' in match['Home Team'] or 'Tennaqua' in match['Away Team']):
            continue
            
        home_team = match['Home Team']
        away_team = match['Away Team']
        match_key = tuple(sorted([home_team, away_team]))
        
        if match_key in teams_seen:
            continue
            
        teams_seen.add(match_key)
        
        # Get all matches between these teams on this date
        team_matches = [
            m for m in latest_matches 
            if (m['Home Team'] == home_team and m['Away Team'] == away_team) or
               (m['Home Team'] == away_team and m['Away Team'] == home_team)
        ]
        
        # Calculate total score for the team that's Tennaqua
        tennaqua_team = home_team if 'Tennaqua' in home_team else away_team
        opponent_team = away_team if 'Tennaqua' in home_team else home_team
        
        tennaqua_points, opp_points = calculate_match_score(all_matches, latest_date, tennaqua_team)
        
        print(f"\n{tennaqua_team} vs {opponent_team}")
        print(f"Final Score: {tennaqua_team}: {tennaqua_points}, {opponent_team}: {opp_points}")
        
        # Show individual court results
        for i, match in enumerate(sorted(team_matches, key=lambda m: (m['Home Player 1'], m['Home Player 2']))):
            print(f"  Court {i+1}: {match['Home Player 1']}/{match['Home Player 2']} vs "
                  f"{match['Away Player 1']}/{match['Away Player 2']} - {match['Scores']}")

if __name__ == '__main__':
    show_latest_tennaqua_scores()