"""create_snapshot_and_report_tables

Revision ID: e74a81bc9231
Revises: 93ae6eeaf465
Create Date: 2026-11-18 03:22:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e74a81bc9231'
down_revision: Union[str, None] = '93ae6eeaf465'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create ability_snapshots table
    op.create_table(
        'ability_snapshots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('student_id', sa.String(length=64), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('snapshot_sequence', sa.Integer(), nullable=False),
        sa.Column('ability_scores', sa.JSON(), nullable=False),
        sa.Column('uncertainty_scores', sa.JSON(), nullable=False),
        sa.Column('dimension_coverage', sa.JSON(), nullable=False),
        sa.Column('answered_question_count', sa.Integer(), nullable=False),
        sa.Column('algorithm_version', sa.String(length=32), nullable=False),
        sa.Column('checkpoint_type', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['assessment_sessions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'snapshot_sequence', name='uq_snapshot_session_sequence')
    )
    op.create_index(op.f('ix_ability_snapshots_created_at'), 'ability_snapshots', ['created_at'], unique=False)
    op.create_index(op.f('ix_ability_snapshots_session_id'), 'ability_snapshots', ['session_id'], unique=False)
    op.create_index(op.f('ix_ability_snapshots_student_id'), 'ability_snapshots', ['student_id'], unique=False)
    op.create_index('ix_snapshots_student_created', 'ability_snapshots', ['student_id', 'created_at'], unique=False)

    # 2. Create assessment_reports table
    op.create_table(
        'assessment_reports',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('student_id', sa.String(length=64), nullable=False),
        sa.Column('snapshot_id', sa.String(length=36), nullable=False),
        sa.Column('report_version', sa.String(length=32), nullable=False),
        sa.Column('algorithm_version', sa.String(length=32), nullable=False),
        sa.Column('report_payload', sa.JSON(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['assessment_sessions.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['snapshot_id'], ['ability_snapshots.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', name='uq_assessment_reports_session_id')
    )
    op.create_index(op.f('ix_assessment_reports_generated_at'), 'assessment_reports', ['generated_at'], unique=False)
    op.create_index(op.f('ix_assessment_reports_session_id'), 'assessment_reports', ['session_id'], unique=True)
    op.create_index(op.f('ix_assessment_reports_snapshot_id'), 'assessment_reports', ['snapshot_id'], unique=False)
    op.create_index(op.f('ix_assessment_reports_student_id'), 'assessment_reports', ['student_id'], unique=False)
    op.create_index('ix_reports_student_generated', 'assessment_reports', ['student_id', 'generated_at'], unique=False)


def downgrade() -> None:
    op.drop_table('assessment_reports')
    op.drop_table('ability_snapshots')
