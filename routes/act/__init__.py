"""
Action-based route handlers for the Rally application.
"""

from .availability import init_availability_routes
from .schedule import init_schedule_routes
from .lineup import init_lineup_routes
from .find_sub import init_find_sub_routes
from .rally_ai import init_rally_ai_routes
from .auth import init_routes as init_auth_routes
from .settings import init_routes as init_settings_routes
from .court import init_routes as init_court_routes

__all__ = [
    'init_availability_routes',
    'init_schedule_routes',
    'init_lineup_routes',
    'init_find_sub_routes',
    'init_rally_ai_routes',
    'init_auth_routes',
    'init_settings_routes',
    'init_court_routes'
] 