"""
Валидатор ArishaFit client intake JSON.

Использование:
  python scripts/validate_client_intake.py training-skill/templates/example_andrey_intake.json

Exit codes:
  0 — валидный
  1 — ошибки валидации / файл не найден
  2 — jsonschema пакет не установлен

Зависимость: jsonschema. Устанавливается через `pip install jsonschema`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO / "training-skill" / "templates" / "client_intake_schema.validation.json"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python validate_client_intake.py <intake.json>")
        return 1

    intake_path = Path(sys.argv[1])
    if not intake_path.exists():
        print(f"[FAIL] Intake file not found: {intake_path}")
        return 1

    if not SCHEMA_PATH.exists():
        print(f"[FAIL] Schema not found: {SCHEMA_PATH}")
        return 1

    try:
        import jsonschema
    except ImportError:
        print("[FAIL] jsonschema package not installed. Run: pip install jsonschema")
        return 2

    intake = json.loads(intake_path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    # Используем Draft202012Validator для максимально строгой валидации
    validator_cls = jsonschema.Draft202012Validator
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)

    errors = sorted(validator.iter_errors(intake), key=lambda e: e.path)

    if not errors:
        print(f"[OK] {intake_path.name} passes schema validation "
              f"(schema v{intake.get('_meta', {}).get('schema_version', '?')})")
        # Sanity-checks сверх JSON Schema:
        warnings = _sanity_checks(intake)
        if warnings:
            print("\n[WARN] Non-blocking sanity-check warnings:")
            for w in warnings:
                print(f"  - {w}")
        return 0

    print(f"[FAIL] {len(errors)} validation errors in {intake_path.name}:")
    for i, err in enumerate(errors, 1):
        path = ".".join(str(p) for p in err.absolute_path) or "<root>"
        print(f"  {i}. at {path}: {err.message}")
    return 1


def _sanity_checks(intake: dict) -> list[str]:
    """Дополнительные проверки бизнес-логики поверх schema."""
    warnings: list[str] = []

    consent = intake.get("consent", {})
    if not consent.get("medical_disclaimer_accepted"):
        warnings.append("medical_disclaimer_accepted=false — план не может быть сгенерирован без медицинского disclaimer")
    if not consent.get("data_processing_accepted"):
        warnings.append("data_processing_accepted=false — нарушение 152-ФЗ, не генерировать план")

    # Injury checks
    for i, inj in enumerate(intake.get("injuries", [])):
        if inj.get("severity") == "post_op":
            if not inj.get("medical_clearance_for_training"):
                warnings.append(
                    f"injuries[{i}] {inj.get('code')} severity=post_op и medical_clearance_for_training != true — "
                    "требуется явная справка врача до старта тренировок")
        if inj.get("current_pain_level_vas") is not None and inj["current_pain_level_vas"] >= 7:
            warnings.append(
                f"injuries[{i}] {inj.get('code')} VAS={inj['current_pain_level_vas']} (≥7) — "
                "высокий болевой уровень, отложить тренировки до снижения")

    # Pregnancy coherence
    injury_codes = {inj.get("code") for inj in intake.get("injuries", [])}
    pregnancy_codes = {"pregnancy_t1", "pregnancy_t2", "pregnancy_t3"}
    if len(injury_codes & pregnancy_codes) > 1:
        warnings.append("Более одного pregnancy-триместра отмечено — выбрать актуальный (t1/t2/t3)")

    # Training days vs session duration sanity
    c = intake.get("constraints", {})
    days = c.get("training_days_per_week")
    dur = c.get("session_max_duration_min")
    if days and dur and days * dur > 600:
        warnings.append(f"Total weekly training load = {days}×{dur}min = {days*dur} min/week — "
                        "перепроверить: норма 150-360 min/week")

    # Age vs elderly profile
    age = intake.get("personal", {}).get("age")
    if age and age >= 65 and "elderly_65plus" not in injury_codes:
        warnings.append(f"Клиенту {age} лет, но injuries не содержит 'elderly_65plus' — "
                        "рекомендуется явно отметить для применения Part 2.8 профиля")

    return warnings


if __name__ == "__main__":
    sys.exit(main())
