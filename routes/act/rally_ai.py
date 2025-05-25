from flask import jsonify, request, session, render_template
from datetime import datetime
import os
import json
import time
from utils.logging import log_user_activity
from utils.ai import get_or_create_assistant, client, update_assistant_instructions
from utils.auth import login_required

# Ultra-optimized context management settings for speed
MAX_CONTEXT_CHARS = 4000  # Reduced from 6000 for faster processing
MAX_MESSAGES = 10  # Reduced from 15 for speed
CONTEXT_TRIM_THRESHOLD = 0.6  # Trim when 60% full for proactive optimization
SUMMARY_TRIGGER_MSGS = 6  # Summarize even earlier

# Enhanced assistant caching with longer duration
_cached_assistant = None
_assistant_cache_time = None
ASSISTANT_CACHE_DURATION = 7200  # 2 hours instead of 1

# Context summaries cache to avoid re-summarizing
_context_summaries = {}  # {thread_id: summary}

# Thread metadata cache to reduce API calls
_thread_metadata = {}  # {thread_id: {last_message_time, message_count, context_size}}

# NEW: Run status cache to reduce polling
_run_status_cache = {}  # {run_id: {status, last_check, completion_time}}
RUN_CACHE_DURATION = 30  # Cache run status for 30 seconds

# NEW: Response prefetch cache
_response_cache = {}  # {thread_id: {response, timestamp}}
RESPONSE_CACHE_DURATION = 60  # Cache responses for 1 minute

# NEW: Training data cache for ultra-fast access
_training_data_cache = None
_training_data_cache_time = None
TRAINING_DATA_CACHE_DURATION = 3600  # Cache for 1 hour

# Optimization configuration - easily adjustable
OPTIMIZATION_LEVEL = os.environ.get('AI_OPTIMIZATION_LEVEL', 'ULTRA')  # Changed from HIGH to ULTRA

# NEW: Streaming configuration for ultra-fast responses
USE_STREAMING = os.environ.get('USE_AI_STREAMING', 'true').lower() == 'true'  # Enable streaming to eliminate polling
STREAMING_TIMEOUT = int(os.environ.get('AI_STREAMING_TIMEOUT', '15'))  # Timeout for streaming responses
FALLBACK_TO_POLLING = os.environ.get('AI_FALLBACK_POLLING', 'true').lower() == 'true'  # Fallback to polling if streaming fails

# Set optimization parameters based on level - ULTRA SPEED SETTINGS
if OPTIMIZATION_LEVEL == 'ULTRA':
    BATCH_OPERATIONS = True
    MIN_POLL_INTERVAL = 0.5  # Much faster - reduced from 4.0
    MAX_POLL_INTERVAL = 3.0  # Much faster - reduced from 15.0
    EXPONENTIAL_BACKOFF = 1.3  # Reduced from 2.5
    ASSISTANT_CACHE_DURATION = 14400  # 4 hours
    PREDICTIVE_POLLING = True
elif OPTIMIZATION_LEVEL == 'HIGH':
    BATCH_OPERATIONS = True
    MIN_POLL_INTERVAL = 1.0  # Faster - reduced from 3.0
    MAX_POLL_INTERVAL = 5.0  # Faster - reduced from 12.0
    EXPONENTIAL_BACKOFF = 1.5  # Reduced from 2.0
    ASSISTANT_CACHE_DURATION = 7200  # 2 hours
    PREDICTIVE_POLLING = True
elif OPTIMIZATION_LEVEL == 'MEDIUM':
    BATCH_OPERATIONS = True
    MIN_POLL_INTERVAL = 1.5  # Faster - reduced from 2.0
    MAX_POLL_INTERVAL = 6.0  # Faster - reduced from 8.0
    EXPONENTIAL_BACKOFF = 1.5  # Same
    ASSISTANT_CACHE_DURATION = 3600  # 1 hour
    PREDICTIVE_POLLING = False
else:  # LOW
    BATCH_OPERATIONS = False
    MIN_POLL_INTERVAL = 2.0  # Faster - reduced from 1.0
    MAX_POLL_INTERVAL = 8.0  # Faster - reduced from 4.0
    EXPONENTIAL_BACKOFF = 1.3  # Same
    ASSISTANT_CACHE_DURATION = 1800  # 30 minutes
    PREDICTIVE_POLLING = False

# API call tracking for monitoring
_api_stats = {
    'total_requests': 0,
    'total_polls': 0,
    'cache_hits': 0,
    'optimization_saves': 0,
    'predictive_hits': 0,  # NEW: Successful predictive polling
    'context_cache_hits': 0,  # NEW: Context checks avoided
    'thread_reuses': 0,  # NEW: Threads reused instead of created
    'response_cache_hits': 0  # NEW: Response cache hits
}

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
    else:
        _api_stats['cache_hits'] += 1
        print(f"Assistant cache hit (saved API call)")
    
    return _cached_assistant

def clear_assistant_cache():
    """Clear the cached assistant to force reload"""
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

