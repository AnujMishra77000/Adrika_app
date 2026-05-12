from __future__ import annotations

from app.db.models.enums import AssessmentType

_TYPE_ALIASES: dict[str, AssessmentType] = {
    "practice_test": AssessmentType.DAILY_PRACTICE,
    "practice": AssessmentType.DAILY_PRACTICE,
    "online_test": AssessmentType.SCHEDULED,
    "online": AssessmentType.SCHEDULED,
    "daily_practice": AssessmentType.DAILY_PRACTICE,
    "subject_practice": AssessmentType.SUBJECT_PRACTICE,
    "scheduled": AssessmentType.SCHEDULED,
}


def normalize_assessment_type(value: str | AssessmentType | None) -> AssessmentType | None:
    if value is None:
        return None

    if isinstance(value, AssessmentType):
        return value

    normalized = value.strip().lower()
    if not normalized:
        return None

    return _TYPE_ALIASES.get(normalized)


def allowed_assessment_type_inputs() -> list[str]:
    return sorted(_TYPE_ALIASES.keys())


def require_assessment_type(
    value: str | AssessmentType | None,
    *,
    field_name: str = "assessment_type",
) -> AssessmentType:
    normalized = normalize_assessment_type(value)
    if normalized is None:
        raise ValueError(
            f"Unsupported {field_name}. Allowed values: {', '.join(allowed_assessment_type_inputs())}"
        )
    return normalized


def assessment_mode(value: str | AssessmentType | None) -> str:
    normalized = normalize_assessment_type(value)
    if normalized in {AssessmentType.DAILY_PRACTICE, AssessmentType.SUBJECT_PRACTICE}:
        return "practice_test"
    return "online_test"
