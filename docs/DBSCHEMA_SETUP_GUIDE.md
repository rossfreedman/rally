# DbSchema Setup Guide for Rally Platform

## Overview

This guide sets up DbSchema for visual database management and syncing between your local PostgreSQL database and Railway production/staging environments.

## Prerequisites

- DbSchema installed locally ✅
- PostgreSQL running locally
- Railway account with database access
- Environment variables configured (`.env` file)

## Database Connections Setup

### 1. Local Database Connection

Create a new connection in DbSchema:

**Connection Name:** `Rally Local`
**Database Type:** PostgreSQL
**Driver:** PostgreSQL JDBC Driver
**Connection Details:**
```
Host: localhost
Port: 5432
Database: rally
Username: rossfreedman (or your local username)
Password: (your local PostgreSQL password)
```

**Advanced Settings:**
```
SSL Mode: prefer
Application Name: dbschema_rally_local
```

### 2. Railway Production Database Connection

**Connection Name:** `Rally Production (Railway)`
**Database Type:** PostgreSQL
**Driver:** PostgreSQL JDBC Driver

**Get Railway Database URL:**
```bash
# From your Railway dashboard or use:
railway variables
```

**Parse your DATABASE_PUBLIC_URL and configure:**
```
Host: (from your Railway DATABASE_PUBLIC_URL)
Port: (usually 5432)
Database: railway
Username: postgres
Password: (from your Railway DATABASE_PUBLIC_URL)
SSL Mode: require
```

**JDBC URL Format:**
```
jdbc:postgresql://[host]:[port]/railway?sslmode=require&user=[username]&password=[password]
```

### 3. Railway Staging Database Connection (if applicable)

**Connection Name:** `Rally Staging (Railway)`
- Use same configuration as production but with staging database credentials

## DbSchema Project Setup

### 1. Create New Project

1. Open DbSchema
2. File → New Project
3. Name: `Rally Database`
4. Save location: `[workspace]/database_schema/rally_schema.dbs`

### 2. Import Database Schema

**For Local Database:**
1. Connect to `Rally Local`
2. Database → Reverse Engineer
3. Select all tables and relationships
4. Generate visual schema

**Key Tables to Verify:**
- `users` - Authentication and user profiles
- `leagues` - League organizations (APTA_CHICAGO, NSTF, etc.)
- `clubs` - Tennis clubs/facilities  
- `series` - Series/divisions within leagues
- `teams` - Team entities (club + series + league)
- `players` - League-specific player records
- `user_player_associations` - User-player linking table
- `match_scores` - Match results and scores
- `schedule` - Match scheduling
- `series_stats` - Team statistics by series
- `polls` - Team voting system
- `player_availability` - Player availability tracking

### 3. Configure Schema Synchronization

## Environment-Specific Configuration Scripts

Create these helper scripts in your `data/dbschema/` directory:

### Database Connection Validator

```python
# data/dbschema/validate_dbschema_connections.py
import os
import psycopg2
from dotenv import load_dotenv
from database_config import get_db_url, parse_db_url

load_dotenv()

def test_connection(name, url):
    """Test database connection for DbSchema setup"""
    try:
        db_params = parse_db_url(url)
        conn = psycopg2.connect(**db_params)
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"✅ {name}: Connected successfully")
            print(f"   PostgreSQL: {version}")
            
            # Test key tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            print(f"   Tables: {len(tables)} found")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ {name}: Connection failed - {str(e)}")
        return False

def main():
    print("🔍 Validating database connections for DbSchema setup...\n")
    
    # Test local connection
    local_url = "postgresql://localhost/rally"
    test_connection("Local Database", local_url)
    
    print()
    
    # Test Railway production
    if os.getenv("DATABASE_PUBLIC_URL"):
        test_connection("Railway Production", os.getenv("DATABASE_PUBLIC_URL"))
    else:
        print("❌ Railway Production: DATABASE_PUBLIC_URL not configured")
    
    print()
    
    # Test Railway staging (if configured)
    if os.getenv("DATABASE_STAGING_URL"):
        test_connection("Railway Staging", os.getenv("DATABASE_STAGING_URL"))

if __name__ == "__main__":
    main()
```

