import math
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.dimensions import DIMENSION_REGISTRY
from app.domain.enums import SessionStatus
from app.infrastructure.persistence.models.report import AssessmentReportModel
from app.infrastructure.persistence.repositories import (
    AssessmentSessionRepository,
    AssessmentProfileRepository,
    AbilitySnapshotRepository,
    AssessmentReportRepository,
)
from app.application.dto import (
    AssessmentReportDTO,
    DimensionOverviewDTO,
    StrengthOrGrowthItemDTO,
    ConfidenceAuditDTO,
)
from app.application.exceptions import (
    SessionNotFoundError,
    SessionAccessForbiddenError,
    SessionNotCompletedError,
    SnapshotNotFoundError,
)


class AssessmentReportService:
    """
    Application Service implementing TASK-031: Assessment Report.
    Generates deterministic, family-friendly, and scientifically grounded
    diagnostic reports based strictly on the final AbilitySnapshot of a completed session.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        session_repo: Optional[AssessmentSessionRepository] = None,
        profile_repo: Optional[AssessmentProfileRepository] = None,
        snapshot_repo: Optional[AbilitySnapshotRepository] = None,
        report_repo: Optional[AssessmentReportRepository] = None,
    ):
        self.db = db_session
        self.session_repo = session_repo or AssessmentSessionRepository(db_session)
        self.profile_repo = profile_repo or AssessmentProfileRepository(db_session)
        self.snapshot_repo = snapshot_repo or AbilitySnapshotRepository(db_session)
        self.report_repo = report_repo or AssessmentReportRepository(db_session)

    async def get_or_generate_report(self, session_id: str, student_id: str) -> AssessmentReportDTO:
        """
        Retrieves an existing final report, or generates and persists a new report
        anchored strictly to the session's final AbilitySnapshot.

        Args:
            session_id: Unique session identifier.
            student_id: Authenticated student ID (ownership verification).

        Returns:
            AssessmentReportDTO structured report payload.

        Raises:
            SessionNotFoundError: If session does not exist.
            SessionAccessForbiddenError: If session belongs to another student.
            SessionNotCompletedError: If session is still IN_PROGRESS or was ABANDONED.
            SnapshotNotFoundError: If no valid ability snapshot exists for the session.
        """
        # 1. Verify session existence and ownership
        session = await self.session_repo.get_session_with_responses(session_id)
        if not session:
            raise SessionNotFoundError(session_id)

        if session.student_id != student_id:
            raise SessionAccessForbiddenError(session_id, student_id)

        # 2. Enforce session completion
        if session.status != SessionStatus.COMPLETED.value:
            raise SessionNotCompletedError(session_id, session.status)

        # 3. Check if a report was already generated (Deterministic Idempotency)
        existing_report = await self.report_repo.get_by_session_id(session_id)
        if existing_report:
            return AssessmentReportDTO(**existing_report.report_payload)

        # 4. Fetch the final AbilitySnapshot
        snapshot = await self.snapshot_repo.get_latest_by_session_id(session_id)
        if not snapshot:
            # If snapshot not yet created in snapshot table, build a baseline snapshot record
            meta = session.context_metadata or {}
            raw_ability = meta.get("ability_state", {})
            if not raw_ability:
                raise SnapshotNotFoundError(session_id)

            from app.infrastructure.persistence.models.snapshot import AbilitySnapshotModel
            snapshot = AbilitySnapshotModel(
                id=str(uuid.uuid4()),
                student_id=session.student_id,
                session_id=session.id,
                snapshot_sequence=len(session.responses),
                ability_scores=raw_ability.get("dimension_scores", {}),
                uncertainty_scores=raw_ability.get("uncertainty", {}),
                dimension_coverage=raw_ability.get("dimension_coverage", {}),
                answered_question_count=len(session.responses),
                algorithm_version=session.algorithm_version,
                checkpoint_type="SESSION_COMPLETED",
            )
            await self.snapshot_repo.create_snapshot(snapshot)

        # 5. Calculate Elapsed Duration
        now_utc = datetime.now(timezone.utc)
        completed_at = session.completed_at or now_utc
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)

        started_at = session.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        total_duration = max(0.0, (completed_at - started_at).total_seconds())

        # 6. Build Ability Overview across all 5 cognitive dimensions
        overview_list: List[DimensionOverviewDTO] = []
        scores = snapshot.ability_scores
        uncertainties = snapshot.uncertainty_scores
        coverages = snapshot.dimension_coverage

        for dim_code, dim_info in DIMENSION_REGISTRY.items():
            score = round(float(scores.get(dim_code, 0.0)), 2)
            unc = round(float(uncertainties.get(dim_code, 1.0)), 2)
            cov = int(coverages.get(dim_code, 0))

            # Qualitative level mapping
            if score >= 1.5:
                lvl = "EXEMPLARY"
            elif score >= 0.5:
                lvl = "ADVANCED"
            elif score >= -0.5:
                lvl = "COMPETENT"
            elif score >= -1.5:
                lvl = "DEVELOPING"
            else:
                lvl = "BEGINNER"

            dim_name = getattr(dim_info, "display_name_fa", getattr(dim_info, "name_fa", dim_code))
            ci_low = round(max(-3.0, score - 1.96 * unc), 2)
            ci_high = round(min(3.0, score + 1.96 * unc), 2)
            # Standard normal CDF approximation for percentile rank (1..99)
            cdf = 0.5 * (1.0 + math.erf(score / math.sqrt(2.0)))
            percentile = max(1, min(99, int(round(cdf * 100))))

            overview_list.append(DimensionOverviewDTO(
                dimension_code=dim_code,
                dimension_name=dim_name,
                ability_score=score,
                uncertainty=unc,
                confidence_interval_low=ci_low,
                confidence_interval_high=ci_high,
                percentile_rank=percentile,
                evidence_count=cov,
                interpretation_level=lvl,
            ))

        # 7. Identify Strengths and Growth Areas (factoring in Uncertainty and Evidence)
        # Strengths: dimensions with positive scores and adequate evidence
        strengths: List[StrengthOrGrowthItemDTO] = []
        growth_areas: List[StrengthOrGrowthItemDTO] = []

        sorted_by_score = sorted(overview_list, key=lambda x: x.ability_score, reverse=True)

        for item in sorted_by_score:
            ev_level = "SUFFICIENT" if item.evidence_count >= 3 else ("MODERATE" if item.evidence_count >= 1 else "PRELIMINARY")
            if item.ability_score >= 0.0:
                strengths.append(StrengthOrGrowthItemDTO(
                    dimension_code=item.dimension_code,
                    dimension_name=item.dimension_name,
                    ability_score=item.ability_score,
                    uncertainty=item.uncertainty,
                    title=f"توانمندی نسبی در {item.dimension_name}",
                    description=f"عملکرد منسجم و پاسخگویی بهینه در الگوهای مربوط به {item.dimension_name}.",
                    evidence_level=ev_level,
                ))
            else:
                growth_areas.append(StrengthOrGrowthItemDTO(
                    dimension_code=item.dimension_code,
                    dimension_name=item.dimension_name,
                    ability_score=item.ability_score,
                    uncertainty=item.uncertainty,
                    title=f"فرصت رشد و تمرین در {item.dimension_name}",
                    description=f"با تمرین و مواجهه با مسائل متنوع، این حوزه پتانسیل بالایی برای شکوفایی بیشتر دارد.",
                    evidence_level=ev_level,
                ))

        # Guarantee non-empty constructive lists
        if not strengths and sorted_by_score:
            top = sorted_by_score[0]
            strengths.append(StrengthOrGrowthItemDTO(
                dimension_code=top.dimension_code,
                dimension_name=top.dimension_name,
                ability_score=top.ability_score,
                uncertainty=top.uncertainty,
                title=f"حوزه تمایل اولیه در {top.dimension_name}",
                description="پاسخ‌های ثبت‌شده تمایل اولیه در این بُعد را نشان می‌دهند.",
                evidence_level="MODERATE",
            ))

        if not growth_areas and sorted_by_score:
            bottom = sorted_by_score[-1]
            growth_areas.append(StrengthOrGrowthItemDTO(
                dimension_code=bottom.dimension_code,
                dimension_name=bottom.dimension_name,
                ability_score=bottom.ability_score,
                uncertainty=bottom.uncertainty,
                title=f"پیشنهاد تمرین تکمیلی در {bottom.dimension_name}",
                description="مواجهه با چالش‌های بیشتر در این بُعد مهارت‌های شناختی را تقویت می‌کند.",
                evidence_level="MODERATE",
            ))

        # 8. Confidence Audit & Diagnostic Limitations
        avg_unc = round(sum(item.uncertainty for item in overview_list) / max(1, len(overview_list)), 2)
        if avg_unc <= 0.45:
            conf_level = "HIGH"
            cov_summary = "داده‌ها و شواهد کافی برای تحلیل پایدار و معتبر ثبت شده است."
        elif avg_unc <= 0.75:
            conf_level = "MODERATE"
            cov_summary = "شواهد ارزیابی در سطح متوسط قرار دارند و روند کلی قابل اتکا است."
        else:
            conf_level = "PRELIMINARY"
            cov_summary = "شواهد اولیه هستند؛ برای سنجش تفصیلی آزمون‌های تکمیلی پیشنهاد می‌شود."

        conf_audit = ConfidenceAuditDTO(
            overall_confidence=conf_level,
            average_uncertainty=avg_unc,
            coverage_summary=cov_summary,
            limitations_notice=(
                "این گزارش صرفاً یک تحلیل آموزشی و تکوینی بر مبنای آزمون تطبیقی کامپیوتری (CAT) است. "
                "نتایج فوق نباید به عنوان برچسب قطعی توانایی یا پیش‌بینی سرنوشت تحصیلی کودک در نظر گرفته شوند."
            ),
        )

        # 9. General Summary & Analytical Insights (Inspired by Clinical Report Spec)
        top_dims = "، ".join([s.dimension_name for s in strengths[:2]])
        growth_dims = "، ".join([g.dimension_name for g in growth_areas[:2]])

        session_meta = session.context_metadata or {}
        rapid_count = int((session_meta.get("ability_state") or {}).get("metadata", {}).get("rapid_guess_count", 0))

        anomaly_flags: List[str] = []
        quality_reasons: List[str] = []
        if snapshot.answered_question_count < 5:
            quality_status = "INSUFFICIENT"
            quality_reasons.append("تعداد گویه‌های پاسخ‌داده‌شده برای استنتاج پایدار کافی نیست.")
        elif rapid_count >= 2 or avg_unc > 0.75:
            quality_status = "CAUTION"
            if rapid_count >= 2:
                quality_reasons.append(f"ثبت {rapid_count} پاسخ بسیار سریع (کمتر از ۱.۵ ثانیه) که نیازمند تفسیر با احتیاط است.")
            if avg_unc > 0.75:
                quality_reasons.append("پوشش شواهد در برخی ابعاد هنوز در سطح مقدماتی است.")
        else:
            quality_status = "INTERPRETABLE"
            quality_reasons.append("نشست با پایداری مناسب، پوشش کافی گویه‌ها و کیفیت فنی سالم تکمیل شد.")

        if rapid_count > 0:
            anomaly_flags.append(f"تعداد {rapid_count} پاسخ شتاب‌زده (زیر ۱.۵ ثانیه) شناسایی و برای حفظ دقت در برآورد نهایی خنثی شد.")

        summary_text = (
            f"در این نشست ارزیابی انطباقی، مجموعاً {snapshot.answered_question_count} گویه در مدت "
            f"{int(round(total_duration))} ثانیه بررسی شد. برآورد چندبُعدی نشان می‌دهد داوطلب در حوزه‌های "
            f"{top_dims} از انسجام تحلیلی و دقت استدلالی بالاتری برخوردار است. در مقابل، حوزه‌های "
            f"{growth_dims} بیشترین ظرفیت را برای رشد و تقویت هدفمند از طریق تمرین‌های ساختاریافته دارند. "
            f"تفسیر نتایج بر پایه عملکرد مشاهده‌شده در همین نشست و با در نظر گرفتن بازه اطمینان آماری ارائه شده است."
        )

        observed_highlights: List[str] = [
            f"بالاترین انسجام عملکردی در بُعد «{sorted_by_score[0].dimension_name}» با برآورد تتا {sorted_by_score[0].ability_score} (صدک {sorted_by_score[0].percentile_rank}٪) ثبت شد."
            if sorted_by_score else "داده کافی برای استخراج اوج عملکرد ثبت نشد.",
            f"بیشترین فضای رشد در بُعد «{sorted_by_score[-1].dimension_name}» با پوشش {sorted_by_score[-1].evidence_count} گویه مشاهده شد."
            if sorted_by_score else "داده کافی برای تحلیل شکاف رشد ثبت نشد.",
            f"میانگین عدم قطعیت اندازه‌گیری برابر با {avg_unc} و وضعیت کلی کفایت نشست «{quality_status}» ارزیابی شده است.",
        ]

        next_experiments: List[str] = [
            f"طراحی ۲ تا ۳ تمرین چالشی گام‌به‌گام در حوزه «{top_dims}» برای تعمیق مهارت‌های تحلیلی.",
            f"شروع تمرین‌های ملایم و بدون فشار زمانی در حوزه «{growth_dims}» جهت افزایش اعتمادبه‌نفس شناختی.",
            "گفتگو با داوطلب دربارهٔ راهبرد ذهنی او هنگام حل مسائل دشوار و بررسی علاقهٔ واقعی وی پیش از انتخاب مسیر آموزشی.",
        ]

        static_recommendations: List[str] = [
            f"تقویت مستمر نقاط قوت در {top_dims} از طریق مسائل مسئله‌محور و بازی‌های فکری منطقی.",
            f"تمرکز تدریجی بر فرصت‌های رشد در {growth_dims} با تأکید بر ذهنیت رشد (Growth Mindset) و پرهیز از مقایسه با هم‌سالان.",
            "بازبینی این کارنامه در جلسه مشاوره تخصصی به همراه روان‌شناس یا مشاور آموزشی پیش از هر تصمیم تحصیلی.",
        ]

        # 10. Assemble AssessmentReportDTO
        report_id = str(uuid.uuid4())
        report_dto = AssessmentReportDTO(
            report_id=report_id,
            user_id=session.student_id,
            assessment_session_id=session.id,
            assessment_profile_id=session.profile_id,
            completed_at=completed_at,
            total_answered_questions=snapshot.answered_question_count,
            total_duration_seconds=round(total_duration, 1),
            algorithm_version=session.algorithm_version,
            report_version="2.0.0-analytical",
            report_mode="RULE_BASED_ANALYTICAL",
            clinician_review_status="PENDING_REVIEW",
            quality_status=quality_status,
            quality_reasons=quality_reasons,
            ability_overview=overview_list,
            strengths=strengths,
            growth_areas=growth_areas,
            confidence_audit=conf_audit,
            general_summary=summary_text,
            observed_highlights=observed_highlights,
            next_experiments=next_experiments,
            recommendations=static_recommendations,
            anomaly_flags=anomaly_flags,
            generated_at=now_utc,
        )

        # 11. Persist Report Entity (with concurrent idempotency protection)
        report_model = AssessmentReportModel(
            id=report_id,
            session_id=session.id,
            student_id=session.student_id,
            snapshot_id=snapshot.id,
            report_version="1.0.0",
            algorithm_version=session.algorithm_version,
            report_payload=report_dto.model_dump(mode="json"),
            generated_at=now_utc,
        )
        try:
            await self.report_repo.create_report(report_model)
            await self.db.flush()
        except IntegrityError:
            # Concurrent report generation: rollback pending error and retrieve existing report
            await self.db.rollback()
            existing = await self.report_repo.get_by_session_id(session_id)
            if existing:
                return AssessmentReportDTO.model_validate(existing.report_payload)

        return report_dto
