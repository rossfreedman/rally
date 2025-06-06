# Training Data API Module

## Overview

This module provides structured access to platform tennis training data for the OpenAI Assistant. It eliminates URL hallucination by providing exact data retrieval from the training guide JSON file instead of relying on vector search and reasoning.

## Problem Solved

**Before**: The OpenAI Assistant would use vector search to retrieve training data chunks, then "reason over" those chunks, leading to:
- URL hallucination (incorrect or modified YouTube URLs)
- Partial matches and broken data across embeddings
- Assistant guessing based on training data instead of using exact data

**After**: The Assistant calls a structured function tool that:
- Returns exact JSON data with zero hallucination
- Preserves all URLs exactly as stored in the source file
- Provides complete, structured training information

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   OpenAI        │    │   Flask API      │    │   JSON Training     │
│   Assistant     │───▶│   Function Tool  │───▶│   Data File         │
│                 │    │   (Structured)   │    │   (Source of Truth) │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
```

## Files Structure

```
api/
├── __init__.py                    # Module initialization
├── training_data.py              # Main API blueprint
├── test_training_data_api.py     # Test suite
└── README.md                     # This documentation
```

## API Endpoints

### 1. Get Training Data by Topic
**Endpoint**: `POST /api/get-training-data-by-topic`

**Purpose**: Main function tool endpoint for OpenAI Assistant

**Request**:
```json
{
    "topic": "Serve technique and consistency"
}
```

**Response** (Success):
```json
{
    "topic": "Serve technique and consistency",
    "data": {
        "Title": "Step-by-Step Technique (Beginner → Advanced)",
        "Recommendation": [...],
        "Drills to Improve": [...],
        "Common Mistakes & Fixes": [...],
        "Coach's Cues": [...],
        "Reference Videos": [
            {
                "title": "Platform Tennis Serve Fundamentals",
                "url": "https://www.youtube.com/watch?v=3mfRU8A9oG0"
            }
        ]
    }
}
```

**Response** (Error):
```json
{
    "error": "Topic 'xyz' not found",
    "available_topics_sample": ["Serve technique and consistency", ...],
    "total_topics": 65,
    "suggestion": "Try searching for topics like 'serve', 'volley', 'overhead', 'backhand', etc."
}
```

### 2. Get All Training Topics
**Endpoint**: `GET /api/training-topics`

**Purpose**: List all available training topics (for debugging)

**Response**:
```json
{
    "topics": ["Serve technique and consistency", "Forehand volleys", ...],
    "total_count": 65
}
```

### 3. Health Check
**Endpoint**: `GET /api/training-data-health`

**Purpose**: Verify the API and data file are working

**Response**:
```json
{
    "status": "healthy",
    "message": "Training data API is working correctly",
    "data_file_exists": true,
    "total_topics": 65
}
```

## Features

### Smart Topic Matching
The API uses intelligent matching to find topics:

1. **Exact Match**: `"Serve technique and consistency"` → `"Serve technique and consistency"`
2. **Partial Match**: `"serve"` → `"Serve technique and consistency"`
3. **Word Matching**: `"volley"` → `"Forehand volleys"`

### Error Handling
- Validates request format
- Provides helpful error messages
- Suggests alternative topics when not found
- Logs all operations for debugging

### Zero Hallucination
- Reads directly from JSON file
- No AI reasoning or interpretation
- Preserves exact URLs and data structure
- Returns complete structured data

## Integration with OpenAI Assistant

### Function Tool Configuration
Add this function tool to your OpenAI Assistant:

```json
{
    "name": "get_training_data_by_topic",
    "description": "Returns platform tennis training data for a specific topic.",
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The exact topic name to retrieve, such as 'Serve technique and consistency'"
            }
        },
        "required": ["topic"]
    }
}
```

### Usage Example
When a user asks: *"What are the key drills for improving my serve?"*

The Assistant will:
1. Call `get_training_data_by_topic` with `{"topic": "serve"}`
2. Receive exact structured data including drills, videos, and tips
3. Format the response with accurate URLs and complete information

## Testing

Run the test suite:
```bash
python api/test_training_data_api.py
```

The test suite includes:
- Module functionality testing (without server)
- API endpoint testing (requires running server)
- Error handling validation
- URL preservation verification

## Installation & Setup

### 1. Install Dependencies
The module uses standard Flask dependencies already in your project.

### 2. Register Blueprint
In your main `server.py`:
```python
from api.training_data import training_data_bp
app.register_blueprint(training_data_bp)
```

### 3. Verify Setup
1. Start your Flask server
2. Run the test suite
3. Check the health endpoint: `GET /api/training-data-health`

## Data Source

The API reads from: `data/complete_platform_tennis_training_guide.json`

This file contains 65 training topics with structured data including:
- Step-by-step recommendations
- Practice drills
- Common mistakes and fixes
- Coach's cues
- Reference videos with exact YouTube URLs

## Benefits

1. **Eliminates URL Hallucination**: URLs are preserved exactly as stored
2. **Complete Data**: Returns full structured information, not fragments
3. **Reliable**: No AI interpretation or reasoning errors
4. **Fast**: Direct file access, no vector search overhead
5. **Debuggable**: Clear error messages and logging
6. **Modular**: Separate from main server code for maintainability

## Troubleshooting

### Common Issues

**"Training guide data file not found"**
- Ensure `data/complete_platform_tennis_training_guide.json` exists
- Check file permissions

**"Topic not found"**
- Use the `/api/training-topics` endpoint to see available topics
- Try partial matches (e.g., "serve" instead of full topic name)

**Import errors**
- Ensure the `api` directory has `__init__.py`
- Check that the blueprint is properly registered in `server.py`

### Debugging

Enable debug logging to see detailed operation logs:
```python
import logging
logging.getLogger('api.training_data').setLevel(logging.DEBUG)
```

## Future Enhancements

Potential improvements:
1. Caching for better performance
2. Topic search with fuzzy matching
3. Category-based filtering
4. Video availability checking
5. Usage analytics and popular topics tracking 