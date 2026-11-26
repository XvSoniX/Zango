import pytest
from app.engine.protocols import (
    AbilityState,
    EvaluationResult,
    ItemParameterSnapshot,
    AnswerEvaluator,
    AbilityEstimationStrategy
)
from app.engine.evaluator import BaselineAnswerEvaluator
from app.engine.estimator import BaselineMultidimensionalEstimator, create_initial_ability_state
from app.engine.uncertainty import UncertaintyEstimator
from app.engine.exceptions import (
    InvalidAnswerPayloadError,
    InvalidOptionError,
    UnsupportedQuestionTypeError,
    InvalidQuestionVersionError,
)
from app.domain.enums import CognitiveDimension

# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_question():
    """Standard multiple-choice question version snapshot."""
    return {
        "id": 101,
        "question_id": 10,
        "version": 1,
        "question_type": "MULTIPLE_CHOICE",
        "content": "In sequence 2, 4, 8, what comes next?",
        "options": [
            {"key": "A", "text": "10", "order": 1},
            {"key": "B", "text": "16", "order": 2},
            {"key": "C", "text": "14", "order": 3},
            {"key": "D", "text": "12", "order": 4},
        ],
        "correct_answer": "B",
        "difficulty": 0.5,
        "discrimination": 1.1,
        "guessing": 0.25,
        "dimensions": {
            "logical_reasoning": 0.9,
            "algorithmic_thinking": 0.5,
            "problem_solving": 0.2,
            "spatial_reasoning": 0.0,
            "computational_thinking": 0.1,
        },
        "calibration_status": "CALIBRATED",
    }


# ---------------------------------------------------------------------------
# TASK-019: ANSWER EVALUATOR TESTS
# ---------------------------------------------------------------------------

def test_evaluator_correct_answer(sample_question):
    evaluator = BaselineAnswerEvaluator()
    assert isinstance(evaluator, AnswerEvaluator)

    result = evaluator.evaluate(
        question=sample_question,
        submitted_answer={"selected_option": "B"},
        response_time_ms=12000
    )

    assert result.is_correct is True
    assert result.score == 1.0
    assert result.response_time_ms == 12000
    assert result.evaluation_status == "VALID"
    assert result.question_version_id == 101
    # Security: Ensure correct_answer is never exposed in EvaluationResult
    assert not hasattr(result, "correct_answer")
    assert "correct_answer" not in result.metadata

def test_evaluator_correct_answer_case_insensitive(sample_question):
    evaluator = BaselineAnswerEvaluator()
    result = evaluator.evaluate(
        question=sample_question,
        submitted_answer={"selected_option": " b "},
        response_time_ms=5000
    )
    assert result.is_correct is True
    assert result.score == 1.0

def test_evaluator_incorrect_answer(sample_question):
    evaluator = BaselineAnswerEvaluator()
    result = evaluator.evaluate(
        question=sample_question,
        submitted_answer={"selected_option": "A"},
        response_time_ms=8000
    )

    assert result.is_correct is False
    assert result.score == 0.0
    assert result.evaluation_status == "VALID"

def test_evaluator_empty_payload(sample_question):
    evaluator = BaselineAnswerEvaluator()
    with pytest.raises(InvalidAnswerPayloadError, match="non-empty 'selected_option'"):
        evaluator.evaluate(
            question=sample_question,
            submitted_answer={"selected_option": ""},
            response_time_ms=4000
        )

def test_evaluator_malformed_payload(sample_question):
    evaluator = BaselineAnswerEvaluator()
    with pytest.raises(InvalidAnswerPayloadError, match="must be a JSON dictionary"):
        evaluator.evaluate(
            question=sample_question,
            submitted_answer="not_a_dict",  # type: ignore
            response_time_ms=4000
        )

def test_evaluator_option_not_in_choices(sample_question):
    evaluator = BaselineAnswerEvaluator()
    with pytest.raises(InvalidOptionError, match="Selected option 'Z' is not a valid choice"):
        evaluator.evaluate(
            question=sample_question,
            submitted_answer={"selected_option": "Z"},
            response_time_ms=4000
        )

def test_evaluator_invalid_question_version():
    evaluator = BaselineAnswerEvaluator()
    with pytest.raises(InvalidQuestionVersionError):
        evaluator.evaluate(
            question=None,
            submitted_answer={"selected_option": "A"},
            response_time_ms=4000
        )

    with pytest.raises(InvalidQuestionVersionError, match="correct_answer"):
        evaluator.evaluate(
            question={"options": [{"key": "A", "text": "Opt A"}]},
            submitted_answer={"selected_option": "A"},
            response_time_ms=4000
        )

