import pytest
from typing import List, Dict, Any
from app.domain.enums import CognitiveDimension, StoppingReason
from app.engine.protocols import (
    ItemParameterSnapshot,
    AssessmentContext,
    AbilityState,
    SelectionResult,
    StoppingDecision,
    QuestionSelectionStrategy,
    StoppingStrategy,
)
from app.engine.selector import (
    CandidateFilter,
    SelectorWeights,
    CompositeHeuristicSelector,
)
from app.engine.stopping import StandardStoppingStrategy
from app.engine.estimator import create_initial_ability_state

# ---------------------------------------------------------------------------
# FIXTURES & HELPERS
# ---------------------------------------------------------------------------

def make_candidate(
    question_id: int,
    dimensions: Dict[str, float],
    difficulty: float = 0.0,
    min_age: int = 10,
    max_age: int = 18,
    is_active: bool = True,
    exposure_limit: int = 100,
    exposure_count: int = 0,
    calibration_status: str = "CALIBRATED",
    version: int = 1
) -> ItemParameterSnapshot:
    return ItemParameterSnapshot(
        question_id=question_id,
        version=version,
        dimensions=dimensions,
        difficulty=difficulty,
        discrimination=1.0,
        guessing=0.25,
        min_age=min_age,
        max_age=max_age,
        exposure_limit=exposure_limit,
        exposure_count=exposure_count,
        is_active=is_active,
        calibration_status=calibration_status
    )

def make_context(
    student_age: int = 14,
    target_dimensions: List[str] = None,
    answered_ids: List[int] = None,
    ability_state: AbilityState = None,
    elapsed_time: float = 120.0,
    max_duration: float = 2700.0,
    min_questions: int = 10,
    max_questions: int = 20,
) -> AssessmentContext:
    target_dims = target_dimensions or [d.value for d in CognitiveDimension]
    current_ability = ability_state or create_initial_ability_state(target_dimensions=target_dims)
    return AssessmentContext(
        session_id="session-test-uuid",
        student_id="student-test-uuid",
        student_age=student_age,
        profile_code="TECHNICAL_TALENT_V1",
        target_dimensions=target_dims,
        current_ability=current_ability,
        answered_question_ids=answered_ids or [],
        response_history=[],
        elapsed_time_seconds=elapsed_time,
        max_duration_seconds=max_duration,
        min_questions=min_questions,
        max_questions=max_questions,
        random_seed=42
    )


# ---------------------------------------------------------------------------
# TASK-022: CANDIDATE FILTERING & SELECTION STRATEGY CONTRACT TESTS
# ---------------------------------------------------------------------------

def test_selector_protocol_conformance():
    selector = CompositeHeuristicSelector()
    assert isinstance(selector, QuestionSelectionStrategy)

def test_filter_removes_answered_questions():
    q1 = make_candidate(1, {"logical_reasoning": 0.9})
    q2 = make_candidate(2, {"logical_reasoning": 0.8})
    context = make_context(answered_ids=[1])

    eligible, stats = CandidateFilter.filter_candidates([q1, q2], context)
    assert len(eligible) == 1
    assert eligible[0].question_id == 2
    assert stats["already_answered"] == 1

def test_filter_removes_inactive_questions():
    q1 = make_candidate(1, {"logical_reasoning": 0.9}, is_active=False)
    q2 = make_candidate(2, {"logical_reasoning": 0.9}, is_active=True)
    context = make_context()

    eligible, stats = CandidateFilter.filter_candidates([q1, q2], context)
    assert len(eligible) == 1
    assert eligible[0].question_id == 2
    assert stats["inactive"] == 1

def test_filter_removes_age_mismatch():
    q_young = make_candidate(1, {"logical_reasoning": 0.9}, min_age=8, max_age=12)
    q_match = make_candidate(2, {"logical_reasoning": 0.9}, min_age=12, max_age=16)
    q_old = make_candidate(3, {"logical_reasoning": 0.9}, min_age=16, max_age=20)
    context = make_context(student_age=14)

    eligible, stats = CandidateFilter.filter_candidates([q_young, q_match, q_old], context)
    assert len(eligible) == 1
    assert eligible[0].question_id == 2
    assert stats["age_mismatch"] == 2

