"""
Route Validation Utilities

This module provides utilities to detect duplicate routes and prevent conflicts
between blueprints and direct app routes.
"""

import logging
from flask import Flask
from collections import defaultdict
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

class RouteConflictDetector:
    """Detects and reports route conflicts in Flask applications"""
    
    def __init__(self):
        self.routes = defaultdict(list)
        self.conflicts = []
    
    def analyze_app_routes(self, app: Flask) -> Dict[str, any]:
        """
        Analyze all routes registered in the Flask app and detect conflicts
        
        Returns:
            Dict containing analysis results and conflicts
        """
        self.routes.clear()
        self.conflicts.clear()
        
        # Collect all routes
        for rule in app.url_map.iter_rules():
            endpoint = rule.endpoint
            methods = sorted(rule.methods - {'HEAD', 'OPTIONS'})  # Exclude auto-added methods
            route_key = f"{rule.rule}::{':'.join(methods)}"
            
            self.routes[route_key].append({
                'endpoint': endpoint,
                'rule': rule.rule,
                'methods': methods,
                'blueprint': self._extract_blueprint_name(endpoint)
            })
        
        # Find conflicts
        for route_key, route_list in self.routes.items():
            if len(route_list) > 1:
                self.conflicts.append({
                    'route': route_key,
                    'conflicting_endpoints': route_list
                })
        
        return {
            'total_routes': len(self.routes),
            'conflicts': self.conflicts,
            'routes_by_blueprint': self._group_routes_by_blueprint()
        }
    
    def _extract_blueprint_name(self, endpoint: str) -> str:
        """Extract blueprint name from endpoint"""
        if '.' in endpoint:
            return endpoint.split('.')[0]
        return 'main_app'
    
    def _group_routes_by_blueprint(self) -> Dict[str, List[str]]:
        """Group routes by blueprint for organization"""
        blueprint_routes = defaultdict(list)
        
        for route_key, route_list in self.routes.items():
            for route_info in route_list:
                blueprint = route_info['blueprint']
                blueprint_routes[blueprint].append(route_info['rule'])
        
        return dict(blueprint_routes)
    
    def log_conflicts(self):
        """Log all detected conflicts"""
        if not self.conflicts:
            logger.info("✅ No route conflicts detected")
            return
        
        logger.warning(f"⚠️  Found {len(self.conflicts)} route conflicts:")
        for i, conflict in enumerate(self.conflicts, 1):
            logger.warning(f"\n  Conflict #{i}: {conflict['route']}")
            for endpoint_info in conflict['conflicting_endpoints']:
                blueprint = endpoint_info['blueprint']
                endpoint = endpoint_info['endpoint']
                logger.warning(f"    - {blueprint}.{endpoint} ({endpoint_info['methods']})")
    
    def print_route_summary(self):
        """Print a summary of all routes organized by blueprint"""
        analysis = self.analyze_app_routes(self.app) if hasattr(self, 'app') else None
        
        if not analysis:
            return
        
        print("\n" + "="*60)
        print("ROUTE SUMMARY")
        print("="*60)
        
        for blueprint, routes in analysis['routes_by_blueprint'].items():
            print(f"\n📁 {blueprint.upper()}")
            print("-" * 40)
            for route in sorted(set(routes)):
                print(f"  {route}")
        
        print(f"\n📊 TOTAL ROUTES: {analysis['total_routes']}")
        if analysis['conflicts']:
            print(f"⚠️  CONFLICTS: {len(analysis['conflicts'])}")
        else:
            print("✅ NO CONFLICTS")
        print("="*60)

def validate_routes_on_startup(app: Flask) -> bool:
    """
    Validate routes on application startup
    
    Args:
        app: Flask application instance
        
    Returns:
        True if no conflicts, False if conflicts found
    """
    detector = RouteConflictDetector()
    detector.app = app
    analysis = detector.analyze_app_routes(app)
    
    # Log the summary
    detector.log_conflicts()
    
    # Print detailed summary in development
    import os
    if os.environ.get('FLASK_ENV') == 'development':
        detector.print_route_summary()
    
    return len(analysis['conflicts']) == 0

def get_routes_documentation(app: Flask) -> str:
    """
    Generate documentation of all routes
    
    Args:
        app: Flask application instance
        
    Returns:
        Formatted string with route documentation
    """
    detector = RouteConflictDetector()
    analysis = detector.analyze_app_routes(app)
    
    docs = ["# Route Documentation\n"]
    docs.append(f"Total routes: {analysis['total_routes']}\n")
    
    if analysis['conflicts']:
        docs.append("## ⚠️ CONFLICTS DETECTED\n")
        for conflict in analysis['conflicts']:
            docs.append(f"### {conflict['route']}\n")
            for endpoint in conflict['conflicting_endpoints']:
                docs.append(f"- {endpoint['blueprint']}.{endpoint['endpoint']}\n")
        docs.append("\n")
    
    docs.append("## Routes by Blueprint\n")
    for blueprint, routes in analysis['routes_by_blueprint'].items():
        docs.append(f"### {blueprint}\n")
        for route in sorted(set(routes)):
            docs.append(f"- `{route}`\n")
        docs.append("\n")
    
    return "".join(docs) 