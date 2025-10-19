"""add_player_notes_table

Revision ID: 1a9c5410ef91
Revises: 20251012_food_videos
Create Date: 2025-10-16 15:59:27.117366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a9c5410ef91'
down_revision: Union[str, None] = '20251012_food_videos'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create player_notes table
    op.create_table(
        'player_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.String(length=255), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('club_id', sa.Integer(), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_player_notes_player_id', 'player_notes', ['player_id'], unique=False)
    op.create_index('idx_player_notes_club_id', 'player_notes', ['club_id'], unique=False)
    op.create_index('idx_player_notes_creator_id', 'player_notes', ['creator_id'], unique=False)
    op.create_index('idx_player_notes_player_club', 'player_notes', ['player_id', 'club_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('idx_player_notes_player_club', table_name='player_notes')
    op.drop_index('idx_player_notes_creator_id', table_name='player_notes')
    op.drop_index('idx_player_notes_club_id', table_name='player_notes')
    op.drop_index('idx_player_notes_player_id', table_name='player_notes')
    
    # Drop table
    op.drop_table('player_notes')
