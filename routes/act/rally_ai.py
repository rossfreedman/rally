import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta

from flask import jsonify, render_template, request, session
from sqlalchemy import desc, func
from sqlalchemy.orm import sessionmaker

from app.models.database_models import (
    Club,
    League,
    MatchScore,
    Player,
    PlayerHistory,
    Series,
    User,
    UserPlayerAssociation,
)

# ADD: Database imports for PostgreSQL queries
from database import get_db
from utils.ai import client, get_or_create_assistant, update_assistant_instructions
from utils.auth import login_required
from utils.logging import log_user_activity

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

# NEW: Response prefetch cache - increased duration for speed
_response_cache = {}  # {thread_id: {response, timestamp}}
RESPONSE_CACHE_DURATION = 180  # Cache responses for 3 minutes (increased from 1 minute)

# NEW: Training data cache for ultra-fast access - using database instead of JSON
_training_data_cache = None
_training_data_cache_time = None
TRAINING_DATA_CACHE_DURATION = 3600  # Cache for 1 hour

# Optimization configuration - easily adjustable
OPTIMIZATION_LEVEL = os.environ.get(
    "AI_OPTIMIZATION_LEVEL", "ULTRA"
)  # Changed from HIGH to ULTRA

# NEW: Streaming configuration - DISABLED due to conflict issues
USE_STREAMING = False  # Disabled - causes active run conflicts
STREAMING_TIMEOUT = int(
    os.environ.get("AI_STREAMING_TIMEOUT", "5")
)  # Not used when streaming disabled
FALLBACK_TO_POLLING = True  # Always use polling for reliability

# NEW: User context caching for speed
_user_context_cache = {}  # {user_email: {context, timestamp}}
USER_CONTEXT_CACHE_DURATION = 300  # Cache for 5 minutes

# Set optimization parameters based on level - ULTRA SPEED SETTINGS
if OPTIMIZATION_LEVEL == "ULTRA":
    BATCH_OPERATIONS = True
    MIN_POLL_INTERVAL = 0.1  # Ultra-fast - reduced from 0.2
    MAX_POLL_INTERVAL = 0.8  # Much faster - reduced from 1.5
    EXPONENTIAL_BACKOFF = 1.1  # Reduced from 1.2
    ASSISTANT_CACHE_DURATION = 14400  # 4 hours
    PREDICTIVE_POLLING = True
elif OPTIMIZATION_LEVEL == "HIGH":
    BATCH_OPERATIONS = True
    MIN_POLL_INTERVAL = 1.0  # Faster - reduced from 3.0
    MAX_POLL_INTERVAL = 5.0  # Faster - reduced from 12.0
    EXPONENTIAL_BACKOFF = 1.5  # Reduced from 2.0
    ASSISTANT_CACHE_DURATION = 7200  # 2 hours
    PREDICTIVE_POLLING = True
elif OPTIMIZATION_LEVEL == "MEDIUM":
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
    "total_requests": 0,
    "total_polls": 0,
    "cache_hits": 0,
    "optimization_saves": 0,
    "predictive_hits": 0,  # NEW: Successful predictive polling
    "context_cache_hits": 0,  # NEW: Context checks avoided
    "thread_reuses": 0,  # NEW: Threads reused instead of created
    "response_cache_hits": 0,  # NEW: Response cache hits
}

# NEW: Fast response system - configurable via environment
ENABLE_FAST_RESPONSE = os.environ.get("ENABLE_FAST_RESPONSE", "false").lower() == "true"  # Disabled temporarily
FAST_RESPONSE_TIMEOUT = float(os.environ.get("FAST_RESPONSE_TIMEOUT", "2.0"))


def get_cached_assistant():
    """Get assistant with caching to reduce API calls"""
    global _cached_assistant, _assistant_cache_time

    current_time = time.time()
    if (
        _cached_assistant is None
        or _assistant_cache_time is None
        or current_time - _assistant_cache_time > ASSISTANT_CACHE_DURATION
    ):

        _cached_assistant = get_or_create_assistant()
        _assistant_cache_time = current_time
        print(f"Assistant cached: {_cached_assistant.id}")
    else:
        _api_stats["cache_hits"] += 1
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
    important_keywords = [
        "serve",
        "volley",
        "paddle",
        "strategy",
        "technique",
        "coach",
        "improvement",
    ]
    words = content.split()

    # Build compressed version prioritizing important terms
    compressed = []
    char_count = 0

    for word in words:
        if char_count + len(word) + 1 > max_length:
            break
        if (
            any(keyword in word.lower() for keyword in important_keywords)
            or len(compressed) < 10
        ):
            compressed.append(word)
            char_count += len(word) + 1

    result = " ".join(compressed)
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
        content = msg.content[0].text.value if hasattr(msg.content[0], "text") else ""

        if msg.role == "user":
            # Extract user topics/questions
            compressed = compress_message_content(content, 50)
            if compressed:
                user_topics.append(compressed)
        else:
            # Extract key advice points
            if any(
                keyword in content.lower()
                for keyword in ["improve", "practice", "technique", "tip"]
            ):
                compressed = compress_message_content(content, 100)
                if compressed:
                    key_advice.append(compressed)

    # Create concise summary
    summary_parts = []
    if user_topics:
        summary_parts.append(f"Previous topics: {', '.join(user_topics[:3])}")
    if key_advice:
        summary_parts.append(f"Key advice given: {'; '.join(key_advice[:2])}")

    summary = (
        " | ".join(summary_parts)
        if summary_parts
        else "Previous general paddle tennis discussion"
    )

    # Cache the summary
    _context_summaries[thread_id] = summary
    return summary