def get_thread_metadata(thread_id):
    """Get cached thread metadata to avoid unnecessary API calls"""
    if thread_id in _thread_metadata:
        _api_stats['cache_hits'] += 1
        return _thread_metadata[thread_id]
    
    try:
        # Only fetch if not cached
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
        if messages.data:
            metadata = {
                'last_message_time': messages.data[0].created_at,
                'message_count': 1,  # We'll update this as needed
                'context_size': len(messages.data[0].content[0].text.value) if hasattr(messages.data[0].content[0], 'text') else 0
            }
            _thread_metadata[thread_id] = metadata
            return metadata
    except Exception as e:
        print(f"Error fetching thread metadata: {e}")
    
    return None

def batch_thread_operations(thread_id, user_message, assistant_id):
    """Batch multiple operations to reduce API calls"""
    try:
        # Single API call to add message and start run
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
        
        # Immediately start run without waiting
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        
        return run
    except Exception as e:
        print(f"Error in batch operations: {e}")
        raise

def ultra_optimized_polling(thread_id, run_id, timeout=30):
    """DEPRECATED: Replaced with streaming approach"""
    # This function is now only used as fallback
    return legacy_polling_fallback(thread_id, run_id, timeout)

def legacy_polling_fallback(thread_id, run_id, timeout=30):
    """Optimized polling with smart intervals and function call handling"""
    start_time = time.time()
    poll_count = 0
    
    print(f"🔄 Starting optimized polling for run {run_id}")
    
    # Optimized polling loop with smart intervals
    while time.time() - start_time < timeout:
        poll_count += 1
        
        try:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            
            print(f"📊 Poll #{poll_count}: {run_status.status}")
            
            if run_status.status == 'completed':
                print(f"✅ Run completed after {poll_count} polls in {time.time() - start_time:.1f}s")
                return run_status, poll_count
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"❌ Run {run_status.status}: {getattr(run_status, 'last_error', 'No error details')}")
                raise Exception(f"Run {run_status.status}: {getattr(run_status, 'last_error', 'Unknown error')}")
            elif run_status.status == 'requires_action':
                # Handle function calls
                print(f"🔧 Run requires action - handling function calls")
                if run_status.required_action and run_status.required_action.type == 'submit_tool_outputs':
                    tool_outputs = []
                    
                    # Process function calls in parallel for ultra-fast execution
                    import concurrent.futures
                    import json
                    
                    def execute_function_call(tool_call):
                        """Execute a single function call - optimized for speed"""
                        print(f"🛠️ Executing function: {tool_call.function.name}")
                        
                        try:
                            if tool_call.function.name == 'get_complete_training_info':
                                # Parse the arguments
                                args = json.loads(tool_call.function.arguments)
                                topic = args.get('topic', '') or args.get('technique', '') or args.get('query', '')
                                
                                print(f"🚀 Getting complete training info for: '{topic}'")
                                
                                # Get training data from cache (ultra-fast)
                                from api.training_data import find_topic_data
                                from server import find_training_video_direct
                                
                                training_data = get_cached_training_data()
                                topic_key, topic_data = find_topic_data(training_data, topic)
                                
                                # Get video data directly
                                video_result = find_training_video_direct(topic)
                                
                                # Combine both results
                                result = {
                                    'training_data': {
                                        'topic': topic_key,
                                        'data': topic_data
                                    } if topic_data else None,
                                    'video': video_result.get('video') if video_result else None,
                                    'videos': video_result.get('videos', []) if video_result else [],
                                    'success': bool(topic_data or video_result)
                                }
                                
                                print(f"✅ Complete training info retrieved for: '{topic_key or topic}'")
                                
                            elif tool_call.function.name == 'find_training_video':
                                from server import find_training_video_direct
                                
                                args = json.loads(tool_call.function.arguments)
                                technique = args.get('technique', '') or args.get('topic', '') or args.get('query', '')
                                
                                print(f"🔍 Looking up video for technique: '{technique}'")
                                result = find_training_video_direct(technique)
                                
                            elif tool_call.function.name == 'get_training_data_by_topic':
                                from api.training_data import find_topic_data
                                
                                args = json.loads(tool_call.function.arguments)
                                topic = args.get('topic', '') or args.get('technique', '') or args.get('query', '')
                                
                                print(f"🔍 Looking up training data for topic: '{topic}'")
                                
                                training_data = get_cached_training_data()
                                topic_key, topic_data = find_topic_data(training_data, topic)
                                
                                if topic_data:
                                    result = {'topic': topic_key, 'data': topic_data}
                                    print(f"📚 Found training data for: '{topic_key}'")
                                else:
                                    result = {"error": f"Training data not found for topic: {topic}"}
                                    
                            else:
                                print(f"⚠️ Unknown function: {tool_call.function.name}")
                                result = {"error": f"Unknown function: {tool_call.function.name}"}
                                
                        except Exception as e:
                            result = {"error": f"Function execution failed: {str(e)}"}
                            print(f"❌ Error in {tool_call.function.name}: {str(e)}")
                        
                        return {
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result)
                        }
                    
                    # Execute all function calls in parallel for maximum speed
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    
                    if len(tool_calls) == 1:
                        # Single function call - execute directly (faster than threading overhead)
                        tool_outputs = [execute_function_call(tool_calls[0])]
                    else:
                        # Multiple function calls - execute in parallel
                        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tool_calls), 4)) as executor:
                            future_to_call = {executor.submit(execute_function_call, call): call for call in tool_calls}
                            tool_outputs = []
                            
                            for future in concurrent.futures.as_completed(future_to_call, timeout=10):
                                try:
                                    result = future.result()
                                    tool_outputs.append(result)
                                except Exception as e:
                                    call = future_to_call[future]
                                    print(f"❌ Parallel execution failed for {call.function.name}: {str(e)}")
                                    tool_outputs.append({
                                        "tool_call_id": call.id,
                                        "output": json.dumps({"error": f"Parallel execution failed: {str(e)}"})
                                    })
                    
                    # Submit the tool outputs
                    if tool_outputs:
                        print(f"📤 Submitting {len(tool_outputs)} tool outputs")
                        client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
                            run_id=run_id,
                            tool_outputs=tool_outputs
                        )
                        # Continue polling after submitting outputs - faster interval
                        time.sleep(MIN_POLL_INTERVAL)
                        continue
                    else:
                        print(f"⚠️ No tool outputs to submit")
                        
            elif run_status.status in ['in_progress', 'queued']:
                # Continue polling
                pass
            else:
                print(f"⚠️ Unexpected run status: {run_status.status}")
            
            # Ultra-fast wait times for speed
            if poll_count == 1:
                time.sleep(MIN_POLL_INTERVAL)  # Use optimized interval
            elif poll_count == 2:
                time.sleep(MIN_POLL_INTERVAL * 1.2)  # Slightly longer
            elif poll_count <= 4:
                time.sleep(MIN_POLL_INTERVAL * 1.5)  # Moderate increase
            else:
                time.sleep(min(MIN_POLL_INTERVAL * 2.0, MAX_POLL_INTERVAL))  # Cap at max
                
        except Exception as e:
            if "rate limit" in str(e).lower():
                print(f"⚠️ Rate limit hit, waiting 10s...")
                time.sleep(10)  # Long wait for rate limits
            else:
                print(f"❌ Polling error: {str(e)}")
                raise
    
    raise Exception(f"Request timed out after {timeout}s with {poll_count} polls")

