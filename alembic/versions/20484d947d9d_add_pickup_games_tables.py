"""add_pickup_games_tables

Revision ID: 20484d947d9d
Revises: a7bcfd488790
Create Date: 2025-07-07 14:23:10.844322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20484d947d9d'
down_revision: Union[str, None] = 'a7bcfd488790'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create pickup_games table
    op.create_table(
        'pickup_games',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('game_date', sa.Date(), nullable=False),
        sa.Column('game_time', sa.Time(), nullable=False),
        sa.Column('players_requested', sa.Integer(), nullable=False),
        sa.Column('players_committed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pti_low', sa.Integer(), nullable=False, server_default='-30'),
        sa.Column('pti_high', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('series_low', sa.Integer(), nullable=True),
        sa.Column('series_high', sa.Integer(), nullable=True),
        sa.Column('club_only', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('creator_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint('players_requested > 0', name='ck_players_requested_positive'),
        sa.CheckConstraint('players_committed >= 0', name='ck_players_committed_non_negative'),
        sa.CheckConstraint('players_committed <= players_requested', name='ck_valid_player_counts'),
        sa.CheckConstraint('pti_low <= pti_high', name='ck_valid_pti_range'),
        sa.CheckConstraint('series_low IS NULL OR series_high IS NULL OR series_low <= series_high', name='ck_valid_series_range'),
        sa.ForeignKeyConstraint(['creator_user_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Create pickup_game_participants junction table
    op.create_table(
        'pickup_game_participants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('pickup_game_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('joined_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['pickup_game_id'], ['pickup_games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('pickup_game_id', 'user_id', name='uc_unique_game_participant'),
    )

    # Create indexes for better performance
    op.create_index('idx_pickup_games_date_time', 'pickup_games', ['game_date', 'game_time'])
    op.create_index('idx_pickup_games_creator', 'pickup_games', ['creator_user_id'])
    op.create_index('idx_pickup_games_status', 'pickup_games', ['players_requested', 'players_committed'])
    op.create_index('idx_pickup_participants_game', 'pickup_game_participants', ['pickup_game_id'])
    op.create_index('idx_pickup_participants_user', 'pickup_game_participants', ['user_id'])

    # Create trigger function for updating updated_at timestamp
    op.execute("""
    CREATE OR REPLACE FUNCTION update_pickup_games_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # Create trigger to automatically update updated_at timestamp
    op.execute("""
    CREATE TRIGGER trigger_pickup_games_updated_at
        BEFORE UPDATE ON pickup_games
        FOR EACH ROW
        EXECUTE FUNCTION update_pickup_games_updated_at();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS trigger_pickup_games_updated_at ON pickup_games;")
    op.execute("DROP FUNCTION IF EXISTS update_pickup_games_updated_at();")
    
    # Drop indexes
    op.drop_index('idx_pickup_participants_user', 'pickup_game_participants')
    op.drop_index('idx_pickup_participants_game', 'pickup_game_participants')
    op.drop_index('idx_pickup_games_status', 'pickup_games')
    op.drop_index('idx_pickup_games_creator', 'pickup_games')
    op.drop_index('idx_pickup_games_date_time', 'pickup_games')
    
    # Drop tables (participants first due to foreign key)
    op.drop_table('pickup_game_participants')
    op.drop_table('pickup_games')
