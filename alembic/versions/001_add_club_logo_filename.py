"""add club logo filename

Revision ID: 001_add_club_logo_filename  
Revises: 07d5e9498cf9
Create Date: 2024-12-30

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "001_add_club_logo_filename"
down_revision = "3fc2223138ae"  # Current head revision
branch_labels = None
depends_on = None


def upgrade():
    # Add logo_filename column to clubs table
    op.add_column('clubs', sa.Column('logo_filename', sa.String(500), nullable=True))
    
    # Update existing clubs with known logo filenames
    op.execute("""
        UPDATE clubs 
        SET logo_filename = 'static/images/clubs/tennaqua_logo.jpeg' 
        WHERE name = 'Tennaqua'
    """)
    
    op.execute("""
        UPDATE clubs 
        SET logo_filename = 'static/images/clubs/glenbrook_rc_logo.png' 
        WHERE name = 'Glenbrook RC'
    """)


def downgrade():
    # Remove the logo_filename column
    op.drop_column('clubs', 'logo_filename') 