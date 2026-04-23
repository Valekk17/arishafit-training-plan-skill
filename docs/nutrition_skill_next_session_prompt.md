# Промт для следующей сессии — Nutrition Skill (v1)

Скопируй всё ниже черты в новый чат Claude Opus.

---

# Контекст

Репо: `C:/Users/morod/fitness-andrey`
GitHub: https://github.com/Valekk17/arishafit-training-plan-skill

**Состояние:** training-skill закрыт на 6 из 7 приоритетов.
- Part 1 (science) + Part 2 (injury library 2.0-2.9) + 1.7 goal scaffolds
- Part 3 (plan JSON format), Part 4 (generation process с Phase 0 intake contract)
- Client intake schema v1.0.0 (templates/client_intake_schema.json + validation + validator script)
- DB hygiene (1500 упражнений, 0 проблем, 3 правки литерального перевода)
- info_boxes library (39 записей, 29 Andrey-specific + 10 generic)

**Последние коммиты:**
- `65bcba4` Client intake schema v1.0.0
- `cb3d481` DB hygiene
- `05935cf` SKILL.md +8 injury profiles +7 goal scaffolds

Текущая сессия закрывает последний приоритет training-skill (Priority 6 — glossary) и подготавливает этот промт. **В следующей сессии строим nutrition skill параллельный training skill.**

---

# Цель сессии

Построить **nutrition skill** = движок генерации планов питания по анкете клиента, парный с training skill. Должен интегрироваться с тренировочными днями: в тренировочные дни — больше углеводов и pre/post workout meals, в дни отдыха — другой профиль.

**Контракт интеграции:** каждый день в nutrition плане имеет `training_day_ref` → ссылка на день из training плана (по дате или по (plan_id, week_num, day_num)).

---

# Hard Rules (наследуются от training skill)

1. **Генерирует ТОЛЬКО Opus.** Скрипты — транспорт (DB query, merge JSON, render HTML). Никакого рандомайзерного подбора блюд.
2. **PostgreSQL — источник правды.** Новые таблицы: `foods`, `recipes`, `recipe_ingredients`, `meal_plans`, `meal_plan_days`, `meal_plan_meals`. JSON — формат импорта/экспорта.
3. **UNIT rule:** `recipeId ↔ nameRu ↔ kcal ↔ macros ↔ ingredients[]` неразделима, как в training skill для exerciseId.
4. **Safety + allergy check — работа Opus.** Клиент с `allergies: ["лактоза"]` → keyword-скрипт пропустит «сливочное масло» в рецепте, Opus не пропустит.
5. **Интеграция с training plan** через `training_day_ref` обязательна — иначе macros не подстраиваются.

---

# Этап 1 — База данных (блюда, ингредиенты, БЖУ, рецепты)

## Схема