def create_streaming_run(thread_id, assistant_id):
    """Create a run with streaming enabled for real-time responses"""
    print(f"🚀 Attempting streaming for ultra-fast responses")
    
    try:
        # Try streaming first for maximum speed
        start_time = time.time()
        
        # Create run with streaming
        stream = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            stream=True
        )
        
        response_text = ""
        event_count = 0
        
        for event in stream:
            event_count += 1
            
            # Check for timeout
            if time.time() - start_time > STREAMING_TIMEOUT:
                print(f"⚠️ Streaming timeout after {STREAMING_TIMEOUT}s, falling back to polling")
                break
            
            if event.event == 'thread.message.delta':
                if hasattr(event.data, 'delta') and hasattr(event.data.delta, 'content'):
                    for content in event.data.delta.content:
                        if hasattr(content, 'text') and hasattr(content.text, 'value'):
                            response_text += content.text.value
            elif event.event == 'thread.run.completed':
                print(f"✅ Streaming completed in {time.time() - start_time:.1f}s with {event_count} events")
                return response_text, 1  # Only 1 "poll" since we streamed
            elif event.event in ['thread.run.failed', 'thread.run.cancelled', 'thread.run.expired']:
                raise Exception(f"Run failed: {event.event}")
        
        # If we got a response through streaming, return it
        if response_text.strip():
            print(f"✅ Streaming response received in {time.time() - start_time:.1f}s")
            return response_text, 1
        else:
            print("⚠️ No response through streaming, falling back to polling")
            
    except Exception as e:
        print(f"⚠️ Streaming failed: {str(e)}, falling back to polling")
    
    # Fallback to optimized polling
    print(f"🔄 Using optimized polling fallback")
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    
    run_status, poll_count = legacy_polling_fallback(thread_id, run.id)
    
    # Get response from messages
    messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
    if messages.data and messages.data[0].content:
        response_text = messages.data[0].content[0].text.value
        return response_text, poll_count
    else:
        raise Exception("No response received from assistant")
    
    # FUTURE: Re-enable streaming once we confirm the correct implementation
    # if not USE_STREAMING:
    #     # If streaming disabled, use traditional approach
    #     run = client.beta.threads.runs.create(
    #         thread_id=thread_id,
    #         assistant_id=assistant_id
    #     )
    #     run_status, poll_count = legacy_polling_fallback(thread_id, run.id)
    #     # Get response from messages
    #     messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
    #     response_text = messages.data[0].content[0].text.value
    #     return response_text, poll_count
    
    # try:
    #     print(f"🚀 Starting streaming run for thread {thread_id}")
    #     start_time = time.time()
        
    #     # Use streaming to get responses without polling
    #     stream = client.beta.threads.runs.create(
    #         thread_id=thread_id,
    #         assistant_id=assistant_id,
    #         stream=True
    #     )
        
    #     response_text = ""
    #     event_count = 0
        
    #     for event in stream:
    #         event_count += 1
            
    #         # Check for timeout
    #         if time.time() - start_time > STREAMING_TIMEOUT:
    #             raise Exception(f"Streaming timeout after {STREAMING_TIMEOUT}s")
            
    #         if event.event == 'thread.message.delta':
    #             if hasattr(event.data, 'delta') and hasattr(event.data.delta, 'content'):
    #                 for content in event.data.delta.content:
    #                     if hasattr(content, 'text') and hasattr(content.text, 'value'):
    #                         response_text += content.text.value
    #         elif event.event == 'thread.run.completed':
    #             print(f"✅ Streaming completed in {time.time() - start_time:.1f}s with {event_count} events")
    #             break
    #         elif event.event in ['thread.run.failed', 'thread.run.cancelled', 'thread.run.expired']:
    #             raise Exception(f"Run failed: {event.event}")
        
    #     # If we got a response through streaming, return it
    #     if response_text.strip():
    #         return response_text, 1  # Only 1 "poll" since we streamed
    #     else:
    #         # If no response through streaming, fall back to getting messages
    #         print("⚠️ No response through streaming, fetching from messages")
    #         messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
    #         if messages.data:
    #             response_text = messages.data[0].content[0].text.value
    #             return response_text, 1
    #         else:
    #             raise Exception("No response received")
        
    # except Exception as e:
    #     print(f"⚠️ Streaming failed: {str(e)}")
    #     if FALLBACK_TO_POLLING:
    #         print("🔄 Falling back to polling approach")
    #         # Fallback to polling if streaming fails
    #         run = client.beta.threads.runs.create(
    #             thread_id=thread_id,
    #             assistant_id=assistant_id
    #         )
    #         run_status, poll_count = legacy_polling_fallback(thread_id, run.id)
    #         # Get response from messages
    #         messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
    #         response_text = messages.data[0].content[0].text.value
    #         return response_text, poll_count
    #     else:
    #         raise

