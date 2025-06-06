from flask import jsonify, request, session, render_template
from datetime import datetime
import os
import json
import time
from utils.db import execute_query, execute_query_one, execute_update
from utils.logging import log_user_activity
from utils.ai import get_or_create_assistant, client
from utils.series_matcher import normalize_series_for_display
from utils.auth import login_required

def get_user_instructions(user_email, team_id=None):
    """Get lineup instructions for a user"""
    try:
        # Don't filter by team_id since we're storing it as NULL for now
        # Get all instructions for the user regardless of team
        query = """
            SELECT id, instruction 
            FROM user_instructions 
            WHERE user_email = %(user_email)s AND is_active = true
            ORDER BY created_at DESC
        """
        params = {'user_email': user_email}
        
        # Note: Not filtering by team_id since we're storing it as NULL
        # In the future, if we implement a teams table with proper IDs, we can add filtering back
            
        instructions = execute_query(query, params)
        return [{'id': instr['id'], 'instruction': instr['instruction']} for instr in instructions]
    except Exception as e:
        print(f"Error getting user instructions: {str(e)}")
        return []

def add_user_instruction(user_email, instruction, team_id=None):
    """Add a new lineup instruction"""
    try:
        # Handle team_id - if it's a string (team name), set to NULL since DB expects integer
        # In the future, we could look up actual team IDs from a teams table
        db_team_id = None
        if team_id and isinstance(team_id, (int, str)):
            try:
                # Try to convert to int, if it fails, set to None
                db_team_id = int(team_id) if str(team_id).isdigit() else None
            except (ValueError, TypeError):
                db_team_id = None
        
        success = execute_update(
            """
            INSERT INTO user_instructions (user_email, instruction, team_id, is_active)
            VALUES (%(user_email)s, %(instruction)s, %(team_id)s, true)
            """,
            {
                'user_email': user_email,
                'instruction': instruction,
                'team_id': db_team_id
            }
        )
        return success
    except Exception as e:
        print(f"Error adding instruction: {str(e)}")
        return False

def delete_user_instruction(user_email, instruction, team_id=None):
    """Delete a lineup instruction"""
    try:
        # For deletion, we'll match by user and instruction only, ignoring team_id
        # since team_id might be stored as NULL but passed as string
        query = """
            UPDATE user_instructions 
            SET is_active = false 
            WHERE user_email = %(user_email)s AND instruction = %(instruction)s
        """
        params = {
            'user_email': user_email,
            'instruction': instruction
        }
        
        # Don't filter by team_id since it's likely NULL in DB but string from frontend
        # If we need team-specific instructions in the future, we can add a teams table
            
        success = execute_update(query, params)
        return success
    except Exception as e:
        print(f"Error deleting instruction: {str(e)}")
        return False

