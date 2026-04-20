# Следующая сессия — точка продолжения

Последний стабильный коммит: `f1ef84b` (2026-04-20).

## ⏳ ТЕКУЩАЯ ЗАДАЧА — регенерация plan_andrey_v6.json

Прошлая сессия закончилась на попытке перегенерации плана через Opus. Агент сжёг квоту (66 tool uses, 11 минут) и упал с ошибкой `Your organization does not have access to Claude` ДО того как записал файл. `plan_andrey_v6.json` не создан.

### Почему нужна v6

В v5 найдены **4 проблемы**, требуют фикса:

1. **Leg press 45° (`10Z2DXU`) вызывал дискомфорт в пояснице** у клиента. При глубокой амплитуде таз подкатывается (posterior pelvic tilt), поясница выходит из нейтрали — провокация L4-L5.

2. **Гиперэкстензия (`rUXfn3R`) без строгой инструкции** — классическое выполнение с прогибом в поясничном отделе = прямое противопоказание при грыже.

3. **Однообразие**: 4 из 9 упражнений неизменны все 4 недели (leg press, ягодичный мост, dead bug, боковая планка, гиперэкстензия). Клиенту скучно + тело адаптируется за 3-4 недели.

4. **Ягодичный мост со штангой (`qKBpF7I`)** — tips должны явно требовать валик/подушку под штангу и нейтральный таз (без гипер-моста с прогибом).

### Контекст уже готов

- `training-skill/output/_v6_candidates.json` — предварительно отфильтрованные кандидаты на замену по каждому слоту (26 пулов, 3-6 упражнений в каждом). **Не заставляй Opus browsить всю БД — он падает на квоте.**
- Текущий план: `training-skill/output/plan_andrey_v5.json`
- Скрипт предподготовки: `scripts/prepare_v6_context.py` (если нужно регенерить кандидатов)

### Что Opus должен сделать

Написать `training-skill/output/plan_andrey_v6.json` — копия v5 с правками:

**Изменения:**
- Leg press 45° → выбор из `_v6_candidates.json` → `squat_safe_seated` или `squat_safe_hack` (6 кандидатов: `10Z2DXU` не брать; нужны hack squat/seated lever без 45° sled)
- Если в slot пусто — разбить на `leg_extension` (2) + `lying_leg_curl` (2) как суперсет
- `rUXfn3R` гиперэкстензия — либо оставить с новыми tips (hip hinge only, нет прогиба поясницы), либо заменить на `hinge_cable_pullthrough` (3 cand) / `hinge_reverse_hyper` (3 cand)
- `qKBpF7I` ягодичный мост — проверить tips, добавить про валик + нейтральный таз
- Dead Bug (`iny3m5y`) — keystone, не менять, остаётся W1-W4

**Ротация по неделям:**
- Day A: W1 базовые (Хаммер жим / верх. блок широкий / squat safe / Dead Bug / Side plank) → W2 другое оборудование (кроссовер / обратный хват / leg ext+curl) → W3 ещё вариация (incline / cable pullover / split squat) → W4 дилоуд = W1 с 50%
- Day B: W1 (нижн. блок / Хаммер плеч / ягодичн. мост / Dead Bug / back ext strict) → W2 (one-arm row / lateral raise machine / cable pull-through / Bird-Dog) → W3 (lever row / shoulder press dumbbell supported / reverse hyper / Pallof) → W4 = W1 дилоуд
- Кардио (day 2) — не трогать, копировать из v5

**Что копировать 1-в-1 из v5:**
- `plan.client`
- `plan.program` (включая `training_history`, `progression`, `scientific_basis`, `program_meta`)
- `plan.warmups` и `plan.cooldowns`
- `plan.warmups_info_box`, `plan.cooldowns_info_box`
- `plan.weeks[*].focus`, `.info_box`
- `plan.weeks[*].days[*].info_box`
- Все tips/warning прежних упражнений если они остаются (только ротация упражнений меняет их)

### Шаги после v6.json