def test_filter_removes_profile_incompatible():
    # Context targets only logical_reasoning
    context = make_context(target_dimensions=["logical_reasoning"])
    q_compat = make_candidate(1, {"logical_reasoning": 0.8, "spatial_reasoning": 0.2})
    q_incompat = make_candidate(2, {"spatial_reasoning": 0.9})

    eligible, stats = CandidateFilter.filter_candidates([q_compat, q_incompat], context)
    assert len(eligible) == 1
    assert eligible[0].question_id == 1
    assert stats["profile_incompatible"] == 1

def test_filter_removes_invalid_dimensions_and_difficulty():
    q_empty_dim = make_candidate(1, {})
    q_all_zeros = make_candidate(2, {"logical_reasoning": 0.0})
    q_bad_diff = make_candidate(3, {"logical_reasoning": 0.8}, difficulty=5.5)  # Out of [-4, 4]
    q_valid = make_candidate(4, {"logical_reasoning": 0.8}, difficulty=0.5)

    eligible, stats = CandidateFilter.filter_candidates(
        [q_empty_dim, q_all_zeros, q_bad_diff, q_valid],
        make_context()
    )
    assert len(eligible) == 1
    assert eligible[0].question_id == 4

def test_filter_removes_overexposed_questions():
    q_over = make_candidate(1, {"logical_reasoning": 0.8}, exposure_limit=10, exposure_count=10)
    q_ok = make_candidate(2, {"logical_reasoning": 0.8}, exposure_limit=10, exposure_count=5)

    eligible, stats = CandidateFilter.filter_candidates([q_over, q_ok], make_context())
    assert len(eligible) == 1
    assert eligible[0].question_id == 2
    assert stats["exposure_limit_reached"] == 1


# ---------------------------------------------------------------------------
# TASK-023: COMPOSITE HEURISTIC SELECTOR TESTS
# ---------------------------------------------------------------------------

def test_selector_empty_candidate_pool():
    selector = CompositeHeuristicSelector()
    result = selector.select([], make_context())

    assert result.selected_question_id is None
    assert result.selected_version is None
    assert result.candidate_scores == {}
    assert "NO_ELIGIBLE_QUESTIONS" in result.selection_reason

def test_selector_prioritizes_under_covered_dimension():
    # Setup ability state where logical_reasoning has coverage 3, and spatial_reasoning has coverage 0
    state = AbilityState(
        dimension_scores={d.value: 0.0 for d in CognitiveDimension},
        uncertainty={d.value: 0.8 for d in CognitiveDimension},
        response_count=3,
        dimension_coverage={
            "logical_reasoning": 3,
            "algorithmic_thinking": 2,
            "problem_solving": 2,
            "spatial_reasoning": 0,
            "computational_thinking": 2,
        }
    )
    context = make_context(ability_state=state)

    q_log = make_candidate(1, {"logical_reasoning": 0.9, "spatial_reasoning": 0.0}, difficulty=0.0)
    q_spa = make_candidate(2, {"spatial_reasoning": 0.9, "logical_reasoning": 0.0}, difficulty=0.0)

    selector = CompositeHeuristicSelector()
    res = selector.select([q_log, q_spa], context)

    # Spatial reasoning question MUST be selected because of zero coverage
    assert res.selected_question_id == 2
    assert res.candidate_scores[2] > res.candidate_scores[1]

