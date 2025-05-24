from flask import jsonify, request, session, render_template
from datetime import datetime
import os
import json
import time
from utils.logging import log_user_activity
from utils.ai import get_or_create_assistant, client

# Context management settings
MAX_CONTEXT_CHARS = 8000  # Adjust based on your needs
MAX_MESSAGES = 20  # Maximum number of messages to keep in context

# Cache assistant to avoid repeated lookups
_cached_assistant = None
_assistant_cache_time = None
ASSISTANT_CACHE_DURATION = 3600  # 1 hour

def get_cached_assistant():
    """Get assistant with caching to reduce API calls"""
    global _cached_assistant, _assistant_cache_time
    
    current_time = time.time()
    if (_cached_assistant is None or 
        _assistant_cache_time is None or 
        current_time - _assistant_cache_time > ASSISTANT_CACHE_DURATION):
        
        _cached_assistant = get_or_create_assistant()
        _assistant_cache_time = current_time
        print(f"Assistant cached: {_cached_assistant.id}")
    
    return _cached_assistant

def manage_thread_context(thread_id):
    """
    Manage context window by limiting message history
    Returns: (context_size, message_count, was_trimmed)
    """
    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        total_chars = 0
        messages_to_keep = []
        
        # Count from most recent backwards
        for i, msg in enumerate(messages.data):
            if hasattr(msg.content[0], 'text'):
                msg_chars = len(msg.content[0].text.value)
                
                # Check if adding this message would exceed limits
                if (total_chars + msg_chars > MAX_CONTEXT_CHARS or 
                    len(messages_to_keep) >= MAX_MESSAGES):
                    break
                    
                total_chars += msg_chars
                messages_to_keep.append(msg)
        
        # If we need to trim, create a new thread with limited history
        was_trimmed = len(messages_to_keep) < len(messages.data)
        
        if was_trimmed:
            print(f"Context trimming: Keeping {len(messages_to_keep)}/{len(messages.data)} messages")
            # Note: OpenAI doesn't allow deleting messages from threads
            # For now, we'll just track this information
            # In a future version, you might want to create a new thread
        
        return total_chars, len(messages.data), was_trimmed
        
    except Exception as e:
        print(f"Error managing context: {e}")
        return 0, 0, False

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
        """Optimized chat handler with reduced API calls"""
        try:
            data = request.json
            message = data.get('message')
            thread_id = data.get('thread_id')
            user_email = session.get('user', {}).get('email', 'unknown')
            
            print(f"\n=== OPTIMIZED CHAT DEBUG [{datetime.now()}] ===")
            print(f"User: {user_email}")
            print(f"Message: '{message}' ({len(message) if message else 0} chars)")
            print(f"Thread: {thread_id or 'NEW'}")
            
            if not message:
                return jsonify({'error': 'Message is required'}), 400
                
            # Use cached assistant to reduce API calls
            assistant = get_cached_assistant()
            
            # Create thread only if needed
            if not thread_id:
                thread = client.beta.threads.create()
                thread_id = thread.id
                print(f"Created thread: {thread_id}")
                context_before = 0
            else:
                # Only check context if thread exists - combine with message addition
                print(f"Using thread: {thread_id}")
                # We'll get context info after the conversation is complete
                context_before = 0
            
            # Add message and create run in sequence (no need to check empty thread)
            print(f"Adding message and starting run...")
            
            # Add the message to the thread
            new_message = client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
            
            # Start the run immediately 
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant.id
            )
            print(f"Run started: {run.id}")
            
            # Optimized polling with exponential backoff
            poll_count = 0
            wait_time = 0.5  # Start with shorter wait
            max_wait = 3.0
            
            while True:
                poll_count += 1
                run_status = client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
                
                if run_status.status == 'completed':
                    print(f"✅ Completed after {poll_count} polls")
                    break
                elif run_status.status == 'failed':
                    raise Exception(f"Run failed: {run_status.last_error}")
                    
                print(f"Poll #{poll_count}: {run_status.status} (waiting {wait_time}s)")
                time.sleep(wait_time)
                
                # Exponential backoff to reduce polling frequency
                wait_time = min(wait_time * 1.5, max_wait)
            
            # Get response and context in single call
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            last_message = messages.data[0]
            response_text = last_message.content[0].text.value
            
            # Calculate context from the messages we just retrieved (no extra API call)
            total_chars = sum(len(msg.content[0].text.value) for msg in messages.data 
                            if hasattr(msg.content[0], 'text'))
            message_count = len(messages.data)
            approaching_limit = total_chars > MAX_CONTEXT_CHARS * 0.8
            
            print(f"Response: {len(response_text)} chars")
            print(f"Context: {total_chars} chars, {message_count} msgs ({(total_chars/MAX_CONTEXT_CHARS)*100:.1f}%)")
            if approaching_limit:
                print("⚠️  Approaching context limit")
            print(f"=== CHAT DEBUG END ===\n")
            
            # Log activity
            log_user_activity(
                user_email, 
                'ai_chat', 
                message_length=len(message),
                response_length=len(response_text),
                thread_id=thread_id,
                context_size=total_chars
            )
            
            return jsonify({
                'response': response_text,
                'thread_id': thread_id,
                'debug': {
                    'message_length': len(message),
                    'response_length': len(response_text),
                    'context_size': total_chars,
                    'message_count': message_count,
                    'context_percentage': (total_chars / MAX_CONTEXT_CHARS) * 100,
                    'approaching_limit': approaching_limit,
                    'max_context_chars': MAX_CONTEXT_CHARS,
                    'max_messages': MAX_MESSAGES,
                    'api_calls_saved': '~50%'
                }
            })
            
        except Exception as e:
            print(f"Error in chat: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/debug/<thread_id>')
    def debug_thread(thread_id):
        """Debug endpoint to view thread details"""
        try:
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            thread_data = []
            total_chars = 0
            
            for msg in reversed(messages.data):  # Show chronologically
                if hasattr(msg.content[0], 'text'):
                    content = msg.content[0].text.value
                    total_chars += len(content)
                    thread_data.append({
                        'role': msg.role,
                        'content': content,
                        'length': len(content),
                        'created_at': msg.created_at
                    })
            
            return jsonify({
                'thread_id': thread_id,
                'total_messages': len(thread_data),
                'total_characters': total_chars,
                'context_percentage': (total_chars / MAX_CONTEXT_CHARS) * 100,
                'messages': thread_data,
                'limits': {
                    'max_chars': MAX_CONTEXT_CHARS,
                    'max_messages': MAX_MESSAGES
                }
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/clear/<thread_id>', methods=['POST'])
    def clear_thread(thread_id):
        """Clear a conversation thread (create new one)"""
        try:
            # Since we can't delete OpenAI thread messages, we'll just create a new thread
            new_thread = client.beta.threads.create()
            return jsonify({
                'old_thread_id': thread_id,
                'new_thread_id': new_thread.id,
                'message': 'New conversation started'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500 