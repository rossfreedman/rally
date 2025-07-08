"""
Groups Service
Handles all group management functionality including creation, member management, and search
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.database_models import Group, GroupMember, User, Player, UserPlayerAssociation


class GroupsService:
    """Service class for managing user groups and group membership"""

    def __init__(self, session: Session):
        self.session = session

    def get_user_groups(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all groups that a user has created or is a member of
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of group dictionaries with member counts and metadata
        """
        # Get groups created by user
        created_groups = (
            self.session.query(Group)
            .filter(Group.creator_user_id == user_id)
            .all()
        )

        # Get groups where user is a member (but not creator)
        member_groups = (
            self.session.query(Group)
            .join(GroupMember, Group.id == GroupMember.group_id)
            .filter(
                and_(
                    GroupMember.user_id == user_id,
                    Group.creator_user_id != user_id
                )
            )
            .all()
        )

        # Combine and format results
        all_groups = []
        
        # Add created groups
        for group in created_groups:
            all_groups.append({
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'member_count': group.get_member_count(self.session),
                'created_at': group.created_at,
                'is_creator': True,
                'creator_name': f"{group.creator.first_name} {group.creator.last_name}" if group.creator else "Unknown"
            })

        # Add member groups
        for group in member_groups:
            all_groups.append({
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'member_count': group.get_member_count(self.session),
                'created_at': group.created_at,
                'is_creator': False,
                'creator_name': f"{group.creator.first_name} {group.creator.last_name}" if group.creator else "Unknown"
            })

        # Sort by creation date (newest first)
        all_groups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return all_groups

    def create_group(self, user_id: int, name: str, description: str = None) -> Dict[str, Any]:
        """
        Create a new group
        
        Args:
            user_id: ID of the user creating the group
            name: Name of the group
            description: Optional description
            
        Returns:
            Dictionary with success status and group data or error message
        """
        try:
            # Check if user already has a group with this name
            existing_group = (
                self.session.query(Group)
                .filter(
                    and_(
                        Group.creator_user_id == user_id,
                        Group.name == name
                    )
                )
                .first()
            )
            
            if existing_group:
                return {
                    'success': False,
                    'error': 'You already have a group with this name'
                }

            # Create new group
            new_group = Group(
                name=name,
                description=description,
                creator_user_id=user_id
            )
            
            self.session.add(new_group)
            self.session.commit()
            
            return {
                'success': True,
                'group': {
                    'id': new_group.id,
                    'name': new_group.name,
                    'description': new_group.description,
                    'member_count': 0,
                    'created_at': new_group.created_at,
                    'is_creator': True
                }
            }
            
        except Exception as e:
            self.session.rollback()
            return {
                'success': False,
                'error': f'Failed to create group: {str(e)}'
            }

    def get_group_details(self, group_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get detailed information about a group including members
        
        Args:
            group_id: ID of the group
            user_id: ID of the requesting user (for permission checking)
            
        Returns:
            Dictionary with group details and members list
        """
        # Get the group
        group = self.session.query(Group).filter(Group.id == group_id).first()
        
        if not group:
            return {
                'success': False,
                'error': 'Group not found'
            }

        # Check if user has access (creator or member)
        is_creator = group.creator_user_id == user_id
        is_member = group.is_member(self.session, user_id)
        
        if not (is_creator or is_member):
            return {
                'success': False,
                'error': 'Access denied'
            }

        # Get group members with details
        members = (
            self.session.query(User, GroupMember)
            .join(GroupMember, User.id == GroupMember.user_id)
            .filter(GroupMember.group_id == group_id)
            .all()
        )

        members_list = []
        for user, membership in members:
            # Get player info for this user
            player_info = self._get_user_player_info(user.id)
            
            members_list.append({
                'user_id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'added_at': membership.added_at,
                'player_info': player_info,
                'can_remove': is_creator  # Only creator can remove members
            })

        return {
            'success': True,
            'group': {
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'creator_id': group.creator_user_id,
                'creator_name': f"{group.creator.first_name} {group.creator.last_name}" if group.creator else "Unknown",
                'created_at': group.created_at,
                'member_count': len(members_list),
                'is_creator': is_creator,
                'members': members_list
            }
        }

    def search_players(self, query: str, user_id: int, league_id: int = None) -> List[Dict[str, Any]]:
        """
        Search for players to add to groups
        
        Args:
            query: Search query (name)
            user_id: ID of the searching user (to exclude them)
            league_id: Optional league filter
            
        Returns:
            List of matching players with their details
        """
        if len(query) < 2:
            return []

        # Build base query for players table
        base_query = self.session.query(Player)

        # Add search filters for player names
        search_filter = or_(
            func.lower(Player.first_name).contains(func.lower(query)),
            func.lower(Player.last_name).contains(func.lower(query)),
            func.lower(func.concat(Player.first_name, ' ', Player.last_name)).contains(func.lower(query))
        )
        
        base_query = base_query.filter(search_filter)

        # Apply league filter if provided
        if league_id:
            base_query = base_query.filter(Player.league_id == league_id)

        # Only include active players
        base_query = base_query.filter(Player.is_active == True)

        # Exclude the searching user's players if we can identify them
        if user_id:
            # Get the user's tenniscores_player_ids to exclude
            user_player_ids = (
                self.session.query(UserPlayerAssociation.tenniscores_player_id)
                .filter(UserPlayerAssociation.user_id == user_id)
                .subquery()
            )
            base_query = base_query.filter(
                Player.tenniscores_player_id.notin_(user_player_ids)
            )

        # Execute query and get results
        players = base_query.limit(20).all()
        
        results = []
        for player in players:
            # Try to find associated user for this player
            user_association = (
                self.session.query(User)
                .join(UserPlayerAssociation, User.id == UserPlayerAssociation.user_id)
                .filter(UserPlayerAssociation.tenniscores_player_id == player.tenniscores_player_id)
                .first()
            )

            # Format player info
            player_info = [{
                'league': player.league.league_name if player.league else 'Unknown',
                'club': player.club.name if player.club else 'Unknown', 
                'series': player.series.name if player.series else 'Unknown',
                'pti': float(player.pti) if player.pti else None,
                'wins': player.wins or 0,
                'losses': player.losses or 0
            }]

            result = {
                'first_name': player.first_name,
                'last_name': player.last_name,
                'full_name': f"{player.first_name} {player.last_name}",
                'player_info': player_info,
                'tenniscores_player_id': player.tenniscores_player_id
            }

            # If we found a user association, include user info for adding to group
            if user_association:
                result['user_id'] = user_association.id
                result['email'] = user_association.email
            else:
                # Player exists but no user account - can't add to group
                result['user_id'] = None
                result['email'] = None
                result['no_account'] = True

            results.append(result)

        return results

    def add_member_to_group(self, group_id: int, user_id: int, member_user_id: int) -> Dict[str, Any]:
        """
        Add a member to a group
        
        Args:
            group_id: ID of the group
            user_id: ID of the user adding the member (must be group creator)
            member_user_id: ID of the user to add as member
            
        Returns:
            Dictionary with success status and result
        """
        try:
            # Get the group and verify permissions
            group = self.session.query(Group).filter(Group.id == group_id).first()
            
            if not group:
                return {
                    'success': False,
                    'error': 'Group not found'
                }

            if group.creator_user_id != user_id:
                return {
                    'success': False,
                    'error': 'Only the group creator can add members'
                }

            # Check if user is already a member
            existing_membership = (
                self.session.query(GroupMember)
                .filter(
                    and_(
                        GroupMember.group_id == group_id,
                        GroupMember.user_id == member_user_id
                    )
                )
                .first()
            )

            if existing_membership:
                return {
                    'success': False,
                    'error': 'User is already a member of this group'
                }

            # Verify the user to add exists
            member_user = self.session.query(User).filter(User.id == member_user_id).first()
            if not member_user:
                return {
                    'success': False,
                    'error': 'User not found'
                }

            # Add the membership
            new_membership = GroupMember(
                group_id=group_id,
                user_id=member_user_id,
                added_by_user_id=user_id
            )
            
            self.session.add(new_membership)
            self.session.commit()
            
            return {
                'success': True,
                'message': f'{member_user.first_name} {member_user.last_name} added to group'
            }
            
        except Exception as e:
            self.session.rollback()
            return {
                'success': False,
                'error': f'Failed to add member: {str(e)}'
            }

    def remove_member_from_group(self, group_id: int, user_id: int, member_user_id: int) -> Dict[str, Any]:
        """
        Remove a member from a group
        
        Args:
            group_id: ID of the group
            user_id: ID of the user removing the member (must be group creator)
            member_user_id: ID of the user to remove
            
        Returns:
            Dictionary with success status and result
        """
        try:
            # Get the group and verify permissions
            group = self.session.query(Group).filter(Group.id == group_id).first()
            
            if not group:
                return {
                    'success': False,
                    'error': 'Group not found'
                }

            if group.creator_user_id != user_id:
                return {
                    'success': False,
                    'error': 'Only the group creator can remove members'
                }

            # Find the membership
            membership = (
                self.session.query(GroupMember)
                .filter(
                    and_(
                        GroupMember.group_id == group_id,
                        GroupMember.user_id == member_user_id
                    )
                )
                .first()
            )

            if not membership:
                return {
                    'success': False,
                    'error': 'User is not a member of this group'
                }

            # Get user name for response
            member_user = self.session.query(User).filter(User.id == member_user_id).first()
            member_name = f'{member_user.first_name} {member_user.last_name}' if member_user else 'User'

            # Remove the membership
            self.session.delete(membership)
            self.session.commit()
            
            return {
                'success': True,
                'message': f'{member_name} removed from group'
            }
            
        except Exception as e:
            self.session.rollback()
            return {
                'success': False,
                'error': f'Failed to remove member: {str(e)}'
            }

    def delete_group(self, group_id: int, user_id: int) -> Dict[str, Any]:
        """
        Delete a group (only by creator)
        
        Args:
            group_id: ID of the group to delete
            user_id: ID of the user requesting deletion
            
        Returns:
            Dictionary with success status and result
        """
        try:
            # Get the group and verify permissions
            group = self.session.query(Group).filter(Group.id == group_id).first()
            
            if not group:
                return {
                    'success': False,
                    'error': 'Group not found'
                }

            if group.creator_user_id != user_id:
                return {
                    'success': False,
                    'error': 'Only the group creator can delete the group'
                }

            group_name = group.name
            
            # Delete the group (cascade will handle members)
            self.session.delete(group)
            self.session.commit()
            
            return {
                'success': True,
                'message': f'Group "{group_name}" deleted successfully'
            }
            
        except Exception as e:
            self.session.rollback()
            return {
                'success': False,
                'error': f'Failed to delete group: {str(e)}'
            }

    def update_group(self, group_id: int, user_id: int, name: str, description: str = None) -> Dict[str, Any]:
        """
        Update group details (creator only)
        
        Args:
            group_id: ID of the group to update
            user_id: ID of the user requesting update (must be creator)
            name: New name for the group
            description: New description for the group
            
        Returns:
            Dictionary with success status and result
        """
        try:
            # Get the group and verify permissions
            group = self.session.query(Group).filter(Group.id == group_id).first()
            
            if not group:
                return {
                    'success': False,
                    'error': 'Group not found'
                }

            if group.creator_user_id != user_id:
                return {
                    'success': False,
                    'error': 'Only the group creator can update the group'
                }

            # Check if user already has another group with this name
            existing_group = (
                self.session.query(Group)
                .filter(
                    and_(
                        Group.creator_user_id == user_id,
                        Group.name == name,
                        Group.id != group_id  # Exclude current group
                    )
                )
                .first()
            )
            
            if existing_group:
                return {
                    'success': False,
                    'error': 'You already have another group with this name'
                }

            # Update the group
            group.name = name
            group.description = description
            
            self.session.commit()
            
            return {
                'success': True,
                'message': 'Group updated successfully',
                'group': {
                    'id': group.id,
                    'name': group.name,
                    'description': group.description,
                    'updated_at': group.updated_at
                }
            }
            
        except Exception as e:
            self.session.rollback()
            return {
                'success': False,
                'error': f'Failed to update group: {str(e)}'
            }

    def send_group_message(self, group_id: int, user_id: int, subject: str, message: str) -> Dict[str, Any]:
        """
        Send a message to all members of a group
        
        Args:
            group_id: ID of the group
            user_id: ID of the user sending the message
            subject: Subject of the message
            message: Message content
            
        Returns:
            Dictionary with success status and result
        """
        try:
            # Get the group and verify permissions
            group = self.session.query(Group).filter(Group.id == group_id).first()
            
            if not group:
                return {
                    'success': False,
                    'error': 'Group not found'
                }

            # Check if user has access (creator or member)
            is_creator = group.creator_user_id == user_id
            is_member = group.is_member(self.session, user_id)
            
            if not (is_creator or is_member):
                return {
                    'success': False,
                    'error': 'Only group members can send messages'
                }

            # Get all group members
            members = (
                self.session.query(User)
                .join(GroupMember, User.id == GroupMember.user_id)
                .filter(GroupMember.group_id == group_id)
                .all()
            )

            # Get sender info
            sender = self.session.query(User).filter(User.id == user_id).first()
            sender_name = f"{sender.first_name} {sender.last_name}" if sender else "Unknown"

            # For now, we'll just return success with recipient info
            # In the future, this could integrate with an email service
            recipient_names = [f"{member.first_name} {member.last_name}" for member in members]
            recipient_emails = [member.email for member in members if member.email]

            return {
                'success': True,
                'message': f'Message sent to {len(members)} group members',
                'details': {
                    'sender': sender_name,
                    'group_name': group.name,
                    'subject': subject,
                    'recipient_count': len(members),
                    'recipients': recipient_names,
                    'recipient_emails': recipient_emails
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to send message: {str(e)}'
            }

    def _get_user_player_info(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get player information for a user across all leagues
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of player records with league/club/series info
        """
        players = (
            self.session.query(Player)
            .join(UserPlayerAssociation, Player.tenniscores_player_id == UserPlayerAssociation.tenniscores_player_id)
            .filter(UserPlayerAssociation.user_id == user_id)
            .all()
        )

        player_info = []
        for player in players:
            player_info.append({
                'league': player.league.league_name if player.league else 'Unknown',
                'club': player.club.name if player.club else 'Unknown',
                'series': player.series.name if player.series else 'Unknown',
                'pti': float(player.pti) if player.pti else None,
                'wins': player.wins or 0,
                'losses': player.losses or 0
            })

        return player_info 