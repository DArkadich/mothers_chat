from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Идентификатор ревизии
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    # user_profiles
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # assistants
    op.create_table(
        "assistants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("base_model", sa.String(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column(
            "extra_config",
            postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=False,
        ),
    )
    op.create_index("ix_assistants_id", "assistants", ["id"])
    op.create_index("ix_assistants_code", "assistants", ["code"], unique=True)

    # user_assistants
    op.create_table(
        "user_assistants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assistant_id", sa.Integer(), sa.ForeignKey("assistants.id"), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # user_limits
    op.create_table(
        "user_limits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("daily_requests_base", sa.Integer(), nullable=True),
        sa.Column("monthly_requests_base", sa.Integer(), nullable=True),
        sa.Column("daily_requests_bonus", sa.Integer(), nullable=True),
        sa.Column("monthly_requests_bonus", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # conversations
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assistant_id", sa.Integer(), sa.ForeignKey("assistants.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
    )

    # messages
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # kb_articles
    op.create_table(
        "kb_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("age_group", sa.String(), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # kb_examples
    op.create_table(
        "kb_examples",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assistant_id", sa.Integer(), sa.ForeignKey("assistants.id"), nullable=True),
        sa.Column("question_example", sa.Text(), nullable=False),
        sa.Column("answer_example", sa.Text(), nullable=False),
        sa.Column("age_group", sa.String(), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    # удаляем в порядке, обратном зависимостям
    op.drop_table("kb_examples")
    op.drop_table("kb_articles")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("user_limits")
    op.drop_table("user_assistants")
    op.drop_index("ix_assistants_code", table_name="assistants")
    op.drop_index("ix_assistants_id", table_name="assistants")
    op.drop_table("assistants")
    op.drop_table("user_profiles")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

