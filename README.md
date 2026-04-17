# ArishaFit — Training Plan Skill

Reusable engine for generating personalized gym training plans with adaptive exercise selection, injury-aware filtering, and animated MP4 demonstrations.

## Что это

Скилл для генерации персональных планов тренировок из анкеты клиента (JSON) в HTML-документ с запечёнными видео упражнений.

**Ключевые возможности:**
- База из 1500 упражнений (ExerciseDB) с профессиональными русскими названиями
- Автоматический подбор упражнений под травмы, оборудование, цели клиента
- Периодизация (линейная/волновая/блочная) на 4-недельный цикл
- MP4-видео каждого упражнения с запечёнными 1-секундными паузами на ключевых позах
- Суперсеты, Zone 2 кардио, дроп-сеты — полный арсенал методик

## Структура репо

```
.
├── annotator/                  # Инструмент разметки ключевых кадров упражнений
│   ├── server.py               # Локальный HTTP-сервер (http://localhost:8787)
│   ├── index.html              # Web-UI для просмотра/правки разметки
│   ├── autodetect.py           # Авто-поиск ключевых кадров по blackness
│   ├── bake_pauses.py          # Запекает паузы в MP4 через ffmpeg
│   ├── annotations_auto.json   # Результат автодетекта (1322 упражнения)
│   ├── annotations_manual.json # Ручные правки
│   └── _batch_[1-3]_*.json     # Opus-батчи для переименования упражнений
│
├── exercisedb_data/
│   └── exercise_db_final.json  # Каноническая БД (1500 упражнений с Opus-именами)
│   # mp4/, mp4_paused/, gifs_hd/ — НЕ в git (слишком большие), доступны отдельно
│
├── training-skill/
│   ├── SKILL.md                # Описание скилла для Claude
│   ├── scripts/
│   │   ├── fill_template.py    # Рендер плана (JSON → HTML)
│   │   ├── build_safe_pool.py  # Подбор безопасных упражнений по травмам
│   │   ├── query_exercises.py  # Поиск упражнений в БД
│   │   └── extract_hd_frame.py # Утилита для WebP фреймов
│   ├── templates/
│   │   └── training_plan_v4.html  # HTML-шаблон плана
│   └── output/
│       └── plan_andrey_v5.json    # Пример плана (не в git: рендер и бэкапы)
│
├── nutrition-skill/            # Питание (отдельный скилл, в разработке)
│
├── ARCHITECTURE.md
├── CLAUDE.md                   # Контекст проекта для LLM
├── SKILL_BLUEPRINT.md
└── CLAUDE_CODE_PROMPT.md
```

## Как запустить

### 1. Установка зависимостей

```bash
pip install opencv-python-headless pillow numpy
# ffmpeg должен быть в PATH
```

### 2. Подготовка медиа

Папки `exercisedb_data/{mp4,mp4_paused,gifs_hd}` не в git — скачай отдельно (см. отдельный storage) или запусти локальную пайплайну:

```bash
# Автодетект ключевых кадров
python annotator/autodetect.py

# Запечь 1-секундные паузы в MP4
python annotator/bake_pauses.py
```

### 3. Разметка ключевых кадров (опционально)

Для ручной корректировки автодетекта:

```bash
python annotator/server.py
# Открой http://localhost:8787/ в браузере
```

### 4. Рендер плана

```bash
python training-skill/scripts/fill_template.py \
  --plan training-skill/output/plan_andrey_v5.json \
  --output training-skill/output/andrey_v5_rendered.html
```

## Данные MP4

Каждое упражнение имеет:
- `mp4/<id>.mp4` — оригинал ExerciseDB (~12-36 кадров, 10 fps)
- `mp4_paused/<id>.mp4` — с запечёнными паузами на ключевых позах (1 сек × N поз)

`mp4_paused/` используется в рендере планов по умолчанию — не требует JS для пауз.

## Переименование БД

Все 1500 названий сгенерированы через Claude Opus в 3 батча по 500:
- `annotator/_batch_[1-3]_output.json` — результаты
- `annotator/_renames_all.json` — сведённый словарь `{exerciseId: nameRu}`

Принципы: профессиональная зальная терминология, 2-5 слов, уникальность в пределах всех 1500 имён.

## Лицензия

Проприетарный, ArishaFit © 2025
