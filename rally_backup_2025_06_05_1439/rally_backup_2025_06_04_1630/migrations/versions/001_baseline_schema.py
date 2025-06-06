"""baseline schema

Revision ID: 001
Revises: 
Create Date: 2024-03-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create series table
    op.create_table(
        'series',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create clubs table
    op.create_table(
        'clubs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(255), nullable=False),
        sa.Column('last_name', sa.String(255), nullable=False),
        sa.Column('club_id', sa.Integer(), nullable=True),
        sa.Column('series_id', sa.Integer(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id']),
        sa.ForeignKeyConstraint(['series_id'], ['series.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create player_availability table
    op.create_table(
        'player_availability',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('player_name', sa.String(255), nullable=False),
        sa.Column('match_date', sa.Date(), nullable=False),
        sa.Column('availability_status', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('series_id', sa.Integer(), nullable=False),
        sa.CheckConstraint('availability_status IN (1, 2, 3)'),
        sa.ForeignKeyConstraint(['series_id'], ['series.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('player_name', 'match_date', 'series_id')
    )

    # Create user_activity_logs table
    op.create_table(
        'user_activity_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('activity_type', sa.String(255), nullable=False),
        sa.Column('page', sa.String(255)),
        sa.Column('action', sa.Text()),
        sa.Column('details', sa.Text()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('timestamp', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_instructions table
    op.create_table(
        'user_instructions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_email', sa.String(255), nullable=False),
        sa.Column('instruction', sa.Text(), nullable=False),
        sa.Column('team_id', sa.Integer()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_user_email', 'users', ['email'])
    op.create_index('idx_player_availability', 'player_availability', ['player_name', 'match_date', 'series_id'])
    op.create_index('idx_user_activity_logs_user_email', 'user_activity_logs', ['user_email', 'timestamp'])
    op.create_index('idx_user_instructions_email', 'user_instructions', ['user_email'])

def downgrade():
    # Drop tables in reverse order
    op.drop_table('user_instructions')
    op.drop_table('user_activity_logs')
    op.drop_table('player_availability')
    op.drop_table('users')
    op.drop_table('clubs')
    op.drop_table('series') 