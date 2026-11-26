"""
Ability Estimation Quality Metrics Calculator (TASK-035).
Evaluates accuracy of engine ability estimates against synthetic ground truth.
Computes MAE, RMSE, Bias, Dimensional tables, Uncertainty calibration, and Assessment length curves.
"""
from typing import List, Dict, Any, Optional
import math
import statistics
from collections import defaultdict

from app.evaluation.domain.config import (
    EvaluationSettings,
    CANONICAL_DIMENSIONS,
    DIMENSION_LABELS,
)


class EstimationMetricsCalculator:
    """
    Pure analytical engine for evaluating multidimensional ability estimation quality.
    Compares synthetic ground truth abilities against final engine estimates.
    """

    def __init__(self, settings: Optional[EvaluationSettings] = None):
        self.settings = settings or EvaluationSettings()

    def calculate(self, participant_results: List[Any]) -> Dict[str, Any]:
        """
        Main calculation entrypoint.
        Processes completed participant simulation results and generates psychometric accuracy metrics.
        """
        # 1. Validate & Segregate valid and invalid/excluded participants
        valid_items = []
        excluded_items = []

        for p in participant_results:
            session_status = self._get_field(p, "session_status", "UNKNOWN")
            gt = self._get_field(p, "ground_truth_ability", {}) or {}
            est = self._get_field(p, "estimated_ability", {}) or {}
            uid = self._get_field(p, "synthetic_user_id", "unknown")

            if session_status == "FAILED":
                excluded_items.append({"synthetic_user_id": uid, "reason": "Session execution failed"})
                continue

            if not gt or not isinstance(gt, dict):
                excluded_items.append({"synthetic_user_id": uid, "reason": "Missing or invalid ground_truth_ability"})
                continue

            # Verify ground truth contains canonical dimensions
            missing_gt = [d for d in CANONICAL_DIMENSIONS if d not in gt]
            if missing_gt:
                excluded_items.append({"synthetic_user_id": uid, "reason": f"Ground truth missing dimensions: {missing_gt}"})
                continue

            # Verify estimated contains at least one tested dimension
            if not est or not isinstance(est, dict):
                excluded_items.append({"synthetic_user_id": uid, "reason": "Estimated ability vector is empty"})
                continue

            valid_items.append(p)

        n_valid = len(valid_items)
        n_excluded = len(excluded_items)

        if n_valid == 0:
            return {
                "error": "No valid completed simulation participants to evaluate for ability estimation",
                "eligible_count": 0,
                "excluded_count": n_excluded,
                "exclusions": excluded_items,
            }

        # 2. Compute individual metric sections
        dim_metrics_res = self._compute_dimension_metrics(valid_items)
        uncertainty_res = self._compute_uncertainty_evaluation(valid_items)
        length_curve_res = self._compute_length_vs_quality(valid_items)
        archetype_res = self._compute_archetype_breakdown(valid_items)
        anomalies, limitations = self._detect_anomalies_and_limitations(dim_metrics_res, uncertainty_res, n_valid)

        # 3. Format Top-Level Summary & Table (Directly matching user dashboard mockup)
        # Table of dimensions: Logical, Algorithmic, Problem Solving, Spatial, Computational
        dimensional_table = []
        for d in CANONICAL_DIMENSIONS:
            dm = dim_metrics_res["per_dimension"].get(d, {})
            bias_val = dm.get("bias", 0.0)
            bias_str = f"+{bias_val:.2f}" if bias_val >= 0 else f"{bias_val:.2f}"
            dimensional_table.append({
                "dimension": DIMENSION_LABELS.get(d, d),
                "dimension_code": d,
                "mae": dm.get("mae", 0.0),
                "rmse": dm.get("rmse", 0.0),
                "bias": round(bias_val, 4),
                "bias_formatted": bias_str,
                "sample_size": dm.get("sample_size", 0),
            })

        overall_bias_val = dim_metrics_res["overall"]["bias"]
        overall_bias_str = f"+{overall_bias_val:.2f}" if overall_bias_val >= 0 else f"{overall_bias_val:.2f}"

        summary = {
            "overall_mae": dim_metrics_res["overall"]["mae"],
            "overall_rmse": dim_metrics_res["overall"]["rmse"],
            "overall_bias": dim_metrics_res["overall"]["bias"],
            "overall_bias_formatted": overall_bias_str,
            "total_evaluated_participants": n_valid,
            "dimensional_table": dimensional_table,
        }

        return {
            "eligible_sessions_count": n_valid,
            "excluded_sessions_count": n_excluded,
            "excluded_sessions": excluded_items,
            "summary_metrics": summary,
            "dimension_metrics": dim_metrics_res,
            "uncertainty_analysis": uncertainty_res,
            "length_vs_quality": length_curve_res,
            "archetype_breakdowns": archetype_res,
            "anomalies": anomalies,
            "limitations": limitations,
        }

    def _get_field(self, p: Any, field_name: str, default: Any = None) -> Any:
        return getattr(p, field_name, None) if hasattr(p, field_name) else (p.get(field_name, default) if isinstance(p, dict) else default)

    # -------------------------------------------------------------------------
    # 4.2 - 4.5. Per-Dimension & Overall Metrics (MAE, RMSE, Bias)
    # -------------------------------------------------------------------------
    def _compute_dimension_metrics(self, valid_items: List[Any]) -> Dict[str, Any]:
        """
        Calculates MAE, RMSE, and Signed Bias for each dimension and overall.
        Error = Estimated Ability - Ground Truth Ability
        """
        all_errors_global: List[float] = []
        all_abs_errors_global: List[float] = []
        all_sq_errors_global: List[float] = []

        per_dim_errors: Dict[str, List[float]] = {d: [] for d in CANONICAL_DIMENSIONS}

        for p in valid_items:
            gt = self._get_field(p, "ground_truth_ability", {}) or {}
            est = self._get_field(p, "estimated_ability", {}) or {}

            for d in CANONICAL_DIMENSIONS:
                if d in gt and d in est:
                    y_true = float(gt[d])
                    y_pred = float(est[d])
                    err = y_pred - y_true
                    per_dim_errors[d].append(err)
                    all_errors_global.append(err)
                    all_abs_errors_global.append(abs(err))
                    all_sq_errors_global.append(err ** 2)

        # Per dimension statistics
        per_dim_res = {}
        for d in CANONICAL_DIMENSIONS:
            errs = per_dim_errors[d]
            if not errs:
                per_dim_res[d] = {
                    "mae": 0.0,
                    "rmse": 0.0,
                    "bias": 0.0,
                    "sample_size": 0,
                    "min_error": 0.0,
                    "max_error": 0.0,
                    "median_error": 0.0,
                }
                continue

            abs_errs = [abs(e) for e in errs]
            mae = statistics.mean(abs_errs)
            rmse = math.sqrt(statistics.mean([e ** 2 for e in errs]))
            bias = statistics.mean(errs)

            per_dim_res[d] = {
                "dimension_code": d,
                "dimension_label": DIMENSION_LABELS.get(d, d),
                "mae": round(mae, 3),
                "rmse": round(rmse, 3),
                "bias": round(bias, 4),
                "sample_size": len(errs),
                "min_error": round(min(errs), 3),
                "max_error": round(max(errs), 3),
                "median_error": round(statistics.median(errs), 3),
            }

        # Overall across all dimensions
        if all_abs_errors_global:
            overall_mae = statistics.mean(all_abs_errors_global)
            overall_rmse = math.sqrt(statistics.mean(all_sq_errors_global))
            overall_bias = statistics.mean(all_errors_global)
        else:
            overall_mae = 0.0
            overall_rmse = 0.0
            overall_bias = 0.0

        return {
            "overall": {
                "mae": round(overall_mae, 3),
                "rmse": round(overall_rmse, 3),
                "bias": round(overall_bias, 4),
                "total_observations": len(all_abs_errors_global),
            },
            "per_dimension": per_dim_res,
        }

    # -------------------------------------------------------------------------
    # 4.6. Uncertainty Evaluation & Calibration
    # -------------------------------------------------------------------------
    def _compute_uncertainty_evaluation(self, valid_items: List[Any]) -> Dict[str, Any]:
        """
        Analyzes uncertainty consistency with observed estimation error.
        Groups observations into uncertainty buckets to evaluate empirical calibration.
        """
        per_dim_uncertainties: Dict[str, List[float]] = {d: [] for d in CANONICAL_DIMENSIONS}
        observations: List[Dict[str, float]] = []

        for p in valid_items:
            gt = self._get_field(p, "ground_truth_ability", {}) or {}
            est = self._get_field(p, "estimated_ability", {}) or {}
            unc = self._get_field(p, "uncertainty_vector", {}) or {}

            for d in CANONICAL_DIMENSIONS:
                if d in gt and d in est and d in unc:
                    y_true = float(gt[d])
                    y_pred = float(est[d])
                    sigma = float(unc[d])
                    abs_err = abs(y_pred - y_true)

                    per_dim_uncertainties[d].append(sigma)
                    observations.append({
                        "dimension": d,
                        "uncertainty": sigma,
                        "abs_error": abs_err,
                        "sq_error": abs_err ** 2,
                    })

        # Summary per dimension
        per_dim_unc_stats = {}
        for d in CANONICAL_DIMENSIONS:
            vals = per_dim_uncertainties[d]
            per_dim_unc_stats[d] = {
                "dimension_code": d,
                "dimension_label": DIMENSION_LABELS.get(d, d),
                "mean_uncertainty": round(statistics.mean(vals), 3) if vals else 1.0,
                "median_uncertainty": round(statistics.median(vals), 3) if vals else 1.0,
                "min_uncertainty": round(min(vals), 3) if vals else 1.0,
                "max_uncertainty": round(max(vals), 3) if vals else 1.0,
            }

        # Calibration Buckets
        calibration_buckets = []
        for lower, upper in self.settings.uncertainty_buckets:
            bucket_obs = [o for o in observations if lower <= o["uncertainty"] < upper]
            cnt = len(bucket_obs)
            if cnt > 0:
                mean_pred_unc = statistics.mean([o["uncertainty"] for o in bucket_obs])
                obs_mae = statistics.mean([o["abs_error"] for o in bucket_obs])
                obs_rmse = math.sqrt(statistics.mean([o["sq_error"] for o in bucket_obs]))
            else:
                mean_pred_unc = 0.0
                obs_mae = 0.0
                obs_rmse = 0.0

            calibration_buckets.append({
                "uncertainty_interval": f"[{lower:.2f}, {upper:.2f})",
                "sample_count": cnt,
                "mean_predicted_uncertainty": round(mean_pred_unc, 3),
                "observed_mae": round(obs_mae, 3),
                "observed_rmse": round(obs_rmse, 3),
            })

        # Correlation between uncertainty and absolute error
        correlation = self._calculate_correlation(
            [o["uncertainty"] for o in observations],
            [o["abs_error"] for o in observations],
        )

        return {
            "per_dimension_uncertainty": per_dim_unc_stats,
            "calibration_buckets": calibration_buckets,
            "uncertainty_error_correlation": round(correlation, 3),
            "correlation_interpretation": (
                "Positive (Higher uncertainty aligns with higher estimation error)"
                if correlation > 0.1 else
                ("Weak / Neutral" if correlation >= -0.1 else "Negative / Misaligned")
            ),
        }

    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        if len(x) < 3 or len(y) < 3:
            return 0.0
        try:
            mean_x = statistics.mean(x)
            mean_y = statistics.mean(y)
            num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
            den = math.sqrt(sum((xi - mean_x) ** 2 for xi, yi in zip(x, y)) * sum((yi - mean_y) ** 2 for xi, yi in zip(x, y)))
            return num / den if den != 0 else 0.0
        except Exception:
            return 0.0

    # -------------------------------------------------------------------------
    # 4.7. Estimation Quality vs. Number of Questions
    # -------------------------------------------------------------------------
    def _compute_length_vs_quality(self, valid_items: List[Any]) -> Dict[str, Any]:
        """
        Groups completed simulations into question count intervals to inspect accuracy scaling.
        """
        bucket_results = []
        for lower, upper in self.settings.question_count_buckets:
            matching = [
                p for p in valid_items
                if lower <= int(self._get_field(p, "answered_question_count", 0)) <= upper
            ]
            cnt = len(matching)
            if cnt == 0:
                bucket_results.append({
                    "question_range": f"{lower}-{upper}",
                    "session_count": 0,
                    "mae": 0.0,
                    "rmse": 0.0,
                    "bias": 0.0,
                    "mean_uncertainty": 0.0,
                })
                continue

            abs_errs = []
            sq_errs = []
            signed_errs = []
            uncs = []

            for p in matching:
                gt = self._get_field(p, "ground_truth_ability", {}) or {}
                est = self._get_field(p, "estimated_ability", {}) or {}
                unc = self._get_field(p, "uncertainty_vector", {}) or {}

                for d in CANONICAL_DIMENSIONS:
                    if d in gt and d in est:
                        err = float(est[d]) - float(gt[d])
                        signed_errs.append(err)
                        abs_errs.append(abs(err))
                        sq_errs.append(err ** 2)
                    if d in unc:
                        uncs.append(float(unc[d]))

            mae = statistics.mean(abs_errs) if abs_errs else 0.0
            rmse = math.sqrt(statistics.mean(sq_errs)) if sq_errs else 0.0
            bias = statistics.mean(signed_errs) if signed_errs else 0.0
            mean_unc = statistics.mean(uncs) if uncs else 1.0

            bucket_results.append({
                "question_range": f"{lower}-{upper}",
                "session_count": cnt,
                "mae": round(mae, 3),
                "rmse": round(rmse, 3),
                "bias": round(bias, 4),
                "mean_uncertainty": round(mean_unc, 3),
            })

        return {"question_count_intervals": bucket_results}

    # -------------------------------------------------------------------------
    # 4.8. Archetype-Based Estimation Analysis
    # -------------------------------------------------------------------------
    def _compute_archetype_breakdown(self, valid_items: List[Any]) -> Dict[str, Any]:
        """
        Breaks down estimation errors across synthetic user archetypes.
        """
        by_archetype: Dict[str, List[Any]] = defaultdict(list)
        for p in valid_items:
            arch = self._get_field(p, "archetype", "UNKNOWN")
            by_archetype[arch].append(p)

        results = {}
        for arch, arch_items in by_archetype.items():
            abs_errs = []
            sq_errs = []
            signed_errs = []
            uncs = []

            for p in arch_items:
                gt = self._get_field(p, "ground_truth_ability", {}) or {}
                est = self._get_field(p, "estimated_ability", {}) or {}
                unc = self._get_field(p, "uncertainty_vector", {}) or {}

                for d in CANONICAL_DIMENSIONS:
                    if d in gt and d in est:
                        err = float(est[d]) - float(gt[d])
                        signed_errs.append(err)
                        abs_errs.append(abs(err))
                        sq_errs.append(err ** 2)
                    if d in unc:
                        uncs.append(float(unc[d]))

            mae = statistics.mean(abs_errs) if abs_errs else 0.0
            rmse = math.sqrt(statistics.mean(sq_errs)) if sq_errs else 0.0
            bias = statistics.mean(signed_errs) if signed_errs else 0.0
            mean_unc = statistics.mean(uncs) if uncs else 1.0

            results[arch] = {
                "archetype": arch,
                "session_count": len(arch_items),
                "mae": round(mae, 3),
                "rmse": round(rmse, 3),
                "bias": round(bias, 4),
                "mean_uncertainty": round(mean_unc, 3),
            }

        return results

    # -------------------------------------------------------------------------
    # Anomalies & Limitations
    # -------------------------------------------------------------------------
    def _detect_anomalies_and_limitations(
        self,
        dim_metrics: Dict[str, Any],
        unc_metrics: Dict[str, Any],
        n_valid: int,
    ) -> (List[Dict[str, str]], List[str]):
        anomalies = []
        limitations = [
            "Simulation observations reflect synthetic 3PL response models and do not guarantee real-world psychometric validity.",
            "Subgroup sample sizes under 10 may produce noisy RMSE and calibration estimates.",
            "Engine ability scale is bounded in [-3.0, +3.0]; extreme ground-truth abilities outside this range experience boundary truncation.",
        ]

        # Check for high dimensional bias
        for d, dm in dim_metrics.get("per_dimension", {}).items():
            bias = abs(dm.get("bias", 0.0))
            if bias > 0.40:
                anomalies.append({
                    "severity": "HIGH",
                    "type": "DIMENSIONAL_BIAS",
                    "message": f"Dimension '{d}' exhibits substantial directional bias of {dm.get('bias', 0.0):.3f}.",
                })

        # Check sample size
        if n_valid < self.settings.min_subgroup_sample_size:
            anomalies.append({
                "severity": "MEDIUM",
                "type": "INSUFFICIENT_SAMPLE_SIZE",
                "message": f"Total evaluated sample size ({n_valid}) is below the recommended minimum ({self.settings.min_subgroup_sample_size}).",
            })

        return anomalies, limitations
