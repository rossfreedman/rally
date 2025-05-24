from flask import jsonify, request, session, render_template
from datetime import datetime
import os
import json
import time
from utils.logging import log_user_activity
from utils.ai import get_or_create_assistant, client

# Ultra-optimized context management settings for speed
MAX_CONTEXT_CHARS = 4000  # Reduced from 6000 for faster processing
MAX_MESSAGES = 10  # Reduced from 15 for speed
CONTEXT_TRIM_THRESHOLD = 0.6  # Trim when 60% full for proactive optimization
SUMMARY_TRIGGER_MSGS = 6  # Summarize even earlier

# Enhanced assistant caching
_cached_assistant = None
_assistant_cache_time = None
ASSISTANT_CACHE_DURATION = 3600  # 1 hour

# Context summaries cache to avoid re-summarizing
_context_summaries = {}  # {thread_id: summary}

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

def clear_assistant_cache():
    """Clear the cached assistant to force reload with new instructions"""
    global _cached_assistant, _assistant_cache_time
    _cached_assistant = None
    _assistant_cache_time = None
    print("Assistant cache cleared")

def compress_message_content(content, max_length=150):
    """Compress message content while preserving key information"""
    if len(content) <= max_length:
        return content
    
    # Keep important keywords and truncate rest
    important_keywords = ['serve', 'volley', 'paddle', 'strategy', 'technique', 'coach', 'improvement']
    words = content.split()
    
    # Build compressed version prioritizing important terms
    compressed = []
    char_count = 0
    
    for word in words:
        if char_count + len(word) + 1 > max_length:
            break
        if any(keyword in word.lower() for keyword in important_keywords) or len(compressed) < 10:
            compressed.append(word)
            char_count += len(word) + 1
    
    result = ' '.join(compressed)
    if len(result) < len(content):
        result += "..."
    
    return result

def create_context_summary(messages, thread_id):
    """Create a concise summary of older conversation context"""
    if thread_id in _context_summaries and len(messages) <= SUMMARY_TRIGGER_MSGS:
        return _context_summaries[thread_id]
    
    # Extract key topics and advice from older messages
    user_topics = []
    key_advice = []
    
    for msg in messages[5:]:  # Skip recent 5 messages
        content = msg.content[0].text.value if hasattr(msg.content[0], 'text') else ""
        
        if msg.role == "user":
            # Extract user topics/questions
            compressed = compress_message_content(content, 50)
            if compressed:
                user_topics.append(compressed)
        else:
            # Extract key advice points
            if any(keyword in content.lower() for keyword in ['improve', 'practice', 'technique', 'tip']):
                compressed = compress_message_content(content, 100)
                if compressed:
                    key_advice.append(compressed)
    
    # Create concise summary
    summary_parts = []
    if user_topics:
        summary_parts.append(f"Previous topics: {', '.join(user_topics[:3])}")
    if key_advice:
        summary_parts.append(f"Key advice given: {'; '.join(key_advice[:2])}")
    
    summary = " | ".join(summary_parts) if summary_parts else "Previous general paddle tennis discussion"
    
    # Cache the summary
    _context_summaries[thread_id] = summary
    return summary

def optimize_thread_context(thread_id):
    """
    Intelligent context management that preserves important info while reducing tokens
    Returns: (context_size, message_count, was_optimized, summary)
    """
    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=50)
        messages_list = list(messages.data)
        
        if not messages_list:
            return 0, 0, False, ""
        
        # Calculate current context size
        total_chars = sum(len(msg.content[0].text.value) for msg in messages_list 
                         if hasattr(msg.content[0], 'text'))
        
        # Check if optimization is needed
        should_optimize = (
            len(messages_list) > SUMMARY_TRIGGER_MSGS or 
            total_chars > MAX_CONTEXT_CHARS * CONTEXT_TRIM_THRESHOLD
        )
        
        if not should_optimize:
            return total_chars, len(messages_list), False, ""
        
        print(f"🔧 Optimizing context: {len(messages_list)} msgs, {total_chars} chars")
        
        # Create summary of older context
        context_summary = create_context_summary(messages_list, thread_id)
        
        # Calculate how many recent messages to keep
        recent_chars = 0
        messages_to_keep = []
        
        # Always keep the most recent conversation (last 6 messages minimum)
        for msg in messages_list[:8]:
            msg_chars = len(msg.content[0].text.value) if hasattr(msg.content[0], 'text') else 0
            if recent_chars + msg_chars > MAX_CONTEXT_CHARS * 0.6:  # Keep 60% for recent
                break
            recent_chars += msg_chars
            messages_to_keep.append(msg)
        
        optimized_chars = len(context_summary) + recent_chars
        was_optimized = len(messages_to_keep) < len(messages_list)
        
        if was_optimized:
            print(f"✨ Context optimized: {len(messages_list)}→{len(messages_to_keep)} msgs, {total_chars}→{optimized_chars} chars")
        
        return optimized_chars, len(messages_to_keep), was_optimized, context_summary
        
    except Exception as e:
        print(f"Error optimizing context: {e}")
        return 0, 0, False, ""