```sql
-- Одиночные продукты (яйцо, куриная грудка, овсянка)
CREATE TABLE foods (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(64) UNIQUE NOT NULL,  -- "chicken_breast", "oat_rolled"
    name_ru         VARCHAR(255) NOT NULL,
    name_en         VARCHAR(255),
    category        VARCHAR(64),  -- "meat", "grain", "vegetable", "dairy", ...
    kcal_per_100g   NUMERIC(6,2) NOT NULL,
    protein_g       NUMERIC(5,2) NOT NULL,
    fat_g           NUMERIC(5,2) NOT NULL,
    carb_g          NUMERIC(5,2) NOT NULL,
    fiber_g         NUMERIC(5,2) DEFAULT 0,
    allergens       VARCHAR(32)[] DEFAULT '{}',  -- "gluten","lactose","nuts","eggs","fish","soy"
    dietary_flags   VARCHAR(32)[] DEFAULT '{}',  -- "vegetarian","vegan","gluten_free","no_sugar"
    source          VARCHAR(64),  -- "USDA", "CKBN", "manual"
    usda_fdc_id     INTEGER,  -- USDA FoodData Central ID для трассировки
    notes           TEXT
);

-- Готовые блюда (рецепты)
CREATE TABLE recipes (
    id                  SERIAL PRIMARY KEY,
    slug                VARCHAR(128) UNIQUE NOT NULL,
    name_ru             VARCHAR(255) NOT NULL,
    meal_slot           VARCHAR(32) NOT NULL,  -- "breakfast","lunch","dinner","snack","pre_workout","post_workout"
    total_kcal          NUMERIC(6,2),  -- вычисляется из ingredients
    total_protein_g     NUMERIC(5,2),
    total_fat_g         NUMERIC(5,2),
    total_carb_g        NUMERIC(5,2),
    total_fiber_g       NUMERIC(5,2),
    prep_minutes        INTEGER,
    allergens           VARCHAR(32)[] DEFAULT '{}',
    dietary_flags       VARCHAR(32)[] DEFAULT '{}',
    cuisine             VARCHAR(32),  -- "russian","mediterranean","asian"
    recipe_url          TEXT,  -- ссылка на рецепт
    image_url           TEXT,
    instructions        TEXT,  -- краткая инструкция готовки
    notes               TEXT
);

CREATE TABLE recipe_ingredients (
    id              SERIAL PRIMARY KEY,
    recipe_id       INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
    food_id         INTEGER REFERENCES foods(id) ON DELETE RESTRICT,
    grams           NUMERIC(6,2) NOT NULL,
    optional        BOOLEAN DEFAULT FALSE,
    substitution_group VARCHAR(32)  -- группа для замен "protein_source","carb_source"
);

-- План питания = мезоцикл (28 дней типично)
CREATE TABLE meal_plans (
    id                  SERIAL PRIMARY KEY,
    client_id           INTEGER REFERENCES clients(id) ON DELETE CASCADE,
    training_plan_id    INTEGER REFERENCES plans(id),  -- связь с training plan
    total_days          INTEGER DEFAULT 28,
    daily_kcal_target   INTEGER,
    daily_protein_g     INTEGER,
    daily_fat_g         INTEGER,
    daily_carb_g        INTEGER,
    calc_method         VARCHAR(32),  -- "mifflin_st_jeor","katch_mcardle"
    activity_multiplier NUMERIC(3,2),  -- 1.2-1.9
    deficit_or_surplus  INTEGER,  -- kcal +/-
    scientific_basis    TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE meal_plan_days (
    id                  SERIAL PRIMARY KEY,
    meal_plan_id        INTEGER REFERENCES meal_plans(id) ON DELETE CASCADE,
    day_num             INTEGER NOT NULL,  -- 1..28
    week_num            INTEGER NOT NULL,  -- 1..4
    date_iso            DATE,
    training_day_ref    INTEGER REFERENCES days(id),  -- FK на training plan day (NULL если rest day)
    is_training_day     BOOLEAN DEFAULT FALSE,
    day_kcal_target     INTEGER,  -- может отличаться от plan-level
    day_protein_g       INTEGER,
    day_fat_g           INTEGER,
    day_carb_g          INTEGER,
    notes               TEXT
);

CREATE TABLE meal_plan_meals (
    id              SERIAL PRIMARY KEY,
    day_id          INTEGER REFERENCES meal_plan_days(id) ON DELETE CASCADE,
    slot            VARCHAR(32) NOT NULL,  -- "breakfast","lunch","snack1","dinner","pre_workout","post_workout"
    slot_time       VARCHAR(8),  -- "08:00"
    recipe_id       INTEGER REFERENCES recipes(id) ON DELETE RESTRICT,
    portion_multiplier NUMERIC(3,2) DEFAULT 1.0,  -- если порция увеличена
    notes           TEXT
);

-- Сгенерированный shopping list
CREATE TABLE meal_plan_shopping_lists (
    id              SERIAL PRIMARY KEY,
    meal_plan_id    INTEGER REFERENCES meal_plans(id) ON DELETE CASCADE,
    week_num        INTEGER,
    items_json      JSONB NOT NULL  -- [{food_id, total_grams, name_ru, category}]
);
```

## Что нужно построить на Этапе 1

1. `db/models.py` — SQLAlchemy модели для foods, recipes, recipe_ingredients, meal_plans, meal_plan_days, meal_plan_meals, meal_plan_shopping_lists
2. `db/init/002_nutrition_schema.sql` — DDL для новых таблиц (001 уже занят training schema)
3. `scripts/import_usda_foods.py` — импорт базовых продуктов из USDA FoodData Central
4. `scripts/import_ckbn_foods.py` — импорт из CKBN (Химический состав российских продуктов, 2002)

---

# Этап 2 — Источники данных

## USDA FoodData Central (основа)
- URL: https://fdc.nal.usda.gov/
- API (бесплатный, требует API key): https://fdc.nal.usda.gov/api-guide.html
- Покрытие: ~380k продуктов с полными nutrition facts
- Формат: JSON, лицензия public domain
- Стратегия: скачать Foundation + SR Legacy databases (~7k отборных продуктов), фильтрнуть по категории, перевести названия на русский через Opus