def test_evaluator_unsupported_question_type(sample_question):
    evaluator = BaselineAnswerEvaluator()
    bad_q = dict(sample_question, question_type="OPEN_ENDED_ESSAY")
    with pytest.raises(UnsupportedQuestionTypeError, match="only supports MULTIPLE_CHOICE"):
        evaluator.evaluate(
            question=bad_q,
            submitted_answer={"selected_option": "A"},
            response_time_ms=4000
        )

def test_evaluator_is_pure_and_stateless(sample_question):
    evaluator = BaselineAnswerEvaluator()
    # Multiple evaluations with identical inputs yield identical outputs
    r1 = evaluator.evaluate(sample_question, {"selected_option": "B"}, 5000)
    r2 = evaluator.evaluate(sample_question, {"selected_option": "B"}, 5000)
    assert r1 == r2


# ---------------------------------------------------------------------------
# TASK-020: ABILITY STATE & BASELINE ESTIMATOR TESTS
# ---------------------------------------------------------------------------

def test_initial_ability_state():
    state = create_initial_ability_state()
    assert len(state.dimension_scores) == 5
    assert len(state.uncertainty) == 5
    assert state.response_count == 0

    for dim in CognitiveDimension:
        assert state.dimension_scores[dim.value] == 0.0
        assert state.uncertainty[dim.value] == 1.0
        assert state.dimension_coverage[dim.value] == 0

def test_estimator_correct_answer_increases_ability(sample_question):
    estimator = BaselineMultidimensionalEstimator()
    assert isinstance(estimator, AbilityEstimationStrategy)

    state = create_initial_ability_state()
    eval_result = EvaluationResult(
        is_correct=True,
        score=1.0,
        response_time_ms=5000,
        raw_answer={"selected_option": "B"},
        evaluator_version="1.0.0"
    )

    new_state = estimator.estimate(state, eval_result, sample_question)

    # Dimension with high correlation (logical_reasoning=0.9) must increase
    assert new_state.dimension_scores["logical_reasoning"] > state.dimension_scores["logical_reasoning"]
    # Dimension with zero correlation (spatial_reasoning=0.0) must not change
    assert new_state.dimension_scores["spatial_reasoning"] == state.dimension_scores["spatial_reasoning"]
    # Coverage for logical_reasoning increases by 1
    assert new_state.dimension_coverage["logical_reasoning"] == 1
    assert new_state.dimension_coverage["spatial_reasoning"] == 0
    assert new_state.response_count == 1

def test_estimator_incorrect_answer_decreases_ability(sample_question):
    estimator = BaselineMultidimensionalEstimator()
    state = create_initial_ability_state()

    eval_result = EvaluationResult(
        is_correct=False,
        score=0.0,
        response_time_ms=5000,
        raw_answer={"selected_option": "A"},
        evaluator_version="1.0.0"
    )

    new_state = estimator.estimate(state, eval_result, sample_question)

    assert new_state.dimension_scores["logical_reasoning"] < state.dimension_scores["logical_reasoning"]
    assert new_state.dimension_scores["spatial_reasoning"] == state.dimension_scores["spatial_reasoning"]

def test_estimator_dimensions_vector_proportional_impact(sample_question):
    estimator = BaselineMultidimensionalEstimator()
    state = create_initial_ability_state()

    eval_result = EvaluationResult(
        is_correct=True,
        score=1.0,
        response_time_ms=5000,
        raw_answer={"selected_option": "B"},
        evaluator_version="1.0.0"
    )

    new_state = estimator.estimate(state, eval_result, sample_question)

    # Question weight: logical=0.9, algorithmic=0.5, problem_solving=0.2
    delta_log = new_state.dimension_scores["logical_reasoning"] - state.dimension_scores["logical_reasoning"]
    delta_alg = new_state.dimension_scores["algorithmic_thinking"] - state.dimension_scores["algorithmic_thinking"]
    delta_prb = new_state.dimension_scores["problem_solving"] - state.dimension_scores["problem_solving"]

    assert delta_log > delta_alg > delta_prb > 0