def optimize_thread_context(thread_id):
    """
    Intelligent context management that preserves important info while reducing tokens
    Returns: (context_size, message_count, was_optimized, summary)
    """
    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=5)
        messages_list = list(messages.data)

        if not messages_list:
            return 0, 0, False, ""

        # Calculate current context size
        total_chars = sum(
            len(msg.content[0].text.value)
            for msg in messages_list
            if hasattr(msg.content[0], "text")
        )

        # Check if optimization is needed
        should_optimize = (
            len(messages_list) > SUMMARY_TRIGGER_MSGS
            or total_chars > MAX_CONTEXT_CHARS * CONTEXT_TRIM_THRESHOLD
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
            msg_chars = (
                len(msg.content[0].text.value) if hasattr(msg.content[0], "text") else 0
            )
            if (
                recent_chars + msg_chars > MAX_CONTEXT_CHARS * 0.6
            ):  # Keep 60% for recent
                break
            recent_chars += msg_chars
            messages_to_keep.append(msg)

        optimized_chars = len(context_summary) + recent_chars
        was_optimized = len(messages_to_keep) < len(messages_list)

        if was_optimized:
            print(
                f"✨ Context optimized: {len(messages_list)}→{len(messages_to_keep)} msgs, {total_chars}→{optimized_chars} chars"
            )

        return optimized_chars, len(messages_to_keep), was_optimized, context_summary

    except Exception as e:
        print(f"Error optimizing context: {e}")
        return 0, 0, False, ""


def create_optimized_thread_with_context(
    original_thread_id, context_summary, recent_messages
):
    """Create a new thread with optimized context"""
    try:
        # Create new thread
        new_thread = client.beta.threads.create()

        # Add context summary as first message if we have one
        if context_summary:
            client.beta.threads.messages.create(
                thread_id=new_thread.id,
                role="assistant",
                content=f"[Previous conversation context: {context_summary}]",
            )

        # Add recent messages to maintain conversation flow
        for msg in reversed(
            recent_messages[1:]
        ):  # Skip the very latest (will be added separately)
            if hasattr(msg.content[0], "text"):
                client.beta.threads.messages.create(
                    thread_id=new_thread.id,
                    role=msg.role,
                    content=msg.content[0].text.value,
                )

        print(f"CREATED: Optimized thread: {new_thread.id}")
        return new_thread.id

    except Exception as e:
        print(f"Error creating optimized thread: {e}")
        return original_thread_id  # Fallback to original


def get_thread_metadata(thread_id):
    """Get cached thread metadata to avoid unnecessary API calls"""
    if thread_id in _thread_metadata:
        _api_stats["cache_hits"] += 1
        return _thread_metadata[thread_id]

    try:
        # Only fetch if not cached
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
        if messages.data:
            metadata = {
                "last_message_time": messages.data[0].created_at,
                "message_count": 1,  # We'll update this as needed
                "context_size": (
                    len(messages.data[0].content[0].text.value)
                    if hasattr(messages.data[0].content[0], "text")
                    else 0
                ),
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
            thread_id=thread_id, role="user", content=user_message
        )

        # Immediately start run without waiting
        run = client.beta.threads.runs.create(
            thread_id=thread_id, assistant_id=assistant_id
        )

        return run
    except Exception as e:
        print(f"Error in batch operations: {e}")
        raise


def ultra_optimized_polling(thread_id, run_id, timeout=30):
    """DEPRECATED: Replaced with streaming approach"""
    # This function is now only used as fallback
    return legacy_polling_fallback(thread_id, run_id, timeout)


def legacy_polling_fallback(thread_id, run_id, timeout=3):
    """Optimized polling with smart intervals and function call handling"""
    start_time = time.time()
    poll_count = 0

    print(f"POLLING: Starting optimized polling for run {run_id}")

    # Optimized polling loop with smart intervals
    while time.time() - start_time < timeout:
        poll_count += 1

        try:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run_id
            )

            print(f"Poll #{poll_count}: {run_status.status}")

            if run_status.status == "completed":
                print(
                    f"COMPLETED: Run completed after {poll_count} polls in {time.time() - start_time:.1f}s"
                )
                return run_status, poll_count
            elif run_status.status in ["failed", "cancelled", "expired"]:
                print(
                    f"ERROR: Run {run_status.status}: {getattr(run_status, 'last_error', 'No error details')}"
                )
                raise Exception(
                    f"Run {run_status.status}: {getattr(run_status, 'last_error', 'Unknown error')}"
                )
            elif run_status.status == "requires_action":
                # Handle function calls
                print(f"ACTION: Run requires action - handling function calls")
                if (
                    run_status.required_action
                    and run_status.required_action.type == "submit_tool_outputs"
                ):
                    tool_outputs = []

                    # Process function calls in parallel for ultra-fast execution
                    import concurrent.futures
                    import json

                    def execute_function_call(tool_call):
                        """Execute a single function call - optimized for speed"""
                        print(f"EXEC: Executing function: {tool_call.function.name}")

                        try:
                            if tool_call.function.name == "get_complete_training_info":
                                # Parse the arguments
                                args = json.loads(tool_call.function.arguments)
                                topic = (
                                    args.get("topic", "")
                                    or args.get("technique", "")
                                    or args.get("query", "")
                                )

                                print(
                                    f"TRAINING: Getting complete training info for: '{topic}'"
                                )

                                # Get training data from cache (ultra-fast)
                                from api.training_data import find_topic_data

                                training_data = get_cached_training_data()
                                topic_key, topic_data = find_topic_data(
                                    training_data, topic
                                )

                                # Get video data directly
                                video_result = find_training_video_direct(topic)

                                # Combine both results
                                result = {
                                    "training_data": (
                                        {"topic": topic_key, "data": topic_data}
                                        if topic_data
                                        else None
                                    ),
                                    "video": (
                                        video_result.get("video")
                                        if video_result
                                        else None
                                    ),
                                    "videos": (
                                        video_result.get("videos", [])
                                        if video_result
                                        else []
                                    ),
                                    "success": bool(topic_data or video_result),
                                }

                                print(
                                    f"SUCCESS: Complete training info retrieved for: '{topic_key or topic}'"
                                )

                            elif tool_call.function.name == "find_training_video":
                                args = json.loads(tool_call.function.arguments)
                                technique = (
                                    args.get("technique", "")
                                    or args.get("topic", "")
                                    or args.get("query", "")
                                )

                                print(
                                    f"LOOKUP: Looking up video for technique: '{technique}'"
                                )
                                result = find_training_video_direct(technique)

                            elif (
                                tool_call.function.name == "get_training_data_by_topic"
                            ):
                                from api.training_data import find_topic_data

                                args = json.loads(tool_call.function.arguments)
                                topic = (
                                    args.get("topic", "")
                                    or args.get("technique", "")
                                    or args.get("query", "")
                                )

                                print(
                                    f"LOOKUP: Looking up training data for topic: '{topic}'"
                                )

                                training_data = get_cached_training_data()
                                topic_key, topic_data = find_topic_data(
                                    training_data, topic
                                )

                                if topic_data:
                                    result = {"topic": topic_key, "data": topic_data}
                                    print(f"FOUND: Found training data for: '{topic_key}'")
                                else:
                                    result = {
                                        "error": f"Training data not found for topic: {topic}"
                                    }

                            else:
                                print(f"WARNING: Unknown function: {tool_call.function.name}")
                                result = {
                                    "error": f"Unknown function: {tool_call.function.name}"
                                }

                        except Exception as e:
                            result = {"error": f"Function execution failed: {str(e)}"}
                            print(f"ERROR: Error in {tool_call.function.name}: {str(e)}")

                        return {
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result),
                        }

                    # Execute all function calls in parallel for maximum speed
                    tool_calls = (
                        run_status.required_action.submit_tool_outputs.tool_calls
                    )

                    if len(tool_calls) == 1:
                        # Single function call - execute directly (faster than threading overhead)
                        tool_outputs = [execute_function_call(tool_calls[0])]
                    else:
                        # Multiple function calls - execute in parallel
                        with concurrent.futures.ThreadPoolExecutor(
                            max_workers=min(len(tool_calls), 4)
                        ) as executor:
                            future_to_call = {
                                executor.submit(execute_function_call, call): call
                                for call in tool_calls
                            }
                            tool_outputs = []

                            for future in concurrent.futures.as_completed(
                                future_to_call, timeout=10
                            ):
                                try:
                                    result = future.result()
                                    tool_outputs.append(result)
                                except Exception as e:
                                    call = future_to_call[future]
                                    print(
                                        f"ERROR: Parallel execution failed for {call.function.name}: {str(e)}"
                                    )
                                    tool_outputs.append(
                                        {
                                            "tool_call_id": call.id,
                                            "output": json.dumps(
                                                {
                                                    "error": f"Parallel execution failed: {str(e)}"
                                                }
                                            ),
                                        }
                                    )

                    # Submit the tool outputs
                    if tool_outputs:
                        print(f"SUBMIT: Submitting {len(tool_outputs)} tool outputs")
                        client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
                            run_id=run_id,
                            tool_outputs=tool_outputs,
                        )
                        # Continue polling after submitting outputs - faster interval
                        time.sleep(MIN_POLL_INTERVAL)
                        continue
                    else:
                        print(f"WARNING: No tool outputs to submit")

            elif run_status.status in ["in_progress", "queued"]:
                # Continue polling
                pass
            else:
                print(f"WARNING: Unexpected run status: {run_status.status}")

            # Ultra-fast wait times for speed - optimized for sub-5s responses
            if poll_count == 1:
                time.sleep(0.05)  # Very fast first poll
            elif poll_count == 2:
                time.sleep(0.1)  # Still very fast
            elif poll_count <= 5:
                time.sleep(0.15)  # Slightly longer but still fast
            elif poll_count <= 10:
                time.sleep(0.2)  # Moderate increase
            else:
                time.sleep(0.3)  # Cap at reasonable max

        except Exception as e:
            if "rate limit" in str(e).lower():
                print(f"RATE_LIMIT: Rate limit hit, waiting 10s...")
                time.sleep(10)  # Long wait for rate limits
            else:
                print(f"ERROR: Polling error: {str(e)}")
                raise

    raise Exception(f"Request timed out after {timeout}s with {poll_count} polls")


def create_streaming_run(thread_id, assistant_id):
    """Direct polling approach with early response capability"""
    print(f"POLLING: Using direct polling for reliable responses")

    # Skip streaming entirely - go straight to polling
    run = client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=assistant_id
    )

    # Try to get response quickly with early timeout
    try:
        run_status, poll_count = legacy_polling_fallback(thread_id, run.id)
        
        # Get response from messages
        messages = client.beta.threads.messages.list(thread_id=thread_id, limit=1)
        if messages.data and messages.data[0].content:
            response_text = messages.data[0].content[0].text.value
            return response_text, poll_count
        else:
            raise Exception("No response received from assistant")
            
    except Exception as e:
        if "timed out" in str(e).lower():
            # Return a quick response if we're taking too long
            print(f"TIMEOUT: Returning quick response after timeout")
            return get_cached_quick_response(""), 1
        else:
            raise e

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
            if run.status in ["in_progress", "queued", "requires_action"]:
                print(f"FOUND: Found active run {run.id} with status: {run.status}")

                if run.status == "requires_action":
                    # Try to complete the existing run by handling function calls
                    print(f"ATTEMPTING: Attempting to complete existing run {run.id}")
                    try:
                        run_status, poll_count = legacy_polling_fallback(
                            thread_id, run.id, timeout=5  # Much shorter timeout
                        )
                        return True  # Successfully completed existing run
                    except Exception as e:
                        print(f"WARNING: Could not complete existing run: {str(e)}")
                        # Cancel the run immediately if we can't complete it quickly
                        try:
                            client.beta.threads.runs.cancel(
                                thread_id=thread_id, run_id=run.id
                            )
                            print(f"CANCELLED: Cancelled stuck run {run.id}")
                            time.sleep(0.5)  # Shorter wait
                            return True
                        except Exception as cancel_error:
                            print(f"WARNING: Could not cancel run: {str(cancel_error)}")

                elif run.status in ["in_progress", "queued"]:
                    # Don't wait long for existing runs - cancel them quickly
                    print(f"CANCELLING: Cancelling existing run {run.id} for speed...")
                    try:
                        client.beta.threads.runs.cancel(
                            thread_id=thread_id, run_id=run.id
                        )
                        print(f"CANCELLED: Cancelled existing run {run.id}")
                        time.sleep(0.5)
                        return True
                    except Exception as e:
                        print(f"WARNING: Could not cancel existing run: {str(e)}")
                        # If we can't cancel, try waiting briefly
                        try:
                            run_status, poll_count = legacy_polling_fallback(
                                thread_id, run.id, timeout=3  # Very short timeout
                            )
                            return True
                        except Exception as wait_error:
                            print(f"WARNING: Existing run timeout: {str(wait_error)}")
                            return False  # Give up and create new thread

        return True  # No active runs found

    except Exception as e:
        print(f"WARNING: Error handling active run conflict: {str(e)}")
        return False


