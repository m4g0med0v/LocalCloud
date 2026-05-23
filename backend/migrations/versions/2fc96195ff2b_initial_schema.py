"""initial schema

Revision ID: 2fc96195ff2b
Revises:
Create Date: 2026-05-23 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

from database.metadata import get_metadata

revision = "2fc96195ff2b"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    metadata = get_metadata()
    metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    metadata = get_metadata()
    metadata.drop_all(bind=op.get_bind(), checkfirst=True)