def test_estimator_difficulty_influence():
    estimator = BaselineMultidimensionalEstimator()
    state = create_initial_ability_state()

    eval_correct = EvaluationResult(
        is_correct=True,
        score=1.0,
        response_time_ms=5000,
        raw_answer={"selected_option": "A"},
        evaluator_version="1.0.0"
    )

    # Hard question (b = 2.0) vs Easy question (b = -2.0) with identical dimension weights
    hard_q = {"dimensions": {"logical_reasoning": 1.0}, "difficulty": 2.0}
    easy_q = {"dimensions": {"logical_reasoning": 1.0}, "difficulty": -2.0}

    state_hard = estimator.estimate(state, eval_correct, hard_q)
    state_easy = estimator.estimate(state, eval_correct, easy_q)

    # Answering a hard question correctly yields larger ability increase than answering an easy question
    delta_hard = state_hard.dimension_scores["logical_reasoning"] - state.dimension_scores["logical_reasoning"]
    delta_easy = state_easy.dimension_scores["logical_reasoning"] - state.dimension_scores["logical_reasoning"]

    assert delta_hard > delta_easy

def test_estimator_bounds_clamping():
    estimator = BaselineMultidimensionalEstimator(learning_rate=1.0, min_ability=-3.0, max_ability=3.0)
    state = create_initial_ability_state()

    # Simulate 20 consecutive correct answers on hard items
    q = {"dimensions": {"logical_reasoning": 1.0}, "difficulty": 2.0}
    eval_correct = EvaluationResult(is_correct=True, score=1.0, response_time_ms=1000, raw_answer={}, evaluator_version="1")

    curr = state
    for _ in range(25):
        curr = estimator.estimate(curr, eval_correct, q)

    assert curr.dimension_scores["logical_reasoning"] <= 3.0
    assert curr.dimension_scores["logical_reasoning"] >= -3.0

def test_estimator_deterministic(sample_question):
    estimator = BaselineMultidimensionalEstimator()
    state = create_initial_ability_state()
    eval_res = EvaluationResult(is_correct=True, score=1.0, response_time_ms=5000, raw_answer={}, evaluator_version="1")

    run1 = estimator.estimate(state, eval_res, sample_question)
    run2 = estimator.estimate(state, eval_res, sample_question)

    assert run1.dimension_scores == run2.dimension_scores
    assert run1.uncertainty == run2.uncertainty


# ---------------------------------------------------------------------------
# TASK-021: UNCERTAINTY ESTIMATOR TESTS
# ---------------------------------------------------------------------------

def test_uncertainty_initial_state():
    unc_est = UncertaintyEstimator(initial_uncertainty=1.0)
    init_unc = unc_est.create_initial_uncertainty()
    assert len(init_unc) == 5
    for val in init_unc.values():
        assert val == 1.0

def test_uncertainty_decreases_with_evidence():
    unc_est = UncertaintyEstimator(initial_uncertainty=1.0)
    state = create_initial_ability_state()

    dim_weights = {"logical_reasoning": 0.9, "spatial_reasoning": 0.0}
    new_unc, new_ev = unc_est.compute_uncertainty(state, dim_weights, is_valid_response=True)

    # Logical Reasoning had 0.9 evidence -> uncertainty decreases
    assert new_unc["logical_reasoning"] < 1.0
    assert new_ev["logical_reasoning"] == 0.9

    # Spatial Reasoning had 0.0 evidence -> uncertainty strictly remains at 1.0
    assert new_unc["spatial_reasoning"] == 1.0
    assert new_ev["spatial_reasoning"] == 0.0

def test_uncertainty_monotonic_decrease():
    unc_est = UncertaintyEstimator(initial_uncertainty=1.0, min_uncertainty=0.25)
    state = create_initial_ability_state()

    dim_weights = {"logical_reasoning": 0.8}

    u1, _ = unc_est.compute_uncertainty(state, dim_weights)
    # Simulate updated state
    s1 = AbilityState(
        dimension_scores=state.dimension_scores,
        uncertainty=u1,
        response_count=1,
        dimension_coverage=state.dimension_coverage,
        metadata={"accumulated_evidence": {"logical_reasoning": 0.8}}
    )
    u2, _ = unc_est.compute_uncertainty(s1, dim_weights)

    # Uncertainty must strictly decrease: 1.0 > u1 > u2 >= 0.25
    assert 1.0 > u1["logical_reasoning"] > u2["logical_reasoning"] >= 0.25

def test_uncertainty_respects_invalid_responses():
    unc_est = UncertaintyEstimator(initial_uncertainty=1.0)
    state = create_initial_ability_state()

    dim_weights = {"logical_reasoning": 1.0}
    # Response is structurally invalid
    new_unc, new_ev = unc_est.compute_uncertainty(state, dim_weights, is_valid_response=False)

    # Uncertainty should NOT decrease for invalid response
    assert new_unc["logical_reasoning"] == 1.0
    assert new_ev["logical_reasoning"] == 0.0