## CKBN / Skurihin-Tutelyan (российская классика)
- «Химический состав российских пищевых продуктов» под ред. И.М. Скурихина (ИПП РАМН, 2002)
- Формат: PDF-таблицы, требует OCR или ручной ввод
- Покрытие: ~2000 продуктов с российской спецификой (творог, гречка, сметана и т.д.)
- Стратегия: взять 200-300 ключевых продуктов вручную из таблиц, дополнить USDA

## OpenFoodFacts (опционально)
- https://world.openfoodfacts.org/data
- Barcode-scan готовых продуктов (для клиентов, которые фотографируют упаковки)
- Сомнительное качество — user-generated

## Рекомендация
Старт: USDA (500 ключевых продуктов) + CKBN (200 российских специфик) = **~700 foods** должно хватить на 99% рецептов. Расширять по мере возникновения gap-ов.

---

# Этап 3 — nutrition-skill/SKILL.md (параллельный training-skill/SKILL.md)

## Структура

```
nutrition-skill/
├── SKILL.md                            # главный skill (400-600 строк)
├── assets/
│   └── nutrition_info_boxes.json       # научные справки
├── scripts/
│   ├── calc_kbzhu.py                   # калькулятор TDEE + macros
│   ├── generate_plan.py                # (опционально) помощник
│   └── fill_meal_template.py           # HTML render
├── templates/
│   ├── meal_plan_v1.html               # HTML template
│   ├── client_nutrition_intake.json    # опциональные дополнения к intake
│   └── example_andrey_meal_plan.json   # reference
└── output/
    └── meal_plan_*.json                # сгенерированные планы
```

## Части SKILL.md

### Part 0 — Role
Сертифицированный nutrition coach (PN Level 1 / ISSN-SNS), 10+ лет опыта. Работа с клиентами на дефиците, surplus, recomp, с травмами (грыжа L4-L5 → низкий impact, не диета).

### Part 1 — Nutrition Science
1.1. **KBZHU calc:**
   - TDEE = BMR × activity_multiplier
   - BMR: Mifflin-St Jeor `10×W + 6.25×H − 5×age + s` (s=+5 муж / −161 жен)
   - Activity multipliers: 1.2 sed / 1.375 light / 1.55 mod / 1.725 active / 1.9 very active
   - Для training days: +100-300 kcal к rest day (зависит от intensity)

1.2. **Macros по целям:**
   - **Fat loss:** дефицит 300-500 kcal, P 1.8-2.2 g/kg, F 0.8-1.0 g/kg, остальное C
   - **Hypertrophy:** surplus 200-400 kcal, P 1.6-2.0 g/kg, F 0.8-1.0 g/kg, C 4-7 g/kg
   - **Recomposition:** maintenance ±100 kcal, P 2.0-2.4 g/kg, F 0.8-1.0 g/kg, C 3-4 g/kg
   - **Endurance:** P 1.4-1.7 g/kg, F 1.0-1.2 g/kg, C 5-10 g/kg (выше на длинные сессии)

1.3. **Протеин распределение:** 4-5 приёмов × 0.4-0.5 g/kg (leucine threshold ~2.5g на приём для MPS trigger)

1.4. **Fiber target:** 14g per 1000 kcal (ACSM)

1.5. **Micronutrients check:** vitamin D, omega-3, iron (ж), calcium, B12 (вег/веганы)

### Part 2 — Training Integration
2.1. **Training day vs rest day macros:**
   - Training day: +20-30% carbs (топливо), -10% fat
   - Rest day: baseline carb, normal fat
   - Protein: НЕ меняется

2.2. **Pre-workout (1-2h до):**
   - 20-30g P + 40-60g slow C + низкий F
   - Примеры: куриная грудка + рис, творог + овсянка, омлет + хлеб бз

2.3. **Post-workout (в течение 1-2h):**
   - 30-40g P + 40-80g fast C + низкий F
   - Примеры: сывороточный протеин + банан, курица + картофель, яйца + тост бз

2.4. **Grocery timing vs training schedule:** закупка в день до тренировочной недели

### Part 3 — Dietary Restrictions
Обработка флагов из client intake:
- `vegetarian`, `vegan` — filter recipes, адаптация протеина (sources: tofu, tempeh, seitan, legumes+grains)
- `gluten_free` — exclude wheat/rye/barley
- `no_sugar`, `no_flour` — классический Андрей-preset, расширить
- `lactose_free` — exclude dairy, substitute almond/oat milk + alt protein sources
- `allergies[]` — жёсткий filter по allergens array