def test_selector_prioritizes_high_uncertainty_dimension():
    # Coverage is identical, but spatial_reasoning has higher uncertainty (1.0 vs 0.3)
    state = AbilityState(
        dimension_scores={d.value: 0.0 for d in CognitiveDimension},
        uncertainty={
            "logical_reasoning": 0.3,
            "algorithmic_thinking": 0.3,
            "problem_solving": 0.3,
            "spatial_reasoning": 1.0,
            "computational_thinking": 0.3,
        },
        response_count=10,
        dimension_coverage={d.value: 2 for d in CognitiveDimension}
    )
    context = make_context(ability_state=state)

    q_log = make_candidate(1, {"logical_reasoning": 0.9}, difficulty=0.0)
    q_spa = make_candidate(2, {"spatial_reasoning": 0.9}, difficulty=0.0)

    selector = CompositeHeuristicSelector()
    res = selector.select([q_log, q_spa], context)

    # Question measuring spatial_reasoning has higher uncertainty reduction score
    assert res.selected_question_id == 2
    assert res.candidate_scores[2] > res.candidate_scores[1]

def test_selector_difficulty_matching_selects_closest_to_ability():
    # Student ability in logical_reasoning is +1.5
    state = AbilityState(
        dimension_scores={
            "logical_reasoning": 1.5,
            "algorithmic_thinking": 0.0,
            "problem_solving": 0.0,
            "spatial_reasoning": 0.0,
            "computational_thinking": 0.0,
        },
        uncertainty={d.value: 0.5 for d in CognitiveDimension},
        response_count=5,
        dimension_coverage={d.value: 1 for d in CognitiveDimension}
    )
    context = make_context(ability_state=state)

    q_easy = make_candidate(1, {"logical_reasoning": 1.0}, difficulty=-2.0)
    q_matched = make_candidate(2, {"logical_reasoning": 1.0}, difficulty=1.4)
    q_hard = make_candidate(3, {"logical_reasoning": 1.0}, difficulty=3.8)

    selector = CompositeHeuristicSelector()
    res = selector.select([q_easy, q_matched, q_hard], context)

    # Matched question (b=1.4) should have highest score for student at theta=1.5
    assert res.selected_question_id == 2
    assert res.candidate_scores[2] > res.candidate_scores[1]
    assert res.candidate_scores[2] > res.candidate_scores[3]

def test_selector_weights_configuration_validation():
    # Negative weight must raise ValueError
    with pytest.raises(ValueError, match="must be non-negative"):
        SelectorWeights(weight_coverage=-0.1)

    # All-zero weights must raise ValueError
    with pytest.raises(ValueError, match="must be strictly positive"):
        SelectorWeights(
            weight_coverage=0.0,
            weight_uncertainty=0.0,
            weight_difficulty_fit=0.0,
            weight_ability=0.0,
            weight_relevance=0.0,
        )

def test_selector_deterministic_tie_breaking():
    # Two identical questions
    q1 = make_candidate(10, {"logical_reasoning": 0.8}, difficulty=0.0)
    q2 = make_candidate(20, {"logical_reasoning": 0.8}, difficulty=0.0)
    context = make_context()

    selector = CompositeHeuristicSelector()
    res1 = selector.select([q1, q2], context)
    res2 = selector.select([q2, q1], context)  # Different input order

    # Due to deterministic tie-breaker (lowest ID), question 10 is consistently chosen
    assert res1.selected_question_id == 10
    assert res2.selected_question_id == 10
    assert res1.candidate_scores == res2.candidate_scores

def test_selector_uncalibrated_questions_allowed_with_metadata():
    q_uncal = make_candidate(1, {"logical_reasoning": 0.8}, calibration_status="UNCALIBRATED")
    context = make_context()

    selector = CompositeHeuristicSelector()
    res = selector.select([q_uncal], context)

    assert res.selected_question_id == 1
    assert res.metadata["chosen_details"]["calibration_status"] == "UNCALIBRATED"


# ---------------------------------------------------------------------------
# TASK-024: STOPPING STRATEGY TESTS
# ---------------------------------------------------------------------------

def test_stopping_strategy_protocol_conformance():
    strategy = StandardStoppingStrategy()
    assert isinstance(strategy, StoppingStrategy)

