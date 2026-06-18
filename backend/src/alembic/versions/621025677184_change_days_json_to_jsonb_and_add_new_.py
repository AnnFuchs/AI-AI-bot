"""change_days_json_to_jsonb_and_add_new_entrytype

Revision ID: 621025677184
Revises: 0ad95b8a8a93
Create Date: 2026-06-18 11:29:05.793568+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '621025677184'
down_revision: Union[str, Sequence[str], None] = '0ad95b8a8a93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE entry_type_enum ADD VALUE IF NOT EXISTS 'EXERCISE'")
    op.alter_column(
        'reminders', 'days',
        type_=JSONB,
        postgresql_using='days::jsonb',
        server_default='[]',
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'reminders', 'days',
        type_=sa.JSON(),
        postgresql_using='days::json',
        server_default='[]',
        nullable=False,
    )