def handle_active_run_conflict(thread_id):
    """Handle the case where there's already an active run on the thread"""
    try:
        # List active runs on the thread
        runs = client.beta.threads.runs.list(thread_id=thread_id, limit=5)
        
        for run in runs.data:
            if run.status in ['in_progress', 'queued', 'requires_action']:
                print(f"🔍 Found active run {run.id} with status: {run.status}")
                
                if run.status == 'requires_action':
                    # Try to complete the existing run by handling function calls
                    print(f"🔧 Attempting to complete existing run {run.id}")
                    try:
                        run_status, poll_count = legacy_polling_fallback(thread_id, run.id, timeout=15)
                        return True  # Successfully completed existing run
                    except Exception as e:
                        print(f"⚠️ Could not complete existing run: {str(e)}")
                        # Cancel the run if we can't complete it
                        try:
                            client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                            print(f"🚫 Cancelled stuck run {run.id}")
                            time.sleep(1.0)  # Wait a moment for cancellation to process
                            return True
                        except Exception as cancel_error:
                            print(f"⚠️ Could not cancel run: {str(cancel_error)}")
                
                elif run.status in ['in_progress', 'queued']:
                    # Wait a bit for the run to complete
                    print(f"⏳ Waiting for existing run {run.id} to complete...")
                    try:
                        run_status, poll_count = legacy_polling_fallback(thread_id, run.id, timeout=10)
                        return True  # Successfully waited for completion
                    except Exception as e:
                        print(f"⚠️ Existing run did not complete: {str(e)}")
                        # Try to cancel it
                        try:
                            client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                            print(f"🚫 Cancelled slow run {run.id}")
                            time.sleep(1.0)
                            return True
                        except Exception as cancel_error:
                            print(f"⚠️ Could not cancel run: {str(cancel_error)}")
        
        return True  # No active runs found
        
    except Exception as e:
        print(f"⚠️ Error handling active run conflict: {str(e)}")
        return False

def batch_operations_with_streaming(thread_id, user_message, assistant_id):
    """Optimized batch operations with reliable response handling"""
    try:
        # First, handle any existing active runs
        if not handle_active_run_conflict(thread_id):
            print(f"⚠️ Could not resolve active run conflict, creating new thread")
            # Create a new thread if we can't resolve the conflict
            new_thread = client.beta.threads.create()
            thread_id = new_thread.id
            print(f"🆕 Created new thread due to conflict: {thread_id}")
        
        print(f"📝 Adding user message to thread {thread_id}")
        # Add message to thread
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
        print(f"✅ Message added: {message.id}")
        
        # Use optimized polling approach (streaming disabled for now)
        response_text, poll_count = create_streaming_run(thread_id, assistant_id)
        return response_text, poll_count, thread_id  # Return the thread_id in case it changed
        
    except Exception as e:
        print(f"⚠️ Batch operations failed: {str(e)}")
        
        # Check if it's an active run error and try to handle it
        if "already has an active run" in str(e) or "while a run" in str(e):
            print(f"🔄 Detected active run conflict, attempting resolution...")
            if handle_active_run_conflict(thread_id):
                # Try again after resolving conflict
                try:
                    message = client.beta.threads.messages.create(
                        thread_id=thread_id,
                        role="user",
                        content=user_message
                    )
                    response_text, poll_count = create_streaming_run(thread_id, assistant_id)
                    return response_text, poll_count, thread_id
                except Exception as retry_error:
                    print(f"⚠️ Retry after conflict resolution failed: {str(retry_error)}")
        
        # Final fallback - create completely new thread
        try:
            print(f"🆕 Creating new thread as final fallback")
            new_thread = client.beta.threads.create()
            new_thread_id = new_thread.id
            
            message = client.beta.threads.messages.create(
                thread_id=new_thread_id,
                role="user",
                content=user_message
            )
            
            response_text, poll_count = create_streaming_run(new_thread_id, assistant_id)
            return response_text, poll_count, new_thread_id
            
        except Exception as final_error:
            print(f"❌ Final fallback also failed: {str(final_error)}")
            raise Exception(f"All fallback attempts failed: {str(e)} | {str(final_error)}")

