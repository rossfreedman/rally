#!/bin/bash

# --- CONFIGURATION ---
PROD_HOST="trolley.proxy.rlwy.net"
PROD_PORT="34555"
PROD_USER="postgres"
PROD_DB="railway"
PROD_PASSWORD="OoxuYNiTfyRqbqyoFTNTUHRGjtjHVscf"

LOCAL_HOST="localhost"
LOCAL_PORT="5432"
LOCAL_USER="postgres"
LOCAL_DB="rally"

# --- 1. BACKUP PRODUCTION DATABASE ---
echo "Backing up production database..."
PGPASSWORD=$PROD_PASSWORD pg_dump -h $PROD_HOST -p $PROD_PORT -U $PROD_USER -d $PROD_DB > prod_backup.sql
echo "Production backup saved as prod_backup.sql"

# --- 2. DROP ALL TABLES IN PRODUCTION ---
echo "Dropping all tables in production database..."
PGPASSWORD=$PROD_PASSWORD psql -h $PROD_HOST -p $PROD_PORT -U $PROD_USER -d $PROD_DB <<EOF
DO \$\$ DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE;';
    END LOOP;
END \$\$;
EOF
echo "All tables dropped."

# --- 3. CREATE CLEAN DUMP OF LOCAL DATABASE ---
echo "Creating clean dump of local database..."
pg_dump --clean --if-exists -U $LOCAL_USER -h $LOCAL_HOST -p $LOCAL_PORT -d $LOCAL_DB > local_rally_backup.sql
echo "Local dump saved as local_rally_backup.sql"

# --- 4. IMPORT LOCAL DUMP INTO PRODUCTION ---
echo "Importing local dump into production database..."
PGPASSWORD=$PROD_PASSWORD psql -h $PROD_HOST -p $PROD_PORT -U $PROD_USER -d $PROD_DB < local_rally_backup.sql
echo "Import complete!"

echo "All done! Your production database now matches your local database." 