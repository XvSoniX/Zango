"""add_performance_and_hardening_indexes

Revision ID: b1c2d3e4f5a6
Revises: a9b1c2d3e4f5
Create Date: 2026-11-18 04:02:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a9b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Performance index for active questions by profile (frequently used in next_question)
    op.create_index(
        'ix_profile_questions_active',
        'profile_questions',
        ['profile_id', 'is_active'],
        unique=False
    )

    # 2. Performance composite index for latest ability snapshot retrieval
    op.create_index(
        'ix_snapshots_session_seq_desc',
        'ability_snapshots',
        ['session_id', 'snapshot_sequence'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_snapshots_session_seq_desc', table_name='ability_snapshots')
    op.drop_index('ix_profile_questions_active', table_name='profile_questions')
