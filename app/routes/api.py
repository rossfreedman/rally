import json
from flask import Blueprint, jsonify, current_app
from pathlib import Path

api = Blueprint('api', __name__)

@api.route('/api/match-history', methods=['GET'])
def get_match_history():
    try:
        # Get the absolute path to the data directory
        data_path = Path(current_app.root_path).parent / 'data' / 'match_history.json'
        with open(data_path, 'r') as f:
            matches = json.load(f)
        return jsonify(matches)
    except Exception as e:
        current_app.logger.error(f"Error loading match history: {str(e)}")
        return jsonify({'error': str(e)}), 500 