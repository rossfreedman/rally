"""add_pros_and_pro_lessons_tables

Revision ID: 2b0c790cc4a1
Revises: series_one_league_refactor
Create Date: 2025-09-08 17:47:27.123305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b0c790cc4a1'
down_revision: Union[str, None] = 'series_one_league_refactor'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create pros table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS pros (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            bio TEXT,
            specialties VARCHAR(500),
            hourly_rate DECIMAL(10,2),
            image_url VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # Create pro_lessons table (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS pro_lessons (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL,
            pro_id INTEGER NOT NULL REFERENCES pros(id),
            lesson_date DATE NOT NULL,
            lesson_time TIME NOT NULL,
            focus_areas TEXT,
            notes TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'requested',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # Create indexes if they don't exist
    op.execute("CREATE INDEX IF NOT EXISTS idx_pros_active ON pros(is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pro_lessons_user_email ON pro_lessons(user_email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pro_lessons_pro_id ON pro_lessons(pro_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pro_lessons_status ON pro_lessons(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pro_lessons_lesson_date ON pro_lessons(lesson_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pro_lessons_created_at ON pro_lessons(created_at)")

    # Insert sample pros data
    op.execute("""
        INSERT INTO pros (name, bio, specialties, hourly_rate, image_url) VALUES
        ('John Smith', 'Professional tennis instructor with 15 years of experience. Specializes in technique improvement and match strategy.', 'Overheads, Serves, Strategy', 75.00, '/static/images/pros/john_smith.jpg'),
        ('Sarah Johnson', 'Former college tennis player and certified instructor. Focuses on footwork and mental game development.', 'Footwork, Mental Game, Volleys', 65.00, '/static/images/pros/sarah_johnson.jpg'),
        ('Mike Davis', 'Platform tennis specialist with expertise in doubles strategy and court positioning.', 'Doubles Strategy, Court Positioning, Backhands', 70.00, '/static/images/pros/mike_davis.jpg')
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_pro_lessons_created_at")
    op.execute("DROP INDEX IF EXISTS idx_pro_lessons_lesson_date")
    op.execute("DROP INDEX IF EXISTS idx_pro_lessons_status")
    op.execute("DROP INDEX IF EXISTS idx_pro_lessons_pro_id")
    op.execute("DROP INDEX IF EXISTS idx_pro_lessons_user_email")
    op.execute("DROP INDEX IF EXISTS idx_pros_active")

    # Drop tables (in reverse order due to foreign key constraints)
    op.execute("DROP TABLE IF EXISTS pro_lessons")
    op.execute("DROP TABLE IF EXISTS pros")
