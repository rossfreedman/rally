"""
Analysis-based route handlers for the Rally application.
"""

from .competition import init_routes as init_competition_routes
from .me import init_routes as init_me_routes
from .my_team import init_routes as init_my_team_routes
from .my_series import init_routes as init_my_series_routes
from .my_club import init_routes as init_my_club_routes

def init_analyze_routes(app):
    """Initialize all analyze routes"""
    init_competition_routes(app)
    init_me_routes(app)
    init_my_team_routes(app)
    init_my_series_routes(app)
    init_my_club_routes(app)

__all__ = [
    'init_analyze_routes',
    'init_competition_routes',
    'init_me_routes',
    'init_my_team_routes',
    'init_my_series_routes',
    'init_my_club_routes'
] 