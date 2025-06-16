"""
Team Polls API Routes
Handles poll creation, voting, and results for team captains and players
"""

from flask import Blueprint, request, jsonify, session, redirect, url_for
from utils.auth import login_required
from utils.logging import log_user_activity
from database_utils import execute_query, execute_query_one, execute_update
from datetime import datetime
import uuid

# Create polls blueprint
polls_bp = Blueprint('polls', __name__)

@polls_bp.route('/api/polls', methods=['POST'])
@login_required
def create_poll():
    """Create a new poll with question and choices"""
    try:
        data = request.get_json()
        
        if not data or not data.get('question') or not data.get('choices'):
            return jsonify({'error': 'Question and choices are required'}), 400
        
        question = data['question'].strip()
        choices = [choice.strip() for choice in data['choices'] if choice.strip()]
        
        if len(choices) < 2:
            return jsonify({'error': 'At least 2 choices are required'}), 400
        
        user_id = session['user']['id']
        
        # Create the poll
        poll_query = '''
            INSERT INTO polls (created_by, question, team_id)
            VALUES (%s, %s, %s)
            RETURNING id
        '''
        
        poll_result = execute_query_one(poll_query, [user_id, question, None])
        
        if not poll_result:
            return jsonify({'error': 'Failed to create poll'}), 500
        
        poll_id = poll_result['id']
        
        # Add choices
        for choice_text in choices:
            choice_query = '''
                INSERT INTO poll_choices (poll_id, choice_text)
                VALUES (%s, %s)
            '''
            execute_update(choice_query, [poll_id, choice_text])
        
        # Log the activity
        log_user_activity(
            session['user']['email'],
            'poll_created',
            details=f'Created poll: {question}'
        )
        
        # Generate shareable link
        poll_link = f"/mobile/polls/{poll_id}"
        
        return jsonify({
            'success': True,
            'poll_id': poll_id,
            'poll_link': poll_link,
            'message': 'Poll created successfully'
        })
        
    except Exception as e:
        print(f"Error creating poll: {str(e)}")
        return jsonify({'error': 'Failed to create poll'}), 500

@polls_bp.route('/api/polls/team/<int:team_id>')
@login_required
def get_team_polls(team_id):
    """Get all polls for a team"""
    try:
        user = session['user']
        user_id = user['id']
        
        print(f"[DEBUG] Getting team polls for user: {user.get('email')}")
        print(f"[DEBUG] User club: {user.get('club')}, series: {user.get('series')}")
        
        # Start with simpler query - get all polls for now, then we can filter by team
        # First, get all polls created by any user
        polls_query = '''
            SELECT 
                p.id,
                p.question,
                p.created_at,
                p.created_by,
                creator.first_name,
                creator.last_name,
                COUNT(DISTINCT pr.player_id) as response_count,
                CASE WHEN p.created_by = %s THEN true ELSE false END as is_creator
            FROM polls p
            LEFT JOIN users creator ON p.created_by = creator.id
            LEFT JOIN poll_responses pr ON p.id = pr.poll_id
            GROUP BY p.id, p.question, p.created_at, p.created_by, creator.first_name, creator.last_name
            ORDER BY p.created_at DESC
        '''
        
        print(f"[DEBUG] Executing polls query...")
        polls = execute_query(polls_query, [user_id])
        print(f"[DEBUG] Found {len(polls)} polls")
        
        # Get choices for each poll
        for poll in polls:
            choices_query = '''
                SELECT id, choice_text
                FROM poll_choices
                WHERE poll_id = %s
                ORDER BY id
            '''
            try:
                poll['choices'] = execute_query(choices_query, [poll['id']])
                print(f"[DEBUG] Poll {poll['id']} has {len(poll['choices'])} choices")
            except Exception as e:
                print(f"[DEBUG] Error getting choices for poll {poll['id']}: {e}")
                poll['choices'] = []
        
        print(f"[DEBUG] Returning {len(polls)} polls successfully")
        return jsonify({
            'success': True,
            'polls': polls
        })
        
    except Exception as e:
        print(f"Error getting team polls: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Failed to get polls', 
            'debug': str(e) if user.get('email') == 'rossfreedman@gmail.com' else None
        }), 500