### Schema Comparison Script

```python
# data/dbschema/compare_schemas_dbschema.py
import psycopg2
from database_config import parse_db_url
import json
import os
from datetime import datetime

def get_schema_info(connection_params, environment_name):
    """Extract comprehensive schema information"""
    try:
        conn = psycopg2.connect(**connection_params)
        schema_info = {
            "environment": environment_name,
            "timestamp": datetime.now().isoformat(),
            "tables": {},
            "indexes": {},
            "constraints": {}
        }
        
        with conn.cursor() as cursor:
            # Get table information
            cursor.execute("""
                SELECT 
                    t.table_name,
                    t.table_type,
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    c.ordinal_position
                FROM information_schema.tables t
                LEFT JOIN information_schema.columns c ON t.table_name = c.table_name
                WHERE t.table_schema = 'public'
                ORDER BY t.table_name, c.ordinal_position
            """)
            
            current_table = None
            for row in cursor.fetchall():
                table_name, table_type, col_name, data_type, nullable, default, position = row
                
                if table_name not in schema_info["tables"]:
                    schema_info["tables"][table_name] = {
                        "type": table_type,
                        "columns": {}
                    }
                
                if col_name:  # Skip if no columns (shouldn't happen)
                    schema_info["tables"][table_name]["columns"][col_name] = {
                        "data_type": data_type,
                        "nullable": nullable,
                        "default": default,
                        "position": position
                    }
            
            # Get foreign key constraints
            cursor.execute("""
                SELECT 
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    tc.constraint_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
            """)
            
            for row in cursor.fetchall():
                table, column, ref_table, ref_column, constraint_name = row
                constraint_key = f"{table}.{column} -> {ref_table}.{ref_column}"
                schema_info["constraints"][constraint_key] = {
                    "type": "FOREIGN KEY",
                    "constraint_name": constraint_name
                }
        
        conn.close()
        return schema_info
        
    except Exception as e:
        print(f"Error getting schema for {environment_name}: {str(e)}")
        return None

def compare_schemas():
    """Compare schemas between environments"""
    print("🔍 Comparing database schemas for DbSchema sync validation...\n")
    
    # Get local schema
    local_params = {
        "host": "localhost",
        "port": 5432,
        "dbname": "rally",
        "user": "rossfreedman"  # Adjust as needed
    }
    
    local_schema = get_schema_info(local_params, "local")
    
    # Get Railway schema (if configured)
    railway_url = os.getenv("DATABASE_PUBLIC_URL")
    if railway_url:
        from database_config import parse_db_url
        railway_params = parse_db_url(railway_url)
        railway_schema = get_schema_info(railway_params, "railway")
        
        if local_schema and railway_schema:
            # Compare table counts
            local_tables = set(local_schema["tables"].keys())
            railway_tables = set(railway_schema["tables"].keys())
            
            print(f"📊 Schema Comparison Results:")
            print(f"   Local tables: {len(local_tables)}")
            print(f"   Railway tables: {len(railway_tables)}")
            
            # Find differences
            missing_in_railway = local_tables - railway_tables
            missing_in_local = railway_tables - local_tables
            
            if missing_in_railway:
                print(f"   ⚠️  Tables missing in Railway: {list(missing_in_railway)}")
            
            if missing_in_local:
                print(f"   ⚠️  Tables missing locally: {list(missing_in_local)}")
            
            if not missing_in_railway and not missing_in_local:
                print(f"   ✅ All tables synchronized")
            
            # Save comparison report
            comparison_file = f"schema_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(comparison_file, 'w') as f:
                json.dump({
                    "local": local_schema,
                    "railway": railway_schema,
                    "differences": {
                        "missing_in_railway": list(missing_in_railway),
                        "missing_in_local": list(missing_in_local)
                    }
                }, f, indent=2)
            
            print(f"   📄 Detailed comparison saved: {comparison_file}")

if __name__ == "__main__":
    compare_schemas()
```

## DbSchema Workflow

### 1. Daily Development Workflow

**Schema Visualization:**
1. Open DbSchema project
2. Refresh schema from local database
3. Review any new tables/changes
4. Document relationships visually