def test_uncertainty_respects_min_threshold():
    unc_est = UncertaintyEstimator(initial_uncertainty=1.0, min_uncertainty=0.25)
    state = AbilityState(
        dimension_scores={},
        uncertainty={},
        response_count=100,
        dimension_coverage={},
        metadata={"accumulated_evidence": {"logical_reasoning": 1000.0}}
    )

    dim_weights = {"logical_reasoning": 1.0}
    new_unc, _ = unc_est.compute_uncertainty(state, dim_weights)
    assert new_unc["logical_reasoning"] == 0.25


# ---------------------------------------------------------------------------
# SECTION 5: THREE-MODULE INTEGRATION TESTS
# ---------------------------------------------------------------------------

def test_three_module_integration_pipeline(sample_question):
    """
    Validates complete pipeline flow:
    QuestionVersion + UserAnswer -> Evaluator -> EvaluationResult ->
    Estimator -> Updated AbilityState (with updated scores and uncertainty).
    """
    evaluator = BaselineAnswerEvaluator()
    estimator = BaselineMultidimensionalEstimator()

    # Step 1: Initial Ability State
    state_0 = create_initial_ability_state()
    assert state_0.dimension_scores["logical_reasoning"] == 0.0
    assert state_0.uncertainty["logical_reasoning"] == 1.0

    # Step 2: Answer evaluation
    user_answer = {"selected_option": "B"}  # Correct answer
    eval_result = evaluator.evaluate(
        question=sample_question,
        submitted_answer=user_answer,
        response_time_ms=15000
    )
    assert eval_result.is_correct is True

    # Step 3: Ability & Uncertainty estimation
    state_1 = estimator.estimate(
        current_state=state_0,
        latest_evaluation=eval_result,
        question=sample_question
    )

    # Verify score updated
    assert state_1.dimension_scores["logical_reasoning"] > 0.0
    assert state_1.dimension_scores["algorithmic_thinking"] > 0.0
    assert state_1.dimension_scores["spatial_reasoning"] == 0.0

    # Verify uncertainty updated
    assert state_1.uncertainty["logical_reasoning"] < 1.0
    assert state_1.uncertainty["algorithmic_thinking"] < 1.0
    assert state_1.uncertainty["spatial_reasoning"] == 1.0

    # Step 4: Subsequent incorrect answer on another question
    q2 = {
        "id": 102,
        "question_type": "MULTIPLE_CHOICE",
        "options": [{"key": "A", "text": "A"}, {"key": "B", "text": "B"}],
        "correct_answer": "A",
        "difficulty": -0.5,
        "dimensions": {"spatial_reasoning": 0.9, "logical_reasoning": 0.1}
    }
    eval_result_2 = evaluator.evaluate(
        question=q2,
        submitted_answer={"selected_option": "B"},  # Incorrect
        response_time_ms=7000
    )
    assert eval_result_2.is_correct is False

    state_2 = estimator.estimate(
        current_state=state_1,
        latest_evaluation=eval_result_2,
        question=q2
    )

    # Spatial reasoning now has negative score and reduced uncertainty
    assert state_2.dimension_scores["spatial_reasoning"] < 0.0
    assert state_2.uncertainty["spatial_reasoning"] < 1.0
    assert state_2.response_count == 2


def test_rapid_guess_is_flagged_and_neutralized(sample_question):
    evaluator = BaselineAnswerEvaluator(rapid_guess_threshold_ms=1500)
    estimator = BaselineMultidimensionalEstimator()
    state = create_initial_ability_state()

    eval_res = evaluator.evaluate(
        question=sample_question,
        submitted_answer={"selected_option": "B"},
        response_time_ms=800,
    )
    assert eval_res.evaluation_status == "RAPID_GUESS"
    assert eval_res.metadata.get("is_rapid_guess") is True

    next_state = estimator.estimate(state, eval_res, sample_question)
    assert next_state.dimension_scores == state.dimension_scores
    assert next_state.uncertainty == state.uncertainty
    assert next_state.response_count == 0
    assert next_state.metadata.get("rapid_guess_count") == 1


def test_3pl_fisher_information_matches_theory():
    from app.engine.uncertainty import probability_3pl, fisher_information_3pl

    p = probability_3pl(theta=0.0, difficulty=0.0, discrimination=1.0, guessing=0.25)
    assert abs(p - 0.625) < 1e-6

    info_at_match = fisher_information_3pl(theta=0.0, difficulty=0.0, discrimination=1.2, guessing=0.25)
    info_far = fisher_information_3pl(theta=3.0, difficulty=0.0, discrimination=1.2, guessing=0.25)
    assert info_at_match > info_far > 0.0
