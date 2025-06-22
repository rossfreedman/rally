"""
Rally Load Testing - User Registration and App Usage
Locust-based load testing to simulate real-world usage patterns
"""

import json
import random
import time
from datetime import datetime, timedelta

from faker import Faker
from locust import HttpUser, between, events, task

fake = Faker()


class RallyUser(HttpUser):
    """Simulates a Rally user performing typical application actions"""

    wait_time = between(1, 5)  # Wait 1-5 seconds between requests

    def on_start(self):
        """Actions performed when a user starts"""
        self.user_data = None
        self.auth_token = None
        self.player_data = None

        # Load test data from scraper if available
        self.load_test_data()

        # Try to register or login
        if random.choice([True, False]):
            self.register_user()
        else:
            self.login_existing_user()

    def load_test_data(self):
        """Load sampled test data for realistic scenarios"""
        try:
            with open("../fixtures/sampled_players.json", "r") as f:
                self.scraped_data = json.load(f)
        except FileNotFoundError:
            # Fallback to mock data
            self.scraped_data = {
                "valid_players": [
                    {
                        "first_name": "John",
                        "last_name": "Smith",
                        "club": "Tennaqua",
                        "series": "Chicago 22",
                        "league": "APTA_CHICAGO",
                    },
                    {
                        "first_name": "Jane",
                        "last_name": "Doe",
                        "club": "Birchwood",
                        "series": "Chicago 15",
                        "league": "APTA_CHICAGO",
                    },
                ]
            }

    def register_user(self):
        """Register a new user"""
        # Use real player data for more realistic testing
        if self.scraped_data["valid_players"]:
            player = random.choice(self.scraped_data["valid_players"])
            first_name = player["first_name"]
            last_name = player["last_name"]
            club = player["club"]
            series = player["series"]
            league = player["league"]
        else:
            first_name = fake.first_name()
            last_name = fake.last_name()
            club = random.choice(["Tennaqua", "Birchwood", "Exmoor"])
            series = random.choice(["Chicago 15", "Chicago 22", "Chicago 25"])
            league = "APTA_CHICAGO"

        # Generate unique email for load testing
        timestamp = int(time.time() * 1000)
        user_id = random.randint(1000, 9999)
        email = f"loadtest_{timestamp}_{user_id}@example.com"

        self.user_data = {
            "email": email,
            "password": "LoadTest123!",
            "firstName": first_name,
            "lastName": last_name,
            "league": league,
            "club": club,
            "series": series,
        }

        with self.client.post(
            "/api/register", json=self.user_data, catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
                self.extract_session_info(response)
            elif response.status_code == 409:  # User already exists
                response.success()  # This is expected in load testing
                self.login_existing_user()
            else:
                response.failure(f"Registration failed: {response.status_code}")

    def login_existing_user(self):
        """Login with existing test credentials"""
        # Use a pool of existing test users
        test_users = [
            {"email": "test1@example.com", "password": "LoadTest123!"},
            {"email": "test2@example.com", "password": "LoadTest123!"},
            {"email": "test3@example.com", "password": "LoadTest123!"},
        ]

        login_data = random.choice(test_users)

        with self.client.post(
            "/api/login", json=login_data, catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                self.extract_session_info(response)
            else:
                response.failure(f"Login failed: {response.status_code}")
                # Fallback to registration
                self.register_user()

    def extract_session_info(self, response):
        """Extract session information from login/registration response"""
        try:
            data = response.json()
            if "user" in data:
                self.user_data = data["user"]
        except:
            pass

    @task(3)
    def view_schedule(self):
        """View user's team schedule"""
        with self.client.get("/api/schedule", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                try:
                    data = response.json()
                    if "matches" in data:
                        self.schedule_data = data["matches"]
                except:
                    pass
            elif response.status_code == 401:
                response.failure("Unauthorized - session expired")
                self.login_existing_user()
            else:
                response.failure(f"Schedule loading failed: {response.status_code}")

    @task(2)
    def view_mobile_dashboard(self):
        """Access the main mobile dashboard"""
        with self.client.get("/mobile", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                # Check for key content
                if b"schedule" in response.content.lower():
                    # Dashboard loaded successfully
                    pass
            elif response.status_code == 302:
                # Redirect to login - session expired
                response.failure("Session expired - redirected to login")
                self.login_existing_user()
            else:
                response.failure(f"Dashboard access failed: {response.status_code}")

    @task(2)
    def check_availability(self):
        """View and update player availability"""
        with self.client.get("/availability", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [302, 401]:
                response.failure("Auth required for availability")
                self.login_existing_user()
            else:
                response.failure(f"Availability check failed: {response.status_code}")

    @task(1)
    def create_poll(self):
        """Create a team poll"""
        poll_questions = [
            "What time should we practice?",
            "Which court do you prefer?",
            "Should we order new equipment?",
            "What day works best for team meeting?",
            "Preferred practice frequency?",
        ]

        poll_choices = {
            "What time should we practice?": ["6:00 PM", "6:30 PM", "7:00 PM"],
            "Which court do you prefer?": ["Court 1", "Court 2", "Court 3"],
            "Should we order new equipment?": ["Yes", "No", "Maybe later"],
            "What day works best for team meeting?": ["Monday", "Wednesday", "Friday"],
            "Preferred practice frequency?": [
                "Once a week",
                "Twice a week",
                "As needed",
            ],
        }

        question = random.choice(poll_questions)
        choices = poll_choices.get(question, ["Option A", "Option B", "Option C"])

        poll_data = {
            "question": question,
            "choices": choices,
            "team_id": random.randint(1, 5),  # Assume teams 1-5 exist
        }

        with self.client.post(
            "/api/polls", json=poll_data, catch_response=True
        ) as response:
            if response.status_code == 201:
                response.success()
                try:
                    data = response.json()
                    poll_id = data.get("poll_id")
                    if poll_id:
                        # Sometimes vote on the poll we just created
                        if random.choice([True, False]):
                            self.vote_on_poll(poll_id, choices)
                except:
                    pass
            elif response.status_code in [401, 403]:
                response.failure("Auth required for poll creation")
            else:
                response.failure(f"Poll creation failed: {response.status_code}")

    def vote_on_poll(self, poll_id, choices):
        """Vote on a specific poll"""
        # First get poll details to get choice IDs
        with self.client.get(f"/api/polls/{poll_id}", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    poll_data = response.json()
                    poll_choices = poll_data.get("choices", [])
                    if poll_choices:
                        choice = random.choice(poll_choices)
                        vote_data = {
                            "choice_id": choice["id"],
                            "player_id": random.randint(
                                1, 20
                            ),  # Assume players 1-20 exist
                        }

                        with self.client.post(
                            f"/api/polls/{poll_id}/vote",
                            json=vote_data,
                            catch_response=True,
                        ) as vote_response:
                            if vote_response.status_code == 200:
                                vote_response.success()
                            else:
                                vote_response.failure(
                                    f"Voting failed: {vote_response.status_code}"
                                )
                except:
                    pass

    @task(1)
    def view_team_polls(self):
        """View polls for user's team"""
        team_id = random.randint(1, 5)  # Assume teams 1-5 exist

        with self.client.get(
            f"/api/polls/team/{team_id}", catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                try:
                    data = response.json()
                    polls = data.get("polls", [])

                    # Sometimes vote on existing polls
                    if polls and random.choice([True, False]):
                        poll = random.choice(polls)
                        poll_id = poll["id"]
                        choices = poll.get("choices", [])
                        if choices:
                            self.vote_on_poll(poll_id, choices)
                except:
                    pass
            else:
                response.failure(f"Team polls loading failed: {response.status_code}")

    @task(1)
    def search_players(self):
        """Search for players (admin feature testing)"""
        search_terms = [
            {"first_name": "John", "last_name": ""},
            {"first_name": "", "last_name": "Smith"},
            {"first_name": "Jane", "last_name": "Doe"},
        ]

        search_data = random.choice(search_terms)

        with self.client.post(
            "/api/players/search", json=search_data, catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()  # Both success and not found are acceptable
            elif response.status_code in [401, 403]:
                response.failure("Auth required for player search")
            else:
                response.failure(f"Player search failed: {response.status_code}")

    @task(1)
    def health_check(self):
        """Check application health"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        # Application is healthy
                        pass
                except:
                    pass
            else:
                response.failure(f"Health check failed: {response.status_code}")


class AdminUser(HttpUser):
    """Simulates admin user actions with higher privileges"""

    wait_time = between(2, 8)  # Admins take more time between actions
    weight = 1  # Lower weight - fewer admin users

    def on_start(self):
        """Login as admin user"""
        admin_credentials = {"email": "admin@example.com", "password": "AdminTest123!"}

        with self.client.post("/api/login", json=admin_credentials) as response:
            if response.status_code == 200:
                self.admin_authenticated = True
            else:
                self.admin_authenticated = False

    @task(2)
    def view_admin_dashboard(self):
        """Access admin dashboard"""
        if not self.admin_authenticated:
            return

        with self.client.get("/admin", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [401, 403]:
                response.failure("Admin access denied")
            else:
                response.failure(f"Admin dashboard failed: {response.status_code}")

    @task(1)
    def manage_users(self):
        """View and manage users"""
        if not self.admin_authenticated:
            return

        with self.client.get("/api/admin/users", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [401, 403]:
                response.failure("Admin user management access denied")
            else:
                response.failure(f"User management failed: {response.status_code}")

    @task(1)
    def view_system_stats(self):
        """View system statistics"""
        if not self.admin_authenticated:
            return

        with self.client.get("/api/admin/stats", catch_response=True) as response:
            if response.status_code in [200, 404]:  # 404 if endpoint doesn't exist yet
                response.success()
            elif response.status_code in [401, 403]:
                response.failure("Admin stats access denied")
            else:
                response.failure(f"System stats failed: {response.status_code}")


# Load testing events and statistics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Actions to perform when load test starts"""
    print("🚀 Rally Load Test Starting")
    print(f"Target host: {environment.host}")
    print(f"User classes: {[cls.__name__ for cls in environment.user_classes]}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Actions to perform when load test stops"""
    print("\n📊 Rally Load Test Complete")
    print("Check Locust web UI for detailed results")


# Custom load test scenarios
class RegistrationBurstUser(HttpUser):
    """Simulates burst registration periods (e.g., season start)"""

    wait_time = between(0.5, 2)  # Faster registration attempts
    weight = 3  # Higher weight during burst periods

    def on_start(self):
        self.burst_registrations()

    def burst_registrations(self):
        """Perform multiple registrations quickly"""
        for i in range(random.randint(1, 3)):
            timestamp = int(time.time() * 1000)
            user_id = random.randint(1000, 9999)

            registration_data = {
                "email": f"burst_{timestamp}_{user_id}_{i}@example.com",
                "password": "BurstTest123!",
                "firstName": fake.first_name(),
                "lastName": fake.last_name(),
                "league": "APTA_CHICAGO",
                "club": random.choice(["Tennaqua", "Birchwood", "Exmoor"]),
                "series": random.choice(["Chicago 15", "Chicago 22"]),
            }

            with self.client.post(
                "/api/register", json=registration_data, catch_response=True
            ) as response:
                if response.status_code in [201, 409]:  # Success or duplicate
                    response.success()
                else:
                    response.failure(
                        f"Burst registration failed: {response.status_code}"
                    )

            time.sleep(random.uniform(0.1, 0.5))  # Small delay between registrations


class MobileHeavyUser(HttpUser):
    """Simulates heavy mobile usage patterns"""

    wait_time = between(0.5, 3)  # Fast mobile interactions
    weight = 5  # Higher weight - mobile is primary interface

    def on_start(self):
        """Quick mobile login"""
        login_data = {
            "email": f"mobile_{random.randint(1000, 9999)}@example.com",
            "password": "MobileTest123!",
        }

        # Try login, fallback to registration
        response = self.client.post("/api/login", json=login_data)
        if response.status_code != 200:
            registration_data = {
                **login_data,
                "firstName": fake.first_name(),
                "lastName": fake.last_name(),
                "league": "APTA_CHICAGO",
                "club": "Tennaqua",
                "series": "Chicago 22",
            }
            self.client.post("/api/register", json=registration_data)

    @task(5)
    def rapid_mobile_navigation(self):
        """Simulate rapid mobile navigation"""
        mobile_pages = [
            "/mobile",
            "/schedule",
            "/availability",
            "/mobile/analyze",
            "/mobile/improve",
        ]

        page = random.choice(mobile_pages)
        with self.client.get(page, catch_response=True) as response:
            if response.status_code in [200, 302]:
                response.success()
            else:
                response.failure(f"Mobile navigation failed: {response.status_code}")

    @task(2)
    def quick_poll_interactions(self):
        """Quick poll creation and voting"""
        # Create quick poll
        poll_data = {
            "question": "Quick mobile poll?",
            "choices": ["Yes", "No"],
            "team_id": random.randint(1, 3),
        }

        response = self.client.post("/api/polls", json=poll_data)
        if response.status_code == 201:
            # Quick vote
            try:
                poll_id = response.json()["poll_id"]
                vote_data = {
                    "choice_id": 1,  # Quick choice
                    "player_id": random.randint(1, 10),
                }
                self.client.post(f"/api/polls/{poll_id}/vote", json=vote_data)
            except:
                pass


if __name__ == "__main__":
    """
    Run load test locally with:
    python -m locust -f load_test_registration.py --host=http://localhost:8080

    Or use Locust web UI:
    locust -f load_test_registration.py --host=http://localhost:8080
    """
    import subprocess
    import sys

    print("Rally Load Test")
    print("Usage: locust -f load_test_registration.py --host=http://localhost:8080")

    # Auto-start if no arguments provided
    if len(sys.argv) == 1:
        cmd = [
            "locust",
            "-f",
            __file__,
            "--host",
            "http://localhost:8080",
            "--web-host",
            "0.0.0.0",
            "--users",
            "10",
            "--spawn-rate",
            "2",
            "--run-time",
            "2m",
        ]
        subprocess.run(cmd)
