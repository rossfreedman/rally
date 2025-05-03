import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def scrape_tennis_stats():
    """
    Scrapes tennis statistics data from webpage and saves to JSON file
    """
    # URL of the tennis stats page
    url = "https://aptachicago.tenniscores.com/?mod=nndz-TjJiOWtOR3QzTU4yakRrY1U4UEtOUGNkcGc9PQ%3D%3D&did=nndz-WnkrNXhiWT0%3D"  # Replace with actual URL
    
    try:
        # Get the webpage content
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize list to store team stats
        stats = []
        
        # Find the standings table
        table = soup.find('table', class_='standings-table2')
        if not table:
            raise Exception("Could not find standings table")
            
        # Process each team row
        for row in table.find_all('tr')[2:]:  # Skip header rows
            cols = row.find_all('td')
            if len(cols) >= 17:  # Ensure row has all columns
                team_stats = {
                    "team": cols[0].text.strip(),
                    "points": int(cols[1].text.strip()),
                    "matches": {
                        "won": int(cols[2].text.strip()),
                        "lost": int(cols[3].text.strip()),
                        "tied": int(cols[4].text.strip()),
                        "percentage": cols[5].text.strip()
                    },
                    "lines": {
                        "won": int(cols[6].text.strip()),
                        "lost": int(cols[7].text.strip()),
                        "for": int(cols[8].text.strip()),
                        "ret": int(cols[9].text.strip()),
                        "percentage": cols[10].text.strip()
                    },
                    "sets": {
                        "won": int(cols[11].text.strip()),
                        "lost": int(cols[12].text.strip()),
                        "percentage": cols[13].text.strip()
                    },
                    "games": {
                        "won": int(cols[14].text.strip()),
                        "lost": int(cols[15].text.strip()),
                        "percentage": cols[16].text.strip()
                    }
                }
                stats.append(team_stats)
        
        # Sort by points (descending)
        stats.sort(key=lambda x: x['points'], reverse=True)
        
        # Save to JSON file with today's date
        today = datetime.now().strftime("%Y%m%d")
        output_file = f"data/tennis_stats_{today}.json"
        with open(output_file, 'w') as f:
            json.dump(stats, f, indent=4)
            
        print(f"Successfully scraped stats for {len(stats)} teams")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching webpage: {e}")
    except Exception as e:
        print(f"Error processing data: {e}")

if __name__ == "__main__":
    scrape_tennis_stats()