def create_optimized_thread_with_context(original_thread_id, context_summary, recent_messages):
    """Create a new thread with optimized context"""
    try:
        # Create new thread
        new_thread = client.beta.threads.create()
        
        # Add context summary as first message if we have one
        if context_summary:
            client.beta.threads.messages.create(
                thread_id=new_thread.id,
                role="assistant",
                content=f"[Previous conversation context: {context_summary}]"
            )
        
        # Add recent messages to maintain conversation flow
        for msg in reversed(recent_messages[1:]):  # Skip the very latest (will be added separately)
            if hasattr(msg.content[0], 'text'):
                client.beta.threads.messages.create(
                    thread_id=new_thread.id,
                    role=msg.role,
                    content=msg.content[0].text.value
                )
        
        print(f"📝 Created optimized thread: {new_thread.id}")
        return new_thread.id
        
    except Exception as e:
        print(f"Error creating optimized thread: {e}")
        return original_thread_id  # Fallback to original

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
        """Highly optimized chat handler with smart context management"""
        try:
            data = request.json
            message = data.get('message')
            thread_id = data.get('thread_id')
            user_email = session.get('user', {}).get('email', 'unknown')
            
            print(f"\n=== OPTIMIZED CHAT v2.0 [{datetime.now().strftime('%H:%M:%S')}] ===")
            print(f"User: {user_email}")
            print(f"Message: '{message[:50]}...' ({len(message)} chars)")
            print(f"Thread: {thread_id or 'NEW'}")
            
            if not message:
                return jsonify({'error': 'Message is required'}), 400
            
            # Get cached assistant
            assistant = get_cached_assistant()
            
            # Handle thread creation or optimization
            context_summary = ""
            if not thread_id:
                # Create new thread
                thread = client.beta.threads.create()
                thread_id = thread.id
                print(f"🆕 Created thread: {thread_id}")
                context_chars = 0
                message_count = 0
                was_optimized = False
            else:
                # Check if existing thread needs optimization
                context_chars, message_count, was_optimized, context_summary = optimize_thread_context(thread_id)
                
                # If context is too large, create optimized thread
                if was_optimized and context_chars > MAX_CONTEXT_CHARS:
                    messages = client.beta.threads.messages.list(thread_id=thread_id, limit=8)
                    new_thread_id = create_optimized_thread_with_context(
                        thread_id, context_summary, list(messages.data)
                    )
                    thread_id = new_thread_id
                    print(f"🔄 Switched to optimized thread: {thread_id}")
            
            # Add user message
            start_time = time.time()
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
            
            # Start run with optimized assistant
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant.id
            )
            
            # Ultra-efficient polling with aggressive optimization
            poll_count = 0
            wait_time = 0.1  # Start much faster
            max_wait = 1.0   # Much lower max wait
            timeout = 20     # Reduced timeout for faster failure detection
            
            while time.time() - start_time < timeout:
                poll_count += 1
                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                
                if run_status.status == 'completed':
                    break
                elif run_status.status in ['failed', 'cancelled', 'expired']:
                    raise Exception(f"Run {run_status.status}: {getattr(run_status, 'last_error', 'Unknown error')}")
                
                # Aggressive polling for first few attempts, then back off
                if poll_count <= 3:
                    time.sleep(0.1)  # Very fast initial polling
                elif poll_count <= 6:
                    time.sleep(0.3)  # Medium polling
                else:
                    time.sleep(min(wait_time * 1.1, max_wait))  # Gradual backoff
                    wait_time = min(wait_time * 1.1, max_wait)
            
            if run_status.status != 'completed':
                raise Exception(f"Request timed out after {timeout}s")
            
            # Get response efficiently
            messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
            response_text = messages.data[0].content[0].text.value
            
            processing_time = time.time() - start_time
            
            # Calculate final stats
            final_context_chars = context_chars + len(message) + len(response_text)
            final_message_count = message_count + 2
            
            print(f"✅ Response: {len(response_text)} chars in {processing_time:.1f}s ({poll_count} polls)")
            print(f"📊 Context: {final_context_chars} chars, {final_message_count} msgs")
            if was_optimized:
                print(f"🎯 Optimization saved ~{max(0, context_chars - MAX_CONTEXT_CHARS)} chars")
            print(f"=== CHAT COMPLETE ===\n")
            
            # Log with optimization info
            log_user_activity(
                user_email, 
                'ai_chat', 
                message_length=len(message),
                response_length=len(response_text),
                thread_id=thread_id,
                context_size=final_context_chars,
                was_optimized=was_optimized,
                processing_time=processing_time
            )
            
            return jsonify({
                'response': response_text,
                'thread_id': thread_id,
                'debug': {
                    'message_length': len(message),
                    'response_length': len(response_text),
                    'context_size': final_context_chars,
                    'message_count': final_message_count,
                    'context_percentage': (final_context_chars / MAX_CONTEXT_CHARS) * 100,
                    'was_optimized': was_optimized,
                    'processing_time': f"{processing_time:.1f}s",
                    'polls_required': poll_count,
                    'efficiency_rating': 'Excellent' if processing_time < 3 else 'Good' if processing_time < 6 else 'Fair',
                    'token_savings': f"~{max(0, (8000 - MAX_CONTEXT_CHARS) / 8000 * 100):.0f}%" if was_optimized else "0%"
                }
            })
            
        except Exception as e:
            print(f"❌ Chat error: {str(e)}")
            return jsonify({'error': f'Chat processing failed: {str(e)}'}), 500

    @app.route('/api/chat/debug/<thread_id>')
    def debug_thread(thread_id):
        """Enhanced debug info with optimization details"""
        try:
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            context_chars, message_count, was_optimized, summary = optimize_thread_context(thread_id)
            
            return jsonify({
                'thread_id': thread_id,
                'message_count': len(messages.data),
                'context_size': context_chars,
                'optimization_candidate': context_chars > MAX_CONTEXT_CHARS * CONTEXT_TRIM_THRESHOLD,
                'context_summary': summary if summary else "No summary available",
                'efficiency_score': min(100, (MAX_CONTEXT_CHARS / max(context_chars, 1)) * 100),
                'messages': [
                    {
                        'role': msg.role,
                        'content': msg.content[0].text.value[:100] + "..." if len(msg.content[0].text.value) > 100 else msg.content[0].text.value,
                        'length': len(msg.content[0].text.value),
                        'timestamp': msg.created_at
                    }
                    for msg in messages.data
                ]
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/clear/<thread_id>', methods=['POST'])
    def clear_thread(thread_id):
        """Clear thread and its cached summary"""
        try:
            # Clear from summary cache
            if thread_id in _context_summaries:
                del _context_summaries[thread_id]
            
            # Note: OpenAI doesn't allow deleting threads, so we just clear our cache
            return jsonify({'message': 'Thread cache cleared', 'thread_id': thread_id})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/optimize/<thread_id>', methods=['POST'])
    def manually_optimize_thread(thread_id):
        """Manually trigger thread optimization"""
        try:
            context_chars, message_count, was_optimized, summary = optimize_thread_context(thread_id)
            
            if context_chars > MAX_CONTEXT_CHARS * 0.5:  # If context is substantial
                messages = client.beta.threads.messages.list(thread_id=thread_id, limit=8)
                new_thread_id = create_optimized_thread_with_context(
                    thread_id, summary, list(messages.data)
                )
                
                return jsonify({
                    'message': 'Thread optimized successfully',
                    'old_thread_id': thread_id,
                    'new_thread_id': new_thread_id,
                    'original_size': context_chars,
                    'summary': summary
                })
            else:
                return jsonify({
                    'message': 'Thread does not need optimization',
                    'thread_id': thread_id,
                    'context_size': context_chars
                })
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat/clear-cache', methods=['POST'])
    def clear_cache():
        """Clear assistant cache to force reload with new instructions"""
        try:
            clear_assistant_cache()
            return jsonify({'message': 'Assistant cache cleared successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500 