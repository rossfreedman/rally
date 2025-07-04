"""add_unique_player_constraint

Revision ID: 6f517e10b193
Revises: fix_cnswpl_team_names_final
Create Date: 2025-07-04 13:00:15.055271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f517e10b193'
down_revision: Union[str, None] = 'fix_cnswpl_team_names_final'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # First, check for existing violations before adding the constraint
    # This query will help identify any duplicates that need to be resolved
    connection = op.get_bind()
    
    # Check for existing duplicate associations
    result = connection.execute(sa.text("""
        SELECT tenniscores_player_id, COUNT(DISTINCT user_id) as user_count
        FROM user_player_associations
        GROUP BY tenniscores_player_id
        HAVING COUNT(DISTINCT user_id) > 1
    """))
    
    duplicates = result.fetchall()
    if duplicates:
        print(f"WARNING: Found {len(duplicates)} duplicate player associations:")
        for dup in duplicates:
            print(f"  - Player ID {dup[0]}: {dup[1]} users")
        print("These duplicates must be resolved before the constraint can be added.")
        raise Exception("Cannot add unique constraint: duplicate associations exist")
    
    # Check if constraint already exists
    constraint_exists = connection.execute(sa.text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'user_player_associations' 
        AND constraint_type = 'UNIQUE'
        AND constraint_name = 'unique_tenniscores_player_id'
    """)).fetchone()
    
    if not constraint_exists:
        # Add unique constraint to prevent future violations
        op.create_unique_constraint(
            'unique_tenniscores_player_id',
            'user_player_associations',
            ['tenniscores_player_id']
        )
        print("✅ Added unique constraint: unique_tenniscores_player_id")
    else:
        print("ℹ️  Unique constraint already exists: unique_tenniscores_player_id")
    
    # Check if index already exists
    index_exists = connection.execute(sa.text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'user_player_associations' 
        AND indexname = 'idx_upa_unique_player_check'
    """)).fetchone()
    
    if not index_exists:
        # Create index for performance
        op.create_index(
            'idx_upa_unique_player_check',
            'user_player_associations',
            ['tenniscores_player_id']
        )
        print("✅ Added index: idx_upa_unique_player_check")
    else:
        print("ℹ️  Index already exists: idx_upa_unique_player_check")


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    
    # Check if constraint exists before trying to remove it
    constraint_exists = connection.execute(sa.text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'user_player_associations' 
        AND constraint_type = 'UNIQUE'
        AND constraint_name = 'unique_tenniscores_player_id'
    """)).fetchone()
    
    if constraint_exists:
        # Remove the unique constraint
        op.drop_constraint('unique_tenniscores_player_id', 'user_player_associations', type_='unique')
        print("✅ Removed unique constraint: unique_tenniscores_player_id")
    else:
        print("ℹ️  Unique constraint does not exist: unique_tenniscores_player_id")
    
    # Check if index exists before trying to remove it
    index_exists = connection.execute(sa.text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'user_player_associations' 
        AND indexname = 'idx_upa_unique_player_check'
    """)).fetchone()
    
    if index_exists:
        # Remove the index
        op.drop_index('idx_upa_unique_player_check', 'user_player_associations')
        print("✅ Removed index: idx_upa_unique_player_check")
    else:
        print("ℹ️  Index does not exist: idx_upa_unique_player_check")