### Part 4 — Output Format (Meal Plan JSON)
```json
{
  "client_ref": {...},
  "training_plan_ref": "plan_id=42",
  "program": {
    "total_days": 28,
    "daily_targets": {"kcal": 2300, "protein_g": 180, "fat_g": 70, "carb_g": 250},
    "calc_method": "mifflin_st_jeor",
    "activity_multiplier": 1.55,
    "deficit_or_surplus": -400,
    "scientific_basis": "..."
  },
  "days": [
    {
      "day_num": 1,
      "week_num": 1,
      "date": "2026-05-01",
      "training_day_ref": {"plan_id": 42, "week_num": 1, "day_num": 1, "name": "Push Day"},
      "is_training_day": true,
      "day_targets": {"kcal": 2500, "protein_g": 180, "fat_g": 65, "carb_g": 290},
      "meals": [
        {"slot": "breakfast", "time": "08:00", "recipe_id": 15, "nameRu": "..."},
        {"slot": "pre_workout", "time": "17:00", "recipe_id": 42, ...},
        {"slot": "post_workout", "time": "19:30", "recipe_id": 78, ...},
        {"slot": "dinner", "time": "21:00", "recipe_id": 92, ...}
      ],
      "day_totals": {"kcal": 2487, "protein_g": 178, "fat_g": 68, "carb_g": 285}
    }
  ],
  "shopping_lists": [
    {"week_num": 1, "items": [{"name_ru": "Куриная грудка", "total_g": 1800, "category": "meat"}, ...]}
  ]
}
```

### Part 5 — Generation Process (4 phases)

**Phase 0: Pre-flight**
- Read client intake (personal, goals, lifestyle.dietary_preferences, constraints)
- Read training_plan (identify training days per week)
- Validate dietary consistency (vegetarian + high protein goal = tofu/legumes emphasis)

**Phase 1: Calculate targets**
- BMR (Mifflin-St Jeor) × activity_multiplier → TDEE
- Apply deficit/surplus based on goal
- Split into daily P/F/C targets
- Differentiate training vs rest day macros

**Phase 2: Opus generates (ME)**
- Design week 1 meal structure (slots + timings)
- Select recipes per slot per day
  - Apply dietary filters (allergens, vegetarian, etc.)
  - Ensure variety (no same recipe 2 days in a row)
  - Match macros within ±10% of day_target
  - For training days — insert pre/post-workout meals
- Rotate across 4 weeks (different recipes, similar macros)
- Generate shopping list per week

**Phase 3: Self-audit**
- Allergens: 0 rule violations
- Dietary flags: 100% compliance
- Daily macros: ±10% target
- Variety: recipe repeats < 3× in 28 days
- Training day macros higher than rest day

**Phase 4: Transport + render**
- Merge meal plan JSON
- Migrate to DB (meal_plans + children)
- Render HTML with recipe cards

### Part 6 — Language
- «Белок/белки» не «протеин» (разговорный)
- «Углеводы», «жиры», «ккал» — стандарт
- Приёмы пищи: «завтрак / второй завтрак / обед / полдник / ужин / перекус / до тренировки / после тренировки»
- Не «макросы» → «БЖУ»
- Ингредиенты на русском, граммы цифрами

### Part 7 — Legal Disclaimers (РФ)
- Консультация с врачом/нутрициологом требуется
- Не заменяет медицинское назначение диетолога
- Аллергены обязательно указаны
- 323-ФЗ, 152-ФЗ, ТР ТС 022/2011, ТР ТС 021/2011 (пищевая безопасность)

---

# Этап 4 — Integration с training skill

## Контракт `training_day_ref`

В `meal_plan_days` поле `training_day_ref` ссылается на `days.id` из training plan.

**Logic при generation:**
```python
# Phase 0 pre-flight
training_plan = db.query(Plan).filter_by(id=client.active_training_plan_id).one()
training_days_by_weekday = {}  # {"monday": Day(push), "wednesday": Day(cardio), ...}

# Или по date-index если training plan has scheduled dates:
training_days_by_date = {}  # {"2026-05-01": Day(push), "2026-05-02": None, ...}

# Phase 2 generation
for meal_day in meal_plan_days:
    training_day = training_days_by_date.get(meal_day.date_iso)
    meal_day.training_day_ref = training_day.id if training_day else None
    meal_day.is_training_day = training_day is not None
    if training_day:
        # +20% carbs, +200 kcal, add pre/post workout meals
        ...
```

## Проверки в Self-Audit
- Каждый `meal_plan_days.is_training_day=True` имеет pre_workout И/ИЛИ post_workout meals
- Day kcal для training days > day kcal для rest days
- Carb distribution: training days 45-55% kcal, rest days 35-45%

---

# Что нужно сделать в сессии (порядок)

