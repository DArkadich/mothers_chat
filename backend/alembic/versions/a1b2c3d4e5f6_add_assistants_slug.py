"""add assistants.slug

Revision ID: a1b2c3d4e5f6
Revises: 0001_initial_schema
Create Date: 2024-12-20 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assistants", sa.Column("slug", sa.String(), nullable=True))
    # опционально: если хочешь уникальность
    # op.create_unique_constraint("uq_assistants_slug", "assistants", ["slug"])


def downgrade() -> None:
    # опционально: если создавал constraint
    # op.drop_constraint("uq_assistants_slug", "assistants", type_="unique")
    op.drop_column("assistants", "slug")