@polls_bp.route('/api/polls/<int:poll_id>')
def get_poll_details(poll_id):
    """Get poll details + current results (public endpoint for sharing)"""
    try:
        # Get poll details
        poll_query = '''
            SELECT 
                p.id,
                p.question,
                p.created_at,
                u.first_name,
                u.last_name
            FROM polls p
            LEFT JOIN users u ON p.created_by = u.id
            WHERE p.id = %s
        '''
        
        poll = execute_query_one(poll_query, [poll_id])
        
        if not poll:
            return jsonify({'error': 'Poll not found'}), 404
        
        # Get choices with vote counts
        choices_query = '''
            SELECT 
                pc.id,
                pc.choice_text,
                COUNT(pr.id) as vote_count
            FROM poll_choices pc
            LEFT JOIN poll_responses pr ON pc.id = pr.choice_id
            WHERE pc.poll_id = %s
            GROUP BY pc.id, pc.choice_text
            ORDER BY pc.id
        '''
        
        choices = execute_query(choices_query, [poll_id])
        
        # Get total votes
        total_votes = sum(choice['vote_count'] for choice in choices)
        
        # Calculate percentages
        for choice in choices:
            choice['percentage'] = (choice['vote_count'] / total_votes * 100) if total_votes > 0 else 0
        
        # Get voter details (who voted for what)
        voters_query = '''
            SELECT 
                pr.choice_id,
                p.first_name,
                p.last_name,
                pr.responded_at
            FROM poll_responses pr
            JOIN players p ON pr.player_id = p.id
            WHERE pr.poll_id = %s
            ORDER BY pr.responded_at DESC
        '''
        
        voters = execute_query(voters_query, [poll_id])
        
        # Group voters by choice
        voters_by_choice = {}
        for voter in voters:
            choice_id = voter['choice_id']
            if choice_id not in voters_by_choice:
                voters_by_choice[choice_id] = []
            voters_by_choice[choice_id].append({
                'name': f"{voter['first_name']} {voter['last_name']}",
                'responded_at': voter['responded_at']
            })
        
        # Check if current user has voted (if logged in)
        user_vote = None
        if 'user' in session:
            # Get user's player ID
            user_player_query = '''
                SELECT p.id
                FROM players p
                JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                WHERE upa.user_id = %s
                LIMIT 1
            '''
            user_player = execute_query_one(user_player_query, [session['user']['id']])
            
            if user_player:
                vote_query = '''
                    SELECT choice_id
                    FROM poll_responses
                    WHERE poll_id = %s AND player_id = %s
                '''
                user_vote_result = execute_query_one(vote_query, [poll_id, user_player['id']])
                if user_vote_result:
                    user_vote = user_vote_result['choice_id']
        
        return jsonify({
            'success': True,
            'poll': poll,
            'choices': choices,
            'total_votes': total_votes,
            'voters_by_choice': voters_by_choice,
            'user_vote': user_vote
        })
        
    except Exception as e:
        print(f"Error getting poll details: {str(e)}")
        return jsonify({'error': 'Failed to get poll details'}), 500

@polls_bp.route('/api/polls/<int:poll_id>/respond', methods=['POST'])
@login_required
def respond_to_poll(poll_id):
    """Submit a player's response to a poll"""
    try:
        data = request.get_json()
        
        if not data or not data.get('choice_id'):
            return jsonify({'error': 'Choice ID is required'}), 400
        
        choice_id = data['choice_id']
        
        # Get user's player ID
        user_player_query = '''
            SELECT p.id
            FROM players p
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            WHERE upa.user_id = %s
            LIMIT 1
        '''
        user_player = execute_query_one(user_player_query, [session['user']['id']])
        
        if not user_player:
            return jsonify({'error': 'Player profile not found'}), 400
        
        player_id = user_player['id']
        
        # Verify the choice exists for this poll
        choice_query = '''
            SELECT id FROM poll_choices
            WHERE id = %s AND poll_id = %s
        '''
        choice_exists = execute_query_one(choice_query, [choice_id, poll_id])
        
        if not choice_exists:
            return jsonify({'error': 'Invalid choice for this poll'}), 400
        
        # Check if user has already voted
        existing_vote_query = '''
            SELECT id FROM poll_responses
            WHERE poll_id = %s AND player_id = %s
        '''
        existing_vote = execute_query_one(existing_vote_query, [poll_id, player_id])
        
        if existing_vote:
            # Update existing vote
            update_query = '''
                UPDATE poll_responses
                SET choice_id = %s, responded_at = NOW()
                WHERE poll_id = %s AND player_id = %s
            '''
            execute_update(update_query, [choice_id, poll_id, player_id])
        else:
            # Insert new vote
            insert_query = '''
                INSERT INTO poll_responses (poll_id, choice_id, player_id)
                VALUES (%s, %s, %s)
            '''
            execute_update(insert_query, [poll_id, choice_id, player_id])
        
        # Log the activity
        log_user_activity(
            session['user']['email'],
            'poll_voted',
            details=f'Voted in poll {poll_id}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Vote submitted successfully'
        })
        
    except Exception as e:
        print(f"Error submitting poll response: {str(e)}")
        return jsonify({'error': 'Failed to submit vote'}), 500 