import json

def analyze_birchwood_matches():
    with open('data/match_history.json', 'r') as f:
        matches = json.load(f)
    
    total_matches = 0
    straight_set_wins = 0
    three_set_wins = 0
    three_set_losses = 0
    comeback_wins = 0
    
    for match in matches:
        if match['Home Team'] == 'Birchwood - 6' or match['Away Team'] == 'Birchwood - 6':
            total_matches += 1
            is_home = match['Home Team'] == 'Birchwood - 6'
            won_match = (is_home and match['Winner'] == 'home') or (not is_home and match['Winner'] == 'away')
            
            scores = match['Scores'].split(', ')
            if len(scores) == 2:  # Straight sets
                if won_match:
                    straight_set_wins += 1
            elif len(scores) == 3:  # Three sets
                if won_match:
                    three_set_wins += 1
                    # Check for comeback win
                    first_set = scores[0].split('-')
                    if is_home:
                        if int(first_set[0]) < int(first_set[1]):
                            comeback_wins += 1
                    else:
                        if int(first_set[1]) < int(first_set[0]):
                            comeback_wins += 1
                else:
                    three_set_losses += 1
    
    print(f"Total Matches: {total_matches}")
    print(f"Straight Set Wins: {straight_set_wins}")
    print(f"Three-Set Record: {three_set_wins}-{three_set_losses}")
    print(f"Comeback Wins: {comeback_wins}")

if __name__ == "__main__":
    analyze_birchwood_matches() 