## 🔴 Priority 1 — DB schema
1. Написать `db/init/002_nutrition_schema.sql` (DDL)
2. Расширить `db/models.py` — новые SQLAlchemy модели
3. Проверить миграцию: `docker compose up -d postgres` → `psql -f 002_nutrition_schema.sql`

## 🟠 Priority 2 — Foods DB seed (USDA)
1. Написать `scripts/import_usda_foods.py`:
   - Загрузить FoodData Central Foundation + SR Legacy JSON dumps
   - Фильтр: белковые (meat/fish/eggs/dairy), углеводы (grains/legumes), жиры (oils/nuts), овощи, фрукты
   - Выбрать top 500 по частоте использования в рецептах
   - Перевести name на русский через Opus batch (30-50 за раз)
   - INSERT в `foods` таблицу

2. CKBN — ручной ввод 200 российских продуктов (творог 5%, гречка, сметана, квашеная капуста и т.д.)

## 🟡 Priority 3 — nutrition-skill/SKILL.md
Написать полный SKILL.md (400-600 строк) по структуре выше.

## 🟢 Priority 4 — Recipes seed
1. Написать 50-80 базовых рецептов вручную:
   - 15 завтраков (разной сложности, разных профилей)
   - 20 обедов/ужинов
   - 10 перекусов
   - 10 pre-workout
   - 10 post-workout
   - 10 recipes для vegetarian/vegan вариантов
2. INSERT через `scripts/seed_recipes.py` из YAML/JSON

## 🔵 Priority 5 — Example generation (Андрей)
Сгенерировать `example_andrey_meal_plan.json` = 28-day план для Андрея:
- Использовать его client intake из `training-skill/templates/example_andrey_intake.json`
- Линковать к training plan Push/Cardio/Pull+Legs (3 training days per week)
- Применить dietary flags: `no_sugar: true, no_flour: true`
- Weight_loss дефицит 400 kcal

## ⚪ Priority 6 — HTML render
Адаптировать training_plan_v4.html → meal_plan_v1.html:
- Карточки блюд с картинками и рецептами
- Разные дни = разные вкладки / скролл секции
- Shopping list отдельная секция
- Watermark ArishaFit, цветовая схема `#B7EFFF / #575757 / Nunito`

---

# Что НЕ делать

1. НЕ начинать в одной сессии ВСЕ 6 приоритетов — это overflow. Рекомендую Priority 1+2 в первой сессии, Priority 3+4 во второй, Priority 5+6 в третьей.
2. НЕ импортировать 380k продуктов из USDA — только top 500 + top 200 CKBN.
3. НЕ генерировать рецепты через LLM без валидации БЖУ (считать из ingredients по формуле, НЕ верить LLM arithmetic).
4. НЕ писать рецепты где сумма kcal из P×4 + C×4 + F×9 расходится с total_kcal больше чем на 5% — это индикатор ошибки.
5. НЕ создавать hardcoded meal pools — все meals через Opus selection из DB.
6. НЕ забыть валидировать allergens на КАЖДОМ упражнении self-audit — это work safety критичный чек.

---

# Ключевые ссылки на training skill (для контекста)

- `training-skill/SKILL.md` — 834 строки, образец структуры
- `training-skill/templates/client_intake_schema.json` — intake контракт
- `training-skill/templates/example_andrey_intake.json` — пример заполненного
- `training-skill/assets/info_boxes.json` — 39 научных справок
- `db/models.py` — SQLAlchemy схема training skill
- `scripts/validate_client_intake.py` — паттерн для валидатора

---

# Hard Rules reminder

1. Планы генерирует ТОЛЬКО Opus. Скрипты — транспорт.
2. Postgres = источник правды для foods + recipes.
3. UNIT rule: recipeId ↔ nameRu ↔ kcal ↔ macros ↔ ingredients.
4. Safety + allergy check — работа Opus, не keyword-скрипта.
5. Training integration через `training_day_ref` обязательна.

---

# Dev окружение

```bash
cd C:/Users/morod/fitness-andrey
docker compose up -d postgres
psql -h localhost -U arishafit -d arishafit -f db/init/002_nutrition_schema.sql

# Импорт foods
python scripts/import_usda_foods.py --limit 500

# Генерация примера
# ... (через Opus intake)
python scripts/fill_meal_template.py --plan output/meal_plan_andrey.json --output docs/andrey_nutrition.html
```

---

**Старт сессии:** прочитай этот промт + `training-skill/SKILL.md` (для наследования стиля) + `db/models.py` (для понимания текущей схемы) + `training-skill/templates/example_andrey_intake.json` (целевой клиент для первого example).

Затем начинай с Priority 1 (DB schema) — без базы всё остальное построить невозможно.
