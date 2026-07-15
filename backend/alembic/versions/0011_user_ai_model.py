"""per-user AI model assignment (users.ai_model)

Revision ID: 0011_user_ai_model
Revises: 0010_ai_usage
Create Date: 2026-07-15

The AI model an editor uses is now chosen PER USER (each org member has a model
assigned to them, admin-managed on the Users panel) rather than per document.
`documents.ai_model` is left in place (dormant) so nothing that still reads it
breaks; AI resolution now keys off `users.ai_model`.

Additive: new column defaults to the enabled Gemini model so existing users get
the same behaviour they had before.
"""
from alembic import op
import sqlalchemy as sa

revision: str = "0011_user_ai_model"
down_revision: str = "0010_ai_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "ai_model",
            sa.Text(),
            nullable=False,
            server_default="gemini-2.5-flash",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "ai_model")
