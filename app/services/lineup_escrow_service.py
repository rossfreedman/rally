"""
Lineup Escrow Service
====================

This module handles lineup escrow functionality for fair lineup disclosure between captains.
Includes creating escrow sessions, sending notifications, and managing the escrow flow.
"""

import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.database_models import LineupEscrow, LineupEscrowView, SavedLineup, User, Team
from app.services.notifications_service import send_sms_notification
from utils.logging import log_user_activity

logger = logging.getLogger(__name__)


class LineupEscrowService:
    """Service for managing lineup escrow functionality"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_escrow_session(
        self,
        initiator_user_id: int,
        recipient_name: str,
        recipient_contact: str,
        contact_type: str,
        initiator_lineup: str,
        subject: str,
        message_body: str,
        initiator_team_id: int = None,
        recipient_team_id: int = None,
        expires_in_hours: int = 48
    ) -> Dict:
        """
        Create a new lineup escrow session
        
        Args:
            initiator_user_id: ID of the user creating the escrow
            recipient_name: Name of the recipient captain
            recipient_contact: Email or phone of recipient
            contact_type: 'email' or 'sms'
            initiator_lineup: The lineup data to escrow
            subject: Email subject (for email type)
            message_body: The message to send with the escrow
            expires_in_hours: Hours until escrow expires
            
        Returns:
            Dict with success status and escrow details
        """
        try:
            # Generate unique escrow token
            escrow_token = self._generate_escrow_token()
            
            # Calculate expiration time
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
            
            # Create escrow record
            escrow = LineupEscrow(
                escrow_token=escrow_token,
                initiator_user_id=initiator_user_id,
                recipient_name=recipient_name,
                recipient_contact=recipient_contact,
                contact_type=contact_type,
                initiator_team_id=initiator_team_id,
                recipient_team_id=recipient_team_id,
                initiator_lineup=initiator_lineup,
                status='pending',
                subject=subject,
                message_body=message_body,
                expires_at=expires_at
            )
            
            self.db_session.add(escrow)
            self.db_session.commit()
            
            # Send notification to recipient
            notification_sent = self._send_escrow_notification(escrow)
            
            # Log activity
            initiator = self.db_session.query(User).filter(User.id == initiator_user_id).first()
            if initiator:
                log_user_activity(
                    initiator.email,
                    "lineup_escrow_created",
                    details={
                        "escrow_id": escrow.id,
                        "recipient_name": recipient_name,
                        "recipient_contact": recipient_contact[-4:] if len(recipient_contact) > 4 else "****",
                        "contact_type": contact_type,
                        "notification_sent": notification_sent
                    }
                )
            
            return {
                "success": True,
                "escrow_id": escrow.id,
                "escrow_token": escrow_token,
                "notification_sent": notification_sent
            }
            
        except Exception as e:
            logger.error(f"Error creating escrow session: {str(e)}")
            self.db_session.rollback()
            return {
                "success": False,
                "error": f"Failed to create escrow session: {str(e)}"
            }

    def submit_recipient_lineup(
        self,
        escrow_token: str,
        recipient_contact: str,
        recipient_lineup: str
    ) -> Dict:
        """
        Submit the recipient's lineup to complete the escrow
        
        Args:
            escrow_token: The escrow token
            recipient_contact: Contact info for verification
            recipient_lineup: The recipient's lineup data
            
        Returns:
            Dict with success status and next steps
        """
        try:
            # Find escrow session
            escrow = self.db_session.query(LineupEscrow).filter(
                LineupEscrow.escrow_token == escrow_token,
                LineupEscrow.status == 'pending'
            ).first()
            
            if not escrow:
                return {
                    "success": False,
                    "error": "Escrow session not found or already completed"
                }
            
            # Normalize and compare contact info
            def is_email(contact):
                return '@' in contact
            if is_email(escrow.recipient_contact):
                stored = self._normalize_email(escrow.recipient_contact)
                submitted = self._normalize_email(recipient_contact)
            else:
                stored = self._normalize_phone(escrow.recipient_contact)
                submitted = self._normalize_phone(recipient_contact)
            if stored != submitted:
                return {
                    "success": False,
                    "error": "Contact information does not match"
                }
            
            # Check if expired
            if escrow.expires_at and datetime.now(timezone.utc) > escrow.expires_at:
                escrow.status = 'expired'
                self.db_session.commit()
                return {
                    "success": False,
                    "error": "Escrow session has expired"
                }
            
            # Update escrow with recipient lineup
            escrow.recipient_lineup = recipient_lineup
            escrow.recipient_submitted_at = datetime.now(timezone.utc)
            escrow.status = 'both_submitted'
            
            self.db_session.commit()
            
            # Send notifications to both parties
            self._notify_both_parties(escrow)
            
            return {
                "success": True,
                "escrow_id": escrow.id,
                "both_submitted": True
            }
            
        except Exception as e:
            logger.error(f"Error submitting recipient lineup: {str(e)}")
            self.db_session.rollback()
            return {
                "success": False,
                "error": f"Failed to submit lineup: {str(e)}"
            }

    def _clean_lineup_text(self, lineup_text: str) -> str:
        """Clean lineup text by removing HTML entities and formatting consistently"""
        if not lineup_text:
            return lineup_text
        
        # Handle double-encoded HTML entities first
        cleaned = lineup_text.replace('&lt;br&gt;', '\n').replace('&amp;amp;', '&')
        
        # Then handle single-encoded HTML entities
        cleaned = cleaned.replace('<br>', '\n').replace('&amp;', '&')
        
        # Remove any trailing <br> tags
        cleaned = cleaned.rstrip('<br>')
        
        # Convert old format to new format if needed
        # Old format: "LINEUP:\nCourt 1: Player1 & Player2\n"
        # New format: "Court 1:\n  Ad: Player1\n  Deuce: Player2\n"
        if cleaned.startswith('LINEUP:'):
            lines = cleaned.split('\n')
            new_lines = []
            
            for line in lines:
                if line.startswith('LINEUP:'):
                    continue  # Skip the LINEUP: header
                elif line.startswith('Court ') and '&' in line:
                    # Parse "Court X: Player1 & Player2" format
                    court_match = line.split(':')
                    if len(court_match) == 2:
                        court_header = court_match[0].strip()
                        players_text = court_match[1].strip()
                        players = players_text.split('&')
                        
                        if len(players) == 2:
                            player1 = players[0].strip()
                            player2 = players[1].strip()
                            
                            # Add court header once
                            new_lines.append(f"{court_header}:")
                            
                            # Skip placeholder text
                            if not player1.startswith('[Need Partner]'):
                                new_lines.append(f"  Ad: {player1}")
                            if not player2.startswith('[Need Partner]'):
                                new_lines.append(f"  Deuce: {player2}")
                            new_lines.append('')  # Add blank line between courts
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            cleaned = '\n'.join(new_lines)
        
        return cleaned

    def get_escrow_details(self, escrow_token: str, viewer_contact: str) -> Dict:
        """
        Get escrow details for viewing
        
        Args:
            escrow_token: The escrow token
            viewer_contact: Contact info of the viewer
            
        Returns:
            Dict with escrow details and lineup visibility
        """
        try:
            # Validate viewer contact
            if not viewer_contact or not viewer_contact.strip():
                return {
                    "success": False,
                    "error": "Contact information is required to view this lineup escrow"
                }
            
            escrow = self.db_session.query(LineupEscrow).filter(
                LineupEscrow.escrow_token == escrow_token
            ).first()
            
            if not escrow:
                return {
                    "success": False,
                    "error": "Escrow session not found"
                }
            
            # Validate that viewer contact matches recipient contact
            if escrow.recipient_contact != viewer_contact.strip():
                return {
                    "success": False,
                    "error": "Contact information does not match this escrow session"
                }
            
            # Record view
            self._record_view(escrow.id, viewer_contact)
            
            # Get team and club information
            initiator_team_name = "Unknown Team"
            recipient_team_name = "Unknown Team"
            initiator_club_name = "Unknown Club"
            recipient_club_name = "Unknown Club"
            
            if escrow.initiator_team_id:
                initiator_team = self.db_session.query(Team).filter(Team.id == escrow.initiator_team_id).first()
                if initiator_team:
                    initiator_team_name = initiator_team.display_name
                    if hasattr(initiator_team, 'club_id') and initiator_team.club_id:
                        from app.models.database_models import Club
                        club = self.db_session.query(Club).filter(Club.id == initiator_team.club_id).first()
                        if club:
                            initiator_club_name = club.name
            
            if escrow.recipient_team_id:
                recipient_team = self.db_session.query(Team).filter(Team.id == escrow.recipient_team_id).first()
                if recipient_team:
                    recipient_team_name = recipient_team.display_name
                    if hasattr(recipient_team, 'club_id') and recipient_team.club_id:
                        from app.models.database_models import Club
                        club = self.db_session.query(Club).filter(Club.id == recipient_team.club_id).first()
                        if club:
                            recipient_club_name = club.name
            
            # Determine what to show based on status
            if escrow.status == 'both_submitted':
                return {
                    "success": True,
                    "escrow_data": {
                        "id": escrow.id,
                        "status": escrow.status,
                        "initiator_lineup": self._clean_lineup_text(escrow.initiator_lineup),
                        "recipient_lineup": self._clean_lineup_text(escrow.recipient_lineup),
                        "initiator_submitted_at": escrow.initiator_submitted_at.isoformat(),
                        "recipient_submitted_at": escrow.recipient_submitted_at.isoformat() if escrow.recipient_submitted_at else None,
                        "subject": escrow.subject,
                        "message_body": escrow.message_body,
                        "initiator_team_name": initiator_team_name,
                        "recipient_team_name": recipient_team_name,
                        "initiator_club_name": initiator_club_name,
                        "recipient_club_name": recipient_club_name,
                        "initiator_team_id": escrow.initiator_team_id,
                        "recipient_team_id": escrow.recipient_team_id
                    },
                    "both_lineups_visible": True
                }
            elif escrow.status == 'pending':
                # For pending status, only the recipient can view (initiator sees blurred)
                return {
                    "success": True,
                    "escrow_data": {
                        "id": escrow.id,
                        "status": escrow.status,
                        "initiator_lineup": self._clean_lineup_text(escrow.initiator_lineup),
                        "recipient_lineup": None,
                        "initiator_submitted_at": escrow.initiator_submitted_at.isoformat(),
                        "recipient_submitted_at": None,
                        "subject": escrow.subject,
                        "message_body": escrow.message_body,
                        "is_initiator": True,  # Since we validated contact, this is the recipient
                        "initiator_team_name": initiator_team_name,
                        "recipient_team_name": recipient_team_name,
                        "initiator_club_name": initiator_club_name,
                        "recipient_club_name": recipient_club_name,
                        "initiator_team_id": escrow.initiator_team_id,
                        "recipient_team_id": escrow.recipient_team_id
                    },
                    "both_lineups_visible": False
                }
            else:
                return {
                    "success": True,
                    "escrow": {
                        "id": escrow.id,
                        "status": escrow.status,
                        "initiator_lineup": self._clean_lineup_text(escrow.initiator_lineup),
                        "recipient_lineup": self._clean_lineup_text(escrow.recipient_lineup),
                        "initiator_submitted_at": escrow.initiator_submitted_at.isoformat(),
                        "recipient_submitted_at": escrow.recipient_submitted_at.isoformat() if escrow.recipient_submitted_at else None,
                        "subject": escrow.subject,
                        "message_body": escrow.message_body,
                        "initiator_team_name": initiator_team_name,
                        "recipient_team_name": recipient_team_name,
                        "initiator_club_name": initiator_club_name,
                        "recipient_club_name": recipient_club_name
                    },
                    "both_lineups_visible": True
                }
                
        except Exception as e:
            logger.error(f"Error getting escrow details: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get escrow details: {str(e)}"
            }

    def save_lineup(
        self,
        user_id: int,
        team_id: int,
        lineup_name: str,
        lineup_data: str
    ) -> Dict:
        """
        Save a lineup for a user and team
        
        Args:
            user_id: ID of the user
            team_id: ID of the team
            lineup_name: Name for the saved lineup
            lineup_data: JSON string containing lineup data
            
        Returns:
            Dict with success status
        """
        try:
            # Check if lineup with this name already exists
            existing = self.db_session.query(SavedLineup).filter(
                SavedLineup.user_id == user_id,
                SavedLineup.team_id == team_id,
                SavedLineup.lineup_name == lineup_name,
                SavedLineup.is_active == True
            ).first()
            
            if existing:
                # Update existing lineup
                existing.lineup_data = lineup_data
                existing.updated_at = datetime.now(timezone.utc)
            else:
                # Create new lineup
                saved_lineup = SavedLineup(
                    user_id=user_id,
                    team_id=team_id,
                    lineup_name=lineup_name,
                    lineup_data=lineup_data
                )
                self.db_session.add(saved_lineup)
            
            self.db_session.commit()
            
            return {
                "success": True,
                "message": "Lineup saved successfully"
            }
            
        except Exception as e:
            logger.error(f"Error saving lineup: {str(e)}")
            self.db_session.rollback()
            return {
                "success": False,
                "error": f"Failed to save lineup: {str(e)}"
            }

    def get_saved_lineups(self, user_id: int, team_id: int) -> Dict:
        """
        Get all saved lineups for a user and team
        
        Args:
            user_id: ID of the user
            team_id: ID of the team
            
        Returns:
            Dict with list of saved lineups
        """
        try:
            lineups = self.db_session.query(SavedLineup).filter(
                SavedLineup.user_id == user_id,
                SavedLineup.team_id == team_id,
                SavedLineup.is_active == True
            ).order_by(SavedLineup.updated_at.desc()).all()
            
            return {
                "success": True,
                "lineups": [
                    {
                        "id": lineup.id,
                        "name": lineup.lineup_name,
                        "data": lineup.lineup_data,
                        "created_at": lineup.created_at.isoformat(),
                        "updated_at": lineup.updated_at.isoformat()
                    }
                    for lineup in lineups
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting saved lineups: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get saved lineups: {str(e)}"
            }

    def delete_saved_lineup(self, lineup_id: int, user_id: int) -> Dict:
        """
        Soft delete a saved lineup
        
        Args:
            lineup_id: ID of the lineup to delete
            user_id: ID of the user (for verification)
            
        Returns:
            Dict with success status
        """
        try:
            lineup = self.db_session.query(SavedLineup).filter(
                SavedLineup.id == lineup_id,
                SavedLineup.user_id == user_id,
                SavedLineup.is_active == True
            ).first()
            
            if not lineup:
                return {
                    "success": False,
                    "error": "Lineup not found"
                }
            
            lineup.is_active = False
            self.db_session.commit()
            
            return {
                "success": True,
                "message": "Lineup deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting saved lineup: {str(e)}")
            self.db_session.rollback()
            return {
                "success": False,
                "error": f"Failed to delete lineup: {str(e)}"
            }

    def update_saved_lineup(self, lineup_id: int, user_id: int, lineup_name: str = None, lineup_data: str = None) -> Dict:
        """
        Update a saved lineup
        
        Args:
            lineup_id: ID of the lineup to update
            user_id: ID of the user (for verification)
            lineup_name: New name for the lineup (optional)
            lineup_data: New data for the lineup (optional)
            
        Returns:
            Dict with success status
        """
        try:
            lineup = self.db_session.query(SavedLineup).filter(
                SavedLineup.id == lineup_id,
                SavedLineup.user_id == user_id,
                SavedLineup.is_active == True
            ).first()
            
            if not lineup:
                return {
                    "success": False,
                    "error": "Lineup not found"
                }
            
            # Update fields if provided
            if lineup_name is not None:
                lineup.lineup_name = lineup_name
            if lineup_data is not None:
                lineup.lineup_data = lineup_data
                
            lineup.updated_at = datetime.now(timezone.utc)
            self.db_session.commit()
            
            return {
                "success": True,
                "message": "Lineup updated successfully",
                "lineup": {
                    "id": lineup.id,
                    "name": lineup.lineup_name,
                    "data": lineup.lineup_data,
                    "updated_at": lineup.updated_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating saved lineup: {str(e)}")
            self.db_session.rollback()
            return {
                "success": False,
                "error": f"Failed to update lineup: {str(e)}"
            }

    def _generate_escrow_token(self) -> str:
        """Generate a unique escrow token"""
        return f"escrow_{secrets.token_urlsafe(16)}"

    def _blur_lineup(self, lineup_text: str) -> str:
        """Blur lineup text for privacy"""
        lines = lineup_text.split('\n')
        blurred_lines = []
        
        for line in lines:
            if line.strip():
                # Replace most characters with asterisks, keep some structure
                blurred_line = ""
                for char in line:
                    if char.isalpha():
                        blurred_line += "*"
                    elif char.isdigit():
                        blurred_line += "#"
                    else:
                        blurred_line += char
                blurred_lines.append(blurred_line)
            else:
                blurred_lines.append(line)
        
        return '\n'.join(blurred_lines)

    def _send_escrow_notification(self, escrow: LineupEscrow) -> bool:
        """Send notification to recipient about escrow"""
        try:
            # Get base URL from Flask request context or use relative path
            try:
                from flask import request, session
                base_url = request.host_url.rstrip('/')
            except RuntimeError:
                base_url = ""
            
            # Always include ?contact=... in the link
            contact_param = escrow.recipient_contact
            # Use the new opposing captain page for initial lineup submission
            view_url = f"{base_url}/mobile/lineup-escrow-opposing/{escrow.escrow_token}?contact={contact_param}" if base_url else f"/mobile/lineup-escrow-opposing/{escrow.escrow_token}?contact={contact_param}"
            
            club_name = ""
            # 1. Try team-based lookup
            if escrow.initiator_team_id:
                team = self.db_session.query(Team).filter(Team.id == escrow.initiator_team_id).first()
                if team and team.club_id:
                    from app.models.database_models import Club
                    club = self.db_session.query(Club).filter(Club.id == team.club_id).first()
                    if club and club.name:
                        club_name = club.name
            # 2. Fallback: session club_id
            if not club_name:
                try:
                    from flask import session
                    session_club_id = session.get('user', {}).get('club_id')
                    if session_club_id:
                        from app.models.database_models import Club
                        club = self.db_session.query(Club).filter(Club.id == session_club_id).first()
                        if club and club.name:
                            club_name = club.name
                except Exception:
                    pass
            # 3. Last resort
            if not club_name:
                club_name = "your club"
            
            if escrow.contact_type == 'sms':
                # Gather variables for personalized SMS
                recipient_first_name = escrow.recipient_name.split()[0] if escrow.recipient_name else "Captain"
                initiator = self.db_session.query(User).filter(User.id == escrow.initiator_user_id).first()
                sender_first_name = initiator.first_name if initiator and initiator.first_name else "A fellow captain"
                sender_last_name = initiator.last_name if initiator and initiator.last_name else ""
                # Compose message
                message = (
                    f"Hi {recipient_first_name},\n\n"
                    f"This is {sender_first_name} {sender_last_name} from {club_name}. Looking forward to our upcoming match.  \n\n"
                    "I'm using Lineup Escrow™ in the Rally app to share my lineup with you. Lineup Escrow™ is designed for each captain to send their lineup to the opposing captain before a match, with both lineups being disclosed at the exact same time. This ensures fairness and transparency for both teams.\n\n"
                    "Once you share your lineup with me, both lineups will be disclosed simultaneously.\n\n"
                    "Click the link below to get started...\n"
                    f"{view_url}"
                )
                result = send_sms_notification(
                    to_number=escrow.recipient_contact,
                    message=message,
                    test_mode=False
                )
                return result["success"]
            elif escrow.contact_type == 'email':
                recipient_first_name = escrow.recipient_name.split()[0] if escrow.recipient_name else "Captain"
                initiator = self.db_session.query(User).filter(User.id == escrow.initiator_user_id).first()
                sender_first_name = initiator.first_name if initiator and initiator.first_name else "A fellow captain"
                sender_last_name = initiator.last_name if initiator and initiator.last_name else ""
                # Compose message (same as SMS, but you can add more formatting if you want)
                message = (
                    f"Hi {recipient_first_name},\n\n"
                    f"This is {sender_first_name} {sender_last_name} from {club_name}. Looking forward to our upcoming match.  \n\n"
                    "I'm using Lineup Escrow™ in the Rally app to share my lineup with you. Lineup Escrow™ is designed for each captain to send their lineup to the opposing captain before a match, with both lineups being disclosed at the exact same time. This ensures fairness and transparency for both teams.\n\n"
                    "Once you share your lineup with me, both lineups will be disclosed simultaneously.\n\n"
                    "Click the link below to get started...\n"
                    f"{view_url}"
                )
                # Send email here (or log for now)
                logger.info(f"Email notification would be sent to {escrow.recipient_contact} with message:\n{message}")
                return True
        except Exception as e:
            logger.error(f"Error sending escrow notification: {str(e)}")
            return False

    def _notify_both_parties(self, escrow: LineupEscrow) -> None:
        """Notify both parties that lineups are ready to view"""
        try:
            # Get base URL from Flask request context or use relative path
            try:
                from flask import request
                base_url = request.host_url.rstrip('/')
            except RuntimeError:
                base_url = ""
            
            # Always include ?contact=... in the link
            contact_param = escrow.recipient_contact
            # For completion notifications, use the view page since both lineups are visible
            view_url = f"{base_url}/mobile/lineup-escrow-view/{escrow.escrow_token}?contact={contact_param}" if base_url else f"/mobile/lineup-escrow-view/{escrow.escrow_token}?contact={contact_param}"
            
            # Get initiator user
            initiator = self.db_session.query(User).filter(User.id == escrow.initiator_user_id).first()
            if initiator and initiator.phone_number:
                # Notify initiator (use their own contact info)
                # For completion notifications, use the view page since both lineups are visible
                initiator_url = f"{base_url}/mobile/lineup-escrow-view/{escrow.escrow_token}?contact={initiator.phone_number}" if base_url else f"/mobile/lineup-escrow-view/{escrow.escrow_token}?contact={initiator.phone_number}"
                message = f"🏓 Lineup Escrow™ Complete!\n\nBoth lineups are ready to view.\n\nView results: {initiator_url}"
                send_sms_notification(
                    to_number=initiator.phone_number,
                    message=message,
                    test_mode=False
                )
            # Notify recipient
            if escrow.contact_type == 'sms':
                message = f"🏓 Lineup Escrow™ Complete!\n\nBoth lineups are ready to view.\n\nView results: {view_url}"
                send_sms_notification(
                    to_number=escrow.recipient_contact,
                    message=message,
                    test_mode=False
                )
        except Exception as e:
            logger.error(f"Error notifying both parties: {str(e)}")

    def _record_view(self, escrow_id: int, viewer_contact: str) -> None:
        """Record that someone viewed the escrow"""
        try:
            view = LineupEscrowView(
                escrow_id=escrow_id,
                viewer_contact=viewer_contact
            )
            self.db_session.add(view)
            self.db_session.commit()
        except Exception as e:
            logger.error(f"Error recording view: {str(e)}")
            self.db_session.rollback() 

    def send_email_notification(self, to_email, subject, body):
        """Send email notification for lineup escrow."""
        try:
            from app.services.notifications_service import NotificationsService
            notifications_service = NotificationsService()
            
            # Send email notification
            success = notifications_service.send_email(
                to_email=to_email,
                subject=subject,
                body=body
            )
            
            if success:
                logger.info(f"Email notification sent to {to_email}: {subject}")
            else:
                logger.error(f"Failed to send email notification to {to_email}")
            
            return success
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False

    def notify_recipient_team(self, escrow_id, recipient_team_name, recipient_captain_email):
        """Send notification to recipient team (email only)"""
        escrow = self.db_session.query(LineupEscrow).filter(LineupEscrow.id == escrow_id).first()
        if not escrow:
            return False
        # Compose message (no lineup included)
        # Use the new opposing captain page for initial lineup submission
        link = f"https://rally.club/mobile/lineup-escrow-opposing/{escrow.escrow_token}?contact={escrow.recipient_contact}"
        subject = "Lineup Escrow™ - View and Submit Your Lineup"
        message = f"You have received a Lineup Escrow™ request from another captain.\n\nClick the link below to view and submit your lineup. Both lineups will be revealed simultaneously after submission.\n\n{link}\n\nDo not reply to this message."
        # Send email (implementation omitted)
        # send_email(recipient_captain_email, subject, message)
        return True

    def notify_escrow_completion(self, escrow_id):
        """Send notification when escrow is completed."""
        try:
            escrow = self.get_escrow_details(escrow_id)
            if not escrow:
                return False
            try:
                from flask import request
                base_url = request.host_url.rstrip('/')
            except RuntimeError:
                base_url = ""
            # Always include ?contact=... in the link
            # For both captains, use their email as contact param
            from app.services.team_service import TeamService
            team_service = TeamService()
            home_team = team_service.get_team_by_id(escrow['team_id'])
            away_team = team_service.get_team_by_id(escrow['recipient_team_id'])
            if not home_team or not away_team:
                return False
            home_url = f"{base_url}/lineup-escrow/{escrow_id}?contact={home_team['captain_email']}" if base_url else f"/lineup-escrow/{escrow_id}?contact={home_team['captain_email']}"
            away_url = f"{base_url}/lineup-escrow/{escrow_id}?contact={away_team['captain_email']}" if base_url else f"/lineup-escrow/{escrow_id}?contact={away_team['captain_email']}"
            subject = f"Lineup Escrow Completed - {escrow['team_name']} vs {escrow['recipient_team_name']}"
            body = f"""
Hello Captains,

The lineup escrow for your match has been completed and both lineups are now visible.

Match Details:
- Date: {escrow['match_date']}
- Time: {escrow['match_time']}
- Location: {escrow['match_location']}

View the results at:
Home Captain: {home_url}
Away Captain: {away_url}

Good luck with your match!

Best regards,
Rally Team
            """.strip()
            home_success = self.send_email_notification(home_team['captain_email'], subject, body)
            away_success = self.send_email_notification(away_team['captain_email'], subject, body)
            return home_success and away_success
        except Exception as e:
            logger.error(f"Error notifying escrow completion: {e}")
            return False 

    def _normalize_email(self, email: str) -> str:
        if not email:
            return ''
        return email.strip().lower()

    def _normalize_phone(self, phone: str) -> str:
        if not phone:
            return ''
        import re
        # Remove all non-digit characters
        return re.sub(r'\D', '', phone) 