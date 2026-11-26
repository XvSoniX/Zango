"""create_simulation_tables

Revision ID: f3b890a12e45
Revises: e74a81bc9231
Create Date: 2026-11-18 03:33:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3b890a12e45'
down_revision: Union[str, None] = 'e74a81bc9231'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create simulation_runs table
    op.create_table(
        'simulation_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('profile_code', sa.String(length=64), nullable=False),
        sa.Column('algorithm_version', sa.String(length=32), nullable=False),
        sa.Column('random_seed', sa.Integer(), nullable=False),
        sa.Column('participant_count', sa.Integer(), nullable=False),
        sa.Column('completed_participant_count', sa.Integer(), nullable=False),
        sa.Column('failed_participant_count', sa.Integer(), nullable=False),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulation_runs_created_at'), 'simulation_runs', ['created_at'], unique=False)
    op.create_index(op.f('ix_simulation_runs_status'), 'simulation_runs', ['status'], unique=False)
    op.create_index('ix_simulation_runs_status_created', 'simulation_runs', ['status', 'created_at'], unique=False)

    # 2. Create simulation_participant_results table
    op.create_table(
        'simulation_participant_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_id', sa.String(length=36), nullable=False),
        sa.Column('synthetic_user_id', sa.String(length=64), nullable=False),
        sa.Column('archetype', sa.String(length=32), nullable=False),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('ground_truth_ability', sa.JSON(), nullable=False),
        sa.Column('estimated_ability', sa.JSON(), nullable=False),
        sa.Column('uncertainty_vector', sa.JSON(), nullable=False),
        sa.Column('dimension_coverage', sa.JSON(), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('session_status', sa.String(length=32), nullable=False),
        sa.Column('stopping_reason', sa.String(length=64), nullable=True),
        sa.Column('answered_question_count', sa.Integer(), nullable=False),
        sa.Column('total_duration_seconds', sa.Float(), nullable=False),
        sa.Column('final_snapshot_id', sa.String(length=36), nullable=True),
        sa.Column('question_records', sa.JSON(), nullable=False),
        sa.Column('error_message', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['simulation_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulation_participant_results_archetype'), 'simulation_participant_results', ['archetype'], unique=False)
    op.create_index(op.f('ix_simulation_participant_results_run_id'), 'simulation_participant_results', ['run_id'], unique=False)
    op.create_index(op.f('ix_simulation_participant_results_session_id'), 'simulation_participant_results', ['session_id'], unique=False)
    op.create_index(op.f('ix_simulation_participant_results_synthetic_user_id'), 'simulation_participant_results', ['synthetic_user_id'], unique=False)
    op.create_index('ix_sim_results_run_archetype', 'simulation_participant_results', ['run_id', 'archetype'], unique=False)


def downgrade() -> None:
    op.drop_table('simulation_participant_results')
    op.drop_table('simulation_runs')
