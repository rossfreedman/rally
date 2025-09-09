"""Refactor series to belong to exactly one league

Revision ID: series_one_league_refactor
Revises: fix_schema_001
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import csv
import os
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'series_one_league_refactor'
down_revision = 'fix_schema_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Refactor series to belong to exactly one league"""
    
    # Get database connection for Python operations
    connection = op.get_bind()
    session = Session(bind=connection)
    
    try:
        print("🔧 Starting series one-league refactor migration...")
        
        # Step 1: Add league_id column (nullable initially) if it doesn't exist
        print("   Step 1: Checking if league_id column exists...")
        
        # Check if league_id column already exists
        column_exists = session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'series' AND column_name = 'league_id'
            )
        """)).scalar()
        
        if not column_exists:
            print("   Adding league_id column to series table...")
            op.add_column('series', sa.Column('league_id', sa.Integer(), nullable=True))
        else:
            print("   league_id column already exists")
        
        # Create index if it doesn't exist
        index_exists = session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'series' AND indexname = 'ix_series_league_id'
            )
        """)).scalar()
        
        if not index_exists:
            print("   Creating index on league_id...")
            op.create_index('ix_series_league_id', 'series', ['league_id'])
        else:
            print("   Index already exists")
        
        # Step 2: Check for data conflicts before proceeding
        print("   Step 2: Checking for data conflicts...")
        
        # Check for multi-league conflicts
        conflicts_query = text("""
            SELECT 
                s.id as series_id, 
                s.name as series_name,
                array_agg(DISTINCT sl.league_id) as league_ids,
                array_agg(DISTINCT l.league_name) as league_names,
                COUNT(DISTINCT sl.league_id) as league_count
            FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            JOIN leagues l ON sl.league_id = l.id
            GROUP BY s.id, s.name
            HAVING COUNT(DISTINCT sl.league_id) > 1
            ORDER BY s.name
        """)
        
        conflicts = session.execute(conflicts_query).fetchall()
        
        # Check for series with no league
        no_league_query = text("""
            SELECT s.id, s.name
            FROM series s
            LEFT JOIN series_leagues sl ON s.id = sl.series_id
            WHERE sl.series_id IS NULL
            ORDER BY s.name
        """)
        
        no_league = session.execute(no_league_query).fetchall()
        
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # If conflicts exist, generate report and abort
        if conflicts:
            print(f"   🚨 Found {len(conflicts)} multi-league conflicts - generating report...")
            
            conflicts_file = os.path.join(reports_dir, f'series_multi_league_conflicts_{timestamp}.csv')
            with open(conflicts_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['series_id', 'series_name', 'league_ids', 'league_names', 'league_count'])
                for c in conflicts:
                    writer.writerow([c.series_id, c.series_name, c.league_ids, c.league_names, c.league_count])
            
            print(f"   📋 Conflict report written to: {conflicts_file}")
            raise RuntimeError(
                f"Migration cannot proceed: {len(conflicts)} series have multiple league associations. "
                f"Please review the conflict report at {conflicts_file} and resolve conflicts before retrying."
            )
        
        # If orphaned series exist, generate report and abort
        if no_league:
            print(f"   ⚠️  Found {len(no_league)} series with no league - generating report...")
            
            no_league_file = os.path.join(reports_dir, f'series_no_league_{timestamp}.csv')
            with open(no_league_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['series_id', 'series_name'])
                for s in no_league:
                    writer.writerow([s.id, s.name])
            
            print(f"   📋 No-league report written to: {no_league_file}")
            raise RuntimeError(
                f"Migration cannot proceed: {len(no_league)} series have no league association. "
                f"Please review the report at {no_league_file} and assign leagues before retrying."
            )
        
        print("   ✅ No data conflicts found - proceeding with migration...")
        
        # Step 3: Backfill league_id from series_leagues
        print("   Step 3: Backfilling league_id from series_leagues...")
        
        # Update series with their single league_id
        update_query = text("""
            UPDATE series 
            SET league_id = (
                SELECT sl.league_id 
                FROM series_leagues sl 
                WHERE sl.series_id = series.id 
                LIMIT 1
            )
            WHERE id IN (
                SELECT DISTINCT series_id 
                FROM series_leagues
            )
        """)
        
        result = session.execute(update_query)
        session.commit()
        
        print(f"   ✅ Updated {result.rowcount} series with league_id")
        
        # Step 4: Verify no NULL league_id values
        print("   Step 4: Verifying data integrity...")
        
        null_check = session.execute(text("SELECT COUNT(*) FROM series WHERE league_id IS NULL")).scalar()
        if null_check > 0:
            raise RuntimeError(f"Data integrity check failed: {null_check} series still have NULL league_id")
        
        print("   ✅ All series have league_id values")
        
        # Step 5: Set league_id NOT NULL
        print("   Step 5: Setting league_id NOT NULL...")
        op.alter_column('series', 'league_id', nullable=False)
        
        # Step 6: Add foreign key constraint
        print("   Step 6: Adding foreign key constraint...")
        op.create_foreign_key(
            'fk_series_league_id',
            'series', 'leagues',
            ['league_id'], ['id'],
            onupdate='CASCADE', ondelete='RESTRICT'
        )
        
        # Step 7: Add unique constraint for (league_id, name)
        print("   Step 7: Adding unique constraint (league_id, name)...")
        op.create_unique_constraint('uq_series_league_name', 'series', ['league_id', 'name'])
        
        # Step 8: Drop series_leagues table
        print("   Step 8: Dropping series_leagues table...")
        op.drop_table('series_leagues')
        
        # Step 9: Final validation
        print("   Step 9: Final validation...")
        
        # Verify no NULL league_id
        null_count = session.execute(text("SELECT COUNT(*) FROM series WHERE league_id IS NULL")).scalar()
        if null_count > 0:
            raise RuntimeError(f"Final validation failed: {null_count} series have NULL league_id")
        
        # Verify no duplicate names per league
        duplicate_count = session.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT league_id, name, COUNT(*) c 
                FROM series 
                GROUP BY league_id, name 
                HAVING COUNT(*) > 1
            ) duplicates
        """)).scalar()
        
        if duplicate_count > 0:
            raise RuntimeError(f"Final validation failed: {duplicate_count} duplicate series names per league found")
        
        # Verify series_leagues table is gone
        table_exists = session.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'series_leagues'
        """)).scalar()
        
        if table_exists > 0:
            raise RuntimeError("Final validation failed: series_leagues table still exists")
        
        print("   ✅ All validations passed")
        
        print("🎉 Series one-league refactor migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def downgrade() -> None:
    """Rollback to series_leagues many-to-many relationship"""
    
    print("🔄 Rolling back series one-league refactor...")
    
    # Get database connection for Python operations
    connection = op.get_bind()
    session = Session(bind=connection)
    
    try:
        # Step 1: Recreate series_leagues table
        print("   Step 1: Recreating series_leagues table...")
        op.create_table(
            'series_leagues',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('series_id', sa.Integer(), nullable=False),
            sa.Column('league_id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['series_id'], ['series.id'], onupdate='CASCADE', ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['league_id'], ['leagues.id'], onupdate='CASCADE', ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Step 2: Repopulate series_leagues from series.league_id
        print("   Step 2: Repopulating series_leagues table...")
        
        repopulate_query = text("""
            INSERT INTO series_leagues (series_id, league_id, created_at)
            SELECT id, league_id, updated_at
            FROM series
            WHERE league_id IS NOT NULL
        """)
        
        result = session.execute(repopulate_query)
        session.commit()
        
        print(f"   ✅ Repopulated {result.rowcount} records in series_leagues")
        
        # Step 3: Drop constraints and column from series
        print("   Step 3: Dropping constraints and column from series...")
        op.drop_constraint('uq_series_league_name', 'series', type_='unique')
        op.drop_constraint('fk_series_league_id', 'series', type_='foreignkey')
        op.drop_index('ix_series_league_id', table_name='series')
        op.drop_column('series', 'league_id')
        
        print("   ✅ Rollback completed successfully")
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()
