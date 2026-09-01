"""empty message

Revision ID: 0ad95b8a8a93
Revises: 8c39db93cab4
Create Date: 2026-05-19 15:00:43.152440+00:00

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0ad95b8a8a93'
down_revision: Union[str, Sequence[str], None] = '8c39db93cab4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE reminders SET days = '[]' WHERE days IS NULL")
    op.alter_column('reminders', 'days', server_default='[]', nullable=False)


def downgrade() -> None:
    op.alter_column('reminders', 'days', server_default=None, nullable=True)