def test_stopping_exhausted_question_bank():
    strategy = StandardStoppingStrategy()
    context = make_context()
    state = create_initial_ability_state()

    decision = strategy.evaluate(context, state, remaining_candidates_count=0)
    assert decision.should_stop is True
    assert decision.reason == StoppingReason.QUESTION_BANK_EXHAUSTED

def test_stopping_max_questions_reached():
    strategy = StandardStoppingStrategy()
    context = make_context(min_questions=10, max_questions=20)
    # Student has completed 20 questions
    state = AbilityState(
        dimension_scores={d.value: 0.0 for d in CognitiveDimension},
        uncertainty={d.value: 0.5 for d in CognitiveDimension},
        response_count=20,
        dimension_coverage={d.value: 4 for d in CognitiveDimension}
    )

    decision = strategy.evaluate(context, state, remaining_candidates_count=50)
    assert decision.should_stop is True
    assert decision.reason == StoppingReason.MAX_QUESTIONS_REACHED

def test_stopping_max_duration_expired():
    strategy = StandardStoppingStrategy()
    # 2800 seconds elapsed out of 2700 max
    context = make_context(elapsed_time=2800.0, max_duration=2700.0, min_questions=10, max_questions=20)
    state = create_initial_ability_state()

    decision = strategy.evaluate(context, state, remaining_candidates_count=50)
    assert decision.should_stop is True
    assert decision.reason == StoppingReason.TIME_EXPIRED

def test_stopping_cannot_stop_below_min_questions_even_if_converged():
    strategy = StandardStoppingStrategy(min_uncertainty_threshold=0.25)
    # Only 6 questions answered (less than min_questions=10), but low uncertainty
    context = make_context(min_questions=10, max_questions=20)
    state = AbilityState(
        dimension_scores={d.value: 0.5 for d in CognitiveDimension},
        uncertainty={d.value: 0.20 for d in CognitiveDimension},  # Below 0.25!
        response_count=6,
        dimension_coverage={d.value: 3 for d in CognitiveDimension}
    )

    decision = strategy.evaluate(context, state, remaining_candidates_count=50)
    # Floor gate MUST prevent premature stopping!
    assert decision.should_stop is False
    assert decision.reason is None
    assert decision.metadata["floor_gate_passed"] is False

def test_stopping_cannot_stop_if_dimension_coverage_insufficient():
    strategy = StandardStoppingStrategy(min_uncertainty_threshold=0.25, min_coverage_per_dimension=2)
    # 12 questions answered (above min_questions=10) and low uncertainty,
    # BUT spatial_reasoning only has 1 question covered (less than min 2)
    context = make_context(min_questions=10, max_questions=20)
    state = AbilityState(
        dimension_scores={d.value: 0.5 for d in CognitiveDimension},
        uncertainty={d.value: 0.20 for d in CognitiveDimension},
        response_count=12,
        dimension_coverage={
            "logical_reasoning": 4,
            "algorithmic_thinking": 3,
            "problem_solving": 3,
            "spatial_reasoning": 1,  # Unmet coverage!
            "computational_thinking": 3,
        }
    )

    decision = strategy.evaluate(context, state, remaining_candidates_count=50)
    assert decision.should_stop is False
    assert "spatial_reasoning" in decision.metadata["unmet_coverage_dims"]

def test_stopping_successful_convergence():
    strategy = StandardStoppingStrategy(min_uncertainty_threshold=0.25, min_coverage_per_dimension=2)
    # 14 questions answered, all dimensions have >= 2 coverage and uncertainty <= 0.25
    context = make_context(min_questions=10, max_questions=20)
    state = AbilityState(
        dimension_scores={d.value: 0.5 for d in CognitiveDimension},
        uncertainty={d.value: 0.22 for d in CognitiveDimension},  # Converged!
        response_count=14,
        dimension_coverage={d.value: 3 for d in CognitiveDimension}  # Fully covered!
    )

    decision = strategy.evaluate(context, state, remaining_candidates_count=50)
    assert decision.should_stop is True
    assert decision.reason == StoppingReason.MIN_UNCERTAINTY_ACHIEVED

