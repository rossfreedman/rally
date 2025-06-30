"""Add user_id column to player_availability for stable references

Revision ID: 9e89c138eadd
Revises: 001_add_club_logo_filename
Create Date: 2025-06-30 13:10:22.855200

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e89c138eadd'
down_revision: Union[str, None] = '001_add_club_logo_filename'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_id column to player_availability for stable references.
    
    This migration fixes the "column user_id does not exist" error in production
    by adding the missing user_id column and populating it with existing data.
    """
    # Check if user_id column already exists (for cases where it was manually added)
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'player_availability' 
            AND column_name = 'user_id'
        )
    """))
    column_exists = result.fetchone()[0]
    
    # Step 1: Add user_id column with foreign key reference to users table (if it doesn't exist)
    if not column_exists:
        op.add_column('player_availability', 
                      sa.Column('user_id', sa.Integer(), 
                               sa.ForeignKey('users.id'), nullable=True))
        print("✅ Added user_id column to player_availability")
    else:
        print("✅ user_id column already exists, skipping column creation")
    
    # Step 2: Populate user_id for existing records by linking through player associations
    # This is safe to run multiple times
    op.execute("""
        UPDATE player_availability 
        SET user_id = (
            SELECT u.id 
            FROM players p
            JOIN user_player_associations upa ON p.tenniscores_player_id = upa.tenniscores_player_id
            JOIN users u ON upa.user_id = u.id
            WHERE p.id = player_availability.player_id
            LIMIT 1
        )
        WHERE user_id IS NULL AND player_id IS NOT NULL;
    """)
    print("✅ Populated user_id for existing records")
    
    # Step 3: Create performance indexes (with IF NOT EXISTS safety)
    try:
        op.create_index('idx_availability_user_date', 'player_availability', 
                        ['user_id', 'match_date'], 
                        postgresql_where=sa.text('user_id IS NOT NULL'))
        print("✅ Created idx_availability_user_date index")
    except Exception as e:
        if 'already exists' in str(e):
            print("✅ idx_availability_user_date index already exists")
        else:
            raise
    
    try:
        op.create_index('idx_unique_user_date_availability', 'player_availability',
                        ['user_id', 'match_date'], 
                        unique=True,
                        postgresql_where=sa.text('user_id IS NOT NULL'))
        print("✅ Created idx_unique_user_date_availability index")
    except Exception as e:
        if 'already exists' in str(e):
            print("✅ idx_unique_user_date_availability index already exists")
        else:
            raise


def downgrade() -> None:
    """Remove user_id column and related indexes."""
    # Remove indexes first
    op.drop_index('idx_unique_user_date_availability', table_name='player_availability')
    op.drop_index('idx_availability_user_date', table_name='player_availability')
    
    # Remove the column
    op.drop_column('player_availability', 'user_id')
