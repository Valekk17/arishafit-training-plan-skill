# Следующая сессия — точка продолжения

Последняя сессия закончилась на `d39209c` (2026-04-20).

## Что сделано в последней сессии

### PostgreSQL — источник правды
- `docker-compose.yml` + `.env.example` + `requirements.txt`
- `db/models.py` — SQLAlchemy модели: exercises, info_boxes, clients, plans, weeks, days, plan_exercises, plan_alternatives, warmup_variants, cooldown_variants, session_logs, exercise_logs, one_rm_estimates
- `db/queries.py` — helpers: `load_all_exercises`, `find_exercises`, `load_all_info_boxes`, `is_db_available`
- `db/session.py` — engine + SessionLocal
- `scripts/migrate_json_to_db.py` — JSON → Postgres (1500 упр, 29 справок, план Андрея)
- `scripts/export_plan_from_db.py` — Postgres → JSON для рендера
- `fill_template.py` + `build_safe_pool.py` + `query_exercises.py` — читают из Postgres с JSON-fallback
- `SKILL.md` — hard rules: **планы генерирует ТОЛЬКО Opus**, БД — источник правды, exerciseId ↔ имя+анимация+описание

### Мобильная вёрстка
- Три breakpoint'а: 900px (панель-drawer), 768px (уплотнение), 480px (компакт)
- Исправлены подряд 5 багов с панелью:
  1. Handle торчал в середине экрана — перенёс transform на wrap
  2. Клики не работали (pointer-events перехват) — добавил pointer-events:none
  3. Блюр выезжающих окон — убрал backdrop-filter, sub-pixel transforms, info-slide animation
  4. Панель выезжала под backdrop — исправил stacking context (`.training-layout { z-index: auto }` + `wrap z:9999`)
  5. Страница прыгала в верх — убрал `overflow:hidden` на html/body, вместо этого `touch-action:none` на backdrop

### Блок «Базовые понятия и термины»
- `<section id="glossary">` после обзора программы
- 8 карточек: RPE, Суперсет, Дилоуд, Zone 2 кардио, Прогрессивная перегрузка, Ротация, Темп, Осевая нагрузка
- Grid auto-fit на десктопе, 1 колонка на <480px

### Канонизация БД и имен
- Функция `resolve_name()` в fill_template.py — имя ВСЕГДА из БД по exerciseId
- Плановые `nameRu` игнорируются если отличаются от БД (кроме квалификаторов типа `(A1 суперсета)`)
- Все 44 упражнения в плане Андрея проверены — нулевые проблемы по connectivity к БД

## Состояние Postgres
- Docker container: `arishafit-postgres` (postgres:16-alpine)
- Порт 5432
- БД: arishafit / пользователь: arishafit / пароль: arishafit_dev
- Запустить: `docker compose up -d`
- Проверить: `docker exec arishafit-postgres pg_isready -U arishafit`

## Что лежит на очереди

### Мобильная вёрстка — нужно проверить пользователем
- Файл: `training-skill/output/andrey_v5_rendered.html` (21 MB)
- Последний фикс: клик на упражнение не прыгает страницу в верх, панель выезжает поверх backdrop, внутри скролл работает

### Возможные задачи
- [ ] Перекодировать MP4 в 960×960 для retina-дисплеев (убрать остаточный blur в панели) — +100 MB
- [ ] Alembic миграции для production deploy
- [ ] Генератор новых планов: Opus-промпт с `safe_pool + history + catalog + info_boxes` → JSON → БД
- [ ] Session tracking UI (клиент отмечает выполнение, сохраняется в `exercise_logs`)
- [ ] Nutrition skill полноценно внедрить (сейчас только `nutrition-skill/SKILL.md`)

## Запуск dev-окружения

```bash
# 1. Postgres
docker compose up -d

# 2. Миграция JSON → Postgres (если пусто)
python scripts/migrate_json_to_db.py --create-tables --wipe

# 3. Экспорт плана из БД + рендер
python scripts/export_plan_from_db.py --client "Андрей" --output training-skill/output/plan_andrey_v5.json
python training-skill/scripts/fill_template.py \
  --plan training-skill/output/plan_andrey_v5.json \
  --output training-skill/output/andrey_v5_rendered.html
```

## Важные правила (не забыть)

1. **Планы генерирует ТОЛЬКО Opus.** Никаких Python-рандомайзеров для подбора упражнений.
2. **БД — источник правды.** JSON-файлы — формат импорта/экспорта.
3. **exerciseId → имя + анимация + описание.** План не может переименовать упражнение, только добавить квалификатор `(A1 суперсета)`.
4. **Никаких самодельных рисунков.** Для нестандартных упражнений (дыхание) — скриншот похожей позы из БД.
5. **Источники в справках — реальные публикации.** Верифицировать через WebSearch, смягчать числа если не подтверждается.

## GitHub

`https://github.com/Valekk17/arishafit-training-plan-skill`
