"""
Question Selection Metrics Calculator (TASK-034).
Evaluates question selection behavior, dimension coverage, difficulty adaptation,
and exposure distribution from synthetic assessment simulation data.
"""
from typing import List, Dict, Any, Optional
import math
import statistics
from collections import defaultdict, Counter

from app.evaluation.domain.config import (
    EvaluationSettings,
    CANONICAL_DIMENSIONS,
    DIMENSION_LABELS,
)


class SelectionMetricsCalculator:
    """
    Pure analytical engine for evaluating question selection behavior.
    Does not modify simulation data or engine state.
    """

    def __init__(self, settings: Optional[EvaluationSettings] = None):
        self.settings = settings or EvaluationSettings()

    def calculate(
        self,
        participant_results: List[Any],
        total_questions_in_bank: int = 50,
        question_bank_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Main calculation entrypoint.
        Processes completed participant simulation results.
        """
        # 1. Segment valid and excluded participants
        valid_results = []
        excluded_results = []

        for p in participant_results:
            session_status = getattr(p, "session_status", None) or (p.get("session_status") if isinstance(p, dict) else None)
            q_records = getattr(p, "question_records", None) or (p.get("question_records") if isinstance(p, dict) else [])
            
            if session_status == "FAILED" or not q_records:
                excluded_results.append({
                    "synthetic_user_id": getattr(p, "synthetic_user_id", None) or (p.get("synthetic_user_id") if isinstance(p, dict) else "unknown"),
                    "reason": "Session failed or has 0 question records",
                })
            else:
                valid_results.append(p)

        n_valid = len(valid_results)
        n_excluded = len(excluded_results)

        if n_valid == 0:
            return {
                "error": "No valid completed simulation participants to evaluate",
                "eligible_count": 0,
                "excluded_count": n_excluded,
                "exclusions": excluded_results,
            }

        # 2. Compute individual metric sections
        dim_coverage_res = self._compute_dimension_coverage(valid_results)
        diff_dist_res = self._compute_difficulty_distribution(valid_results)
        exposure_res = self._compute_exposure_and_repetition(
            valid_results,
            total_questions_in_bank=total_questions_in_bank,
            question_bank_ids=question_bank_ids,
        )
        length_res = self._compute_assessment_length(valid_results)
        seq_res = self._compute_sequence_analysis(valid_results)
        archetype_res = self._compute_archetype_breakdowns(valid_results)
        anomalies = self._detect_anomalies(
            dim_coverage_res,
            diff_dist_res,
            exposure_res,
            length_res,
        )

        # 3. Top-Level Summary (Formatted specifically for dashboard cards)
        summary = {
            "dimension_coverage_pct": dim_coverage_res["overall_dimension_coverage_pct"],
            "average_questions": length_res["mean_questions_per_session"],
            "within_session_repetition_pct": exposure_res["within_session_repetition_rate_pct"],
            "exposure_distribution_index": exposure_res["exposure_distribution_index"],
            "total_participants_analyzed": n_valid,
            "total_questions_presented": exposure_res["total_question_presentations"],
            "unique_questions_selected": exposure_res["unique_questions_selected"],
            "bank_coverage_ratio": exposure_res["bank_coverage_ratio"],
        }

        return {
            "eligible_sessions_count": n_valid,
            "excluded_sessions_count": n_excluded,
            "excluded_sessions": excluded_results,
            "summary_metrics": summary,
            "dimension_coverage": dim_coverage_res,
            "difficulty_distribution": diff_dist_res,
            "exposure_and_repetition": exposure_res,
            "assessment_length": length_res,
            "selection_sequence": seq_res,
            "archetype_breakdowns": archetype_res,
            "anomalies": anomalies,
        }

    def _get_q_records(self, p: Any) -> List[Dict[str, Any]]:
        return getattr(p, "question_records", None) or (p.get("question_records") if isinstance(p, dict) else [])

    def _get_field(self, p: Any, field_name: str, default: Any = None) -> Any:
        return getattr(p, field_name, None) if hasattr(p, field_name) else (p.get(field_name, default) if isinstance(p, dict) else default)

    # -------------------------------------------------------------------------
    # 3.1. Dimension Coverage
    # -------------------------------------------------------------------------
    def _compute_dimension_coverage(self, valid_results: List[Any]) -> Dict[str, Any]:
        """
        Calculates multi-dimensional coverage across the 5 canonical dimensions
        using actual continuous dimension vector loadings.
        """
        n_sessions = len(valid_results)
        threshold = self.settings.dimension_contribution_threshold
        sufficient_threshold = self.settings.sufficient_dimension_evidence_threshold

        # Aggregation structures
        per_dim_counts = {d: 0 for d in CANONICAL_DIMENSIONS}
        per_dim_weighted = {d: 0.0 for d in CANONICAL_DIMENSIONS}
        per_dim_sessions_with_exposure = {d: 0 for d in CANONICAL_DIMENSIONS}
        per_dim_sessions_with_sufficient = {d: 0 for d in CANONICAL_DIMENSIONS}

        session_coverage_ratios = []
        sessions_with_insufficient = 0

        for p in valid_results:
            records = self._get_q_records(p)
            session_dim_counts = {d: 0 for d in CANONICAL_DIMENSIONS}

            for rec in records:
                dims = rec.get("dimensions", {}) or {}
                for d in CANONICAL_DIMENSIONS:
                    w = float(dims.get(d, 0.0))
                    if w >= threshold:
                        session_dim_counts[d] += 1
                        per_dim_counts[d] += 1
                        per_dim_weighted[d] += w

            # Evaluate this session's coverage
            covered_dims = sum(1 for d in CANONICAL_DIMENSIONS if session_dim_counts[d] >= 1)
            sufficient_dims = sum(1 for d in CANONICAL_DIMENSIONS if session_dim_counts[d] >= sufficient_threshold)

            session_ratio = covered_dims / len(CANONICAL_DIMENSIONS)
            session_coverage_ratios.append(session_ratio)

            if sufficient_dims < len(CANONICAL_DIMENSIONS):
                sessions_with_insufficient += 1

            for d in CANONICAL_DIMENSIONS:
                if session_dim_counts[d] >= 1:
                    per_dim_sessions_with_exposure[d] += 1
                if session_dim_counts[d] >= sufficient_threshold:
                    per_dim_sessions_with_sufficient[d] += 1

        # Per dimension details
        per_dimension_metrics = {}
        for d in CANONICAL_DIMENSIONS:
            per_dimension_metrics[d] = {
                "dimension_code": d,
                "dimension_label": DIMENSION_LABELS.get(d, d),
                "total_question_exposures": per_dim_counts[d],
                "total_weighted_exposure": round(per_dim_weighted[d], 3),
                "sessions_covered_count": per_dim_sessions_with_exposure[d],
                "sessions_covered_pct": round((per_dim_sessions_with_exposure[d] / n_sessions) * 100, 2) if n_sessions else 0.0,
                "sessions_sufficient_pct": round((per_dim_sessions_with_sufficient[d] / n_sessions) * 100, 2) if n_sessions else 0.0,
            }

        mean_coverage_per_session = statistics.mean(session_coverage_ratios) if session_coverage_ratios else 0.0
        min_coverage_per_session = min(session_coverage_ratios) if session_coverage_ratios else 0.0
        insufficient_coverage_session_pct = (sessions_with_insufficient / n_sessions * 100) if n_sessions else 0.0

        # Overall dimension coverage: % of dimensions receiving sufficient exposure across all sessions
        dims_with_sufficient_overall = sum(
            1 for d in CANONICAL_DIMENSIONS if per_dim_sessions_with_exposure[d] >= max(1, int(0.2 * n_sessions))
        )
        overall_dim_coverage_pct = round((dims_with_sufficient_overall / len(CANONICAL_DIMENSIONS)) * 100, 1)

        return {
            "overall_dimension_coverage_pct": overall_dim_coverage_pct,
            "average_dimension_coverage_per_session": round(mean_coverage_per_session, 3),
            "minimum_dimension_coverage_across_sessions": round(min_coverage_per_session, 3),
            "sessions_with_insufficient_coverage_pct": round(insufficient_coverage_session_pct, 1),
            "per_dimension_metrics": per_dimension_metrics,
            "contribution_threshold_used": threshold,
            "sufficient_evidence_threshold_used": sufficient_threshold,
        }

    # -------------------------------------------------------------------------
    # 3.2. Difficulty Distribution
    # -------------------------------------------------------------------------
    def _compute_difficulty_distribution(self, valid_results: List[Any]) -> Dict[str, Any]:
        """
        Analyzes difficulty of questions selected across all sessions and steps.
        """
        all_difficulties: List[float] = []
        step_difficulties: Dict[int, List[float]] = defaultdict(list)

        for p in valid_results:
            records = self._get_q_records(p)
            for rec in records:
                diff = float(rec.get("difficulty", 0.0))
                step = int(rec.get("step", 1))
                all_difficulties.append(diff)
                step_difficulties[step].append(diff)

        if not all_difficulties:
            return {}

        mean_diff = statistics.mean(all_difficulties)
        median_diff = statistics.median(all_difficulties)
        min_diff = min(all_difficulties)
        max_diff = max(all_difficulties)
        std_diff = statistics.stdev(all_difficulties) if len(all_difficulties) > 1 else 0.0
        var_diff = statistics.variance(all_difficulties) if len(all_difficulties) > 1 else 0.0

        # Binning across configurable difficulty buckets
        bucket_counts = []
        total_presents = len(all_difficulties)
        for lower, upper in self.settings.difficulty_buckets:
            cnt = sum(1 for d in all_difficulties if lower <= d < upper)
            pct = round((cnt / total_presents * 100), 2) if total_presents else 0.0
            bucket_counts.append({
                "interval": f"[{lower:.1f}, {upper:.1f})",
                "lower": lower,
                "upper": upper,
                "count": cnt,
                "percentage": pct,
            })

        # Progression across steps
        progression = []
        for step in sorted(step_difficulties.keys()):
            s_diffs = step_difficulties[step]
            progression.append({
                "step": step,
                "sample_count": len(s_diffs),
                "mean_difficulty": round(statistics.mean(s_diffs), 3),
                "std_difficulty": round(statistics.stdev(s_diffs), 3) if len(s_diffs) > 1 else 0.0,
            })

        return {
            "mean_difficulty": round(mean_diff, 3),
            "median_difficulty": round(median_diff, 3),
            "min_difficulty": round(min_diff, 3),
            "max_difficulty": round(max_diff, 3),
            "variance": round(var_diff, 4),
            "std_deviation": round(std_diff, 4),
            "difficulty_buckets": bucket_counts,
            "step_progression": progression,
        }

    # -------------------------------------------------------------------------
    # 3.3. Question Exposure and Repetition
    # -------------------------------------------------------------------------
    def _compute_exposure_and_repetition(
        self,
        valid_results: List[Any],
        total_questions_in_bank: int = 50,
        question_bank_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates question exposure, unique selections, within-session repetition,
        and exposure uniformity index.
        """
        all_presentations: List[int] = []
        within_session_duplicates = 0
        total_presentations_count = 0

        for p in valid_results:
            records = self._get_q_records(p)
            seen_in_session = set()
            for rec in records:
                qid = int(rec.get("question_id", 0))
                all_presentations.append(qid)
                total_presentations_count += 1
                if qid in seen_in_session:
                    within_session_duplicates += 1
                else:
                    seen_in_session.add(qid)

        # Within-session repetition rate
        within_session_rep_rate = (
            (within_session_duplicates / total_presentations_count * 100)
            if total_presentations_count > 0 else 0.0
        )

        counts = Counter(all_presentations)
        unique_selected = len(counts)
        bank_total = max(total_questions_in_bank, unique_selected)

        # Top 5 most and least frequently selected
        most_frequent = [
            {"question_id": qid, "selection_count": cnt, "exposure_rate": round(cnt / total_presentations_count, 4)}
            for qid, cnt in counts.most_common(5)
        ]
        least_frequent = [
            {"question_id": qid, "selection_count": cnt, "exposure_rate": round(cnt / total_presentations_count, 4)}
            for qid, cnt in sorted(counts.items(), key=lambda x: x[1])[:5]
        ]

        # Questions never selected
        never_selected_ids = []
        if question_bank_ids:
            never_selected_ids = [qid for qid in question_bank_ids if qid not in counts]
        never_selected_count = max(0, bank_total - unique_selected)

        # Exposure Distribution Index (Gini-derived uniformity)
        # Perfectly uniform = 1.0; totally skewed = 0.0
        exposure_index = self._calculate_exposure_distribution_index(counts, bank_total)

        return {
            "total_question_presentations": total_presentations_count,
            "unique_questions_selected": unique_selected,
            "total_questions_in_bank": bank_total,
            "bank_coverage_ratio": round(unique_selected / bank_total, 3) if bank_total else 0.0,
            "within_session_repetition_rate_pct": round(within_session_rep_rate, 2),
            "within_session_duplicate_count": within_session_duplicates,
            "exposure_distribution_index": round(exposure_index, 2),
            "most_frequently_selected": most_frequent,
            "least_frequently_selected": least_frequent,
            "never_selected_count": never_selected_count,
            "never_selected_question_ids": never_selected_ids[:20],
        }

    def _calculate_exposure_distribution_index(self, counts: Counter, bank_total: int) -> float:
        """
        Calculates exposure uniformity index based on normalized Gini coefficient.
        Returns value in [0.0, 1.0] where 1.0 is completely uniform exposure.
        """
        if bank_total <= 0 or not counts:
            return 0.0

        # Construct vector including zero-counts for never selected questions
        all_counts = [counts.get(qid, 0) for qid in range(1, bank_total + 1)]
        all_counts.sort()

        n = len(all_counts)
        total_sum = sum(all_counts)
        if total_sum == 0:
            return 0.0

        # Gini coefficient calculation
        cumulative = 0.0
        for i, val in enumerate(all_counts, 1):
            cumulative += i * val
        gini = (2.0 * cumulative) / (n * total_sum) - (n + 1.0) / n

        # Uniformity Index = 1.0 - Gini (bounded in [0.0, 1.0])
        uniformity = max(0.0, min(1.0, 1.0 - gini))
        return uniformity

    # -------------------------------------------------------------------------
    # 3.4. Average Assessment Length
    # -------------------------------------------------------------------------
    def _compute_assessment_length(self, valid_results: List[Any]) -> Dict[str, Any]:
        """
        Analyzes questions answered per completed session with breakdown by stopping reason and age.
        """
        lengths = [
            int(self._get_field(p, "answered_question_count", len(self._get_q_records(p))))
            for p in valid_results
        ]

        if not lengths:
            return {}

        mean_len = statistics.mean(lengths)
        median_len = statistics.median(lengths)
        min_len = min(lengths)
        max_len = max(lengths)
        std_len = statistics.stdev(lengths) if len(lengths) > 1 else 0.0

        # Breakdown by stopping reason
        by_stopping: Dict[str, List[int]] = defaultdict(list)
        for p in valid_results:
            reason = self._get_field(p, "stopping_reason", "UNKNOWN") or "UNKNOWN"
            count = int(self._get_field(p, "answered_question_count", len(self._get_q_records(p))))
            by_stopping[reason].append(count)

        stopping_breakdown = {}
        for reason, vals in by_stopping.items():
            stopping_breakdown[reason] = {
                "session_count": len(vals),
                "mean_length": round(statistics.mean(vals), 2),
                "min_length": min(vals),
                "max_length": max(vals),
            }

        return {
            "mean_questions_per_session": round(mean_len, 1),
            "median_questions_per_session": round(median_len, 1),
            "min_questions_per_session": min_len,
            "max_questions_per_session": max_len,
            "std_deviation": round(std_len, 2),
            "by_stopping_reason": stopping_breakdown,
        }

    # -------------------------------------------------------------------------
    # 3.5. Selection Sequence Analysis
    # -------------------------------------------------------------------------
    def _compute_sequence_analysis(self, valid_results: List[Any]) -> Dict[str, Any]:
        """
        Inspects adaptive difficulty response to correct and incorrect answers.
        """
        delta_after_correct: List[float] = []
        delta_after_incorrect: List[float] = []

        for p in valid_results:
            records = self._get_q_records(p)
            for i in range(len(records) - 1):
                cur = records[i]
                nxt = records[i + 1]
                cur_diff = float(cur.get("difficulty", 0.0))
                nxt_diff = float(nxt.get("difficulty", 0.0))
                delta = nxt_diff - cur_diff

                is_correct = bool(cur.get("is_correct", False))
                if is_correct:
                    delta_after_correct.append(delta)
                else:
                    delta_after_incorrect.append(delta)

        mean_delta_correct = statistics.mean(delta_after_correct) if delta_after_correct else 0.0
        mean_delta_incorrect = statistics.mean(delta_after_incorrect) if delta_after_incorrect else 0.0

        is_responsive = mean_delta_correct >= mean_delta_incorrect

        return {
            "mean_difficulty_delta_after_correct": round(mean_delta_correct, 3),
            "mean_difficulty_delta_after_incorrect": round(mean_delta_incorrect, 3),
            "adaptive_responsiveness_status": "RESPONSIVE" if is_responsive else "UNRESPONSIVE",
            "total_transitions_evaluated": len(delta_after_correct) + len(delta_after_incorrect),
        }

    # -------------------------------------------------------------------------
    # 3.6. Archetype-Based Analysis
    # -------------------------------------------------------------------------
    def _compute_archetype_breakdowns(self, valid_results: List[Any]) -> Dict[str, Any]:
        """
        Partitions selection metrics across synthetic participant archetypes.
        """
        by_archetype: Dict[str, List[Any]] = defaultdict(list)
        for p in valid_results:
            arch = self._get_field(p, "archetype", "UNKNOWN")
            by_archetype[arch].append(p)

        results = {}
        for arch, arch_participants in by_archetype.items():
            arch_lengths = [int(self._get_field(p, "answered_question_count", len(self._get_q_records(p)))) for p in arch_participants]
            arch_diffs = [
                float(rec.get("difficulty", 0.0))
                for p in arch_participants
                for rec in self._get_q_records(p)
            ]

            results[arch] = {
                "participant_count": len(arch_participants),
                "mean_questions": round(statistics.mean(arch_lengths), 1) if arch_lengths else 0.0,
                "mean_difficulty": round(statistics.mean(arch_diffs), 3) if arch_diffs else 0.0,
                "min_difficulty": round(min(arch_diffs), 3) if arch_diffs else 0.0,
                "max_difficulty": round(max(arch_diffs), 3) if arch_diffs else 0.0,
            }

        return results

    # -------------------------------------------------------------------------
    # Anomalies
    # -------------------------------------------------------------------------
    def _detect_anomalies(
        self,
        dim_coverage: Dict[str, Any],
        diff_dist: Dict[str, Any],
        exposure: Dict[str, Any],
        length_res: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        anomalies = []

        # Check for unexposed dimensions
        for d, m in dim_coverage.get("per_dimension_metrics", {}).items():
            if m.get("total_question_exposures", 0) == 0:
                anomalies.append({
                    "severity": "HIGH",
                    "type": "DIMENSION_STARVATION",
                    "message": f"Dimension '{d}' received 0 question selections across all evaluated sessions.",
                })

        # Check for high within-session repetition
        rep_rate = exposure.get("within_session_repetition_rate_pct", 0.0)
        if rep_rate > 5.0:
            anomalies.append({
                "severity": "MEDIUM",
                "type": "HIGH_WITHIN_SESSION_REPETITION",
                "message": f"Within-session question repetition is {rep_rate}%, which exceeds expected limits.",
            })

        # Check for bank starvation
        never_count = exposure.get("never_selected_count", 0)
        bank_total = exposure.get("total_questions_in_bank", 50)
        if bank_total > 0 and (never_count / bank_total) > 0.60:
            anomalies.append({
                "severity": "LOW",
                "type": "LOW_BANK_UTILIZATION",
                "message": f"{never_count} questions out of {bank_total} were never selected in this simulation run.",
            })

        return anomalies