def batch_operations_with_streaming(thread_id, user_message, assistant_id):
    """Ultra-simple approach with proper timeout and cleanup"""
    import threading
    import time
    
    result_container = {}
    exception_container = {}
    timeout_flag = threading.Event()
    
    def run_with_timeout():
        try:
            # Check if we've been timed out before starting
            if timeout_flag.is_set():
                return
                
            print(f"ADDING: Adding user message to thread {thread_id}")
            message = client.beta.threads.messages.create(
                thread_id=thread_id, role="user", content=user_message
            )
            print(f"SUCCESS: Message added: {message.id}")

            # Check timeout again before expensive operation
            if timeout_flag.is_set():
                return
                
            response_text, poll_count = create_streaming_run(thread_id, assistant_id)
            
            # Only set results if not timed out
            if not timeout_flag.is_set():
                result_container['response'] = response_text
                result_container['poll_count'] = poll_count
                result_container['thread_id'] = thread_id
        except Exception as e:
            if not timeout_flag.is_set():
                exception_container['error'] = e
    
    # Start the operation in a separate thread
    thread = threading.Thread(target=run_with_timeout)
    thread.daemon = True
    thread.start()
    
    # Wait for completion with 3-second timeout (reduced from 4)
    thread.join(timeout=3.0)
    
    if thread.is_alive():
        print(f"TIMEOUT: Operation timed out, returning detailed quick response")
        timeout_flag.set()  # Signal timeout to the thread
        return get_cached_quick_response(user_message), 1, thread_id
    
    if exception_container:
        error = exception_container['error']
        print(f"WARNING: Thread conflict detected, creating new thread immediately")
        
        # ANY error = create new thread immediately (no complex resolution)
        new_thread = client.beta.threads.create()
        thread_id = new_thread.id
        print(f"NEW: Created new thread: {thread_id}")

        message = client.beta.threads.messages.create(
            thread_id=thread_id, role="user", content=user_message
        )

        response_text, poll_count = create_streaming_run(thread_id, assistant_id)
        return response_text, poll_count, thread_id
    
    if result_container:
        return result_container['response'], result_container['poll_count'], result_container['thread_id']
    
    # Fallback
    return get_cached_quick_response(user_message), 1, thread_id


def estimate_completion_time(thread_id):
    """Estimate completion time based on context and historical patterns"""
    base_time = MIN_POLL_INTERVAL

    # Factor in context size
    if thread_id in _thread_metadata:
        context_size = _thread_metadata[thread_id].get("context_size", 0)
        message_count = _thread_metadata[thread_id].get("message_count", 0)

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
    if cached and time.time() - cached["timestamp"] < RESPONSE_CACHE_DURATION:
        _api_stats["response_cache_hits"] += 1  # NEW: Track response cache hits
        print(f"CACHE: Response cache hit for thread {thread_id}")
        return cached["response"]
    return None


def cache_response(thread_id, response):
    """Cache a response for potential reuse"""
    _response_cache[thread_id] = {"response": response, "timestamp": time.time()}


def get_cached_training_data():
    """Get training data with caching for ultra-fast access - using robust file path"""
    global _training_data_cache, _training_data_cache_time

    current_time = time.time()
    if (
        _training_data_cache is None
        or _training_data_cache_time is None
        or current_time - _training_data_cache_time > TRAINING_DATA_CACHE_DURATION
    ):

        print(f"LOADING: Loading training data into cache...")
        try:
            import json

            # Use absolute path to ensure reliability
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            training_guide_path = os.path.join(
                project_root,
                "data",
                "leagues",
                "all",
                "improve_data",
                "complete_platform_tennis_training_guide.json",
            )

            if os.path.exists(training_guide_path):
                with open(training_guide_path, "r", encoding="utf-8") as f:
                    _training_data_cache = json.load(f)
                _training_data_cache_time = current_time
                print(f"SUCCESS: Training data cached: {len(_training_data_cache)} topics")
            else:
                print(
                    f"WARNING: Training guide not found at {training_guide_path}, using empty cache"
                )
                _training_data_cache = {}
                _training_data_cache_time = current_time
        except Exception as e:
            print(f"ERROR: Error loading training data: {str(e)}, using empty cache")
            _training_data_cache = {}
            _training_data_cache_time = current_time
    else:
        print(f"CACHE: Training data cache hit")

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
        time_diff = time.time() - metadata.get("last_message_time", 0)
        if time_diff < 600:  # 10 minutes instead of 5
            estimated_size = metadata.get("context_size", 0)

            # Be more aggressive about avoiding optimization checks
            if (
                estimated_size < MAX_CONTEXT_CHARS * 0.8
            ):  # Increased threshold from 0.6 to 0.8
                _api_stats["optimization_saves"] += 1
                _api_stats["context_cache_hits"] += 1  # NEW: Track context cache hits
                print(
                    f"🎯 Smart cache hit - avoiding context check (estimated: {estimated_size} chars)"
                )
                return estimated_size, metadata.get("message_count", 0), False, ""

    # Only do full optimization if really needed
    print(f"📊 Performing context check for thread {thread_id}")
    return optimize_thread_context(thread_id)


def enhanced_metadata_update(
    thread_id, message_length, response_length, was_optimized=False
):
    """Enhanced metadata tracking with better estimates"""
    current_time = time.time()

    if thread_id in _thread_metadata:
        # Update existing metadata
        metadata = _thread_metadata[thread_id]
        metadata["last_message_time"] = current_time
        metadata["message_count"] += 2  # User message + assistant response
        metadata["context_size"] += message_length + response_length

        # If context was optimized, reset the size estimate
        if was_optimized:
            metadata["context_size"] = (
                message_length + response_length + 500
            )  # Base context
            metadata["message_count"] = 2  # Reset to just this exchange
    else:
        # Create new metadata
        _thread_metadata[thread_id] = {
            "last_message_time": current_time,
            "message_count": 2,
            "context_size": message_length
            + response_length
            + 200,  # Include some base overhead
            "created_time": current_time,
        }

    # Clean up old metadata to prevent memory bloat
    cleanup_old_metadata()


def cleanup_old_metadata():
    """Clean up metadata for threads older than 24 hours"""
    current_time = time.time()
    old_threads = []

    for thread_id, metadata in _thread_metadata.items():
        if current_time - metadata.get("last_message_time", 0) > 86400:  # 24 hours
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


def get_user_playing_context(user):
    """Get comprehensive user playing context for personalized AI assistance using database queries"""
    try:
        user_context = {
            "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "email": user.get("email", "unknown"),
            "club": user.get("club", "Unknown"),
            "series": user.get("series", "Unknown"),
            "current_pti": None,
            "weekly_pti_change": None,
            "recent_matches": [],
            "playing_trends": {},
            "areas_for_improvement": [],
        }

        # Get player data from database
        try:
            with get_db() as conn:
                cursor = conn.cursor()

                # Find the user's player record using email or name
                user_email = user.get("email", "")
                user_name = user_context["name"]

                # First try to find player via user_player_associations
                cursor.execute(
                    """
                    SELECT DISTINCT p.id, p.tenniscores_player_id, p.first_name, p.last_name, 
                           p.pti, p.wins, p.losses, p.win_percentage,
                           s.name as series_name, c.name as club_name, l.league_name,
                           p.updated_at
                    FROM players p
                    JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
                    JOIN users u ON upa.user_id = u.id
                    LEFT JOIN series s ON p.series_id = s.id
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN leagues l ON p.league_id = l.id
                    WHERE u.email = %s
                    ORDER BY p.updated_at DESC
                    LIMIT 1
                """,
                    (user_email,),
                )

                player_record = cursor.fetchone()

                # If no association found, try to match by name
                if not player_record and user_name:
                    cursor.execute(
                        """
                        SELECT DISTINCT p.id, p.tenniscores_player_id, p.first_name, p.last_name, 
                               p.pti, p.wins, p.losses, p.win_percentage,
                               s.name as series_name, c.name as club_name, l.league_name,
                               p.updated_at
                        FROM players p
                        LEFT JOIN series s ON p.series_id = s.id
                        LEFT JOIN clubs c ON p.club_id = c.id
                        LEFT JOIN leagues l ON p.league_id = l.id
                        WHERE LOWER(CONCAT(p.first_name, ' ', p.last_name)) = LOWER(%s)
                        ORDER BY p.updated_at DESC
                        LIMIT 1
                    """,
                        (user_name,),
                    )
                    player_record = cursor.fetchone()

                if player_record:
                    (
                        player_id,
                        tenniscores_id,
                        first_name,
                        last_name,
                        current_pti,
                        wins,
                        losses,
                        win_pct,
                        series_name,
                        club_name,
                        league_name,
                        updated_at,
                    ) = player_record

                    # Update context with player info
                    user_context.update(
                        {
                            "name": f"{first_name} {last_name}",
                            "current_pti": float(current_pti) if current_pti else None,
                            "series": series_name or user_context["series"],
                            "club": club_name or user_context["club"],
                        }
                    )

                    # Get recent player history for PTI tracking
                    cursor.execute(
                        """
                        SELECT date, end_pti, series
                        FROM player_history
                        WHERE player_id = %s
                        ORDER BY date DESC
                        LIMIT 10
                    """,
                        (player_id,),
                    )

                    pti_history = cursor.fetchall()

                    if pti_history and len(pti_history) > 1:
                        # Calculate weekly PTI change
                        current_date = pti_history[0][0]
                        current_pti_hist = (
                            float(pti_history[0][1]) if pti_history[0][1] else None
                        )

                        # Find PTI from about a week ago
                        for hist_record in pti_history[1:]:
                            hist_date = hist_record[0]
                            hist_pti = float(hist_record[1]) if hist_record[1] else None

                            if (
                                hist_pti
                                and current_pti_hist
                                and (current_date - hist_date).days >= 5
                            ):
                                user_context["weekly_pti_change"] = (
                                    current_pti_hist - hist_pti
                                )
                                break

                    # Get recent match results
                    cursor.execute(
                        """
                        SELECT ms.match_date, ms.home_team, ms.away_team, ms.winner, ms.scores,
                               ms.home_player_1_id, ms.home_player_2_id, ms.away_player_1_id, ms.away_player_2_id
                        FROM match_scores ms
                        WHERE ms.home_player_1_id = %s OR ms.home_player_2_id = %s 
                           OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s
                        ORDER BY ms.match_date DESC
                        LIMIT 10
                    """,
                        (
                            tenniscores_id,
                            tenniscores_id,
                            tenniscores_id,
                            tenniscores_id,
                        ),
                    )

                    recent_matches = cursor.fetchall()

                    if recent_matches:
                        match_results = []
                        wins = 0

                        for match in recent_matches:
                            (
                                match_date,
                                home_team,
                                away_team,
                                winner,
                                scores,
                                hp1,
                                hp2,
                                ap1,
                                ap2,
                            ) = match

                            # Determine if player was on home or away team
                            is_home = tenniscores_id in [hp1, hp2]
                            opponent_team = away_team if is_home else home_team

                            # Determine if won
                            won = (is_home and winner == "home") or (
                                not is_home and winner == "away"
                            )
                            if won:
                                wins += 1

                            match_results.append(
                                {
                                    "date": (
                                        match_date.strftime("%m/%d/%Y")
                                        if match_date
                                        else "Unknown"
                                    ),
                                    "opponent": opponent_team,
                                    "result": "Win" if won else "Loss",
                                    "scores": scores,
                                }
                            )

                        user_context["recent_matches"] = match_results[:5]

                        # Calculate playing trends
                        total_matches = len(recent_matches)
                        losses = total_matches - wins

                        user_context["playing_trends"] = {
                            "recent_record": f"{wins}W-{losses}L",
                            "win_percentage": (
                                round((wins / total_matches) * 100, 1)
                                if total_matches > 0
                                else 0
                            ),
                            "total_matches": total_matches,
                        }

                        # Identify areas for improvement
                        if (
                            user_context["weekly_pti_change"]
                            and user_context["weekly_pti_change"] < -2
                        ):
                            user_context["areas_for_improvement"].append(
                                "Recent PTI decline - focus on consistency"
                            )

                        if user_context["playing_trends"]["win_percentage"] < 40:
                            user_context["areas_for_improvement"].append(
                                "Below average win rate - work on fundamentals"
                            )

                        if total_matches >= 5 and wins == 0:
                            user_context["areas_for_improvement"].append(
                                "Recent losing streak - consider technique review"
                            )

        except Exception as e:
            print(f"Error loading player data from database: {str(e)}")
            # Continue with basic info if database query fails

        return user_context

    except Exception as e:
        print(f"Error getting user playing context: {str(e)}")
        return {
            "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "email": user.get("email", "unknown"),
            "club": user.get("club", "Unknown"),
            "series": user.get("series", "Unknown"),
        }


