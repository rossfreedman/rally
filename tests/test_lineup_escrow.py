"""
Tests for Lineup Escrow functionality
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.services.lineup_escrow_service import LineupEscrowService


class TestLineupEscrowService:
    """Test cases for LineupEscrowService"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session for testing"""
        return MagicMock()
    
    @pytest.fixture
    def escrow_service(self, mock_db_session):
        """Create an escrow service instance with mock database"""
        return LineupEscrowService(mock_db_session)
    
    @pytest.fixture
    def sample_lineup(self):
        """Sample lineup data for testing"""
        return json.dumps({
            "court1": {"player1": "John Doe", "player2": "Jane Smith"},
            "court2": {"player1": "Bob Johnson", "player2": "Alice Brown"},
            "court3": {"player1": "Charlie Wilson", "player2": "Diana Davis"},
            "court4": {"player1": "Eve Miller", "player2": "Frank Garcia"}
        })
    
    @patch('app.services.lineup_escrow_service.log_user_activity')
    @patch('app.services.lineup_escrow_service.send_sms_notification')
    def test_create_escrow_session(self, mock_sms, mock_log, escrow_service, sample_lineup):
        """Test creating a new escrow session"""
        # Mock the database operations
        mock_escrow = MagicMock()
        mock_escrow.id = 123
        mock_escrow.escrow_token = "test-token-123"
        
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        
        escrow_service.db_session.add = MagicMock()
        escrow_service.db_session.commit = MagicMock()
        escrow_service.db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        result = escrow_service.create_escrow_session(
            initiator_user_id=1,
            recipient_name="Opponent Team",
            recipient_contact="opponent@example.com",
            contact_type="email",
            initiator_lineup=sample_lineup,
            subject="Lineup Escrow",
            message_body="Please submit your lineup"
        )
        
        assert result['success'] is True
        assert 'escrow_id' in result
        assert 'escrow_token' in result
        
        # Verify database operations were called
        escrow_service.db_session.add.assert_called_once()
        escrow_service.db_session.commit.assert_called_once()
    
    def test_submit_recipient_lineup(self, escrow_service, sample_lineup):
        """Test submitting recipient lineup"""
        # Mock the database operations
        mock_escrow = MagicMock()
        mock_escrow.escrow_token = "test-token"
        mock_escrow.recipient_contact = "opponent@example.com"
        mock_escrow.status = "pending"
        mock_escrow.expires_at = datetime.utcnow() + timedelta(hours=1)
        
        escrow_service.db_session.query.return_value.filter.return_value.first.return_value = mock_escrow
        escrow_service.db_session.commit = MagicMock()
        
        # Submit recipient lineup
        result = escrow_service.submit_recipient_lineup(
            escrow_token="test-token",
            recipient_contact="opponent@example.com",
            recipient_lineup=sample_lineup
        )
        
        assert result['success'] is True
        assert result['both_submitted'] is True
        
        # Verify database operations were called
        escrow_service.db_session.commit.assert_called_once()
    
    def test_get_escrow_details(self, escrow_service, sample_lineup):
        """Test getting escrow details"""
        # Mock the database operations
        mock_escrow = MagicMock()
        mock_escrow.escrow_token = "test-token"
        mock_escrow.recipient_contact = "opponent@example.com"
        mock_escrow.status = "pending"
        mock_escrow.initiator_lineup = sample_lineup
        mock_escrow.recipient_lineup = None
        mock_escrow.expires_at = datetime.utcnow() + timedelta(hours=1)
        
        escrow_service.db_session.query.return_value.filter.return_value.first.return_value = mock_escrow
        
        # Get details
        result = escrow_service.get_escrow_details("test-token", "opponent@example.com")
        
        assert result['success'] is True
        assert result['escrow']['escrow_token'] == "test-token"
        assert result['escrow']['status'] == "pending"
    
    def test_save_lineup(self, escrow_service, sample_lineup):
        """Test saving a lineup"""
        # Mock the database operations
        mock_lineup = MagicMock()
        mock_lineup.id = 456
        
        escrow_service.db_session.add = MagicMock()
        escrow_service.db_session.commit = MagicMock()
        escrow_service.db_session.execute.return_value.fetchone.return_value = {'id': 456}
        
        result = escrow_service.save_lineup(
            user_id=1,
            team_id=1,
            lineup_name="Test Lineup",
            lineup_data=sample_lineup
        )
        
        assert result['success'] is True
        assert result['lineup_id'] == 456
        
        # Verify database operations were called
        escrow_service.db_session.add.assert_called_once()
        escrow_service.db_session.commit.assert_called_once()
    
    def test_get_saved_lineups(self, escrow_service):
        """Test getting saved lineups"""
        # Mock the database operations
        mock_lineups = [
            MagicMock(id=1, lineup_name="Test Lineup", lineup_data="{}", created_at=datetime.utcnow())
        ]
        
        escrow_service.db_session.execute.return_value.fetchall.return_value = [
            {'id': 1, 'lineup_name': 'Test Lineup', 'lineup_data': '{}', 'created_at': datetime.utcnow()}
        ]
        
        result = escrow_service.get_saved_lineups(1, 1)
        
        assert result['success'] is True
        assert len(result['lineups']) == 1
        assert result['lineups'][0]['lineup_name'] == "Test Lineup"
    
    def test_delete_saved_lineup(self, escrow_service):
        """Test deleting a saved lineup"""
        # Mock the database operations
        escrow_service.db_session.execute.return_value.rowcount = 1
        escrow_service.db_session.commit = MagicMock()
        
        result = escrow_service.delete_saved_lineup(1, 1)
        
        assert result['success'] is True
        
        # Verify database operations were called
        escrow_service.db_session.commit.assert_called_once()
    
    def test_escrow_expiration(self, escrow_service, sample_lineup):
        """Test that escrow sessions expire correctly"""
        # Mock the database operations
        mock_escrow = MagicMock()
        mock_escrow.escrow_token = "test-token"
        mock_escrow.recipient_contact = "opponent@example.com"
        mock_escrow.status = "expired"
        mock_escrow.expires_at = datetime.utcnow() - timedelta(hours=1)
        
        escrow_service.db_session.query.return_value.filter.return_value.first.return_value = mock_escrow
        
        # Check that session is expired
        result = escrow_service.get_escrow_details("test-token", "opponent@example.com")
        assert result['escrow']['status'] == "expired"
    
    @patch('app.services.lineup_escrow_service.send_sms_notification')
    def test_sms_notification(self, mock_sms, escrow_service):
        """Test SMS notification sending"""
        mock_sms.return_value = True
        
        # Mock the database operations
        mock_escrow = MagicMock()
        mock_escrow.id = 123
        mock_escrow.escrow_token = "test-token"
        mock_escrow.recipient_contact = "+1234567890"
        mock_escrow.contact_type = "sms"
        mock_escrow.subject = "Lineup Escrow"
        mock_escrow.message_body = "Please submit your lineup"
        
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        
        escrow_service.db_session.add = MagicMock()
        escrow_service.db_session.commit = MagicMock()
        escrow_service.db_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Create escrow session
        result = escrow_service.create_escrow_session(
            initiator_user_id=1,
            recipient_name="Opponent Team",
            recipient_contact="+1234567890",
            contact_type="sms",
            initiator_lineup="test lineup",
            subject="Lineup Escrow",
            message_body="Please submit your lineup"
        )
        
        assert result['success'] is True
        # SMS notification should be called during creation
        mock_sms.assert_called()
    
    @patch('app.services.lineup_escrow_service.NotificationsService')
    def test_email_notification(self, mock_notifications, escrow_service):
        """Test email notification sending"""
        mock_notifications.return_value.send_email.return_value = True
        
        # Send email notification
        success = escrow_service.send_email_notification(
            "test@example.com", 
            "Test Subject", 
            "Test body"
        )
        
        assert success is True
        mock_notifications.return_value.send_email.assert_called_once()


