"""add ix_fsn_parent_active_name

Revision ID: b3f1c2d4e5a6
Revises: ac57ae7d7abd
Create Date: 2026-05-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b3f1c2d4e5a6'
down_revision: Union[str, Sequence[str], None] = 'ac57ae7d7abd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_fsn_parent_active_name',
        'file_system_nodes',
        ['parent_id', 'name'],
        unique=False,
        postgresql_where=sa.text('is_deleted = false'),
    )


def downgrade() -> None:
    op.drop_index(
        'ix_fsn_parent_active_name',
        table_name='file_system_nodes',
        postgresql_where=sa.text('is_deleted = false'),
    )
