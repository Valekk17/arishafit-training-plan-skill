# ArishaFit — Training Plan Skill

Reusable engine для генерации персональных тренировочных планов. Хранит каталог упражнений, планы клиентов и историю тренировок в PostgreSQL. Рендерит HTML-документ с встроенными MP4-анимациями для клиента.

## Архитектура

```
┌─────────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   PostgreSQL 16     │     │  exercisedb_data │     │    Renderer      │
│                     │     │                  │     │                  │
│  exercises (1500)   │◄────│ mp4_paused/*.mp4 │     │  fill_template   │
│  info_boxes (29)    │     │ gifs_hd/*.webp   │────►│       ↓          │
│  clients (N)        │     └──────────────────┘     │   HTML plan      │
│  plans (N)          │                              │  (клиенту)       │
│  weeks / days       │                              └──────────────────┘
│  exercises in plan  │                                        ▲
│  alternatives       │                                        │
│  warmup_variants    │     ┌──────────────────┐              │
│  cooldown_variants  │     │ JSON (export)    │──────────────┘
│  session_logs       │────►│ plan_XX.json     │
│  exercise_logs      │     └──────────────────┘
│  1rm_estimates      │
└─────────────────────┘
```

**БД — источник правды.** JSON-файл плана — промежуточный формат для рендера, генерируется экспортом из БД.

## Быстрый старт

### 1. Зависимости

```bash
pip install -r requirements.txt
# Плюс должен быть установлен Docker Desktop и ffmpeg
```

### 2. Поднять PostgreSQL

```bash
docker compose up -d
# Проверка: docker exec arishafit-postgres pg_isready -U arishafit
```

### 3. Настроить окружение

```bash
cp .env.example .env
# .env содержит DATABASE_URL по умолчанию на локальный Postgres
```

### 4. Создать таблицы и залить данные

```bash
python scripts/migrate_json_to_db.py --create-tables --wipe
# Заливает 1500 упражнений, 29 справок, план Андрея (если JSON на месте)
```

### 5. Экспорт плана из БД + рендер в HTML

```bash
python scripts/export_plan_from_db.py --client "Андрей" --output training-skill/output/plan_andrey_v5.json
python training-skill/scripts/fill_template.py \
  --plan training-skill/output/plan_andrey_v5.json \
  --output training-skill/output/andrey_v5_rendered.html
```

## Схема БД

| Таблица | Назначение |
|---|---|
| `exercises` | Каталог 1500 упражнений из ExerciseDB (read-only) |
| `info_boxes` | Библиотека 29 научных справок |
| `clients` | Клиенты с анкетой, целями, травмами |
| `plans` | Мезоциклы (4-недельные блоки), привязаны к клиенту |
| `weeks`, `days` | Недели и дни в плане |
| `plan_exercises` | Упражнения в дне (ссылка на `exercises`) |
| `plan_alternatives` | Альтернативы к упражнениям |
| `plan_warmup_variants` / `plan_cooldown_variants` | Разминки/заминки (JSONB blocks) |
| `session_logs` | Факты выполнения тренировок клиентом |
| `exercise_logs` | Фактические веса/повторения в каждом подходе |
| `one_rm_estimates` | Расчётные 1RM (для автопрогрессии) |

## Структура репо

```
.
├── docker-compose.yml          # PostgreSQL 16
├── .env.example                # DATABASE_URL
├── requirements.txt            # Python deps (sqlalchemy, psycopg2, alembic, ...)
│
├── db/
│   ├── models.py               # SQLAlchemy ORM модели
│   ├── session.py              # engine + SessionLocal
│   └── __init__.py
│
├── scripts/
│   ├── migrate_json_to_db.py   # JSON → Postgres (первоначальная заливка)
│   └── export_plan_from_db.py  # Postgres → JSON (для рендера)
│
├── exercisedb_data/
│   ├── exercise_db_final.json  # Каталог (источник для migrate_json_to_db.py)
│   ├── mp4_paused/             # Анимации с запечёнными паузами (не в git)
│   ├── mp4/                    # Оригиналы (не в git)
│   └── gifs_hd/                # WebP HD fallback (не в git)
│
├── training-skill/
│   ├── SKILL.md
│   ├── assets/
│   │   ├── info_boxes.json     # Источник для migrate_json_to_db.py
│   │   └── breathing_lying.png
│   ├── scripts/
│   │   ├── fill_template.py    # Рендер JSON → HTML
│   │   ├── build_safe_pool.py
│   │   ├── query_exercises.py
│   │   └── extract_hd_frame.py
│   ├── templates/
│   │   └── training_plan_v4.html
│   └── output/
│       ├── plan_andrey_v5.json # Экспорт из БД
│       └── andrey_v5_rendered.html
│
├── annotator/                  # Инструмент разметки ключевых кадров MP4
│   ├── server.py
│   ├── index.html
│   ├── autodetect.py
│   ├── bake_pauses.py
│   └── annotations_*.json
│
├── ARCHITECTURE.md
├── CLAUDE.md                   # Контекст для LLM
├── SKILL_BLUEPRINT.md
└── CLAUDE_CODE_PROMPT.md
```

## Workflow при добавлении нового клиента / плана

1. Анкета клиента → записать в `clients` (вручную или через будущий API)
2. Скилл (будущая реализация) читает историю клиента из БД, генерирует план
3. План записывается в `plans` + `weeks` + `days` + `plan_exercises` и т.д.
4. `export_plan_from_db.py` выгружает план в JSON
5. `fill_template.py` рендерит JSON в HTML
6. HTML отправляется клиенту

## Что даёт БД (vs чистого JSON)

- **Кросс-планные запросы**: «какой вес Андрей жал в 3-м мезоцикле на жим ногами?»
- **Автопрогрессия**: следующий мезоцикл автоматически ставит +2.5 кг от последнего пика
- **Ротация упражнений**: если клиент делал N недель одно и то же — скилл подберёт альтернативу
- **Coach dashboard**: все клиенты в одной витрине
- **Session tracking**: клиент отмечает выполнение, реальные веса идут в `exercise_logs`

## Лицензия

Проприетарный, ArishaFit © 2026
