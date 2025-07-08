# DbSchema Setup for Rally Database 🎯

**Visual database management and schema synchronization made easy**

## Quick Start

Your local database is **ready to go**! Here's how to get started:

### 1. Run Setup Guide
```bash
python data/dbschema/setup_dbschema.py
```
This provides complete step-by-step instructions.

### 2. Validate Connections
```bash
python data/dbschema/validate_dbschema_connections.py
```
Tests all database connections for DbSchema.

### 3. Compare Schemas (after Railway setup)
```bash
python data/dbschema/compare_schemas_dbschema.py
```
Compares local vs Railway schemas for synchronization.

## What You Get

✅ **30 tables** visualized with full relationships  
✅ **42 foreign key constraints** mapped  
✅ **Complete schema documentation** generation  
✅ **Visual query builder** for complex joins  
✅ **Schema comparison** between environments  
✅ **Integration** with your existing Alembic workflow  

## Key Database Tables

Your Rally platform has these core tables ready for visualization:

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

## Connection Details

### Local Database (Ready Now)
```
Host: localhost
Port: 5432
Database: rally
Username: rossfreedman
SSL Mode: prefer
```

### Railway Production (Optional)
Set up `DATABASE_PUBLIC_URL` environment variable, then use the validation script to get connection details.

## Files Created

```
docs/
├── DBSCHEMA_SETUP_GUIDE.md          # Complete setup guide
└── database_documentation/          # Generated documentation

data/
└── dbschema/
    ├── validate_dbschema_connections.py # Connection validator
    ├── compare_schemas_dbschema.py      # Schema comparison
    └── setup_dbschema.py               # Quick setup guide

database_schema/
└── rally_schema.dbs                # DbSchema project file (create this)
```

## Workflow Integration

### Daily Development
1. Make schema changes via Alembic migrations
2. Refresh DbSchema to see changes
3. Document relationships visually
4. Validate with `python data/dbschema/validate_dbschema_connections.py`

### Pre-Deployment
1. Compare schemas: `python data/dbschema/compare_schemas_dbschema.py`
2. Review differences in DbSchema visually
3. Deploy with confidence using your existing workflow

## Advanced Features

🔍 **Visual Schema Exploration** - See your entire database structure at a glance  
📊 **Query Builder** - Build complex joins visually  
🔄 **Schema Sync** - Keep local and production in sync  
📋 **Documentation** - Generate HTML documentation automatically  
🔧 **Migration Planning** - Visualize changes before coding  

## Next Steps

1. **Start Now**: Run `python data/dbschema/setup_dbschema.py`
2. **Open DbSchema** and follow the guided setup
3. **Import your schema** - see all 30 tables with relationships
4. **Generate documentation** for your team
5. **Set up Railway connection** when ready

## Support

- 📖 Full guide: `docs/DBSCHEMA_SETUP_GUIDE.md`
- 🔧 Troubleshooting included in setup script
- ✅ All scripts tested with your current database

---

**Ready to visualize your Rally database?** 🚀  
Run `python data/dbschema/setup_dbschema.py` to get started! 