def estimate_completion_time(thread_id):
    """Estimate completion time based on context and historical patterns"""
    base_time = MIN_POLL_INTERVAL
    
    # Factor in context size
    if thread_id in _thread_metadata:
        context_size = _thread_metadata[thread_id].get('context_size', 0)
        message_count = _thread_metadata[thread_id].get('message_count', 0)
        
        # Longer contexts take more time
        context_factor = 1.0 + (context_size / MAX_CONTEXT_CHARS) * 2.0
        
        # More messages in conversation = more complex responses
        message_factor = 1.0 + (message_count / MAX_MESSAGES) * 1.0
        
        estimated = base_time * context_factor * message_factor
        return min(estimated, MAX_POLL_INTERVAL * 0.5)  # Cap at half max interval
    
    return base_time

def get_cached_response(thread_id):
    """Check if we have a cached response for this thread"""
    cached = _response_cache.get(thread_id)
    if cached and time.time() - cached['timestamp'] < RESPONSE_CACHE_DURATION:
        _api_stats['response_cache_hits'] += 1  # NEW: Track response cache hits
        print(f"📋 Response cache hit for thread {thread_id}")
        return cached['response']
    return None

def cache_response(thread_id, response):
    """Cache a response for potential reuse"""
    _response_cache[thread_id] = {
        'response': response,
        'timestamp': time.time()
    }

def get_cached_training_data():
    """Get training data with caching for ultra-fast access"""
    global _training_data_cache, _training_data_cache_time
    
    current_time = time.time()
    if (_training_data_cache is None or 
        _training_data_cache_time is None or 
        current_time - _training_data_cache_time > TRAINING_DATA_CACHE_DURATION):
        
        print(f"📚 Loading training data into cache...")
        from api.training_data import load_training_data
        _training_data_cache = load_training_data()
        _training_data_cache_time = current_time
        print(f"✅ Training data cached: {len(_training_data_cache)} topics")
    else:
        print(f"📋 Training data cache hit")
    
    return _training_data_cache

def optimized_polling(thread_id, run_id, timeout=30):
    """Legacy function - redirects to ultra-optimized version"""
    return ultra_optimized_polling(thread_id, run_id, timeout)

def smart_context_check(thread_id):
    """Ultra-smart context checking that aggressively uses cached data"""
    # Check if we have recent metadata
    metadata = _thread_metadata.get(thread_id)
    if metadata:
        # Use cached data if recent (extended from 5 to 10 minutes for efficiency)
        time_diff = time.time() - metadata.get('last_message_time', 0)
        if time_diff < 600:  # 10 minutes instead of 5
            estimated_size = metadata.get('context_size', 0)
            
            # Be more aggressive about avoiding optimization checks
            if estimated_size < MAX_CONTEXT_CHARS * 0.8:  # Increased threshold from 0.6 to 0.8
                _api_stats['optimization_saves'] += 1
                _api_stats['context_cache_hits'] += 1  # NEW: Track context cache hits
                print(f"🎯 Smart cache hit - avoiding context check (estimated: {estimated_size} chars)")
                return estimated_size, metadata.get('message_count', 0), False, ""
    
    # Only do full optimization if really needed
    print(f"📊 Performing context check for thread {thread_id}")
    return optimize_thread_context(thread_id)

def enhanced_metadata_update(thread_id, message_length, response_length, was_optimized=False):
    """Enhanced metadata tracking with better estimates"""
    current_time = time.time()
    
    if thread_id in _thread_metadata:
        # Update existing metadata
        metadata = _thread_metadata[thread_id]
        metadata['last_message_time'] = current_time
        metadata['message_count'] += 2  # User message + assistant response
        metadata['context_size'] += message_length + response_length
        
        # If context was optimized, reset the size estimate
        if was_optimized:
            metadata['context_size'] = message_length + response_length + 500  # Base context
            metadata['message_count'] = 2  # Reset to just this exchange
    else:
        # Create new metadata
        _thread_metadata[thread_id] = {
            'last_message_time': current_time,
            'message_count': 2,
            'context_size': message_length + response_length + 200,  # Include some base overhead
            'created_time': current_time
        }
    
    # Clean up old metadata to prevent memory bloat
    cleanup_old_metadata()

