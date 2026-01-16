"""add packages table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-16 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # packages
    op.create_table(
        "packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("section_key", sa.String(64), nullable=False),
        sa.Column("plan_name", sa.String(64), nullable=False),
        sa.Column(
            "details_cards",
            postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_packages_section_key", "packages", ["section_key"])
    op.create_index("ix_packages_plan_name", "packages", ["plan_name"])
    op.create_index("ix_packages_section_plan", "packages", ["section_key", "plan_name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_packages_section_plan", "packages")
    op.drop_index("ix_packages_plan_name", "packages")
    op.drop_index("ix_packages_section_key", "packages")
    op.drop_table("packages")
