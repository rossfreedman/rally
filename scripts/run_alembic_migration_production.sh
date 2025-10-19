#!/bin/bash
#
# Run Alembic Migration Against Production Database
# This script runs pending Alembic migrations against the production database
#

set -e  # Exit on error

echo "================================================================================"
echo "ALEMBIC MIGRATION - PRODUCTION DATABASE"
echo "================================================================================"
echo ""
echo "⚠️  WARNING: This will run Alembic migrations against PRODUCTION"
echo "   Database: ballast.proxy.rlwy.net:40911/railway"
echo ""
echo "Current migration: add_pricing_columns_to_pros_table"
echo ""
echo "This will:"
echo "  1. Add 6 pricing columns to pros table"
echo "  2. Populate pricing for Olga Martinsone"
echo "  3. Populate pricing for Mike Simms"
echo "  4. Set default pricing for other active pros"
echo ""
read -p "Continue? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^yes$ ]]; then
    echo "❌ Migration cancelled"
    exit 0
fi

echo ""
echo "📡 Setting up production database connection..."
echo ""

# Export production database URL
export DATABASE_URL="postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

echo "🔍 Checking current migration status..."
python3 -m alembic current

echo ""
echo "📋 Showing pending migrations..."
python3 -m alembic show head

echo ""
echo "🚀 Running migration upgrade..."
python3 -m alembic upgrade head

echo ""
echo "✅ Migration completed!"
echo ""
echo "🔍 Verifying migration status..."
python3 -m alembic current

echo ""
echo "================================================================================"
echo "✅ MIGRATION SUCCESSFUL"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "  1. Test /mobile/schedule-lesson on production"
echo "  2. Verify pricing displays correctly"
echo "  3. Submit a test lesson request"
echo ""
echo "Production URL: https://rally-production.up.railway.app/mobile/schedule-lesson"
echo "================================================================================"