**Making Changes:**
1. Make schema changes through Alembic migrations (not DbSchema)
2. Run migration: `alembic upgrade head`
3. Refresh DbSchema to see changes
4. Validate with: `python data/dbschema/validate_dbschema_connections.py`

### 2. Pre-Deployment Schema Sync

**Before deploying to Railway:**
```bash
# 1. Validate local schema
python data/dbschema/validate_dbschema_connections.py

# 2. Compare schemas
python data/dbschema/compare_schemas_dbschema.py

# 3. Review differences in DbSchema
# Open both local and Railway connections side-by-side

# 4. Deploy if schemas are compatible
python scripts/milestone.py --branch production
```

### 3. Schema Documentation

**Export Database Documentation:**
1. In DbSchema: Tools → Generate Documentation
2. Choose HTML format
3. Include: Tables, Relationships, Indexes, Constraints
4. Save to: `docs/database_documentation/`

## Advanced Features

### 1. Schema Comparison in DbSchema

**Visual Comparison:**
1. Database → Compare Schemas
2. Select source: Rally Local
3. Select target: Rally Production
4. Review differences visually
5. Generate migration script if needed

### 2. Data Synchronization (Use Carefully)

**For reference data only:**
1. Connect to both databases
2. Tools → Data Compare
3. Select specific tables (clubs, leagues, series)
4. Generate sync SQL
5. **⚠️ Never sync user data or match data**

### 3. Query Builder

**Visual Query Building:**
1. Select tables in diagram
2. Right-click → Query Builder
3. Build complex joins visually
4. Export SQL for use in application

## Security Best Practices

### 1. Connection Security

**Local Development:**
- Use localhost connection only
- No password in DbSchema if possible (use pg_hba.conf trust)

**Production/Staging:**
- Always use SSL (sslmode=require)
- Store passwords in DbSchema encrypted format
- Use read-only user when possible for analysis

### 2. Data Protection

**Never export sensitive data:**
- User passwords
- Email addresses  
- Personal information
- Match history in production

## Troubleshooting

### Common Issues

**Connection Timeout:**
```
Error: Connection timeout
Solution: Check Railway database URL and SSL settings
```

**Schema Refresh Failed:**
```
Error: Permission denied
Solution: Verify database user has schema read permissions
```

**Different Schema Versions:**
```
Error: Table X missing in environment Y
Solution: Run pending Alembic migrations
```

### Health Check Commands

```bash
# Test all connections
python data/dbschema/validate_dbschema_connections.py

# Compare schema versions
python data/dbschema/compare_schemas_dbschema.py

# Check Alembic migration status
alembic current
alembic history --verbose
```

## Integration with Existing Workflow

### 1. With Alembic Migrations

**Process:**
1. Create migration: `alembic revision -m "description"`
2. Edit migration file
3. Test locally: `alembic upgrade head`
4. Refresh DbSchema local connection
5. Validate schema: `python data/dbschema/validate_dbschema_connections.py`
6. Deploy: `python scripts/milestone.py`
7. Refresh DbSchema production connection

### 2. With ETL Process

**Before ETL runs:**
1. Document current schema in DbSchema
2. Export schema backup
3. Run ETL
4. Validate schema integrity
5. Update DbSchema documentation

## Files Created

This setup creates these new files in your workspace:

```
data/
└── dbschema/
    ├── validate_dbschema_connections.py
    ├── compare_schemas_dbschema.py
    └── setup_dbschema.py

docs/
├── DBSCHEMA_SETUP_GUIDE.md (this file)
└── database_documentation/ (generated by DbSchema)

database_schema/
└── rally_schema.dbs (DbSchema project file)
```

## Next Steps

1. **Create validation script**: Run the validation script to test all connections
2. **Import schema**: Import your local database schema into DbSchema
3. **Connect to Railway**: Set up Railway production database connection
4. **Document relationships**: Use DbSchema to visualize and document table relationships
5. **Establish workflow**: Integrate DbSchema into your daily development process

Would you like me to create the validation scripts first, or would you prefer to start with a specific aspect of the DbSchema setup? 