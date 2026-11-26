"""create_evaluation_tables

Revision ID: a9b1c2d3e4f5
Revises: f3b890a12e45
Create Date: 2026-11-18 03:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b1c2d3e4f5'
down_revision: Union[str, None] = 'f3b890a12e45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create evaluation_runs table
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('evaluation_type', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('source_simulation_run_ids', sa.JSON(), nullable=False),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('algorithm_version', sa.String(length=32), nullable=False),
        sa.Column('question_bank_version', sa.String(length=32), nullable=False),
        sa.Column('error_message', sa.String(length=512), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_runs_created_at'), 'evaluation_runs', ['created_at'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_status'), 'evaluation_runs', ['status'], unique=False)
    op.create_index(op.f('ix_evaluation_runs_evaluation_type'), 'evaluation_runs', ['evaluation_type'], unique=False)
    op.create_index('ix_evaluation_runs_type_status', 'evaluation_runs', ['evaluation_type', 'status'], unique=False)

    # 2. Create question_selection_evaluation_results table
    op.create_table(
        'question_selection_evaluation_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('evaluation_run_id', sa.String(length=36), nullable=False),
        sa.Column('summary_metrics', sa.JSON(), nullable=False),
        sa.Column('dimension_coverage', sa.JSON(), nullable=False),
        sa.Column('difficulty_distribution', sa.JSON(), nullable=False),
        sa.Column('exposure_metrics', sa.JSON(), nullable=False),
        sa.Column('assessment_length', sa.JSON(), nullable=False),
        sa.Column('sequence_analysis', sa.JSON(), nullable=False),
        sa.Column('archetype_breakdown', sa.JSON(), nullable=False),
        sa.Column('anomalies', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['evaluation_run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('evaluation_run_id', name='uq_question_selection_evaluation_run')
    )
    op.create_index(
        op.f('ix_question_selection_evaluation_results_evaluation_run_id'),
        'question_selection_evaluation_results',
        ['evaluation_run_id'],
        unique=True
    )

    # 3. Create ability_estimation_evaluation_results table
    op.create_table(
        'ability_estimation_evaluation_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('evaluation_run_id', sa.String(length=36), nullable=False),
        sa.Column('summary_metrics', sa.JSON(), nullable=False),
        sa.Column('dimension_metrics', sa.JSON(), nullable=False),
        sa.Column('uncertainty_analysis', sa.JSON(), nullable=False),
        sa.Column('length_vs_quality', sa.JSON(), nullable=False),
        sa.Column('archetype_breakdown', sa.JSON(), nullable=False),
        sa.Column('anomalies', sa.JSON(), nullable=False),
        sa.Column('limitations', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['evaluation_run_id'], ['evaluation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('evaluation_run_id', name='uq_ability_estimation_evaluation_run')
    )
    op.create_index(
        op.f('ix_ability_estimation_evaluation_results_evaluation_run_id'),
        'ability_estimation_evaluation_results',
        ['evaluation_run_id'],
        unique=True
    )


def downgrade() -> None:
    op.drop_table('ability_estimation_evaluation_results')
    op.drop_table('question_selection_evaluation_results')
    op.drop_table('evaluation_runs')