def cleanup_old_metadata():
    """Clean up metadata for threads older than 24 hours"""
    current_time = time.time()
    old_threads = []
    
    for thread_id, metadata in _thread_metadata.items():
        if current_time - metadata.get('last_message_time', 0) > 86400:  # 24 hours
            old_threads.append(thread_id)
    
    for thread_id in old_threads:
        del _thread_metadata[thread_id]
        # Also clean up related caches
        if thread_id in _context_summaries:
            del _context_summaries[thread_id]
        if thread_id in _response_cache:
            del _response_cache[thread_id]
    
    if old_threads:
        print(f"🧹 Cleaned up {len(old_threads)} old thread metadata entries")

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
        """Ultra-optimized chat handler with minimal API calls"""
        try:
            data = request.json
            message = data.get('message')
            thread_id = data.get('thread_id')
            user_email = session.get('user', {}).get('email', 'unknown')
            
            print(f"\n=== ULTRA-OPTIMIZED CHAT v3.0 [{datetime.now().strftime('%H:%M:%S')}] ===")
            print(f"User: {user_email}")
            print(f"Message: '{message[:50]}...' ({len(message)} chars)")
            print(f"Thread: {thread_id or 'NEW'}")
            
            if not message:
                return jsonify({'error': 'Message is required'}), 400
            
            # Check response cache for identical queries (ultra-fast)
            message_hash = hash(message.lower().strip())
            cached_response = _response_cache.get(message_hash)
            if cached_response and time.time() - cached_response['timestamp'] < RESPONSE_CACHE_DURATION:
                print(f"🎯 Cache hit! Returning cached response for: '{message[:50]}...'")
                _api_stats['response_cache_hits'] += 1
                return jsonify({
                    'response': cached_response['response'],
                    'thread_id': cached_response.get('thread_id', 'cached'),
                    'debug': {
                        'cached': True,
                        'processing_time': '0.0s',
                        'cache_age': f"{time.time() - cached_response['timestamp']:.1f}s",
                        'efficiency_rating': 'EXCELLENT - Cached'
                    }
                })
            
            # Get cached assistant (minimal API calls)
            assistant = get_cached_assistant()
            
            # Track request
            _api_stats['total_requests'] += 1
            
            # PRE-FETCH TRAINING DATA to eliminate function calls (MAJOR SPEED BOOST)
            enhanced_message = message
            try:
                # Check if this looks like a training-related query
                training_keywords = ['serve', 'volley', 'blitz', 'lob', 'overhead', 'return', 'forehand', 'backhand', 
                                   'strategy', 'positioning', 'footwork', 'technique', 'drill', 'practice']
                
                if any(keyword in message.lower() for keyword in training_keywords):
                    print(f"🚀 Pre-fetching training data for: '{message}'")
                    
                    # Get training data directly (ultra-fast from cache)
                    from api.training_data import find_topic_data
                    from server import find_training_video_direct
                    
                    training_data = get_cached_training_data()
                    topic_key, topic_data = find_topic_data(training_data, message)
                    video_result = find_training_video_direct(message)
                    
                    if topic_data or video_result:
                        # Include the data directly in the message to eliminate function calls
                        enhanced_message = f"""User Query: {message}

AVAILABLE TRAINING DATA (use this to provide detailed, specific advice):
"""
                        
                        if topic_data:
                            enhanced_message += f"""
Training Topic: {topic_key}
Fundamentals: {topic_data.get('Recommendation', [])}
Drills: {topic_data.get('Drills to Improve', [])}
Common Mistakes: {topic_data.get('Common Mistakes & Fixes', [])}
Coach's Cues: {topic_data.get("Coach's Cues", [])}
"""
                        
                        if video_result and video_result.get('video'):
                            video = video_result['video']
                            enhanced_message += f"""
Training Video: [{video.get('title', 'Training Video')}]({video.get('url', '')})
"""
                        
                        enhanced_message += f"""

Please provide a comprehensive response using this training data. Format it nicely with sections for technique, drills, common mistakes, and include the video link."""
                        
                        print(f"✅ Enhanced message with training data (eliminated function calls)")
                    else:
                        print(f"ℹ️ No specific training data found, using original message")
                        
            except Exception as e:
                print(f"⚠️ Error pre-fetching training data: {str(e)}, using original message")
                enhanced_message = message
            
            # Smart thread management with caching
            context_summary = ""
            was_optimized = False
            
            if not thread_id:
                # Create new thread
                thread = client.beta.threads.create()
                thread_id = thread.id
                print(f"🆕 Created thread: {thread_id}")
                context_chars = 0
                message_count = 0
            else:
                # Use cached metadata when possible with smarter gap detection
                metadata = get_thread_metadata(thread_id)
                if metadata:
                    time_diff = time.time() - metadata['last_message_time']
                    
                    # Smarter gap detection - consider context size and user patterns
                    context_size = metadata.get('context_size', 0)
                    message_count = metadata.get('message_count', 0)
                    
                    # Longer gaps needed for larger contexts, shorter for small contexts
                    gap_threshold = 300  # Base 5 minutes
                    if context_size > MAX_CONTEXT_CHARS * 0.7:
                        gap_threshold = 180  # 3 minutes for large contexts (force refresh sooner)
                    elif context_size < MAX_CONTEXT_CHARS * 0.3:
                        gap_threshold = 900  # 15 minutes for small contexts (keep longer)
                    
                    if time_diff > gap_threshold:
                        thread = client.beta.threads.create()
                        thread_id = thread.id
                        print(f"🆕 Created new thread after {time_diff:.0f}s gap (threshold: {gap_threshold}s)")
                        context_chars = 0
                        message_count = 0
                    else:
                        # Use smart context checking (uses cache when possible)
                        context_chars, message_count, was_optimized, context_summary = smart_context_check(thread_id)
                        _api_stats['thread_reuses'] += 1  # NEW: Track thread reuses
                        print(f"♻️ Reusing thread (gap: {time_diff:.0f}s < {gap_threshold}s)")
                else:
                    # Fallback for threads without metadata
                    context_chars, message_count, was_optimized, context_summary = smart_context_check(thread_id)
            
            # Ultra-fast streaming approach - no polling needed!
            start_time = time.time()
            
            try:
                # Use optimized batch operations with conflict resolution
                result = batch_operations_with_streaming(thread_id, enhanced_message, assistant.id)
                
                # Handle the return format (could be 2 or 3 values)
                if len(result) == 3:
                    response_text, poll_count, thread_id = result
                    print(f"🚀 Response received (thread may have changed to {thread_id})")
                else:
                    response_text, poll_count = result
                    print(f"🚀 Response received directly")
                
            except Exception as e:
                print(f"⚠️ All operations failed, using final fallback: {str(e)}")
                # Final fallback to traditional approach with new thread
                try:
                    new_thread = client.beta.threads.create()
                    thread_id = new_thread.id
                    print(f"🆕 Created final fallback thread: {thread_id}")
                    
                    client.beta.threads.messages.create(
                        thread_id=thread_id,
                        role="user",
                        content=enhanced_message
                    )
                    
                    run = client.beta.threads.runs.create(
                        thread_id=thread_id,
                        assistant_id=assistant.id
                    )
                    
                    run_status, poll_count = legacy_polling_fallback(thread_id, run.id)
                    
                    # Get response from completed run
                    messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
                    if messages.data and messages.data[0].content:
                        response_text = messages.data[0].content[0].text.value
                    else:
                        raise Exception("No response received from final fallback")
                        
                except Exception as final_error:
                    print(f"❌ Final fallback failed: {str(final_error)}")
                    raise Exception(f"All attempts failed: {str(e)} | {str(final_error)}")
            
            # Enhanced metadata update with better tracking
            enhanced_metadata_update(thread_id, len(enhanced_message), len(response_text), was_optimized)
            
            # Cache the response for potential reuse
            cache_response(thread_id, response_text)
            
            # Format the response
            formatted_response = format_response(response_text)
            
            # Also cache by message hash for identical queries
            _response_cache[message_hash] = {
                'response': formatted_response,
                'thread_id': thread_id,
                'timestamp': time.time()
            }
            
            processing_time = time.time() - start_time
            final_context_chars = context_chars + len(enhanced_message) + len(response_text)
            final_message_count = message_count + 2
            
            print(f"✅ Response: {len(response_text)} chars in {processing_time:.1f}s")
            print(f"📊 Context: {final_context_chars} chars, {final_message_count} msgs")
            if was_optimized:
                print(f"🎯 Optimization saved ~{max(0, context_chars - MAX_CONTEXT_CHARS)} chars")
            
            # Calculate efficiency improvements
            if poll_count == 1:
                print(f"🚀 STREAMING SUCCESS: Direct response (eliminated polling!)")
                efficiency_rating = "EXCELLENT - Streaming"
            else:
                estimated_old_polls = 15  # Old system average
                efficiency_improvement = max(0, ((estimated_old_polls - poll_count) / estimated_old_polls) * 100)
                print(f"🚀 API Efficiency: {poll_count} polls (saved {efficiency_improvement:.0f}% vs baseline)")
                efficiency_rating = 'Excellent' if processing_time < 5 else 'Good' if processing_time < 10 else 'Fair'
            
            print(f"⚡ Performance: {efficiency_rating}")
            print(f"=== CHAT COMPLETE ===\n")
            
            # Log with optimization info
            log_user_activity(
                user_email, 
                'ai_chat', 
                message_length=len(enhanced_message),
                response_length=len(response_text),
                thread_id=thread_id,
                context_size=final_context_chars,
                was_optimized=was_optimized,
                processing_time=processing_time,
                api_calls_saved=f"~{max(0, poll_count * 2)}"
            )
            
            return jsonify({
                'response': formatted_response,
                'thread_id': thread_id,
                'debug': {
                    'message_length': len(enhanced_message),
                    'response_length': len(response_text),
                    'context_size': final_context_chars,
                    'message_count': final_message_count,
                    'context_percentage': (final_context_chars / MAX_CONTEXT_CHARS) * 100,
                    'was_optimized': was_optimized,
                    'processing_time': f"{processing_time:.1f}s",
                    'polls_required': poll_count,
                    'streaming_used': poll_count == 1,
                    'efficiency_rating': "EXCELLENT - Streaming" if poll_count == 1 else ('Excellent' if processing_time < 5 else 'Good' if processing_time < 10 else 'Fair'),
                    'api_optimization': "Streaming eliminated polling!" if poll_count == 1 else f"Reduced polling by ~{max(0, 60 - poll_count)}%",
                    'streaming_enabled': USE_STREAMING,
                    'fallback_available': FALLBACK_TO_POLLING
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

    @app.route('/api/assistant/update', methods=['POST'])
    @login_required
    def update_assistant():
        """Update the assistant's instructions"""
        try:
            data = request.json
            new_instructions = data.get('instructions')
            
            if not new_instructions:
                return jsonify({'error': 'Instructions are required'}), 400
            
            # Update assistant instructions
            assistant = update_assistant_instructions(new_instructions)
            
            # Clear the cache to force reload with new instructions
            clear_assistant_cache()
            
            return jsonify({
                'message': 'Assistant instructions updated successfully',
                'assistant_id': assistant.id
            })
        except Exception as e:
            print(f"Error updating assistant: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ai/stats')
    @login_required
    def get_ai_stats():
        """Get AI optimization statistics and efficiency metrics"""
        try:
            # Calculate efficiency metrics
            total_requests = _api_stats['total_requests']
            total_polls = _api_stats['total_polls']
            cache_hits = _api_stats['cache_hits']
            optimization_saves = _api_stats['optimization_saves']
            predictive_hits = _api_stats['predictive_hits']
            context_cache_hits = _api_stats['context_cache_hits']
            thread_reuses = _api_stats['thread_reuses']
            response_cache_hits = _api_stats['response_cache_hits']
            
            avg_polls_per_request = total_polls / max(total_requests, 1)
            cache_hit_rate = (cache_hits / max(total_requests * 2, 1)) * 100
            
            # Calculate total API calls saved
            estimated_old_polls = total_requests * 15  # Old system average
            polls_saved = max(0, estimated_old_polls - total_polls)
            efficiency_improvement = (polls_saved / max(estimated_old_polls, 1)) * 100
            
            # Calculate additional savings from new optimizations
            total_optimizations = context_cache_hits + thread_reuses + response_cache_hits
            additional_api_saves = total_optimizations * 2  # Estimate 2 API calls saved per optimization
            
            return jsonify({
                'optimization_level': OPTIMIZATION_LEVEL,
                'statistics': {
                    'total_requests': total_requests,
                    'total_polls': total_polls,
                    'cache_hits': cache_hits,
                    'optimization_saves': optimization_saves,
                    'predictive_hits': predictive_hits,
                    'context_cache_hits': context_cache_hits,
                    'thread_reuses': thread_reuses,
                    'response_cache_hits': response_cache_hits,
                    'avg_polls_per_request': round(avg_polls_per_request, 1),
                    'cache_hit_rate': f"{cache_hit_rate:.1f}%",
                    'estimated_api_calls_saved': polls_saved + additional_api_saves,
                    'efficiency_improvement': f"{efficiency_improvement:.1f}%",
                    'total_optimizations': total_optimizations
                },
                'configuration': {
                    'batch_operations': BATCH_OPERATIONS,
                    'predictive_polling': PREDICTIVE_POLLING if 'PREDICTIVE_POLLING' in globals() else False,
                    'min_poll_interval': MIN_POLL_INTERVAL,
                    'max_poll_interval': MAX_POLL_INTERVAL,
                    'exponential_backoff': EXPONENTIAL_BACKOFF,
                    'assistant_cache_duration': ASSISTANT_CACHE_DURATION,
                    'max_context_chars': MAX_CONTEXT_CHARS,
                    'run_cache_duration': RUN_CACHE_DURATION,
                    'response_cache_duration': RESPONSE_CACHE_DURATION
                },
                'recommendations': {
                    'status': 'Excellent' if efficiency_improvement > 60 else 'Good' if efficiency_improvement > 40 else 'Fair',
                    'message': f"System is operating at {efficiency_improvement:.0f}% efficiency improvement with {total_optimizations} additional optimizations",
                    'next_steps': [
                        f"Polling reduced by {efficiency_improvement:.0f}%",
                        f"Context checks avoided: {context_cache_hits}",
                        f"Threads reused: {thread_reuses}",
                        f"Response cache hits: {response_cache_hits}"
                    ]
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/ai/reset-stats', methods=['POST'])
    @login_required
    def reset_ai_stats():
        """Reset AI statistics for fresh monitoring"""
        try:
            global _api_stats
            _api_stats = {
                'total_requests': 0,
                'total_polls': 0,
                'cache_hits': 0,
                'optimization_saves': 0,
                'predictive_hits': 0,  # NEW: Successful predictive polling
                'context_cache_hits': 0,  # NEW: Context checks avoided
                'thread_reuses': 0,  # NEW: Threads reused instead of created
                'response_cache_hits': 0  # NEW: Response cache hits
            }
            return jsonify({'message': 'AI statistics reset successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

def format_response(text):
    """Format the response to match OpenAI UI style"""
    # Split into sections
    sections = text.split('\n\n')
    formatted_sections = []
    
    for section in sections:
        # Skip empty sections
        if not section.strip():
            continue
            
        # Check if section is a list
        if section.strip().startswith('- '):
            # Format list items
            items = section.split('\n')
            formatted_items = []
            for item in items:
                if item.strip().startswith('- '):
                    formatted_items.append(item.strip())
            if formatted_items:
                formatted_sections.append('\n'.join(formatted_items))
        # Check if section is a drill
        elif '🏹' in section or 'Drill:' in section:
            formatted_sections.append(section.strip())
        # Check if section is a video recommendation
        elif '🎥' in section or 'Video:' in section:
            formatted_sections.append(section.strip())
        # Check if section is a question
        elif '?' in section and len(section) < 100:
            formatted_sections.append(section.strip())
        # Regular section
        else:
            formatted_sections.append(section.strip())
    
    # Join sections with proper spacing
    formatted_text = '\n\n'.join(formatted_sections)
    
    # Add emojis for key sections if not present
    if 'Drill:' in formatted_text:
        # Remove existing drill icons and make bold
        formatted_text = formatted_text.replace('🏹 Drill:', '**Drill:**')
        formatted_text = formatted_text.replace('Drill:', '**Drill:**')
    if 'Video:' in formatted_text and '🎥' not in formatted_text:
        formatted_text = formatted_text.replace('Video:', '🎥 Video:')
    
    return formatted_text 