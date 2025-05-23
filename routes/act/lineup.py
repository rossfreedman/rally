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
        query = """
            SELECT id, instruction 
            FROM user_instructions 
            WHERE user_email = %(user_email)s AND is_active = true
        """
        params = {'user_email': user_email}
        
        if team_id:
            query += ' AND team_id = %(team_id)s'
            params['team_id'] = team_id
            
        instructions = execute_query(query, params)
        return [{'id': instr['id'], 'instruction': instr['instruction']} for instr in instructions]
    except Exception as e:
        print(f"Error getting user instructions: {str(e)}")
        return []

def add_user_instruction(user_email, instruction, team_id=None):
    """Add a new lineup instruction"""
    try:
        success = execute_update(
            """
            INSERT INTO user_instructions (user_email, instruction, team_id, is_active)
            VALUES (%(user_email)s, %(instruction)s, %(team_id)s, true)
            """,
            {
                'user_email': user_email,
                'instruction': instruction,
                'team_id': team_id
            }
        )
        return success
    except Exception as e:
        print(f"Error adding instruction: {str(e)}")
        return False

def delete_user_instruction(user_email, instruction, team_id=None):
    """Delete a lineup instruction"""
    try:
        query = """
            UPDATE user_instructions 
            SET is_active = false 
            WHERE user_email = %(user_email)s AND instruction = %(instruction)s
        """
        params = {
            'user_email': user_email,
            'instruction': instruction
        }
        
        if team_id:
            query += ' AND team_id = %(team_id)s'
            params['team_id'] = team_id
            
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
            
            user_series = session['user'].get('series', '')
            display_series = normalize_series_for_display(user_series)
            
            prompt = f"""Create an optimal lineup for these players from {display_series}: {', '.join([f"{p}" for p in selected_players])}

Provide detailed lineup recommendations based on player stats, match history, and team dynamics. Each recommendation should include:

Player Pairings: List the players paired for each court as follows:

Court 1: Player1/Player2
Court 2: Player3/Player4
Court 3: Player5/Player6
Court 4: Player7/Player8

Strategic Explanation: For each court, provide a brief explanation of the strategic reasoning behind the player pairings, highlighting player strengths, intended roles within the pairing, and any specific matchup considerations.
"""
            
            assistant = get_or_create_assistant()
            thread = client.beta.threads.create()
            
            message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )
            
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id
            )
            
            while True:
                run_status = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                if run_status.status == 'completed':
                    break
                elif run_status.status == 'failed':
                    raise Exception(f"Run failed: {run_status.last_error}")
                time.sleep(1)
            
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            suggestion = messages.data[0].content[0].text.value
            
            return jsonify({
                'suggestion': suggestion,
                'prompt': prompt
            })
            
        except Exception as e:
            print(f"Error generating lineup: {str(e)}")
            return jsonify({'error': str(e)}), 500 