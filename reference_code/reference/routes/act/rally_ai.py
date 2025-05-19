from flask import jsonify, request, session, render_template
from datetime import datetime
import os
import json
from utils.logging import log_user_activity
from utils.ai import get_or_create_assistant

def init_rally_ai_routes(app):
    @app.route('/mobile/ask-ai')
    def mobile_ask_ai():
        """Serve the mobile AI chat interface"""
        try:
            user = session['user']
            log_user_activity(user['email'], 'page_visit', page='mobile_ask_ai')
            return render_template('mobile/ask_ai.html', user=user, session_data={'user': user})
        except Exception as e:
            print(f"Error serving AI chat: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat', methods=['POST'])
    def handle_chat():
        """Handle AI chat messages"""
        try:
            data = request.json
            message = data.get('message')
            thread_id = data.get('thread_id')
            
            if not message:
                return jsonify({'error': 'Message is required'}), 400
                
            assistant = get_or_create_assistant()
            
            # Create a new thread if none exists
            if not thread_id:
                thread = client.beta.threads.create()
                thread_id = thread.id
            
            # Add the message to the thread
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
            
            # Run the assistant
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant.id
            )
            
            # Wait for completion
            while True:
                run_status = client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                if run_status.status == 'completed':
                    break
                elif run_status.status == 'failed':
                    raise Exception(f"Run failed: {run_status.last_error}")
                time.sleep(1)
            
            # Get the assistant's response
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            last_message = messages.data[0]
            
            return jsonify({
                'response': last_message.content[0].text.value,
                'thread_id': thread_id
            })
            
        except Exception as e:
            print(f"Error in chat: {str(e)}")
            return jsonify({'error': str(e)}), 500 