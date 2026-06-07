"""add pipeline_config table

Revision ID: 05b83e3bfc58
Revises: 278d45c2a14a
Create Date: 2026-06-07 08:23:54.222778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05b83e3bfc58'
down_revision: Union[str, Sequence[str], None] = '278d45c2a14a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "pipeline_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_by", sa.String(64), nullable=False, server_default="system"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO pipeline_config (id, config) VALUES (1, '{}'::json) "
        "ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("pipeline_config")
