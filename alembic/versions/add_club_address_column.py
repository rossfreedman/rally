"""Add club_address column to clubs table

Revision ID: add_club_address_column
Revises: 995937af9e55
Create Date: 2025-01-02 15:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_club_address_column"
down_revision = "995937af9e55"
branch_labels = None
depends_on = None


def upgrade():
    # Add club_address column to clubs table
    op.add_column("clubs", sa.Column("club_address", sa.String(500), nullable=True))


def downgrade():
    # Remove club_address column from clubs table
    op.drop_column("clubs", "club_address")
