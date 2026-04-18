"""merge_heads

Revision ID: 2b38fe8c2d5d
Revises: 75bad0ff21c7, 4b9975501b19
Create Date: 2026-04-18 14:43:27.038127+00:00

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '2b38fe8c2d5d'
down_revision: Union[str, Sequence[str], None] = (
    '75bad0ff21c7',
    '4b9975501b19',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