def format_user_context_for_assistant(user_context):
    """Format user context into a readable string for the assistant"""
    context_str = f"""
PLAYER PROFILE:
Name: {user_context['name']}
Club: {user_context['club']}
Series: {user_context['series']}"""

    if user_context.get("current_pti"):
        context_str += f"\nCurrent PTI Rating: {user_context['current_pti']}"

    if user_context.get("weekly_pti_change"):
        change_direction = (
            "increased" if user_context["weekly_pti_change"] > 0 else "decreased"
        )
        context_str += f"\nRecent PTI Change: {change_direction} by {abs(user_context['weekly_pti_change'])} points"

    if user_context.get("playing_trends"):
        trends = user_context["playing_trends"]
        context_str += f"\n\nRECENT PERFORMANCE:"
        context_str += f"\nRecord: {trends.get('recent_record', 'N/A')}"
        context_str += f"\nWin Rate: {trends.get('win_percentage', 0)}%"
        if trends.get("avg_pti_change"):
            context_str += f"\nAverage PTI Change: {trends['avg_pti_change']} per match"

    if user_context.get("recent_matches"):
        context_str += f"\n\nRECENT MATCHES:"
        for i, match in enumerate(
            user_context["recent_matches"][:3]
        ):  # Show last 3 matches
            result = match.get("result", "Unknown")
            date = match.get("date", "Unknown")
            opponent = match.get("opponent", "Unknown")
            pti_change = match.get("pti_change", 0)
            context_str += (
                f"\n{i+1}. {date}: {result} vs {opponent} (PTI: {pti_change:+.1f})"
            )

    if user_context.get("areas_for_improvement"):
        context_str += f"\n\nAREAS FOR IMPROVEMENT:"
        for area in user_context["areas_for_improvement"]:
            context_str += f"\n• {area}"

    return context_str