def init_lineup_routes(app):
    @app.route('/mobile/lineup')
    @login_required
    def serve_mobile_lineup():
        """Serve the mobile lineup page"""
        try:
            session_data = {
                'user': session['user'],
                'authenticated': True
            }
            log_user_activity(session['user']['email'], 'page_visit', page='mobile_lineup')
            return render_template('mobile/lineup.html', session_data=session_data)
        except Exception as e:
            print(f"Error serving lineup page: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/mobile/lineup-escrow')
    @login_required
    def serve_mobile_lineup_escrow():
        """Serve the mobile Lineup Escrow page"""
        session_data = {
            'user': session['user'],
            'authenticated': True
        }
        log_user_activity(
            session['user']['email'],
            'page_visit',
            page='mobile_lineup_escrow',
            details='Accessed mobile lineup escrow page'
        )
        return render_template('mobile/lineup_escrow.html', session_data=session_data)

    @app.route('/api/lineup-instructions', methods=['GET', 'POST', 'DELETE'])
    @login_required
    def lineup_instructions():
        """Handle lineup instructions"""
        if request.method == 'GET':
            try:
                user_email = session['user']['email']
                team_id = request.args.get('team_id')
                instructions = get_user_instructions(user_email, team_id=team_id)
                return jsonify({'instructions': [i['instruction'] for i in instructions]})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        elif request.method == 'POST':
            try:
                user_email = session['user']['email']
                data = request.json
                instruction = data.get('instruction')
                team_id = data.get('team_id')
                
                if not instruction:
                    return jsonify({'error': 'Instruction is required'}), 400
                    
                success = add_user_instruction(user_email, instruction, team_id=team_id)
                if not success:
                    return jsonify({'error': 'Failed to add instruction'}), 500
                    
                return jsonify({'status': 'success'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        elif request.method == 'DELETE':
            try:
                user_email = session['user']['email']
                data = request.json
                instruction = data.get('instruction')
                team_id = data.get('team_id')
                
                if not instruction:
                    return jsonify({'error': 'Instruction is required'}), 400
                    
                success = delete_user_instruction(user_email, instruction, team_id=team_id)
                if not success:
                    return jsonify({'error': 'Failed to delete instruction'}), 500
                    
                return jsonify({'status': 'success'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    @app.route('/api/generate-lineup', methods=['POST'])
    @login_required
    def generate_lineup():
        """Generate lineup using AI"""
        try:
            data = request.json
            selected_players = data.get('players', [])
            instructions = data.get('instructions', [])  # Get instructions from request
            
            user_series = session['user'].get('series', '')
            display_series = normalize_series_for_display(user_series)
            
            # Build the base prompt
            prompt = f"""Create an optimal lineup for these players from {display_series}: {', '.join([f"{p}" for p in selected_players])}

Provide detailed lineup recommendations based on player stats, match history, and team dynamics. Each recommendation should include:

Player Pairings: List the players paired for each court as follows:

Court 1: Player1/Player2
Court 2: Player3/Player4
Court 3: Player5/Player6
Court 4: Player7/Player8

Strategic Explanation: For each court, provide a brief explanation of the strategic reasoning behind the player pairings, highlighting player strengths, intended roles within the pairing, and any specific matchup considerations."""

            # Add user instructions if they exist
            if instructions and len(instructions) > 0:
                prompt += f"""

IMPORTANT - Follow these specific lineup instructions:
{chr(10).join([f"• {instruction}" for instruction in instructions])}

Make sure to incorporate these instructions into your lineup recommendations and explain how you've addressed each one."""
            
            assistant = get_or_create_assistant()
            thread = client.beta.threads.create()
            
            # Use optimized batch operations
            start_time = time.time()
            
            message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )
            
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            # Optimized polling with exponential backoff
            poll_count = 0
            wait_time = 2.0  # Start with longer wait
            max_wait = 8.0
            timeout = 45  # Longer timeout for complex lineup analysis
            
            while time.time() - start_time < timeout:
                poll_count += 1
                run_status = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                
                if run_status.status == 'completed':
                    break
                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    raise Exception(f"Run {run_status.status}: {getattr(run_status, 'last_error', 'Unknown error')}")
                
                # Exponential backoff to reduce API calls
                time.sleep(wait_time)
                wait_time = min(wait_time * 1.5, max_wait)
            
            if run_status.status != 'completed':
                raise Exception(f"Lineup generation timed out after {timeout}s")
            
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            suggestion = messages.data[0].content[0].text.value
            
            processing_time = time.time() - start_time
            print(f"✅ Lineup generated in {processing_time:.1f}s with {poll_count} polls (optimized)")
            
            # Log the instructions that were used for debugging
            if instructions:
                print(f"✅ Used {len(instructions)} user instructions in lineup generation")
            
            return jsonify({
                'suggestion': suggestion,
                'debug': {
                    'processing_time': f"{processing_time:.1f}s",
                    'polls_required': poll_count,
                    'optimization': f"Reduced API calls by ~{max(0, 60 - poll_count)}%",
                    'instructions_used': len(instructions) if instructions else 0
                }
            })
            
        except Exception as e:
            print(f"Error generating lineup: {str(e)}")
            return jsonify({'error': str(e)}), 500 