```bash
# Миграция v6 в Postgres
python scripts/migrate_json_to_db.py --wipe   # пересоздаёт план

# Проверить что БД подхватила
python scripts/export_plan_from_db.py --client "Андрей" --output training-skill/output/plan_andrey_v6.json

# Рендер
python training-skill/scripts/fill_template.py \
  --plan training-skill/output/plan_andrey_v6.json \
  --output training-skill/output/andrey_v6_rendered.html

# Копия в docs для GitHub Pages
cp training-skill/output/andrey_v6_rendered.html docs/andrey.html

# Коммит + push — Pages обновится за 1-2 мин
git add -A && git commit -m "v6: safety fixes + rotation" && git push
```

---

## Что сделано в прошлых сессиях (контекст)

### PostgreSQL архитектура
- `docker-compose.yml` + `.env.example` + `requirements.txt`
- `db/models.py` — SQLAlchemy модели: exercises, info_boxes, clients, plans, weeks, days, plan_exercises, plan_alternatives, warmup_variants, cooldown_variants, session_logs, exercise_logs, one_rm_estimates
- `db/queries.py` — helpers: `load_all_exercises`, `find_exercises`, `load_all_info_boxes`, `is_db_available`
- `scripts/migrate_json_to_db.py` — JSON → Postgres
- `scripts/export_plan_from_db.py` — Postgres → JSON
- `fill_template.py` + `build_safe_pool.py` + `query_exercises.py` — читают из Postgres с JSON-fallback

### FastAPI backend (для прода)
- `api/main.py` — endpoints: `/plan/{slug}` (HTML), `/plan/{slug}.json`, `/exercises`, `/exercise/{id}`, `/mp4/{id}.mp4`, `/info-boxes`
- `api/Dockerfile` — готов для Railway/Fly.io
- `docker-compose.yml` включает api service

### GitHub Pages
- `docs/andrey.html` — публикуется автоматически при push в main
- URL: https://valekk17.github.io/arishafit-training-plan-skill/andrey.html
- Для включения Pages в settings → Pages → Source: main / Folder: /docs

### Мобильная вёрстка (много итераций фиксов)
- iOS Safari клики: добавлены cursor:pointer + touch-action:manipulation + webkit-tap-highlight на все интерактивные селекторы
- Шрифты через `<link>` вместо `@import` (Safari блокирует @import)
- Панель drawer: фикс stacking-context (z:9999 + .training-layout z-index:auto)
- Scroll фикс: убраны overflow:hidden/position:fixed на body (ломали scroll iOS), вместо этого touch-action:none на backdrop
- Viewport meta с `viewport-fit=cover` + apple-mobile-web-app-capable

### Глоссарий в плане
- 8 базовых терминов (RPE, Суперсет, Дилоуд, Zone 2, Progressive overload, Ротация, Темп, Осевая нагрузка)
- CSS-переменные для theming: `--swap-color`, `--swap-color-bg`, `--swap-color-strong`
- Зелёный контрастный бейдж «ЗАМЕНЕНО» на заменённых упражнениях

### Канонизация БД
- Функция `resolve_name()` в fill_template: имя ВСЕГДА из БД по exerciseId
- Только квалификатор `(A1 суперсета)` может добавиться из плана
- 1500 упражнений в exercises, 29 справок в info_boxes, план Андрея в plans/weeks/days/plan_exercises

## Запуск dev-окружения

```bash
cd C:/Users/morod/fitness-andrey

# 1. Postgres (если не поднят)
docker compose up -d postgres

# 2. Если БД пустая:
python scripts/migrate_json_to_db.py --create-tables --wipe

# 3. Экспорт + рендер плана:
python scripts/export_plan_from_db.py --client "Андрей" --output training-skill/output/plan_andrey_v5.json
python training-skill/scripts/fill_template.py --plan training-skill/output/plan_andrey_v5.json --output training-skill/output/andrey_v5_rendered.html

# 4. API локально:
uvicorn api.main:app --reload --port 8000
```

## Жёсткие правила (не забывать)

1. **Планы генерирует ТОЛЬКО Opus.** Скрипты готовят контекст, валидируют, рендерят.
2. **PostgreSQL — источник правды.** JSON — формат импорта/экспорта.
3. **exerciseId ↔ имя ↔ анимация ↔ описание** неразделимы. План добавляет только квалификатор в скобках.
4. **Никаких самодельных рисунков.** Для нестандартных упражнений — скриншот похожей позы из БД.
5. **Источники справок верифицированы через WebSearch.** Смягчать числа если не подтверждается.

## GitHub

https://github.com/Valekk17/arishafit-training-plan-skill