class TestLineupEscrowAPI:
    """Test cases for Lineup Escrow API endpoints"""
    
    def test_create_escrow_api(self, client, auth_session):
        """Test creating escrow via API"""
        with patch('app.services.lineup_escrow_service.LineupEscrowService') as mock_service:
            mock_service.return_value.create_escrow_session.return_value = {
                'success': True,
                'escrow_id': 123,
                'escrow_token': 'test-token'
            }
            mock_service.return_value.notify_recipient_team.return_value = True
            
            data = {
                "recipient_name": "Opponent Team",
                "recipient_contact": "opponent@example.com",
                "contact_type": "email",
                "initiator_lineup": json.dumps({"court1": {"player1": "John", "player2": "Jane"}}),
                "message_body": "Please submit your lineup"
            }
            
            response = client.post('/api/lineup-escrow/create', 
                                 json=data,
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 200
            result = json.loads(response.data)
            assert result['escrow_id'] == 123
    
    def test_submit_lineup_api(self, client):
        """Test submitting lineup via API"""
        with patch('app.services.lineup_escrow_service.LineupEscrowService') as mock_service:
            mock_service.return_value.submit_recipient_lineup.return_value = {
                'success': True,
                'escrow_id': 123,
                'both_submitted': True
            }
            mock_service.return_value.get_escrow_details.return_value = {
                'success': True,
                'both_lineups_visible': True
            }
            mock_service.return_value.notify_escrow_completion.return_value = True
            
            data = {
                "escrow_token": "test-token",
                "recipient_contact": "opponent@example.com",
                "recipient_lineup": json.dumps({"court1": {"player1": "Bob", "player2": "Alice"}})
            }
            
            response = client.post('/api/lineup-escrow/submit',
                                 json=data,
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 200
            result = json.loads(response.data)
            assert result['success'] is True
    
    def test_saved_lineups_api(self, client, auth_session):
        """Test saved lineups API endpoints"""
        with patch('app.services.lineup_escrow_service.LineupEscrowService') as mock_service:
            # Test GET
            mock_service.return_value.get_saved_lineups.return_value = {
                'success': True,
                'lineups': [{'id': 1, 'lineup_name': 'Test', 'lineup_data': '{}'}]
            }
            
            response = client.get('/api/saved-lineups?team_id=1')
            assert response.status_code == 200
            result = json.loads(response.data)
            assert len(result['lineups']) == 1
            
            # Test POST
            mock_service.return_value.save_lineup.return_value = {
                'success': True,
                'lineup_id': 2
            }
            
            data = {
                "team_id": 1,
                "lineup_name": "New Lineup",
                "lineup_data": json.dumps({"court1": {"player1": "John", "player2": "Jane"}})
            }
            
            response = client.post('/api/saved-lineups',
                                 json=data,
                                 headers={'Content-Type': 'application/json'})
            assert response.status_code == 200
            
            # Test DELETE
            mock_service.return_value.delete_saved_lineup.return_value = {
                'success': True
            }
            
            data = {"lineup_id": 1}
            response = client.delete('/api/saved-lineups',
                                   json=data,
                                   headers={'Content-Type': 'application/json'})
            assert response.status_code == 200


@pytest.fixture
def auth_session(client):
    """Create an authenticated session for testing"""
    with client.session_transaction() as sess:
        sess['user'] = {
            'id': 1,
            'email': 'test@example.com',
            'is_admin': False
        }
    return client 