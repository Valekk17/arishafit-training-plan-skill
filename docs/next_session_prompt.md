# Промт для следующей сессии — улучшение SKILL

Скопируй всё что ниже черты в новый чат Clause.

---

# Контекст

Репо: `C:/Users/morod/fitness-andrey`
GitHub: https://github.com/Valekk17/arishafit-training-plan-skill
Последний коммит: `0e76013` (главный SKILL.md — `19b211c` после оптимизации на 372 строки)

План для Андрея (v7) отправлен клиенту 2026-04-22, заморожен (tag `andrey-v7-delivered`). Не трогать.

Цель сессии: **дорабатывать SKILL.md и инфраструктуру skill'а в лучшую сторону, без привязки к конкретному плану клиента**.

Сначала прочитай:
- `training-skill/SKILL.md` — текущая версия skill (372 строки)
- `NEXT.md` — контекст проекта, hard rules
- `C:\Users\morod\.claude\projects\C--Users-morod\memory\feedback_fitness_plan_rules.md` — правила usvoennye на прошлых планах

---

# Что можем делать (в порядке приоритета)

## 🔴 Priority 1 — расширить injury profiles

Сейчас в `SKILL.md` Part 2 детально разобран только L4-L5 lumbar hernia. Это основной use case, но skill должен покрывать и другие профили без обращения к внешним источникам.

Добавить FORBIDDEN / CAUTION / SAFE + substitution table для:
- **Cervical hernia (шейный отдел, C5-C6 / C6-C7)** — избегать overhead work, тяга за голову, резкие ротации головы
- **Shoulder impingement / rotator cuff** — избегать upright row, жим за голову, dips глубокий; безопасно: нейтральный хват, face pulls, scap stability
- **Knee arthritis / менискус** — избегать глубокого приседа, прыжки, полный присед; безопасно: leg extension на ограниченной амплитуде, угол 90°, gentle cycling
- **Tennis elbow / golfers elbow** — избегать heavy grip, wrist curls; безопасно: нейтральный хват, lat pulldown с straps, reduce grip fatigue
- **Diastasis recti** (постpartum women) — избегать crunch, plank forward loading; безопасно: Dead Bug modified, supported rows, hip thrust
- **Hypertension / cardiovascular** — избегать isometric holds, Valsalva maneuver, heavy bench; безопасно: circuit training, Zone 2 cardio primary
- **Elderly (65+)** — акцент на balance + falls prevention, supported machines, lower intensity
- **Pregnancy (по триместрам)** — trimester-specific rules, supine position limits, diastasis prevention

Для каждого профиля указать:
1. Основной биомеханический риск
2. 5-10 запрещённых упражнений / паттернов (конкретно)
3. 5-10 каутивных (с обязательным warning)
4. 10-15 безопасных (база для построения плана)
5. Substitution table для стандартных compound движений

## 🟠 Priority 2 — goal-specific scaffolds

Сейчас SKILL.md разбирает split selection и volume/intensity abstractly. Добавить starting scaffolds для 6-7 goal archetypes:

- **Hypertrophy** — классика PPL, 12-15 sets/muscle/week, 8-12 reps, progression +1 rep/week
- **Strength** — upper/lower splits, 5×5 / 3×3 базы, 85-95% 1RM
- **Weight loss / recomposition** — суперсеты антагонистами, metabolic circuits, Zone 2 cardio day
- **Endurance** — hybrid split с Zone 3/4 work, lower body focus
- **Rehab / post-injury** — body-part split с progression из restoration, single-joint → compound
- **General fitness / maintenance** — full body ×2-3/неделя, movement quality focus
- **Powerbuilding** — strength priority + hypertrophy accessories

Scaffold = стартовая структура (split + volume + periodization) которую я как Opus адаптирую под конкретного клиента. Не жёсткий template, а отправная точка.

## 🟡 Priority 3 — translation quality (DB hygiene)

Мы заметили во время v7 что много упражнений в БД имеют `nameRu: None` или странные транслитерации.

Задачи:
1. SQL-query: список всех exerciseId где `name_ru IS NULL` или `name_ru = name_en` (транслитерация вместо перевода) или длина `< 5 chars`
2. Группировать по `movement_patterns` и `target_muscles`
3. Batch через Opus — перевести по 30-50 упражнений за раз, профессиональный фитнес-русский (НЕ дословный перевод, а термин как говорят в зале)
4. Validate: спот-чек после каждого батча
5. UPDATE в Postgres + sync в JSON

