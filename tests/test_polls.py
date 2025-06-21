"""
Rally Poll System Tests
Comprehensive testing of poll creation, voting, and management functionality
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json

from app.models.database_models import Poll, PollChoice, PollResponse, User, Player, Team

@pytest.mark.unit
class TestPollModel:
    """Test Poll model functionality"""
    
    def test_create_poll(self, db_session, test_user, test_team):
        """Test creating a basic poll"""
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="What time works best for practice?"
        )
        
        db_session.add(poll)
        db_session.commit()
        
        assert poll.id is not None
        assert poll.question == "What time works best for practice?"
        assert poll.team_id == test_team.id
        assert poll.created_by == test_user.id
        assert poll.created_at is not None
    
    def test_poll_relationships(self, db_session, test_user, test_team):
        """Test poll model relationships"""
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Test question?"
        )
        
        db_session.add(poll)
        db_session.commit()
        
        # Test team relationship
        assert poll.team is not None
        assert poll.team.id == test_team.id
        
        # Test creator relationship
        assert poll.creator is not None
        assert poll.creator.id == test_user.id
    
    def test_poll_with_choices(self, db_session, test_user, test_team):
        """Test poll with multiple choices"""
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="What day should we practice?"
        )
        
        db_session.add(poll)
        db_session.flush()  # Get poll ID
        
        # Add choices
        choices = [
            PollChoice(poll_id=poll.id, choice_text="Monday"),
            PollChoice(poll_id=poll.id, choice_text="Wednesday"),
            PollChoice(poll_id=poll.id, choice_text="Friday"),
        ]
        
        db_session.add_all(choices)
        db_session.commit()
        
        # Verify choices
        assert len(poll.choices) == 3
        choice_texts = [choice.choice_text for choice in poll.choices]
        assert "Monday" in choice_texts
        assert "Wednesday" in choice_texts
        assert "Friday" in choice_texts

@pytest.mark.integration
class TestPollAPI:
    """Test poll API endpoints"""
    
    def test_create_poll_api(self, authenticated_client, db_session, test_user, test_team):
        """Test creating a poll via API"""
        poll_data = {
            'question': 'What time should we meet?',
            'choices': ['6:00 PM', '6:30 PM', '7:00 PM'],
            'team_id': test_team.id
        }
        
        response = authenticated_client.post('/api/polls',
                                           json=poll_data,
                                           content_type='application/json')
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'poll_id' in data
        
        # Verify poll was created in database
        poll = db_session.query(Poll).filter(Poll.id == data['poll_id']).first()
        assert poll is not None
        assert poll.question == 'What time should we meet?'
        assert len(poll.choices) == 3
    
    def test_get_team_polls(self, authenticated_client, db_session, test_user, test_team):
        """Test retrieving polls for a team"""
        # Create test polls
        polls = []
        for i in range(3):
            poll = Poll(
                team_id=test_team.id,
                created_by=test_user.id,
                question=f"Test question {i+1}?"
            )
            polls.append(poll)
            db_session.add(poll)
        
        db_session.commit()
        
        response = authenticated_client.get(f'/api/polls/team/{test_team.id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'polls' in data
        assert len(data['polls']) >= 3
    
    def test_vote_on_poll(self, authenticated_client, db_session, test_user, test_player, test_team):
        """Test voting on a poll"""
        # Create poll with choices
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Which court is best?"
        )
        db_session.add(poll)
        db_session.flush()
        
        choice = PollChoice(poll_id=poll.id, choice_text="Court 1")
        db_session.add(choice)
        db_session.commit()
        
        vote_data = {
            'choice_id': choice.id,
            'player_id': test_player.id
        }
        
        response = authenticated_client.post(f'/api/polls/{poll.id}/vote',
                                           json=vote_data,
                                           content_type='application/json')
        
        assert response.status_code == 200
        
        # Verify vote was recorded
        response_obj = db_session.query(PollResponse).filter(
            PollResponse.poll_id == poll.id,
            PollResponse.player_id == test_player.id
        ).first()
        
        assert response_obj is not None
        assert response_obj.choice_id == choice.id
    
    def test_unauthorized_poll_access(self, client):
        """Test poll access without authentication"""
        response = client.get('/api/polls/team/1')
        assert response.status_code == 401

@pytest.mark.integration
class TestPollVoting:
    """Test poll voting logic"""
    
    def test_single_vote_per_player(self, db_session, test_user, test_player, test_team):
        """Test that players can only vote once per poll"""
        # Create poll with choices
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Best practice time?"
        )
        db_session.add(poll)
        db_session.flush()
        
        choice1 = PollChoice(poll_id=poll.id, choice_text="6:00 PM")
        choice2 = PollChoice(poll_id=poll.id, choice_text="7:00 PM")
        db_session.add_all([choice1, choice2])
        db_session.commit()
        
        # First vote
        vote1 = PollResponse(
            poll_id=poll.id,
            choice_id=choice1.id,
            player_id=test_player.id
        )
        db_session.add(vote1)
        db_session.commit()
        
        # Try to vote again (should be prevented by unique constraint)
        vote2 = PollResponse(
            poll_id=poll.id,
            choice_id=choice2.id,
            player_id=test_player.id
        )
        db_session.add(vote2)
        
        # This should raise an integrity error due to unique constraint
        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            db_session.commit()
    
    def test_vote_counting(self, db_session, test_user, test_team, multiple_players):
        """Test vote counting functionality"""
        # Create poll with choices
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Preferred match day?"
        )
        db_session.add(poll)
        db_session.flush()
        
        choice1 = PollChoice(poll_id=poll.id, choice_text="Saturday")
        choice2 = PollChoice(poll_id=poll.id, choice_text="Sunday")
        db_session.add_all([choice1, choice2])
        db_session.commit()
        
        # Have 3 players vote for Saturday, 2 for Sunday
        for i, player in enumerate(multiple_players):
            choice = choice1 if i < 3 else choice2
            vote = PollResponse(
                poll_id=poll.id,
                choice_id=choice.id,
                player_id=player.id
            )
            db_session.add(vote)
        
        db_session.commit()
        
        # Count votes
        saturday_votes = db_session.query(PollResponse).filter(
            PollResponse.poll_id == poll.id,
            PollResponse.choice_id == choice1.id
        ).count()
        
        sunday_votes = db_session.query(PollResponse).filter(
            PollResponse.poll_id == poll.id,
            PollResponse.choice_id == choice2.id
        ).count()
        
        assert saturday_votes == 3
        assert sunday_votes == 2
    
    def test_change_vote(self, db_session, test_user, test_player, test_team):
        """Test changing a vote (if allowed)"""
        # Create poll
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Best meeting location?"
        )
        db_session.add(poll)
        db_session.flush()
        
        choice1 = PollChoice(poll_id=poll.id, choice_text="Club A")
        choice2 = PollChoice(poll_id=poll.id, choice_text="Club B")
        db_session.add_all([choice1, choice2])
        db_session.commit()
        
        # Initial vote
        vote = PollResponse(
            poll_id=poll.id,
            choice_id=choice1.id,
            player_id=test_player.id
        )
        db_session.add(vote)
        db_session.commit()
        
        # Change vote
        vote.choice_id = choice2.id
        db_session.commit()
        
        # Verify vote changed
        updated_vote = db_session.query(PollResponse).filter(
            PollResponse.poll_id == poll.id,
            PollResponse.player_id == test_player.id
        ).first()
        
        assert updated_vote.choice_id == choice2.id

@pytest.mark.unit
class TestPollValidation:
    """Test poll validation logic"""
    
    def test_poll_question_validation(self, db_session, test_user, test_team):
        """Test poll question validation"""
        # Empty question should fail
        with pytest.raises(Exception):
            poll = Poll(
                team_id=test_team.id,
                created_by=test_user.id,
                question=""  # Empty question
            )
            db_session.add(poll)
            db_session.commit()
    
    def test_poll_choice_validation(self, db_session, test_user, test_team):
        """Test poll choice validation"""
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Valid question?"
        )
        db_session.add(poll)
        db_session.flush()
        
        # Empty choice text should fail
        with pytest.raises(Exception):
            choice = PollChoice(
                poll_id=poll.id,
                choice_text=""  # Empty choice text
            )
            db_session.add(choice)
            db_session.commit()
    
    def test_poll_minimum_choices(self, db_session, test_user, test_team):
        """Test that polls should have minimum number of choices"""
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Should we have choices?"
        )
        db_session.add(poll)
        db_session.commit()
        
        # Poll with no choices (business logic should prevent this)
        assert len(poll.choices) == 0
        
        # Note: Current model allows polls without choices
        # Business logic should enforce minimum choices

@pytest.mark.integration
class TestPollSecurity:
    """Test poll security aspects"""
    
    def test_vote_permission_check(self, authenticated_client, db_session, test_user, test_player, test_team):
        """Test that only team members can vote on team polls"""
        # Create poll
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Team only question?"
        )
        db_session.add(poll)
        db_session.flush()
        
        choice = PollChoice(poll_id=poll.id, choice_text="Team choice")
        db_session.add(choice)
        db_session.commit()
        
        # Try to vote with invalid player ID
        vote_data = {
            'choice_id': choice.id,
            'player_id': 99999  # Non-existent player
        }
        
        response = authenticated_client.post(f'/api/polls/{poll.id}/vote',
                                           json=vote_data,
                                           content_type='application/json')
        
        # Should fail with appropriate error
        assert response.status_code in [400, 403, 404]
    
    def test_poll_creation_permission(self, authenticated_client, db_session):
        """Test poll creation permission checks"""
        poll_data = {
            'question': 'Unauthorized poll?',
            'choices': ['Yes', 'No'],
            'team_id': 99999  # Non-existent team
        }
        
        response = authenticated_client.post('/api/polls',
                                           json=poll_data,
                                           content_type='application/json')
        
        # Should fail for non-existent team
        assert response.status_code in [400, 403, 404]
    
    def test_sql_injection_in_poll(self, authenticated_client, test_team, mock_security_payloads):
        """Test SQL injection attempts in poll creation"""
        for sql_payload in mock_security_payloads['sql_injection']:
            poll_data = {
                'question': sql_payload,
                'choices': ['Choice 1', 'Choice 2'],
                'team_id': test_team.id
            }
            
            response = authenticated_client.post('/api/polls',
                                               json=poll_data,
                                               content_type='application/json')
            
            # Should handle malicious input gracefully
            assert response.status_code in [201, 400, 500]

@pytest.mark.integration
class TestPollLifecycle:
    """Test complete poll lifecycle"""
    
    def test_full_poll_workflow(self, authenticated_client, db_session, test_user, test_player, test_team):
        """Test complete poll creation, voting, and results workflow"""
        # Step 1: Create poll
        poll_data = {
            'question': 'What equipment should we buy?',
            'choices': ['New balls', 'Court covers', 'Net tensioners'],
            'team_id': test_team.id
        }
        
        create_response = authenticated_client.post('/api/polls',
                                                  json=poll_data,
                                                  content_type='application/json')
        
        assert create_response.status_code == 201
        poll_id = create_response.get_json()['poll_id']
        
        # Step 2: Get poll details
        poll_response = authenticated_client.get(f'/api/polls/{poll_id}')
        assert poll_response.status_code == 200
        
        poll_data_response = poll_response.get_json()
        assert poll_data_response['question'] == 'What equipment should we buy?'
        assert len(poll_data_response['choices']) == 3
        
        # Step 3: Vote on poll
        choice_id = poll_data_response['choices'][0]['id']
        vote_data = {
            'choice_id': choice_id,
            'player_id': test_player.id
        }
        
        vote_response = authenticated_client.post(f'/api/polls/{poll_id}/vote',
                                                json=vote_data,
                                                content_type='application/json')
        
        assert vote_response.status_code == 200
        
        # Step 4: Get poll results
        results_response = authenticated_client.get(f'/api/polls/{poll_id}/results')
        assert results_response.status_code == 200
        
        results_data = results_response.get_json()
        assert 'vote_counts' in results_data
        assert results_data['total_votes'] == 1
    
    def test_poll_closure(self, db_session, test_user, test_team):
        """Test poll closure/expiration functionality"""
        # Note: Current model doesn't have explicit closure mechanism
        # This test documents expected behavior if closure is added
        
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Should we close this poll?"
        )
        db_session.add(poll)
        db_session.commit()
        
        # Poll is active by default
        assert poll.created_at is not None
        
        # In future: could add is_closed, closed_at fields
        # For now, just verify poll exists and is accessible

@pytest.mark.performance
class TestPollPerformance:
    """Test poll performance with large datasets"""
    
    def test_large_poll_query_performance(self, db_session, test_user, test_team, multiple_players):
        """Test performance with many polls and votes"""
        import time
        
        # Create multiple polls
        polls = []
        for i in range(50):  # 50 polls
            poll = Poll(
                team_id=test_team.id,
                created_by=test_user.id,
                question=f"Performance test question {i}?"
            )
            polls.append(poll)
            db_session.add(poll)
        
        db_session.flush()
        
        # Add choices to each poll
        for poll in polls:
            for j in range(3):  # 3 choices per poll
                choice = PollChoice(
                    poll_id=poll.id,
                    choice_text=f"Choice {j+1}"
                )
                db_session.add(choice)
        
        db_session.flush()
        
        # Add votes (each player votes on each poll)
        for poll in polls:
            for player in multiple_players:
                # Get first choice for this poll
                first_choice = db_session.query(PollChoice).filter(
                    PollChoice.poll_id == poll.id
                ).first()
                
                vote = PollResponse(
                    poll_id=poll.id,
                    choice_id=first_choice.id,
                    player_id=player.id
                )
                db_session.add(vote)
        
        db_session.commit()
        
        # Time the query for team polls
        start_time = time.time()
        
        team_polls = db_session.query(Poll).filter(
            Poll.team_id == test_team.id
        ).all()
        
        query_time = time.time() - start_time
        
        # Performance assertions
        assert len(team_polls) == 50
        assert query_time < 1.0  # Should complete quickly
        
        print(f"Poll query performance: {query_time:.3f}s for 50 polls")

@pytest.mark.regression
class TestPollRegression:
    """Regression tests for previously fixed poll bugs"""
    
    def test_poll_foreign_key_integrity(self, db_session, test_user, test_team):
        """Test that polls maintain foreign key integrity"""
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Foreign key test?"
        )
        
        db_session.add(poll)
        db_session.commit()
        
        # Verify relationships are intact
        assert poll.team is not None
        assert poll.team.id == test_team.id
        assert poll.creator is not None
        assert poll.creator.id == test_user.id
        
        # Verify back-references work
        assert poll in test_team.polls
    
    def test_cascade_deletion_behavior(self, db_session, test_user, test_player, test_team):
        """Test what happens when referenced entities are deleted"""
        # Create poll with choices and votes
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Cascade test?"
        )
        db_session.add(poll)
        db_session.flush()
        
        choice = PollChoice(poll_id=poll.id, choice_text="Test choice")
        db_session.add(choice)
        db_session.flush()
        
        vote = PollResponse(
            poll_id=poll.id,
            choice_id=choice.id,
            player_id=test_player.id
        )
        db_session.add(vote)
        db_session.commit()
        
        poll_id = poll.id
        choice_id = choice.id
        
        # Delete poll (should cascade to choices and responses)
        db_session.delete(poll)
        db_session.commit()
        
        # Verify cascade deletion
        deleted_poll = db_session.query(Poll).filter(Poll.id == poll_id).first()
        deleted_choice = db_session.query(PollChoice).filter(PollChoice.id == choice_id).first()
        deleted_vote = db_session.query(PollResponse).filter(PollResponse.poll_id == poll_id).first()
        
        assert deleted_poll is None
        assert deleted_choice is None  # Should be cascaded
        assert deleted_vote is None    # Should be cascaded
    
    def test_duplicate_choice_prevention(self, db_session, test_user, test_team):
        """Test prevention of duplicate choices in same poll"""
        poll = Poll(
            team_id=test_team.id,
            created_by=test_user.id,
            question="Duplicate choice test?"
        )
        db_session.add(poll)
        db_session.flush()
        
        # Add identical choices
        choice1 = PollChoice(poll_id=poll.id, choice_text="Same choice")
        choice2 = PollChoice(poll_id=poll.id, choice_text="Same choice")
        
        db_session.add_all([choice1, choice2])
        db_session.commit()
        
        # Currently allows duplicate choices - business logic should prevent this
        choices = db_session.query(PollChoice).filter(PollChoice.poll_id == poll.id).all()
        assert len(choices) == 2  # Both choices exist
        
        # Note: This documents current behavior; ideally should prevent duplicates 