def init_rally_ai_routes(app):
    # Pre-warm caches for maximum speed
    prewarm_caches()

    @app.route("/mobile/ask-ai")
    def mobile_ask_ai():
        """Serve the mobile AI chat interface"""
        try:
            user = session["user"]
            log_user_activity(
                user["email"], 
                "page_visit", 
                page="mobile_ask_ai",
                first_name=user.get("first_name"),
                last_name=user.get("last_name")
            )
            return render_template(
                "mobile/ask_ai.html", user=user, session_data={"user": user}
            )
        except Exception as e:
            print(f"Error serving AI chat: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chat", methods=["POST"])
    def handle_chat():
        """Ultra-optimized chat handler with minimal API calls"""
        try:
            data = request.json
            message = data.get("message")
            thread_id = data.get("thread_id")
            user_email = session.get("user", {}).get("email", "unknown")

            print(
                f"\n=== ULTRA-OPTIMIZED CHAT v3.0 [{datetime.now().strftime('%H:%M:%S')}] ==="
            )
            print(f"User: {user_email}")
            print(f"Message: '{message[:50]}...' ({len(message)} chars)")
            print(f"Thread: {thread_id or 'NEW'}")

            if not message:
                return jsonify({"error": "Message is required"}), 400

            # For very short messages (1-2 words), use instant cached responses with thinking delay
            if len(message.split()) <= 2:
                print(f"🚀 INSTANT: Short message detected, using instant response with thinking delay")
                instant_response = get_cached_quick_response(message)
                return jsonify(
                    {
                        "response": instant_response,
                        "thread_id": "instant",
                        "thinking_delay": 3.0,  # 3 second thinking animation
                        "debug": {
                            "cached": True,
                            "processing_time": "3.0s (thinking)",
                            "efficiency_rating": "INSTANT - Short message",
                        },
                    }
                )

            # Get cached assistant (minimal API calls)
            assistant = get_cached_assistant()

            # DEBUG: Print assistant instructions (system prompt)
            print(f"\n=== DEBUG: SYSTEM PROMPT (Assistant Instructions) ===")
            print(f"Assistant ID: {assistant.id}")
            print(f"Assistant Name: {assistant.name}")
            print(f"System Prompt Length: {len(assistant.instructions)} characters")
            print("=" * 80)
            print("COMPLETE SYSTEM PROMPT:")
            print(assistant.instructions)
            print("=" * 80)
            print(f"=== END SYSTEM PROMPT DEBUG ===\n")

            # Track request
            _api_stats["total_requests"] += 1

            # ULTRA-FAST MESSAGE ENHANCEMENT (maximum speed optimization)
            try:
                if ENABLE_FAST_RESPONSE:
                    print(f"FAST: Using lightweight user context for maximum speed...")
                    user_context = get_lightweight_user_context(session.get("user", {}))
                    enhanced_message = create_ultra_fast_enhanced_message_minimal(
                        message, user_context
                    )
                else:
                    print(f"FAST: Getting cached user context and creating ultra-fast message...")
                    user_context = get_cached_user_context(session.get("user", {}))
                    enhanced_message = create_ultra_fast_enhanced_message(
                        message, user_context
                    )

                # Minimal debug output for speed
                print(f"SUCCESS: Enhanced: {len(message)} → {len(enhanced_message)} chars")

            except Exception as e:
                print(f"WARNING: Error creating ultra-fast message: {str(e)}, using original")
                enhanced_message = message

            # Smart thread management with caching
            context_summary = ""
            was_optimized = False

            if not thread_id:
                # Create new thread
                thread = client.beta.threads.create()
                thread_id = thread.id
                print(f"NEW: Created thread: {thread_id}")
                context_chars = 0
                message_count = 0
            else:
                # Use cached metadata when possible with smarter gap detection
                metadata = get_thread_metadata(thread_id)
                if metadata:
                    time_diff = time.time() - metadata["last_message_time"]

                    # Smarter gap detection - consider context size and user patterns
                    context_size = metadata.get("context_size", 0)
                    message_count = metadata.get("message_count", 0)

                    # Longer gaps needed for larger contexts, shorter for small contexts
                    gap_threshold = 300  # Base 5 minutes
                    if context_size > MAX_CONTEXT_CHARS * 0.7:
                        gap_threshold = (
                            180  # 3 minutes for large contexts (force refresh sooner)
                        )
                    elif context_size < MAX_CONTEXT_CHARS * 0.3:
                        gap_threshold = (
                            900  # 15 minutes for small contexts (keep longer)
                        )

                    if time_diff > gap_threshold:
                        thread = client.beta.threads.create()
                        thread_id = thread.id
                        print(
                            f"NEW: Created new thread after {time_diff:.0f}s gap (threshold: {gap_threshold}s)"
                        )
                        context_chars = 0
                        message_count = 0
                    else:
                        # Use smart context checking (uses cache when possible)
                        context_chars, message_count, was_optimized, context_summary = (
                            smart_context_check(thread_id)
                        )
                        _api_stats["thread_reuses"] += 1  # NEW: Track thread reuses
                        print(
                            f"REUSING: Reusing thread (gap: {time_diff:.0f}s < {gap_threshold}s)"
                        )
                else:
                    # Fallback for threads without metadata
                    context_chars, message_count, was_optimized, context_summary = (
                        smart_context_check(thread_id)
                    )

            # Ultra-fast response system with 3-second timeout
            start_time = time.time()
            max_response_time = 2.5  # Leave 0.5s buffer for processing

            # Use ultra-simple approach - no complex fallbacks
            try:
                result = batch_operations_with_streaming(
                    thread_id, enhanced_message, assistant.id
                )

                response_text, poll_count, thread_id = result
                response_time = time.time() - start_time
                print(f"RESPONSE: Response received in {response_time:.1f}s")
                
                # If we're approaching the timeout, return a quick response
                if response_time > max_response_time:
                    print(f"TIMEOUT_WARNING: Response took {response_time:.1f}s, using quick response")
                    response_text = get_cached_quick_response(message)

            except Exception as e:
                print(f"ERROR: Chat processing failed: {str(e)}")
                raise Exception(f"Could not process chat request: {str(e)}")

            # Enhanced metadata update with better tracking
            enhanced_metadata_update(
                thread_id, len(enhanced_message), len(response_text), was_optimized
            )

            # Cache the response for potential reuse
            cache_response(thread_id, response_text)

            # Format the response
            formatted_response = format_response(response_text)

            # Calculate message hash for caching identical queries
            message_hash = hashlib.md5(message.encode('utf-8')).hexdigest()

            # Also cache by message hash for identical queries
            _response_cache[message_hash] = {
                "response": formatted_response,
                "thread_id": thread_id,
                "timestamp": time.time(),
            }

            processing_time = time.time() - start_time
            final_context_chars = (
                context_chars + len(enhanced_message) + len(response_text)
            )
            final_message_count = message_count + 2

            print(f"SUCCESS: Response: {len(response_text)} chars in {processing_time:.1f}s")
            print(
                f"CONTEXT: Context: {final_context_chars} chars, {final_message_count} msgs"
            )
            if was_optimized:
                print(
                    f"OPTIMIZATION: Optimization saved ~{max(0, context_chars - MAX_CONTEXT_CHARS)} chars"
                )

            # Calculate efficiency improvements
            if poll_count == 1:
                print(f"STREAMING: STREAMING SUCCESS: Direct response (eliminated polling!)")
                efficiency_rating = "EXCELLENT - Streaming"
            else:
                estimated_old_polls = 15  # Old system average
                efficiency_improvement = max(
                    0, ((estimated_old_polls - poll_count) / estimated_old_polls) * 100
                )
                print(
                    f"EFFICIENCY: API Efficiency: {poll_count} polls (saved {efficiency_improvement:.0f}% vs baseline)"
                )
                efficiency_rating = (
                    "Excellent"
                    if processing_time < 5
                    else "Good" if processing_time < 10 else "Fair"
                )

            print(f"PERFORMANCE: Performance: {efficiency_rating}")
            print(f"=== CHAT COMPLETE ===\n")

            # Log with optimization info
            log_user_activity(
                user_email,
                "ai_chat",
                message_length=len(enhanced_message),
                response_length=len(response_text),
                thread_id=thread_id,
                context_size=final_context_chars,
                was_optimized=was_optimized,
                processing_time=processing_time,
                api_calls_saved=f"~{max(0, poll_count * 2)}",
            )

            return jsonify(
                {
                    "response": formatted_response,
                    "thread_id": thread_id,
                    "thinking_delay": 3.0,  # 3 second thinking animation
                    "debug": {
                        "message_length": len(enhanced_message),
                        "response_length": len(response_text),
                        "context_size": final_context_chars,
                        "message_count": final_message_count,
                        "context_percentage": (final_context_chars / MAX_CONTEXT_CHARS)
                        * 100,
                        "was_optimized": was_optimized,
                        "processing_time": f"{processing_time:.1f}s",
                        "polls_required": poll_count,
                        "streaming_used": poll_count == 1,
                        "efficiency_rating": (
                            "EXCELLENT - Streaming"
                            if poll_count == 1
                            else (
                                "Excellent"
                                if processing_time < 5
                                else "Good" if processing_time < 10 else "Fair"
                            )
                        ),
                        "api_optimization": (
                            "Streaming eliminated polling!"
                            if poll_count == 1
                            else f"Reduced polling by ~{max(0, 60 - poll_count)}%"
                        ),
                        "streaming_enabled": USE_STREAMING,
                        "fallback_available": FALLBACK_TO_POLLING,
                    },
                }
            )

        except Exception as e:
            print(f"ERROR: Chat error: {str(e)}")
            return jsonify({"error": f"Chat processing failed: {str(e)}"}), 500

    @app.route("/api/chat/debug/<thread_id>")
    def debug_thread(thread_id):
        """Enhanced debug info with optimization details"""
        try:
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            context_chars, message_count, was_optimized, summary = (
                optimize_thread_context(thread_id)
            )

            return jsonify(
                {
                    "thread_id": thread_id,
                    "message_count": len(messages.data),
                    "context_size": context_chars,
                    "optimization_candidate": context_chars
                    > MAX_CONTEXT_CHARS * CONTEXT_TRIM_THRESHOLD,
                    "context_summary": summary if summary else "No summary available",
                    "efficiency_score": min(
                        100, (MAX_CONTEXT_CHARS / max(context_chars, 1)) * 100
                    ),
                    "messages": [
                        {
                            "role": msg.role,
                            "content": (
                                msg.content[0].text.value[:100] + "..."
                                if len(msg.content[0].text.value) > 100
                                else msg.content[0].text.value
                            ),
                            "length": len(msg.content[0].text.value),
                            "timestamp": msg.created_at,
                        }
                        for msg in messages.data
                    ],
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chat/clear/<thread_id>", methods=["POST"])
    def clear_thread(thread_id):
        """Clear thread and its cached summary"""
        try:
            # Clear from summary cache
            if thread_id in _context_summaries:
                del _context_summaries[thread_id]

            # Note: OpenAI doesn't allow deleting threads, so we just clear our cache
            return jsonify({"message": "Thread cache cleared", "thread_id": thread_id})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chat/optimize/<thread_id>", methods=["POST"])
    def manually_optimize_thread(thread_id):
        """Manually trigger thread optimization"""
        try:
            context_chars, message_count, was_optimized, summary = (
                optimize_thread_context(thread_id)
            )

            if context_chars > MAX_CONTEXT_CHARS * 0.5:  # If context is substantial
                messages = client.beta.threads.messages.list(
                    thread_id=thread_id, limit=8
                )
                new_thread_id = create_optimized_thread_with_context(
                    thread_id, summary, list(messages.data)
                )

                return jsonify(
                    {
                        "message": "Thread optimized successfully",
                        "old_thread_id": thread_id,
                        "new_thread_id": new_thread_id,
                        "original_size": context_chars,
                        "summary": summary,
                    }
                )
            else:
                return jsonify(
                    {
                        "message": "Thread does not need optimization",
                        "thread_id": thread_id,
                        "context_size": context_chars,
                    }
                )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/chat/clear-cache", methods=["POST"])
    def clear_cache():
        """Clear assistant cache to force reload with new instructions"""
        try:
            clear_assistant_cache()
            return jsonify({"message": "Assistant cache cleared successfully"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/assistant/update", methods=["POST"])
    @login_required
    def update_assistant():
        """Update the assistant's instructions"""
        try:
            data = request.json
            new_instructions = data.get("instructions")

            if not new_instructions:
                return jsonify({"error": "Instructions are required"}), 400

            # Update assistant instructions
            assistant = update_assistant_instructions(new_instructions)

            # Clear the cache to force reload with new instructions
            clear_assistant_cache()

            return jsonify(
                {
                    "message": "Assistant instructions updated successfully",
                    "assistant_id": assistant.id,
                }
            )
        except Exception as e:
            print(f"Error updating assistant: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/ai/stats")
    @login_required
    def get_ai_stats():
        """Get AI optimization statistics and efficiency metrics"""
        try:
            # Calculate efficiency metrics
            total_requests = _api_stats["total_requests"]
            total_polls = _api_stats["total_polls"]
            cache_hits = _api_stats["cache_hits"]
            optimization_saves = _api_stats["optimization_saves"]
            predictive_hits = _api_stats["predictive_hits"]
            context_cache_hits = _api_stats["context_cache_hits"]
            thread_reuses = _api_stats["thread_reuses"]
            response_cache_hits = _api_stats["response_cache_hits"]

            avg_polls_per_request = total_polls / max(total_requests, 1)
            cache_hit_rate = (cache_hits / max(total_requests * 2, 1)) * 100

            # Calculate total API calls saved
            estimated_old_polls = total_requests * 15  # Old system average
            polls_saved = max(0, estimated_old_polls - total_polls)
            efficiency_improvement = (polls_saved / max(estimated_old_polls, 1)) * 100

            # Calculate additional savings from new optimizations
            total_optimizations = (
                context_cache_hits + thread_reuses + response_cache_hits
            )
            additional_api_saves = (
                total_optimizations * 2
            )  # Estimate 2 API calls saved per optimization

            return jsonify(
                {
                    "optimization_level": OPTIMIZATION_LEVEL,
                    "statistics": {
                        "total_requests": total_requests,
                        "total_polls": total_polls,
                        "cache_hits": cache_hits,
                        "optimization_saves": optimization_saves,
                        "predictive_hits": predictive_hits,
                        "context_cache_hits": context_cache_hits,
                        "thread_reuses": thread_reuses,
                        "response_cache_hits": response_cache_hits,
                        "avg_polls_per_request": round(avg_polls_per_request, 1),
                        "cache_hit_rate": f"{cache_hit_rate:.1f}%",
                        "estimated_api_calls_saved": polls_saved + additional_api_saves,
                        "efficiency_improvement": f"{efficiency_improvement:.1f}%",
                        "total_optimizations": total_optimizations,
                    },
                    "configuration": {
                        "batch_operations": BATCH_OPERATIONS,
                        "predictive_polling": (
                            PREDICTIVE_POLLING
                            if "PREDICTIVE_POLLING" in globals()
                            else False
                        ),
                        "min_poll_interval": MIN_POLL_INTERVAL,
                        "max_poll_interval": MAX_POLL_INTERVAL,
                        "exponential_backoff": EXPONENTIAL_BACKOFF,
                        "assistant_cache_duration": ASSISTANT_CACHE_DURATION,
                        "max_context_chars": MAX_CONTEXT_CHARS,
                        "run_cache_duration": RUN_CACHE_DURATION,
                        "response_cache_duration": RESPONSE_CACHE_DURATION,
                    },
                    "recommendations": {
                        "status": (
                            "Excellent"
                            if efficiency_improvement > 60
                            else "Good" if efficiency_improvement > 40 else "Fair"
                        ),
                        "message": f"System is operating at {efficiency_improvement:.0f}% efficiency improvement with {total_optimizations} additional optimizations",
                        "next_steps": [
                            f"Polling reduced by {efficiency_improvement:.0f}%",
                            f"Context checks avoided: {context_cache_hits}",
                            f"Threads reused: {thread_reuses}",
                            f"Response cache hits: {response_cache_hits}",
                        ],
                    },
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/ai/reset-stats", methods=["POST"])
    @login_required
    def reset_ai_stats():
        """Reset AI statistics for fresh monitoring"""
        try:
            global _api_stats
            _api_stats = {
                "total_requests": 0,
                "total_polls": 0,
                "cache_hits": 0,
                "optimization_saves": 0,
                "predictive_hits": 0,  # NEW: Successful predictive polling
                "context_cache_hits": 0,  # NEW: Context checks avoided
                "thread_reuses": 0,  # NEW: Threads reused instead of created
                "response_cache_hits": 0,  # NEW: Response cache hits
            }
            return jsonify({"message": "AI statistics reset successfully"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/ai/performance-config")
    @login_required  
    def get_performance_config():
        """Get current AI performance configuration"""
        try:
            return jsonify({
                "fast_response_enabled": ENABLE_FAST_RESPONSE,
                "fast_response_timeout": FAST_RESPONSE_TIMEOUT,
                "optimization_level": OPTIMIZATION_LEVEL,
                "streaming_enabled": USE_STREAMING,
                "streaming_timeout": STREAMING_TIMEOUT,
                "min_poll_interval": MIN_POLL_INTERVAL,
                "max_poll_interval": MAX_POLL_INTERVAL,
                "recommendations": {
                    "status": "Fast response system enabled for instant user feedback" if ENABLE_FAST_RESPONSE else "Traditional system in use",
                    "expected_improvement": "Responses should appear within 2 seconds max" if ENABLE_FAST_RESPONSE else "Normal OpenAI response times",
                    "fallback": "Traditional system used only if fast response fails" if ENABLE_FAST_RESPONSE else "No fast response fallback"
                }
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500


def format_response(text):
    """Remove all formatting and return plain text only"""
    # Remove all markdown and formatting elements
    text = text.replace("###", "").replace("##", "").replace("#", "")
    text = text.replace("**", "").replace("*", "")
    text = text.replace("___", "").replace("__", "").replace("_", "")
    
    # Remove separators and dividers
    text = text.replace("---", "").replace("===", "").replace("***", "")
    text = text.replace("___", "").replace("...", "")
    
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    
    # Split into lines and process each line
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
            
        # Remove numbered list formatting (1., 2., etc.)
        line = re.sub(r"^\d+\.\s*", "", line)
        
        # Remove bullet points and dashes
        line = re.sub(r"^[-•*]\s*", "", line)
        
        # Remove multiple leading/trailing spaces
        line = line.strip()
        
        if line:
            lines.append(line)
    
    # Join lines with single spaces instead of line breaks for continuous text
    formatted_text = " ".join(lines)
    
    # Clean up multiple spaces
    formatted_text = re.sub(r"\s+", " ", formatted_text)
    
    # Final cleanup
    formatted_text = formatted_text.strip()
    
    return formatted_text


def find_training_video_direct(user_prompt):
    """Direct function to find training videos without Flask request dependency - using cached data"""
    try:
        if not user_prompt:
            return {"videos": [], "video": None}

        user_prompt = user_prompt.lower().strip()

        # Use cached training data instead of loading from file
        try:
            training_guide = get_cached_training_data()
            if not training_guide:
                print(f"No training guide data available")
                return {
                    "videos": [],
                    "video": None,
                    "error": "No training data available",
                }
        except Exception as e:
            print(f"Error getting cached training guide: {str(e)}")
            return {
                "videos": [],
                "video": None,
                "error": "Could not load training guide",
            }

        # Search through training guide sections
        matching_sections = []

        def search_sections(data):
            """Search through the training guide sections"""
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict) and "Reference Videos" in value:
                        # Calculate relevance based on section title
                        relevance_score = calculate_video_relevance(
                            user_prompt, key.lower()
                        )

                        if relevance_score > 0:
                            # Get all videos from Reference Videos
                            videos = value.get("Reference Videos", [])
                            if videos and len(videos) > 0:
                                # Add each video with the section info
                                for video in videos:
                                    matching_sections.append(
                                        {
                                            "title": key.replace("_", " ").title(),
                                            "video": video,
                                            "relevance_score": relevance_score,
                                        }
                                    )

        def calculate_video_relevance(query, section_title):
            """Calculate relevance score for video matching"""
            score = 0
            query_words = query.split()

            # Exact match in section title gets highest score
            if query == section_title:
                score += 200

            # Query appears as a word in the section title
            if query in section_title.split():
                score += 150

            # Query appears anywhere in section title
            if query in section_title:
                score += 100

            # Partial word matches in section title
            for word in query_words:
                if word in section_title:
                    score += 50

            return score

        # Perform the search
        search_sections(training_guide)

        # Sort by relevance score and return all relevant matches
        if matching_sections:
            matching_sections.sort(key=lambda x: x["relevance_score"], reverse=True)

            # Filter to only include videos with sufficient relevance
            relevant_videos = []
            for match in matching_sections:
                if match["relevance_score"] >= 50:  # Minimum threshold for relevance
                    relevant_videos.append(
                        {
                            "title": match["video"]["title"],
                            "url": match["video"]["url"],
                            "topic": match["title"],
                            "relevance_score": match["relevance_score"],
                        }
                    )

            # Return both formats for backward compatibility
            response = {"videos": relevant_videos}

            # Include the best video as 'video' for backward compatibility
            if relevant_videos:
                response["video"] = relevant_videos[0]  # Best match (highest relevance)

            return response

        return {"videos": [], "video": None}

    except Exception as e:
        print(f"Error finding training video: {str(e)}")
        return {"videos": [], "video": None, "error": str(e)}


def create_optimized_enhanced_message(user_message, user_context):
    """Create an optimized enhanced message with concise, targeted training data"""
    try:
        # Start with base message
        enhanced_message = f"User Query: {user_message}"

        # Add concise user context if available
        if user_context.get("name") and user_context["name"] != " ":
            enhanced_message += f"\nPlayer: {user_context['name']}"

            context_details = []
            if user_context.get("current_pti"):
                context_details.append(f"PTI: {user_context['current_pti']}")
            if user_context.get("club") and user_context["club"] != "Unknown":
                context_details.append(f"Club: {user_context['club']}")
            if user_context.get("series") and user_context["series"] != "Unknown":
                context_details.append(f"Series: {user_context['series']}")

            if context_details:
                enhanced_message += f" ({', '.join(context_details)})"

            # Add performance insights if available
            trends = user_context.get("playing_trends", {})
            if trends.get("recent_record"):
                enhanced_message += f"\nRecent: {trends['recent_record']}"

                # Add areas for improvement
                improvements = user_context.get("areas_for_improvement", [])
                if improvements:
                    enhanced_message += (
                        f", Needs work on: {', '.join(improvements[:2])}"  # Max 2 items
                    )

        # Check for training-related keywords
        training_keywords = {
            "serve": ["Serve technique and consistency"],
            "volley": ["Forehand volleys", "Backhand volleys"],
            "overhead": ["Overhead shots"],
            "lob": ["Defensive lobbing", "Offensive lobbing"],
            "return": ["Return of serve"],
            "forehand": ["Forehand groundstrokes", "Forehand volleys"],
            "backhand": ["Backhand groundstrokes", "Backhand volleys"],
            "strategy": ["Match strategy", "Positioning"],
            "positioning": [
                "Court positioning",
                "Understanding and exploiting court geometry",
            ],
            "footwork": ["Footwork patterns"],
            "technique": ["Basic technique fundamentals"],
            "drill": ["Practice drills"],
            "practice": ["Practicing match scenarios"],
        }

        # Find relevant training topics
        message_lower = user_message.lower()
        relevant_topics = []

        for keyword, topics in training_keywords.items():
            if keyword in message_lower:
                relevant_topics.extend(topics)
                break  # Only use first match to keep concise

        # Get specific training data for the most relevant topic
        if relevant_topics:
            try:
                training_data = get_cached_training_data()
                if training_data:
                    topic_name = relevant_topics[0]  # Use most relevant
                    topic_data = training_data.get(topic_name)

                    if topic_data:
                        enhanced_message += f"\n\nTraining Focus: {topic_name}"

                        # Add key fundamentals (concise)
                        recommendations = topic_data.get("Recommendation", [])
                        if recommendations and len(recommendations) > 0:
                            first_rec = recommendations[0]
                            if isinstance(first_rec, dict) and "details" in first_rec:
                                details = first_rec["details"]
                                if details and len(details) > 0:
                                    enhanced_message += f"\nKey Points: {details[0]}"  # Just the first key point

                        # Add one drill
                        drills = topic_data.get("Drills to Improve", [])
                        if drills and len(drills) > 0:
                            drill = drills[0]
                            if isinstance(drill, dict) and "steps" in drill:
                                steps = drill["steps"]
                                if steps and len(steps) > 0:
                                    enhanced_message += (
                                        f"\nDrill: {steps[0]}"  # Just the first step
                                    )

                        # Add one common mistake
                        mistakes = topic_data.get("Common Mistakes & Fixes", [])
                        if mistakes and len(mistakes) > 0:
                            mistake = mistakes[0]
                            if isinstance(mistake, dict):
                                enhanced_message += f"\nCommon Issue: {mistake.get('Mistake', '')} - {mistake.get('Fix', '')}"

                        # Add reference video if available
                        videos = topic_data.get("Reference Videos", [])
                        if videos and len(videos) > 0:
                            video = videos[0]
                            if isinstance(video, dict) and "url" in video:
                                enhanced_message += f"\nVideo: {video.get('title', 'Training Video')} - {video['url']}"
            except Exception as e:
                print(f"WARNING: Error adding training data: {str(e)}")

        enhanced_message += "\n\nProvide specific, actionable advice based on the player's level and recent performance."

        print(
            f"SUCCESS: Optimized enhanced message created: {len(enhanced_message)} chars (vs {len(user_message)} original)"
        )
        return enhanced_message

    except Exception as e:
        print(f"ERROR: Error creating optimized message: {str(e)}")
        return user_message  # Fallback to original message


def get_cached_user_context(user):
    """Get user context with aggressive caching for speed"""
    global _user_context_cache

    user_email = user.get("email", "unknown")
    current_time = time.time()

    # Check cache first
    if user_email in _user_context_cache:
        cached_data = _user_context_cache[user_email]
        if current_time - cached_data["timestamp"] < USER_CONTEXT_CACHE_DURATION:
            print(f"CACHE: User context cache hit for {user_email}")
            return cached_data["context"]

    # Cache miss - get fresh data
    print(f"LOADING: Loading user context for {user_email}")
    user_context = get_user_playing_context(user)

    # Cache the result
    _user_context_cache[user_email] = {
        "context": user_context,
        "timestamp": current_time,
    }

    return user_context


def create_ultra_fast_enhanced_message(user_message, user_context):
    """Create an ultra-fast enhanced message with minimal processing"""
    try:
        # Start with just the message
        enhanced_message = f"User Query: {user_message}"

        # Add only essential user context (no complex processing)
        name = user_context.get("name", "").strip()
        if name and name != " ":
            enhanced_message += f"\nPlayer: {name}"

            # Add only current PTI if available
            pti = user_context.get("current_pti")
            if pti:
                enhanced_message += f" (PTI: {pti})"

            # Add only recent record if available
            trends = user_context.get("playing_trends", {})
            record = trends.get("recent_record")
            if record:
                enhanced_message += f", Recent: {record}"

        # Quick keyword check for training data (simplified)
        message_lower = user_message.lower()
        training_topic = None

        # Simple keyword mapping (fastest possible)
        if "serve" in message_lower:
            training_topic = "Serve technique and consistency"
        elif "volley" in message_lower:
            training_topic = "Forehand volleys"
        elif "lob" in message_lower:
            training_topic = "Defensive lobbing"
        elif "overhead" in message_lower:
            training_topic = "Overhead shots"

        # Add minimal training data if found
        if training_topic:
            try:
                training_data = get_cached_training_data()
                if training_data and training_topic in training_data:
                    topic_data = training_data[training_topic]

                    # Add only one key point and one video (ultra minimal)
                    enhanced_message += f"\n\nTopic: {training_topic}"

                    # Add first recommendation detail
                    recommendations = topic_data.get("Recommendation", [])
                    if recommendations and len(recommendations) > 0:
                        first_rec = recommendations[0]
                        if isinstance(first_rec, dict) and "details" in first_rec:
                            details = first_rec["details"]
                            if details and len(details) > 0:
                                enhanced_message += f"\nKey: {details[0]}"

                    # Add first video with title and URL
                    videos = topic_data.get("Reference Videos", [])
                    if videos and len(videos) > 0:
                        video = videos[0]
                        if isinstance(video, dict) and "url" in video:
                            video_title = video.get("title", "Training Video")
                            enhanced_message += (
                                f"\nVideo: {video_title} - {video['url']}"
                            )
            except Exception as e:
                print(f"WARNING: Quick training data lookup failed: {str(e)}")

        enhanced_message += "\n\nProvide specific advice for this player's level."

        print(f"FAST: Ultra-fast message: {len(enhanced_message)} chars")
        return enhanced_message

    except Exception as e:
        print(f"ERROR: Ultra-fast message failed: {str(e)}")
        return user_message


def prewarm_caches():
    """Pre-warm all caches for maximum speed on first request"""
    try:
        print(f"WARMING: Pre-warming caches for ultra-fast responses...")

        # Pre-warm training data cache
        training_data = get_cached_training_data()
        print(f"SUCCESS: Training data cache warmed: {len(training_data)} topics")

        # Pre-warm assistant cache
        assistant = get_cached_assistant()
        print(f"SUCCESS: Assistant cache warmed: {assistant.id}")

        print(f"COMPLETE: All caches pre-warmed for maximum speed!")

    except Exception as e:
        print(f"WARNING: Cache pre-warming failed: {str(e)}")


def create_fast_response_system(thread_id, user_message, assistant_id):
    """Ultra-fast response system - returns immediately if response takes too long"""
    start_time = time.time()
    
    try:
        # Try to get response quickly
        response_text, poll_count = create_streaming_run(thread_id, assistant_id)
        
        # If we got response quickly, return it
        if time.time() - start_time < FAST_RESPONSE_TIMEOUT:
            return response_text, poll_count, False
        
    except Exception as e:
        print(f"Fast response attempt failed: {str(e)}")
    
    # If taking too long, return processing message
    processing_message = """I'm analyzing your question and preparing a detailed response. This may take a moment...
    
⏳ **Processing your request...**

I'll provide you with:
• Specific technique recommendations
• Training tips tailored to your level
• Relevant practice drills
• Video demonstrations if available

Please wait while I gather the best information for you."""
    
    return processing_message, 1, True  # True indicates this is a processing message

def get_quick_response():
    """Return a quick response when the AI is taking too long"""
    return """Hey there! I'm working on a detailed response for you, but I want to get back to you quickly!

Here are some immediate platform tennis tips that always help:

🎾 **Quick Tips to Get You Started:**
• Focus on your footwork - get to the ball early (this is HUGE!)
• Keep your paddle up and ready at all times (I mean ALL times!)
• Use the back wall strategically for defensive shots (it's your friend!)
• Practice your serve placement and consistency (the serve sets everything up!)

I'm still analyzing your specific question and will provide more detailed advice shortly. What specific aspect of your game would you like to focus on most? Are you working on your serve, volleys, strategy, or something else?"""

def get_cached_quick_response(message):
    """Return cached responses for common questions to avoid API calls"""
    message_lower = message.lower().strip()
    
    # Only use cached responses for very short messages (1-2 words) to avoid generic responses
    if len(message.split()) > 2:
        return get_quick_response()
    
    # More detailed and specific responses for common terms
    quick_responses = {
        "serve": """🎾 **Let's talk about your serve!**

Hey there! I can tell you're thinking about your serve - that's awesome because it's such a crucial part of platform tennis. Let me share some insights that have helped countless players improve their game.

**First, let's nail that toss!** 
You know what I always tell my students? Your toss is like the foundation of a house - if it's not solid, everything else falls apart. Try tossing the ball consistently at 12 o'clock, releasing it at shoulder height with a smooth motion. Aim for about 2-3 feet above your paddle reach. Want a fun drill? Practice 50 tosses daily without even hitting the ball - just focus on that perfect arc!

**Now for the swing...**
Start with your paddle behind your head (not too far back!), then follow through across your body - not down! Use those legs and core for power, and keep your eye on the ball the whole time. Trust me, I've seen so many players lose power because they're not using their whole body.

**Here's a secret:** Mix up your serves! Don't be predictable. Use spin to control placement, aim for those corners and body shots, and practice both flat and spin serves. Your opponents will thank you for keeping them guessing! 😉

**Common mistakes I see:**
• Tossing too low or too high (find that sweet spot!)
• Not following through completely (finish strong!)
• Rushing the motion (slow down, you've got time!)
• Not using your legs for power (get that whole body involved!)

Try practicing 20 serves daily, focusing on just one aspect at a time. You'll be amazed at how quickly you improve! What part of your serve are you working on most right now?""",
        
        "toss": """🎾 **Ah, the toss - the unsung hero of every great serve!**

You know what? I get more questions about the toss than almost anything else, and I totally get it! It seems simple, but it's actually one of the trickiest parts to master. Let me walk you through this step by step.

**Here's the secret to a perfect toss:**
Hold that ball with your fingertips, not your palm - you want control, not a death grip! Toss with a smooth, upward motion, releasing at shoulder height. Aim for about 2-3 feet above your paddle reach, and keep it straight up at 12 o'clock. Think of it like you're gently placing the ball in the perfect spot in the air.

**I see these problems all the time:**
• Tossing too low → The ball drops before you can hit it (frustrating!)
• Tossing too high → Timing becomes a nightmare
• Tossing to the side → Forces you into an awkward swing
• Rushing the toss → Inconsistent placement every time

**Want to know my favorite drill?**
Practice 50 tosses daily without even hitting the ball! Just focus on that perfect arc. Toss and catch to check the height, practice in front of a mirror so you can see your form, and really focus on that smooth, consistent motion.

**Here's the thing:** Your toss should be so consistent that you could hit it with your eyes closed! When you get to that point, everything else becomes so much easier. 

What's your biggest challenge with the toss right now? Are you struggling with height, consistency, or keeping it straight?""",
        
        "volley": """🏓 **Volleying - the heart and soul of platform tennis!**

Oh man, I love talking about volleying! This is where the magic happens in platform tennis. You know what separates good players from great ones? Their volley game. Let me share some secrets that'll have you volleying like a pro!

**First things first - that ready position!**
Keep that paddle up and ready at all times (I mean ALL times!). Knees slightly bent, weight on the balls of your feet, stay light on your feet, and keep those eyes glued to the ball. Think of yourself as a coiled spring, ready to pounce!

**Here's where most people go wrong with their technique:**
Use short, compact strokes - this isn't a groundstroke! Step into the ball for power, keep your paddle face slightly open, and follow through toward your target. I can't tell you how many players I see swinging too big on volleys. Keep it tight and controlled!

**Want to get better fast? Try these drills:**
• Wall practice - rapid fire volleys (my personal favorite!)
• Partner drills - quick exchanges that'll get your heart pumping
• Shadow volleying - practice your form without a ball
• Ball machine work for consistency (if you have access to one)

**Common mistakes I see all the time:**
• Swinging too big (keep it compact!)
• Not stepping into the ball (use that body!)
• Paddle too low in ready position (up and ready!)
• Not watching the ball closely (eyes on the prize!)

**Here's the thing:** The best volleyers are always ready and react quickly! It's like they have a sixth sense for where the ball is going. 

What's your biggest challenge with volleying? Are you struggling with timing, positioning, or just getting to the net in the first place?""",
        
        "strategy": """🧠 **Strategy time - this is where the mental game gets fun!**

You know what I love about platform tennis? It's not just about hitting the ball hard - it's a chess match on the court! Let me share some strategic insights that'll have you thinking like a pro.

**First rule: Control that net!**
Get to the net quickly after serving - don't hang back! Control the net position, use angles to open the court, and force your opponents to hit up. When you're at the net, you're in control. When they're at the net, you're in trouble!

**Here's a secret about shot selection:**
Mix up your shots - don't be predictable! Use the back wall strategically (it's your friend, not your enemy!), create pressure with consistent shots, and always look for opportunities to attack. I see too many players hitting the same shot over and over. Keep your opponents guessing!

**Reading your opponents is like reading a book:**
Watch their paddle position - it tells you everything! Notice their weaknesses and exploit their patterns. Stay one step ahead mentally. Are they always going cross-court? Down the line! Do they hate high balls? Give them high balls!

**Court positioning is everything:**
Cover the middle of the court (that's where most balls go!), communicate with your partner constantly, adjust based on your opponent's strengths, and stay balanced and ready. You should feel like you're dancing out there!

**The mental game:**
Stay focused on each point, don't get frustrated by mistakes (they happen to everyone!), play YOUR game, not theirs, and stay positive and encouraging. Your attitude affects your partner too!

What's your biggest strategic challenge right now? Are you struggling with positioning, shot selection, or reading your opponents?""",
        
        "practice": """💪 **Let's talk practice - the secret sauce to improvement!**

You know what separates good players from great ones? It's not just talent - it's how they practice! I've seen players with average natural ability become absolute beasts because they practice smart. Let me share some insights that'll supercharge your practice sessions.

**Here's my ideal daily practice routine (just 30 minutes!):**
• 10 minutes: Serving practice (focus on one thing - maybe your toss today)
• 10 minutes: Wall work for consistency (this is gold for your game!)
• 10 minutes: Specific skill focus (pick one weakness and attack it!)

**For your weekly practice:**
• 2-3 match play sessions (this is where you test everything!)
• 1 lesson with a pro (fresh eyes see things you miss!)
• Video analysis of your technique (record yourself - it's eye-opening!)
• Practice with different partners (everyone plays differently!)

**Want some specific drills that actually work?**
• Serving: 20 serves focusing just on your toss (quality over quantity!)
• Volleying: Wall practice, rapid fire (get those reflexes sharp!)
• Groundstrokes: Cross-court consistency (boring but effective!)
• Movement: Footwork drills (ladder work is amazing!)

**Here's the thing about practice:**
Focus on one skill at a time - don't try to fix everything at once! Practice with purpose, not just hitting balls around. Record yourself to see improvements (trust me, you'll be surprised!). And play with better players when possible - they'll push you to improve!

**My golden rule:** Quality practice beats quantity every time! I'd rather see you practice 20 minutes with focus than 2 hours just going through the motions.

What's your biggest challenge with practice? Are you struggling to find time, stay focused, or know what to work on?""",
        
        "grip": """🤏 **The grip - your connection to the ball!**

You know what? I get asked about grip more than you'd think, and honestly, it's one of those things that seems simple but makes a HUGE difference in your game. Let me break this down for you in a way that'll make sense.

**Here's the basic grip that works for most people:**
Hold your paddle like you're shaking hands with it - that's the easiest way to remember! You want that V between your thumb and index finger pointing toward your shoulder. Keep it relaxed but firm - no death grip! Stay loose, my friend.

**Now, here's where it gets interesting - grip pressure:**
• Light grip for touch shots (those delicate drop shots!)
• Firm grip for power shots (when you want to crush it!)
• Adjust pressure based on the shot you're hitting
• Relax between points (don't carry tension!)

**I see these grip mistakes ALL the time:**
• Gripping too tight (your arm will thank you for loosening up!)
• Wrong V position (it affects everything!)
• Not adjusting for different shots (one size doesn't fit all!)
• Holding too high on the handle (you lose power and control!)

**Want to practice your grip? Try these drills:**
• Shadow swings with proper grip (feel that connection!)
• Wall practice focusing on grip (repetition is key!)
• Different shots, same grip (consistency is everything!)
• Grip pressure exercises (light, firm, light, firm!)

**Here's the thing:** Your grip is your connection to the ball - make it consistent! When your grip is right, everything else becomes easier. When it's wrong, you're fighting against yourself.

What's your biggest challenge with your grip? Are you gripping too tight, struggling with consistency, or not sure if you're doing it right?""",
        
        "footwork": """👟 **Footwork - the foundation of everything!**

Oh man, footwork! This is one of those things that separates the good players from the great ones, and honestly, most people don't think about it enough. But here's the thing - great footwork makes EVERY shot easier! Let me share some secrets that'll have you moving like a pro.

**First, let's nail that ready position:**
Knees slightly bent, weight on the balls of your feet, stay light and balanced, and be ready to move in any direction. Think of yourself as a coiled spring - ready to explode in any direction the ball goes!

**Here's how to move like a pro:**
• Small, quick steps (don't take those giant strides!)
• Stay on your toes (light on your feet!)
• Don't cross your feet (you'll lose balance!)
• Recover to center after each shot (get back to your base!)

**Court coverage is everything:**
Split step before your opponent hits (this is HUGE!), move to the ball early, get in position before swinging, and use those legs for power. I see so many players trying to hit shots from bad positions - get your feet there first!

**Common footwork mistakes I see:**
• Standing flat-footed (you'll be late to everything!)
• Taking too big steps (you'll lose balance!)
• Not recovering to center (you'll be out of position!)
• Poor balance during shots (you'll miss more than you hit!)

**Want to improve your footwork fast? Try these drills:**
• Ladder drills for quickness (so much fun!)
• Shadow footwork practice (no ball needed!)
• Court coverage exercises (work those angles!)
• Balance and agility work (your body will thank you!)

**Here's the thing:** Great footwork makes every shot easier! When your feet are in the right place, your shots become more powerful, more accurate, and more consistent. It's like having a superpower!

What's your biggest footwork challenge? Are you struggling with quickness, balance, or just knowing where to move on the court?"""
    }
    
    # Check for keyword matches
    for keyword, response in quick_responses.items():
        if keyword in message_lower:
            return response
    
    # Default quick response
    return get_quick_response()

def get_lightweight_user_context(user):
    """Get minimal user context without expensive database queries"""
    return {
        "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        "email": user.get("email", "unknown"),
        "club": user.get("club", "Unknown"),
        "series": user.get("series", "Unknown"),
        # Skip expensive database queries for speed
    }

def create_ultra_fast_enhanced_message_minimal(user_message, user_context):
    """Create enhanced message with minimal context for speed"""
    player_name = user_context.get("name", "Player")
    club = user_context.get("club", "Unknown")
    series = user_context.get("series", "Unknown")
    
    return f"""Player: {player_name} from {club} ({series})
Question: {user_message}

Please provide specific, actionable advice for this paddle tennis question."""
