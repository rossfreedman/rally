"""
Act routes package initialization
"""

from .availability import init_availability_routes
from .schedule import init_schedule_routes
from .lineup import init_lineup_routes
from .find_sub import init_find_sub_routes
from .find_people_to_play import init_find_people_to_play_routes
from .rally_ai import init_rally_ai_routes
# Legacy auth routes removed - using modern auth_bp blueprint instead
# from .auth import init_routes as init_auth_routes
from .settings import init_routes as init_settings_routes
from .court import init_routes as init_court_routes

def init_act_routes(app):
    """Initialize all act routes"""
    init_availability_routes(app)
    init_schedule_routes(app)
    init_lineup_routes(app)
    init_find_sub_routes(app)
    init_find_people_to_play_routes(app)
    init_rally_ai_routes(app)
    # init_auth_routes(app)  # Removed - using modern auth_bp blueprint
    init_settings_routes(app)
    init_court_routes(app)

__all__ = [
    'init_act_routes',
    'init_availability_routes',
    'init_schedule_routes',
    'init_lineup_routes',
    'init_find_sub_routes',
    'init_find_people_to_play_routes',
    'init_rally_ai_routes',
    # 'init_auth_routes',  # Removed - using modern auth_bp blueprint
    'init_settings_routes',
    'init_court_routes'
] 