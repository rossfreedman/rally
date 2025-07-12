"""
Groups Service
Handles all group management functionality including creation, member management, and search
"""

import csv
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.database_models import Group, GroupMember, User, Player, UserPlayerAssociation


class GroupsService:
    """Service class for managing user groups and group membership"""

    def __init__(self, session: Session):
        self.session = session

    def _lookup_phone_from_club_directory(self, first_name: str, last_name: str, user_league_string_id: str = None) -> Optional[str]:
        """
        Look up phone number from club directory CSV file
        
        Args:
            first_name: Player's first name
            last_name: Player's last name
            user_league_string_id: User's league string ID for determining CSV path
            
        Returns:
            Phone number if found, None otherwise
        """
        try:
            # Use dynamic path based on league (similar to /api/player-contact)
            if user_league_string_id and not user_league_string_id.startswith("APTA"):
                # For non-APTA leagues, use league-specific path
                csv_path = os.path.join(
                    "data",
                    "leagues",
                    user_league_string_id,
                    "club_directories",
                    "directory_tennaqua.csv",
                )
            else:
                # For APTA leagues, use the main directory
                csv_path = os.path.join(
                    "data",
                    "leagues",
                    "all",
                    "club_directories",
                    "directory_tennaqua.csv",
                )

            print(f"Looking for phone number in CSV file at: {csv_path}")
            
            if not os.path.exists(csv_path):
                print(f"CSV file not found at: {csv_path}")
                return None

            with open(csv_path, "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Match by first and last name (case insensitive)
                    if (
                        row["First"].strip().lower() == first_name.lower()
                        and row["Last Name"].strip().lower() == last_name.lower()
                    ):
                        phone = row["Phone"].strip()
                        if phone:
                            print(f"Found phone number for {first_name} {last_name} in club directory: {phone}")
                            return phone
                        else:
                            print(f"Found {first_name} {last_name} in club directory but no phone number")
                            return None

            print(f"Player {first_name} {last_name} not found in club directory")
            return None

        except Exception as e:
            print(f"Error looking up phone number in club directory: {str(e)}")
            return None

    def get_user_groups(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all groups that a user has created
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of group dictionaries with member counts and metadata
        """
        # Only get groups created by user (not groups where they are members)
        created_groups = (
            self.session.query(Group)
            .filter(Group.creator_user_id == user_id)
            .order_by(Group.created_at.desc())  # Newest first
            .all()
        )

        # Format results
        all_groups = []
        
        # Add created groups
        for group in created_groups:
            all_groups.append({
                'id': group.id,
                'name': group.name,
                'description': group.description,
                'member_count': group.get_member_count(self.session),
                'created_at': group.created_at,
                'creator_user_id': group.creator_user_id,
                'is_creator': True,
                'creator_name': f"{group.creator.first_name} {group.creator.last_name}" if group.creator else "Unknown"
            })
        
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

        # Get requesting user's league string ID for club directory lookup
        requesting_user_league_string_id = None
        requesting_user = self.session.query(User).filter(User.id == user_id).first()
        if requesting_user:
            # Look up the league string ID from the requesting user's associations
            requesting_user_league_query = """
                SELECT DISTINCT l.league_id 
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN leagues l ON p.league_id = l.id
                WHERE u.id = %s
                ORDER BY l.league_id
                LIMIT 1
            """
            from database_utils import execute_query_one
            user_league_result = execute_query_one(requesting_user_league_query, [user_id])
            if user_league_result:
                requesting_user_league_string_id = user_league_result['league_id']
                print(f"Found requesting user's league string ID: {requesting_user_league_string_id}")

        members_list = []
        for user, membership in members:
            # Get player info for this user
            player_info = self._get_user_player_info(user.id)
            
            # Check for phone number in user profile, with club directory fallback
            phone_number = user.phone_number
            phone_source = 'user_profile'
            
            if not phone_number or not phone_number.strip():
                # Try club directory fallback
                directory_phone = self._lookup_phone_from_club_directory(
                    user.first_name, 
                    user.last_name, 
                    requesting_user_league_string_id
                )
                if directory_phone:
                    phone_number = directory_phone
                    phone_source = 'club_directory'
                    print(f"Found phone number for {user.first_name} {user.last_name} in club directory for UI display: {directory_phone}")
            
            members_list.append({
                'user_id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone_number': phone_number,  # Now includes club directory fallback
                'phone_source': phone_source,  # Track source for UI display
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

    def search_players(self, query: str, user_id: int, league_id: int = None, club_id: int = None) -> List[Dict[str, Any]]:
        """
        Search for players to add to groups
        
        Args:
            query: Search query (name)
            user_id: ID of the searching user (to exclude them)
            league_id: Optional league filter
            club_id: Optional club filter - only show players from this club
            
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

        # Apply club filter if provided (only show players from user's current club)
        if club_id:
            base_query = base_query.filter(Player.club_id == club_id)

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

            # Include user info for adding to group
            if user_association:
                # Player has a user account
                result['user_id'] = user_association.id
                result['email'] = user_association.email
            else:
                # Player exists but no user account - allow adding them anyway
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

    def add_player_without_account_to_group(self, group_id: int, user_id: int, 
                                          tenniscores_player_id: str, first_name: str, 
                                          last_name: str, user_club_id: int = None) -> Dict[str, Any]:
        """
        Handle adding a player without an account to a group
        
        Args:
            group_id: ID of the group
            user_id: ID of the user adding the member (must be group creator)
            tenniscores_player_id: Player's tenniscores ID
            first_name: Player's first name
            last_name: Player's last name
            
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

            # Get the user's league context to ensure we're adding the player from the correct league
            user_obj = self.session.query(User).filter(User.id == user_id).first()
            user_league_id = user_obj.league_context if user_obj else None
            
            # Verify the player record matches the user's context (league and club)
            player_record = (
                self.session.query(Player)
                .filter(Player.tenniscores_player_id == tenniscores_player_id)
                .first()
            )
            
            if player_record and user_league_id and user_club_id:
                # Check if this player record matches the user's league and club
                if player_record.league_id != user_league_id or player_record.club_id != user_club_id:
                    # Try to find the correct player record for this person in the user's league/club
                    correct_player = (
                        self.session.query(Player)
                        .filter(
                            Player.first_name == first_name,
                            Player.last_name == last_name,
                            Player.league_id == user_league_id,
                            Player.club_id == user_club_id,
                            Player.is_active == True
                        )
                        .first()
                    )
                    
                    if correct_player:
                        # Use the correct player's tenniscores_player_id
                        tenniscores_player_id = correct_player.tenniscores_player_id
                        print(f"Corrected player selection: Using {tenniscores_player_id} for {first_name} {last_name} in user's league/club")
                    else:
                        print(f"Warning: Could not find {first_name} {last_name} in user's league/club context")

            # Check if a user already exists for this player
            existing_user = (
                self.session.query(User)
                .join(UserPlayerAssociation, User.id == UserPlayerAssociation.user_id)
                .filter(UserPlayerAssociation.tenniscores_player_id == tenniscores_player_id)
                .first()
            )
            
            if existing_user:
                # User exists, use the regular add member function
                return self.add_member_to_group(group_id, user_id, existing_user.id)
            
            # Create a placeholder user record for the player without an account
            placeholder_email = f"{tenniscores_player_id}@placeholder.rally"
            
            # Check if placeholder user already exists
            existing_placeholder = (
                self.session.query(User)
                .filter(User.email == placeholder_email)
                .first()
            )
            
            if existing_placeholder:
                # Placeholder already exists, use it
                new_user = existing_placeholder
            else:
                # Create new placeholder user
                new_user = User(
                    first_name=first_name,
                    last_name=last_name,
                    email=placeholder_email,
                    password_hash="placeholder"  # They can't log in with this
                )
                
                self.session.add(new_user)
                self.session.flush()  # Get the user ID
                
                # Create the player association
                association = UserPlayerAssociation(
                    user_id=new_user.id,
                    tenniscores_player_id=tenniscores_player_id
                )
                
                self.session.add(association)

            # Check if user is already a member
            existing_membership = (
                self.session.query(GroupMember)
                .filter(
                    and_(
                        GroupMember.group_id == group_id,
                        GroupMember.user_id == new_user.id
                    )
                )
                .first()
            )

            if existing_membership:
                return {
                    'success': False,
                    'error': f'{first_name} {last_name} is already a member of this group'
                }

            # Add the membership
            new_membership = GroupMember(
                group_id=group_id,
                user_id=new_user.id,
                added_by_user_id=user_id
            )
            
            self.session.add(new_membership)
            self.session.commit()
            
            return {
                'success': True,
                'message': f'{first_name} {last_name} added to group (they can join when they create an account)'
            }
            
        except Exception as e:
            self.session.rollback()
            return {
                'success': False,
                'error': f'Failed to add player: {str(e)}'
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
        Send SMS messages to all members of a group
        
        Args:
            group_id: ID of the group
            user_id: ID of the user sending the message
            subject: Subject of the message (used in SMS formatting)
            message: Message content
            
        Returns:
            Dictionary with success status and detailed results
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

            # Get all group members with phone numbers
            members = (
                self.session.query(User)
                .join(GroupMember, User.id == GroupMember.user_id)
                .filter(GroupMember.group_id == group_id)
                .all()
            )

            # Get sender info and league context for club directory lookup
            sender = self.session.query(User).filter(User.id == user_id).first()
            sender_name = f"{sender.first_name} {sender.last_name}" if sender else "Unknown"
            
            # Get sender's league string ID for club directory lookup
            sender_league_string_id = None
            if sender:
                # Look up the league string ID from the sender's associations
                sender_league_query = """
                    SELECT DISTINCT l.league_id 
                    FROM users u
                    JOIN user_player_associations upa ON u.id = upa.user_id
                    JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                    JOIN leagues l ON p.league_id = l.id
                    WHERE u.id = %s
                    ORDER BY l.league_id
                    LIMIT 1
                """
                from database_utils import execute_query_one
                sender_league_result = execute_query_one(sender_league_query, [user_id])
                if sender_league_result:
                    sender_league_string_id = sender_league_result['league_id']
                    print(f"Found sender's league string ID: {sender_league_string_id}")

            # Get admin users with phone numbers for testing (they'll receive all group messages)
            admin_users = (
                self.session.query(User)
                .filter(User.is_admin == True)
                .filter(User.phone_number.isnot(None))
                .filter(User.phone_number != '')
                .all()
            )

            # Separate members with and without phone numbers, with club directory fallback
            members_with_phones = []
            members_without_phones = []
            members_with_directory_phones = []
            
            for member in members:
                if member.phone_number and member.phone_number.strip():
                    # Has phone number in user table
                    members_with_phones.append(member)
                else:
                    # No phone number in user table - try club directory fallback
                    directory_phone = self._lookup_phone_from_club_directory(
                        member.first_name, 
                        member.last_name, 
                        sender_league_string_id
                    )
                    
                    if directory_phone:
                        # Found phone number in club directory
                        # Create a temporary member object with the directory phone
                        member_with_directory_phone = {
                            'user': member,
                            'phone_number': directory_phone,
                            'source': 'club_directory'
                        }
                        members_with_directory_phones.append(member_with_directory_phone)
                        print(f"Using club directory phone for {member.first_name} {member.last_name}: {directory_phone}")
                    else:
                        # No phone number found anywhere
                        members_without_phones.append(member)

            # Add admin users to recipients (but don't count them as group members)
            admin_recipients = []
            for admin in admin_users:
                # Don't duplicate if admin is already a group member
                if admin not in members_with_phones:
                    admin_recipients.append(admin)

            # Check if anyone has phone numbers (members or admins)
            total_members_with_phones = len(members_with_phones) + len(members_with_directory_phones)
            total_recipients = total_members_with_phones + len(admin_recipients)
            if total_recipients == 0:
                return {
                    'success': False,
                    'error': f'No group members have phone numbers available. Please ask members to add their phone numbers in Settings or ensure they are listed in the club directory.',
                    'details': {
                        'total_members': len(members),
                        'members_without_phones': len(members_without_phones),
                        'members_with_phones': 0,
                        'members_with_directory_phones': 0,
                        'admin_recipients': 0
                    }
                }

            # Format the SMS message
            # Keep it concise for SMS
            formatted_message = f"💬 Group message from {sender_name} in '{group.name}':\n\n{message}"
            
            # Import notifications service for SMS sending
            from app.services.notifications_service import send_sms_notification
            
            # Send SMS to each member with a phone number
            successful_sends = []
            failed_sends = []
            admin_successful_sends = []
            admin_failed_sends = []
            
            # Send to group members with phone numbers in user table
            for member in members_with_phones:
                try:
                    result = send_sms_notification(
                        to_number=member.phone_number,
                        message=formatted_message,
                        test_mode=False
                    )
                    
                    if result["success"]:
                        successful_sends.append({
                            'name': f"{member.first_name} {member.last_name}",
                            'phone': member.phone_number,
                            'message_sid': result.get('message_sid'),
                            'status': 'sent',
                            'source': 'user_table'
                        })
                    else:
                        failed_sends.append({
                            'name': f"{member.first_name} {member.last_name}",
                            'phone': member.phone_number,
                            'error': result.get('error'),
                            'status': 'failed',
                            'source': 'user_table'
                        })
                        
                except Exception as e:
                    failed_sends.append({
                        'name': f"{member.first_name} {member.last_name}",
                        'phone': member.phone_number,
                        'error': f'Unexpected error: {str(e)}',
                        'status': 'failed',
                        'source': 'user_table'
                    })
            
            # Send to group members with phone numbers from club directory
            for member_data in members_with_directory_phones:
                member = member_data['user']
                phone = member_data['phone_number']
                try:
                    result = send_sms_notification(
                        to_number=phone,
                        message=formatted_message,
                        test_mode=False
                    )
                    
                    if result["success"]:
                        successful_sends.append({
                            'name': f"{member.first_name} {member.last_name}",
                            'phone': phone,
                            'message_sid': result.get('message_sid'),
                            'status': 'sent',
                            'source': 'club_directory'
                        })
                    else:
                        failed_sends.append({
                            'name': f"{member.first_name} {member.last_name}",
                            'phone': phone,
                            'error': result.get('error'),
                            'status': 'failed',
                            'source': 'club_directory'
                        })
                        
                except Exception as e:
                    failed_sends.append({
                        'name': f"{member.first_name} {member.last_name}",
                        'phone': phone,
                        'error': f'Unexpected error: {str(e)}',
                        'status': 'failed',
                        'source': 'club_directory'
                    })

            # Send to admin users for testing
            admin_message = f"🔧 ADMIN COPY - Group message from {sender_name} in '{group.name}':\n\n{message}"
            
            for admin in admin_recipients:
                try:
                    result = send_sms_notification(
                        to_number=admin.phone_number,
                        message=admin_message,
                        test_mode=False
                    )
                    
                    if result["success"]:
                        admin_successful_sends.append({
                            'name': f"{admin.first_name} {admin.last_name} (Admin)",
                            'phone': admin.phone_number,
                            'message_sid': result.get('message_sid'),
                            'status': 'sent'
                        })
                    else:
                        admin_failed_sends.append({
                            'name': f"{admin.first_name} {admin.last_name} (Admin)",
                            'phone': admin.phone_number,
                            'error': result.get('error'),
                            'status': 'failed'
                        })
                        
                except Exception as e:
                    admin_failed_sends.append({
                        'name': f"{admin.first_name} {admin.last_name} (Admin)",
                        'phone': admin.phone_number,
                        'error': f'Unexpected error: {str(e)}',
                        'status': 'failed'
                    })

            # Determine overall success
            total_attempted = len(members_with_phones) + len(members_with_directory_phones)
            total_successful = len(successful_sends)
            total_failed = len(failed_sends)
            
            admin_attempted = len(admin_recipients)
            admin_successful = len(admin_successful_sends)
            admin_failed = len(admin_failed_sends)
            
            # Consider it successful if at least one message was sent (to members or admins)
            overall_success = (total_successful + admin_successful) > 0
            
            # Create response message with directory fallback info
            directory_count = len(members_with_directory_phones)
            if total_successful == total_attempted and total_attempted > 0:
                response_message = f"✅ Message sent successfully to all {total_successful} group members!"
                if directory_count > 0:
                    response_message += f" ({directory_count} phone number{'s' if directory_count != 1 else ''} found in club directory)"
            elif total_successful > 0:
                response_message = f"⚠️ Message sent to {total_successful} of {total_attempted} members with phone numbers. {total_failed} failed to send."
                if directory_count > 0:
                    response_message += f" ({directory_count} phone number{'s' if directory_count != 1 else ''} found in club directory)"
            else:
                response_message = f"❌ Failed to send message to any group members. Check phone numbers and try again."
            
            # Add admin info if admins received copies
            if admin_successful > 0:
                response_message += f" (Also sent to {admin_successful} admin{'' if admin_successful == 1 else 's'} for testing.)"
            elif admin_attempted > 0:
                response_message += f" (Failed to send to {admin_failed} admin{'' if admin_failed == 1 else 's'}.)"

            return {
                'success': overall_success,
                'message': response_message,
                'details': {
                    'sender': sender_name,
                    'group_name': group.name,
                    'total_members': len(members),
                    'members_with_phones': len(members_with_phones),
                    'members_with_directory_phones': len(members_with_directory_phones),
                    'members_without_phones': len(members_without_phones),
                    'successful_sends': total_successful,
                    'failed_sends': total_failed,
                    'successful_recipients': successful_sends,
                    'failed_recipients': failed_sends,
                    'members_without_phones_list': [
                        f"{m.first_name} {m.last_name}" for m in members_without_phones
                    ] if members_without_phones else [],
                    'admin_recipients': admin_attempted,
                    'admin_successful_sends': admin_successful,
                    'admin_failed_sends': admin_failed,
                    'admin_successful_recipients': admin_successful_sends,
                    'admin_failed_recipients': admin_failed_sends,
                    'testing_note': 'Admin users automatically receive copies of all group messages for testing purposes.',
                    'fallback_note': f'Phone numbers for {directory_count} member{"" if directory_count == 1 else "s"} were found in the club directory.' if directory_count > 0 else None
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to send group message: {str(e)}'
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