def test_stopping_priority_order_max_questions_over_duration():
    # If both max questions and time expired, max_questions is evaluated first in ceiling group
    strategy = StandardStoppingStrategy()
    context = make_context(elapsed_time=3000.0, max_duration=2700.0, min_questions=10, max_questions=20)
    state = AbilityState(
        dimension_scores={d.value: 0.0 for d in CognitiveDimension},
        uncertainty={d.value: 0.5 for d in CognitiveDimension},
        response_count=20,  # Max reached
        dimension_coverage={d.value: 4 for d in CognitiveDimension}
    )

    decision = strategy.evaluate(context, state, remaining_candidates_count=50)
    assert decision.should_stop is True
    assert decision.reason == StoppingReason.MAX_QUESTIONS_REACHED


# ---------------------------------------------------------------------------
# SECTION 6.4: THREE-MODULE INTEGRATION TESTS (SELECTION + STOPPING + ABILITY)
# ---------------------------------------------------------------------------

def test_full_selection_and_stopping_cycle():
    """
    Validates complete adaptive loop step:
    1. Check stopping decision (should be False initially).
    2. Select optimal question based on current AbilityState & Coverage.
    3. Simulate answering question and advancing ability.
    4. Verify sequential adaptation and stopping condition when ceiling reached.
    """
    selector = CompositeHeuristicSelector()
    stopping_strategy = StandardStoppingStrategy(min_uncertainty_threshold=0.25)

    # 1. Start with initial state
    ability = create_initial_ability_state()
    pool = [
        make_candidate(101, {"logical_reasoning": 0.9}, difficulty=0.0),
        make_candidate(102, {"algorithmic_thinking": 0.9}, difficulty=0.0),
        make_candidate(103, {"spatial_reasoning": 0.9}, difficulty=0.0),
    ]

    context = make_context(ability_state=ability, min_questions=2, max_questions=3)

    # Cycle 1: Stopping check
    stop_dec_1 = stopping_strategy.evaluate(context, ability, remaining_candidates_count=len(pool))
    assert stop_dec_1.should_stop is False

    # Cycle 1: Question selection
    sel_res_1 = selector.select(pool, context)
    assert sel_res_1.selected_question_id in [101, 102, 103]
    chosen_id = sel_res_1.selected_question_id

    # Simulate answering chosen question
    updated_answered = [chosen_id]
    updated_coverage = dict(ability.dimension_coverage)
    updated_coverage["logical_reasoning"] = 1
    updated_ability = AbilityState(
        dimension_scores={"logical_reasoning": 0.4, "algorithmic_thinking": 0.0, "problem_solving": 0.0, "spatial_reasoning": 0.0, "computational_thinking": 0.0},
        uncertainty={"logical_reasoning": 0.6, "algorithmic_thinking": 1.0, "problem_solving": 1.0, "spatial_reasoning": 1.0, "computational_thinking": 1.0},
        response_count=1,
        dimension_coverage=updated_coverage
    )

    # Cycle 2: Context updated
    context_2 = make_context(
        answered_ids=updated_answered,
        ability_state=updated_ability,
        min_questions=2,
        max_questions=2
    )

    # Cycle 2: Selector should NOT select the already-answered question
    sel_res_2 = selector.select(pool, context_2)
    assert sel_res_2.selected_question_id != chosen_id
    assert sel_res_2.selected_question_id in [102, 103]

    # Cycle 3: Student completes question 2 -> reached max_questions=2
    ability_final = AbilityState(
        dimension_scores=updated_ability.dimension_scores,
        uncertainty=updated_ability.uncertainty,
        response_count=2,  # max_questions reached
        dimension_coverage=updated_ability.dimension_coverage
    )
    stop_dec_final = stopping_strategy.evaluate(context_2, ability_final, remaining_candidates_count=1)
    assert stop_dec_final.should_stop is True
    assert stop_dec_final.reason == StoppingReason.MAX_QUESTIONS_REACHED