Итоговая метрика: 100% упражнений в БД имеют качественный nameRu.

## 🟢 Priority 4 — client intake schema

Стандартизировать формат анкеты клиента. Сейчас client data вшит в plan JSON. Вынести в отдельный контракт:

```json
// templates/client_intake_schema.json
{
  "personal": { "name", "age", "gender", "height_cm", "weight_kg" },
  "goals": { "primary", "timeline", "target_metric" },
  "experience": { "years_training", "level", "past_programs" },
  "injuries": [
    { "code", "severity", "onset_date", "surgery_history", "current_pain_level", "doctor_restrictions" }
  ],
  "constraints": {
    "training_days_per_week", "session_max_duration_min",
    "equipment_available", "gym_location"
  },
  "lifestyle": { "sleep_hours_avg", "stress_level", "dietary_preferences", "medications" },
  "preferences": { "disliked_exercises", "favorite_movements", "music_preferences" }
}
```

Документировать в SKILL.md как первый phase Generation Process (Phase 0: Pre-flight).

## 🔵 Priority 5 — nutrition skill (отдельный skill)

Сейчас `training-skill/` — только тренировки. Пришло время параллельного `nutrition-skill/` для планов питания.

Цели:
- Учитывать synergy с тренировочным планом (training days = carb-loaded, rest days = protein-focus)
- КБЖУ calculator с учётом goal и activity
- 28-day meal plan structure
- Shopping list per week
- Recipe library с ссылками на source

Отдельный skill — не часть SKILL.md training. Создать `nutrition-skill/SKILL.md`.

## ⚪ Priority 6 — glossary expansion

Template имеет встроенный глоссарий (8 терминов в expandable cards). Расширить:

- Периодизация (линейная, волновая, DUP)
- MEV / MAV / MRV
- Метаболический стресс vs мышечное напряжение
- Cardiac drift
- HIIT vs MISS vs LISS
- Time-under-tension (TUT)
- Eccentric emphasis
- Pre-exhaustion / post-exhaustion
- Rest-pause training
- Drop sets, myo-reps

Это не часть SKILL.md, а data в `training-skill/assets/info_boxes.json` или glossary items в template.

## 🟣 Priority 7 — infrastructure (optional, если останется время)

- Removed deprecated files (старые version рендеров, legacy scripts)
- Dockerfile для GitHub Actions (auto-render при push в main)
- FastAPI backend — production deploy на Railway/Fly.io
- Authenticated links для клиентов (не public GitHub Pages, а protected URL)
- Export to PDF (WeasyPrint или Puppeteer)

---

# Как выбрать приоритет

Рекомендую начать с **Priority 1 (injury profiles)** — наиболее value для skill, расширяет сценарии применения без новой инфраструктуры.

После — **Priority 2 (goal scaffolds)** как estетический вклад в процесс генерации.

Priority 3-7 можно делать по мере надобности, не обязательно все за одну сессию.

# Hard rules (напоминание)

1. Планы генерирует ТОЛЬКО Opus. Скрипты — транспорт.
2. Postgres = источник правды для exercises + info_boxes.
3. UNIT rule: exerciseId ↔ nameRu ↔ gifUrl ↔ tips ↔ warning.
4. Safety check — работа Opus, не keyword-скрипта.
5. Static reference pose (hasAnimation: false) → план может override имя.

# Dev окружение

```bash
cd C:/Users/morod/fitness-andrey
docker compose up -d postgres                    # обычно уже запущен
# SQL запросы: python -c "from sqlalchemy..." или psql напрямую
# Plan render: python training-skill/scripts/fill_template.py --plan ... --output ...
# Migrate: python scripts/migrate_json_to_db.py --wipe --plan <file>
```

---

# Что НЕ делать

- Не перегенерировать plan_andrey_v7.json / docs/andrey.html (tag `andrey-v7-delivered` — frozen)
- Не создавать audit_plan.py или аналогичные safety-check скрипты (keyword-match ненадёжен, safety = работа Opus)
- Не тратить контекст на hardcoded exercise pool lists — вместо них SQL query по DB
- Не добавлять template implementation detail в SKILL.md (localStorage, JS, CSS — render concerns)
