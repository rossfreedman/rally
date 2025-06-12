# Route Organization & Conflict Prevention

This document outlines the strategy for organizing routes in the Rally application to prevent conflicts and maintain clean architecture.

## Route Structure

### Blueprint Organization
- **`api_bp`** (`/api/*`) - All API endpoints
- **`auth_bp`** (`/auth/*`, `/login`, `/signup`) - Authentication routes  
- **`admin_bp`** (`/admin/*`) - Admin interface routes
- **`mobile_bp`** (`/mobile/*`) - Mobile interface routes
- **`player_bp`** (`/player/*`) - Player-specific routes
- **Direct app routes** - Core application routes (`/`, `/health/*`)

### Legacy Act Routes
The `routes/act/` directory contains legacy routes that register directly with the app. These should be gradually migrated to blueprints.

## Conflict Prevention Strategies

### 1. Route Validation on Startup
- Automatic detection of duplicate routes
- Logs conflicts with blueprint information
- Development mode shows detailed route summary

### 2. Blueprint Prefixing
Each blueprint should use consistent URL prefixes:
```python
# Good - Clear prefixing
@api_bp.route('/api/players')
@mobile_bp.route('/mobile/dashboard')
@admin_bp.route('/admin/users')

# Bad - Could conflict
@some_bp.route('/players')  # What if another blueprint has this?
```

### 3. Route Documentation
- `/health/routes` endpoint provides real-time route information
- Automatic conflict detection and reporting
- Blueprint organization visibility

## Migration Plan

### Phase 1: Document Current State ✅
- [x] Create route validation utilities
- [x] Add startup conflict detection
- [x] Document blueprint organization

### Phase 2: Fix Immediate Conflicts
- [x] Remove duplicate `/api/get-series` endpoints
- [ ] Audit other potential conflicts
- [ ] Standardize endpoint naming

### Phase 3: Blueprint Migration
Move remaining direct app routes to appropriate blueprints:

#### Routes to Migrate:
```python
# From routes/act/settings.py
@app.route('/api/get-series') → @api_bp.route('/api/get-series')
@app.route('/api/set-series') → @api_bp.route('/api/set-series')
@app.route('/api/get-user-settings') → @api_bp.route('/api/get-user-settings')
@app.route('/api/update-settings') → @api_bp.route('/api/update-settings')

# From routes/act/find_people_to_play.py  
@app.route('/api/club-players') → @api_bp.route('/api/club-players')

# From other act modules
# Similar pattern for all /api/* routes
```

## Best Practices

### Route Naming Conventions
```python
# API endpoints
/api/{resource}           # GET collection
/api/{resource}/{id}      # GET/PUT/DELETE single item
/api/{resource}/{id}/{sub_resource}  # Nested resources

# Page endpoints  
/mobile/{page}           # Mobile pages
/admin/{page}            # Admin pages
/{page}                  # Desktop pages
```

### Blueprint Registration Order
Blueprints should be registered in this order to prevent conflicts:
1. Most specific routes first (longer prefixes)
2. API blueprints before page blueprints
3. Legacy direct routes last

### Conflict Detection
```python
# In server.py - automatic validation
has_no_conflicts = validate_routes_on_startup(app)
if not has_no_conflicts:
    print("⚠️  Route conflicts detected!")
```

## Development Tools

### Check Routes
```bash
# View all routes and conflicts
curl http://localhost:8080/health/routes

# Start server with detailed route logging
FLASK_ENV=development python server.py
```

### Add New Routes
1. Always use appropriate blueprint
2. Follow naming conventions  
3. Test for conflicts with route validation
4. Update this documentation

## Emergency Conflict Resolution

If you encounter route conflicts:

1. **Identify the conflict** - Check server logs or `/health/routes`
2. **Determine the correct owner** - Which blueprint should own the route?
3. **Remove duplicates** - Delete the incorrect route definition
4. **Test thoroughly** - Ensure functionality still works
5. **Update documentation** - Record the change

## Future Improvements

- [ ] Automated testing for route conflicts in CI/CD
- [ ] Route deprecation system for safe migrations
- [ ] Blueprint-level middleware for common functionality
- [ ] OpenAPI documentation generation from routes 