"""add parent_record_id to completion_records

Revision ID: 7e0a41716e21
Revises: 05b83e3bfc58
Create Date: 2026-06-27 14:11:45.098399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e0a41716e21'
down_revision: Union[str, Sequence[str], None] = '05b83e3bfc58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "completion_records",
        sa.Column("parent_record_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_completion_records_parent_record_id",
        "completion_records",
        ["parent_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_completion_records_parent_record_id", "completion_records")
    op.drop_column("completion_records", "parent_record_id")
