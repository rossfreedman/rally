"""
Rally Test Data Generator
Generates test data by sampling from existing scraped league JSON files
Much faster and more reliable than scraping external websites
"""

import json
import os
import random
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


class LocalLeagueDataSampler:
    """Sample test data from local league JSON files"""

    def __init__(self, max_players_per_league=20, max_invalid_players=10):
        self.max_players_per_league = max_players_per_league
        self.max_invalid_players = max_invalid_players
        self.project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # League data file paths
        self.league_data_files = {
            "all": os.path.join(
                self.project_root, "data", "leagues", "all", "players.json"
            ),
            "APTA_CHICAGO": os.path.join(
                self.project_root, "data", "leagues", "APTA_CHICAGO", "players.json"
            ),
            "NSTF": os.path.join(
                self.project_root, "data", "leagues", "NSTF", "players.json"
            ),

            
        }

        self.valid_players = []
        self.invalid_players = []
        self.leagues_sampled = []

    def load_league_data(self, league_key: str) -> List[Dict]:
        """Load player data from a specific league JSON file"""
        file_path = self.league_data_files.get(league_key)

        if not file_path or not os.path.exists(file_path):
            print(f"❌ League data file not found: {file_path}")
            return []

        try:
            print(f"📂 Loading {league_key} data from: {os.path.basename(file_path)}")

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            print(f"   ✅ Loaded {len(data)} total players from {league_key}")
            return data

        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON file {file_path}: {e}")
            return []
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
            return []

    def sample_league_players(
        self, league_key: str, sample_size: int = None
    ) -> List[Dict]:
        """Sample random players from a specific league"""
        if sample_size is None:
            sample_size = self.max_players_per_league

        print(f"\n🎾 Sampling from {league_key}")
        print(f"   Target: {sample_size} players")

        # Load all players from the league
        all_players = self.load_league_data(league_key)

        if not all_players:
            return []

        # Filter for valid players with required fields
        valid_raw_players = []
        for player in all_players:
            if (
                isinstance(player, dict)
                and player.get("First Name")
                and player.get("Last Name")
                and player.get("League")
            ):
                valid_raw_players.append(player)

        print(f"   📊 {len(valid_raw_players)} valid players available")

        # Randomly sample from valid players
        sample_count = min(sample_size, len(valid_raw_players))
        sampled_players = random.sample(valid_raw_players, sample_count)

        # Convert to test data format
        test_players = []
        for player in sampled_players:
            test_player = self.convert_to_test_format(player)
            if test_player:
                test_players.append(test_player)
                print(
                    f"   ✓ {test_player['first_name']} {test_player['last_name']} | {test_player['club']} | {test_player['series']} | PTI: {test_player.get('pti', 'N/A')}"
                )

        print(f"   📈 Successfully converted {len(test_players)} players")
        self.leagues_sampled.append(league_key)

        return test_players

    def convert_to_test_format(self, raw_player: Dict) -> Optional[Dict]:
        """Convert raw league JSON player data to test format"""
        try:
            first_name = raw_player.get("First Name", "").strip()
            last_name = raw_player.get("Last Name", "").strip()

            if not first_name or not last_name:
                return None

            # Extract PTI and convert to float
            pti_raw = raw_player.get("PTI", "N/A")
            pti = None
            if pti_raw and pti_raw != "N/A":
                try:
                    pti = float(str(pti_raw).replace("%", ""))
                except (ValueError, TypeError):
                    pti = None

            # Extract wins/losses
            wins = self._safe_int_convert(raw_player.get("Wins", 0))
            losses = self._safe_int_convert(raw_player.get("Losses", 0))

            # Calculate win percentage
            total_matches = wins + losses
            win_percentage = (
                round((wins / total_matches) * 100, 1) if total_matches > 0 else 0.0
            )

            # Clean up club and series names
            club = raw_player.get("Club", "Unknown Club").strip()
            series = raw_player.get("Series", "Unknown Series").strip()
            series_mapping_id = raw_player.get("Series Mapping ID", series).strip()

            # Create test player record
            test_player = {
                "first_name": first_name,
                "last_name": last_name,
                "full_name": f"{first_name} {last_name}",
                "club": club,
                "series": series,
                "series_mapping_id": series_mapping_id,
                "league": raw_player.get("League", "UNKNOWN"),
                "league_name": self._get_league_display_name(
                    raw_player.get("League", "UNKNOWN")
                ),
                "pti": pti,
                "wins": wins,
                "losses": losses,
                "win_percentage": win_percentage,
                "tenniscores_player_id": raw_player.get("Player ID"),
                "location_id": raw_player.get("Location ID"),
                "captain": raw_player.get("Captain") == "C",
                "sampled_at": datetime.now().isoformat(),
                "valid_for_testing": True,
                "source": "local_json_file",
            }

            return test_player

        except Exception as e:
            print(
                f"   ⚠️ Error converting player {raw_player.get('First Name', 'Unknown')}: {e}"
            )
            return None

    def _safe_int_convert(self, value) -> int:
        """Safely convert a value to integer"""
        try:
            return int(str(value).replace(",", ""))
        except (ValueError, TypeError):
            return 0

    def _get_league_display_name(self, league_id: str) -> str:
        """Get display name for league"""
        league_names = {
            "APTA_CHICAGO": "APTA Chicago",
            "NSTF": "North Shore Tennis Foundation",
    
    
        }
        return league_names.get(league_id, league_id)

    def generate_invalid_players(self) -> List[Dict]:
        """Generate intentionally invalid player data for negative testing"""
        print(
            f"\n🔧 Generating {self.max_invalid_players} invalid players for negative testing"
        )

        invalid_players = []

        # Pattern 1: Non-existent clubs
        for i in range(max(1, self.max_invalid_players // 4)):
            invalid_players.append(
                {
                    "first_name": f"Invalid{i}",
                    "last_name": "Player",
                    "full_name": f"Invalid{i} Player",
                    "club": f"NonExistentClub{i}",
                    "series": "FakeSeries",
                    "series_mapping_id": "Fake Series - 1",
                    "league": "FAKE_LEAGUE",
                    "league_name": "Fake League",
                    "pti": None,
                    "wins": 0,
                    "losses": 0,
                    "win_percentage": 0.0,
                    "tenniscores_player_id": f"FAKE_{i:03d}",
                    "location_id": f"FAKE_LOCATION_{i}",
                    "captain": False,
                    "sampled_at": datetime.now().isoformat(),
                    "valid_for_testing": False,
                    "invalid_reason": "non_existent_club",
                    "source": "generated_invalid",
                }
            )

        # Pattern 2: Empty/malformed data
        for i in range(max(1, self.max_invalid_players // 4)):
            invalid_players.append(
                {
                    "first_name": "",  # Empty name
                    "last_name": "Test",
                    "full_name": " Test",
                    "club": "ValidClub",
                    "series": "",  # Empty series
                    "series_mapping_id": "",
                    "league": "APTA_CHICAGO",
                    "league_name": "APTA Chicago",
                    "pti": -1,  # Invalid PTI
                    "wins": -5,  # Invalid wins
                    "losses": -3,  # Invalid losses
                    "win_percentage": 150.0,  # Invalid percentage
                    "tenniscores_player_id": None,
                    "location_id": "",
                    "captain": False,
                    "sampled_at": datetime.now().isoformat(),
                    "valid_for_testing": False,
                    "invalid_reason": "malformed_data",
                    "source": "generated_invalid",
                }
            )

        # Pattern 3: SQL injection attempts (for security testing)
        sql_payloads = [
            "'; DROP TABLE players; --",
            "Robert'); DROP TABLE users;--",
            "admin'/*",
            "1' OR '1'='1",
            "'; UPDATE players SET pti=9999; --",
        ]

        for i, payload in enumerate(
            sql_payloads[: max(1, self.max_invalid_players // 4)]
        ):
            invalid_players.append(
                {
                    "first_name": payload,
                    "last_name": "SecurityTest",
                    "full_name": f"{payload} SecurityTest",
                    "club": "TestClub",
                    "series": "TestSeries",
                    "series_mapping_id": "Test Series - 1",
                    "league": "APTA_CHICAGO",
                    "league_name": "APTA Chicago",
                    "pti": 1500,
                    "wins": 10,
                    "losses": 5,
                    "win_percentage": 66.7,
                    "tenniscores_player_id": f"SEC_{i:03d}",
                    "location_id": "TEST_LOCATION",
                    "captain": False,
                    "sampled_at": datetime.now().isoformat(),
                    "valid_for_testing": False,
                    "invalid_reason": "security_payload",
                    "source": "generated_invalid",
                }
            )

        # Pattern 4: XSS attempts (for security testing)
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//'",
        ]

        for i, payload in enumerate(
            xss_payloads[: max(1, self.max_invalid_players // 4)]
        ):
            invalid_players.append(
                {
                    "first_name": f"XSSTest{i}",
                    "last_name": payload,
                    "full_name": f"XSSTest{i} {payload}",
                    "club": "TestClub",
                    "series": payload,
                    "series_mapping_id": f"{payload} - 1",
                    "league": "APTA_CHICAGO",
                    "league_name": "APTA Chicago",
                    "pti": 1200,
                    "wins": 8,
                    "losses": 7,
                    "win_percentage": 53.3,
                    "tenniscores_player_id": f"XSS_{i:03d}",
                    "location_id": "TEST_LOCATION",
                    "captain": False,
                    "sampled_at": datetime.now().isoformat(),
                    "valid_for_testing": False,
                    "invalid_reason": "xss_payload",
                    "source": "generated_invalid",
                }
            )

        print(f"   ✓ Generated {len(invalid_players)} invalid test players")
        return invalid_players

    def sample_all_leagues(self, use_combined_file: bool = True) -> Dict:
        """Sample player data from league files"""
        print("🎯 Starting local league data sampling...")
        print(f"   Target: {self.max_players_per_league} players per league")

        all_valid_players = []

        if use_combined_file:
            # Use the combined 'all' file for maximum variety
            print("📂 Using combined league data file (data/leagues/all/players.json)")
            all_valid_players = self.sample_league_players(
                "all", self.max_players_per_league * 3
            )
        else:
            # Sample from individual league files
            individual_leagues = ["APTA_CHICAGO", "NSTF"]
            print(f"📂 Sampling from individual league files: {individual_leagues}")

            for league_key in individual_leagues:
                league_players = self.sample_league_players(league_key)
                all_valid_players.extend(league_players)

        # Generate invalid players for negative testing
        invalid_players = self.generate_invalid_players()

        # Prepare final dataset
        dataset = {
            "metadata": {
                "sampled_at": datetime.now().isoformat(),
                "leagues_sampled": self.leagues_sampled,
                "total_valid_players": len(all_valid_players),
                "total_invalid_players": len(invalid_players),
                "sampler_version": "2.0",
                "purpose": "Rally application testing",
                "data_source": "local_json_files",
                "max_players_per_league": self.max_players_per_league,
                "use_combined_file": use_combined_file,
            },
            "valid_players": all_valid_players,
            "invalid_players": invalid_players,
        }

        print(f"\n📊 Sampling Summary:")
        print(f"   ✅ Valid players: {len(all_valid_players)}")
        print(f"   ❌ Invalid players: {len(invalid_players)}")
        print(f"   🏆 Leagues covered: {len(self.leagues_sampled)}")

        return dataset

    def save_test_data(self, dataset: Dict, output_dir: str = None) -> str:
        """Save sampled test data to JSON file"""
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")

        os.makedirs(output_dir, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sampled_players_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        # Also save as the default name for test fixtures
        default_filepath = os.path.join(output_dir, "sampled_players.json")

        try:
            # Save timestamped version
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)

            # Save default version for tests
            with open(default_filepath, "w", encoding="utf-8") as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)

            print(f"💾 Test data saved to:")
            print(f"   📁 {filepath}")
            print(f"   📁 {default_filepath}")

            return filepath

        except Exception as e:
            print(f"❌ Error saving test data: {e}")
            return None


def main():
    """Main function to run the test data sampler"""
    print("🎾 Rally Test Data Sampler")
    print("=" * 50)
    print("Sampling player data from local league JSON files")
    print()

    # Initialize sampler
    sampler = LocalLeagueDataSampler(
        max_players_per_league=25, max_invalid_players=12  # Good sample size
    )

    try:
        # Sample from all leagues (using combined file for efficiency)
        dataset = sampler.sample_all_leagues(use_combined_file=True)

        if "error" in dataset:
            print(f"❌ Sampling failed: {dataset['error']}")
            return False

        # Save the data
        output_file = sampler.save_test_data(dataset)

        if output_file:
            print(f"\n✅ Test data sampling completed successfully!")
            print(
                f"📄 Use this data in your tests by loading: tests/fixtures/sampled_players.json"
            )
            print(f"🚀 This is much faster than scraping external websites!")
            return True
        else:
            print(f"\n❌ Failed to save test data")
            return False

    except KeyboardInterrupt:
        print(f"\n⚠️ Sampling interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
