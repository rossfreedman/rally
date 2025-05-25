"""
Training Data API Module

This module provides structured access to platform tennis training data
for the OpenAI Assistant. It eliminates URL hallucination by providing
exact data retrieval from the training guide JSON file.

The main endpoint `/api/get-training-data-by-topic` is designed to be used
as a function tool by the OpenAI Assistant.
"""

import json
import os
import logging
import traceback
from flask import Blueprint, request, jsonify

# Create blueprint for training data routes
training_data_bp = Blueprint('training_data', __name__)

# Set up logging
logger = logging.getLogger(__name__)

def load_training_data():
    """
    Load the complete platform tennis training guide from JSON file.
    
    Returns:
        dict: The training data dictionary
        
    Raises:
        FileNotFoundError: If the training guide file is not found
        json.JSONDecodeError: If the JSON file is malformed
    """
    # Get the path to the training guide file
    # Assuming this module is in api/ and data/ is at the root level
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    training_guide_path = os.path.join(project_root, 'data', 'complete_platform_tennis_training_guide.json')
    
    with open(training_guide_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_topic_data(training_data, topic):
    """
    Find training data for a specific topic with fuzzy matching.
    
    Args:
        training_data (dict): The complete training data dictionary
        topic (str): The topic to search for
        
    Returns:
        tuple: (topic_key, topic_data) if found, (None, None) if not found
    """
    topic_lower = topic.lower().strip()
    
    # First try exact match (case-insensitive)
    for key in training_data.keys():
        if key.lower() == topic_lower:
            return key, training_data[key]
    
    # If no exact match, try partial match
    for key in training_data.keys():
        key_lower = key.lower()
        if topic_lower in key_lower or key_lower in topic_lower:
            return key, training_data[key]
    
    # Try matching individual words
    topic_words = topic_lower.split()
    best_match = None
    best_score = 0
    
    for key in training_data.keys():
        key_lower = key.lower()
        score = 0
        for word in topic_words:
            if word in key_lower:
                score += 1
        
        if score > best_score and score >= len(topic_words) // 2:  # At least half the words match
            best_score = score
            best_match = (key, training_data[key])
    
    return best_match if best_match else (None, None)

@training_data_bp.route('/api/get-training-data-by-topic', methods=['POST'])
def get_training_data_by_topic():
    """
    Function tool endpoint for OpenAI Assistant to retrieve structured platform tennis training data.
    
    This endpoint is designed to be called by the OpenAI Assistant when it needs exact training data
    for a specific topic. It eliminates URL hallucination by providing structured data directly
    from the JSON file.
    
    Request JSON:
        {
            "topic": "string - The topic name to retrieve (e.g., 'Serve technique and consistency')"
        }
    
    Response JSON:
        Success (200):
        {
            "topic": "string - The exact topic key found",
            "data": {
                "Title": "string",
                "Recommendation": [...],
                "Drills to Improve": [...],
                "Common Mistakes & Fixes": [...],
                "Coach's Cues": [...],
                "Reference Videos": [...]
            }
        }
        
        Error (400/404/500):
        {
            "error": "string - Error description",
            "available_topics_sample": [...] (only for 404),
            "total_topics": number (only for 404)
        }
    """
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided in request body'}), 400
            
        topic = data.get('topic', '').strip()
        if not topic:
            return jsonify({'error': 'Topic parameter is required and cannot be empty'}), 400
        
        # Load training data
        try:
            training_data = load_training_data()
        except FileNotFoundError:
            logger.error("Training guide data file not found")
            return jsonify({'error': 'Training guide data file not found'}), 404
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in training guide file: {str(e)}")
            return jsonify({'error': 'Invalid JSON in training guide file'}), 500
        
        # Find the topic data
        topic_key, topic_data = find_topic_data(training_data, topic)
        
        if not topic_data:
            # Return helpful error with available topics
            available_topics = list(training_data.keys())[:10]  # First 10 topics as sample
            logger.warning(f"Topic '{topic}' not found in training data")
            return jsonify({
                'error': f'Topic "{topic}" not found',
                'available_topics_sample': available_topics,
                'total_topics': len(training_data),
                'suggestion': 'Try searching for topics like "serve", "volley", "overhead", "backhand", etc.'
            }), 404
        
        # Prepare response data
        response_data = {
            'topic': topic_key,
            'data': topic_data
        }
        
        # Log successful retrieval
        logger.info(f"Training data successfully retrieved for topic: '{topic_key}' (requested: '{topic}')")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        # Log the full error for debugging
        error_msg = f"Unexpected error in get_training_data_by_topic: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        return jsonify({
            'error': 'Internal server error occurred while retrieving training data',
            'details': str(e) if logger.level <= logging.DEBUG else None
        }), 500

@training_data_bp.route('/api/training-topics', methods=['GET'])
def get_training_topics():
    """
    Get a list of all available training topics.
    
    This endpoint can be used for debugging or to see what topics are available
    in the training data.
    
    Response JSON:
        {
            "topics": ["topic1", "topic2", ...],
            "total_count": number
        }
    """
    try:
        training_data = load_training_data()
        topics = list(training_data.keys())
        
        return jsonify({
            'topics': topics,
            'total_count': len(topics)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving training topics: {str(e)}")
        return jsonify({'error': 'Failed to retrieve training topics'}), 500

@training_data_bp.route('/api/training-data-health', methods=['GET'])
def training_data_health():
    """
    Health check endpoint for the training data API.
    
    Response JSON:
        {
            "status": "healthy" | "error",
            "message": "string",
            "data_file_exists": boolean,
            "total_topics": number (if file exists)
        }
    """
    try:
        training_data = load_training_data()
        return jsonify({
            'status': 'healthy',
            'message': 'Training data API is working correctly',
            'data_file_exists': True,
            'total_topics': len(training_data)
        }), 200
        
    except FileNotFoundError:
        return jsonify({
            'status': 'error',
            'message': 'Training data file not found',
            'data_file_exists': False
        }), 404
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Training data API error: {str(e)}',
            'data_file_exists': False
        }), 500 