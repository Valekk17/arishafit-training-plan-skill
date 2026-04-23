# Интеграция Training Skill ↔ Nutrition Skill

**Status:** design doc для координации двух параллельных сессий.
**Актуально на:** 2026-04-23 (commit `e446e7e`).

---

## 0. TL;DR

Два **отдельных** skill-а, но **тесно связанных** через:
1. **Единый client intake JSON** (`client_intake_schema.json` v1.0.0) — источник правды для обоих
2. **Shared PostgreSQL** — `clients` общая, `plans` training, `meal_plans` nutrition со ссылкой `training_plan_id`
3. **Порядок генерации:** training ПЕРВЫЙ, nutrition ВТОРОЙ (macros зависят от training days, не наоборот)
4. **Контракт `training_day_ref`:** каждый `meal_plan_days.training_day_ref` → `days.id` из training plan
5. **Стиль и конвенции:** nutrition skill наследует hard rules, формат output, Russian conventions от training skill

**Единый skill vs разделённые — выбран разделённый**, потому что:
- Независимая активация (клиент может иметь только training / только nutrition / оба)
- Меньше контекста на одну генерацию (не грузить питание для training generation)
- Возможность обновлять skill-ы независимо
- Клиенты могут попросить «только план питания» без тренировок

---

## 1. Архитектура

```
                    ┌──────────────────────────────────┐
                    │   client_intake_schema v1.0.0    │  (общий JSON-контракт)
                    │   • personal • goals • injuries  │
                    │   • constraints • lifestyle      │
                    │   • dietary_preferences • consent│
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    ▼                              ▼
        ┌──────────────────────┐     ┌──────────────────────┐
        │ Training Skill       │     │ Nutrition Skill      │
        │ (training-skill/)    │     │ (nutrition-skill/)   │
        │                      │     │                      │
        │ Phase 0: read intake │     │ Phase 0: read intake │
        │ Phase 1: SQL catalog │     │          + read      │
        │ Phase 2: generate    │     │            training  │
        │ Phase 3: self-audit  │     │            plan      │
        │ Phase 4: render      │     │ Phase 1: calc KBZHU  │
        │                      │     │ Phase 2: generate    │
        │                      │     │ Phase 3: self-audit  │
        │                      │     │ Phase 4: render      │
        └──────────┬───────────┘     └──────────┬───────────┘
                   │                            │
                   ▼                            ▼
        ┌──────────────────────┐     ┌──────────────────────┐
        │ plan_*.json (output) │     │ meal_plan_*.json     │
        │ andrey.html          │     │ andrey_nutrition.html│
        └──────────┬───────────┘     └──────────┬───────────┘
                   │                            │
                   ▼                            ▼
        ┌──────────────────────────────────────────────┐
        │        PostgreSQL arishafit (shared)         │
        │                                              │
        │  clients ←─┬─── plans (training)             │
        │            │      ↓                          │
        │            │    weeks                        │
        │            │      ↓                          │
        │            │    days (id) ←───┐              │
        │            │      ↓            │              │
        │            │    plan_exercises │              │
        │            │                   │              │
        │            └─── meal_plans ────┘              │
        │                   │  training_plan_id FK     │
        │                   ↓                          │
        │                 meal_plan_days               │
        │                   │  training_day_ref FK     │
        │                   ↓                          │
        │                 meal_plan_meals              │
        │                                              │
        │  foods, recipes, recipe_ingredients          │
        │    (reference tables для nutrition)          │
        │  exercises                                   │
        │    (reference table для training)            │
        │  info_boxes (shared)                         │
        └──────────────────────────────────────────────┘
```

---

## 2. Shared компоненты

### 2.1 Client intake schema

**Уже существует:** `training-skill/templates/client_intake_schema.json` v1.0.0.

Для nutrition skill **не требуется отдельный intake** — текущая схема уже содержит:
- `personal` (age, gender, height, weight) → TDEE calc
- `goals.primary` → macro distribution profile
- `goals.timeline_weeks` → длина meal plan
- `injuries[]` → диастаз прямой → +protein; ГЭРБ → no late meals (если добавим)
- `constraints.training_days_per_week` → какие дни высокие углеводы
- `lifestyle.dietary_preferences` (vegetarian/vegan/gluten_free/no_sugar/no_flour/lactose_free/allergies[]) → filter рецептов
- `lifestyle.sleep_hours_avg` / `stress_level` → cortisol-aware macro split
- `lifestyle.medications[]` → drug-food interaction check
- `preferences.disliked_exercises` (не использовать) / `favorite_movements` (не использовать)
- `consent.medical_disclaimer_accepted` → блокер генерации

**Расширения для nutrition:** если нужны — добавлять в client intake schema v1.1.0 через `preferences.nutrition` sub-object (НЕ отдельный intake):
```json
"preferences": {
  "nutrition": {
    "disliked_foods": [],
    "favorite_cuisines": ["russian", "mediterranean"],
    "meal_prep_willingness": "moderate",  // none/moderate/high
    "kitchen_skill": "intermediate",      // beginner/intermediate/advanced
    "budget_per_day_rub": null
  }
}
```

**Решение:** nutrition-сессия МОЖЕТ расширить intake schema → bump до v1.1.0. Training skill продолжает работать с v1.0.0 через backward compat (unknown fields ignored).

### 2.2 PostgreSQL

**Общие таблицы (нельзя дублировать):**
- `clients` — клиент-то один на обе плоскости
- `info_boxes` — научные справки (training и nutrition могут иметь общие темы вроде sleep, recovery)

**Training tables (уже есть):** `plans`, `weeks`, `days`, `plan_exercises`, `plan_alternatives`, `plan_warmup_variants`, `plan_cooldown_variants`, `exercises`, `session_logs`, `exercise_logs`, `one_rm_estimates`.

**Nutrition tables (nutrition-сессия создаст):** `foods`, `recipes`, `recipe_ingredients`, `meal_plans`, `meal_plan_days`, `meal_plan_meals`, `meal_plan_shopping_lists`.

**Новые foreign keys (критичные для интеграции):**
```sql
meal_plans.training_plan_id  REFERENCES plans(id)  NULL  -- может быть nutrition-only клиент
meal_plan_days.training_day_ref  REFERENCES days(id)  NULL  -- NULL для rest day
```

ON DELETE:
- `training_plan_id`: `ON DELETE SET NULL` (удаление training plan не убивает nutrition plan, но разрывает связь)
- `training_day_ref`: `ON DELETE SET NULL` (если training day удалён — meal day остаётся, просто превращается в «rest day profile»)

---

## 3. Workflow генерации

### 3.1 Порядок — training first, nutrition second

**Почему:**
- Macros **зависят** от training days (carb distribution)
- Training **не зависит** от питания — упражнения подбираются по injuries/goal/level/days
- Если генерировать параллельно — возможны несогласования (например, training назначил 3 days, nutrition посчитал для 4)

**Исключения:**
- Nutrition-only клиент (без тренировок) → генерируем nutrition со всеми днями как `rest day`
- Training-only клиент → всё как раньше

### 3.2 Combined session (обычный кейс)

```
Step 1. Read client_intake.json (один раз)

Step 2. Training Skill (Opus session #1):
  - Phase 0-4 как описано в training-skill/SKILL.md
  - Output: plan_<client>_<version>.json
  - Migrate: python scripts/migrate_json_to_db.py → plans, weeks, days, ...

Step 3. Nutrition Skill (Opus session #2 ИЛИ тот же):
  - Phase 0.1: read client_intake.json (same file)
  - Phase 0.2: read latest active plan:
      SELECT * FROM plans WHERE client_id=... AND status='active'
      ORDER BY created_at DESC LIMIT 1
  - Phase 0.3: build date→training_day mapping:
      for each day in days of that plan:
        date_index[start_date + day_offset] = day.id
  - Phase 1: calc BMR + TDEE + macros
  - Phase 2: generate 28-day meal plan
      for each date:
        training_day_ref = date_index.get(date)  # может быть None
        if training_day_ref: apply training_day_macros profile
        else: apply rest_day_macros profile
  - Phase 3: self-audit (carb differentiation, allergens, variety)
  - Phase 4: render meal_plan_<client>_<version>.html
  - Migrate: python nutrition-skill/scripts/migrate_meal_plan_to_db.py
```

### 3.3 Когда одного нет

**Nutrition-only клиент:**
```python
active_training_plan = None  # или client.active_training_plan_id=NULL
for date in meal_plan_dates:
    training_day_ref = None
    is_training_day = False
    apply_rest_day_macros(date)
```

**Training-only клиент:** просто не генерируем meal plan. Training skill не меняется.

### 3.4 Re-generation при изменении training

Если клиент меняет training plan (v7 → v8):
1. **Soft sync** (light): обновить только `meal_plan_days.training_day_ref` по новым датам, macros оставить
2. **Hard regen** (full): сгенерировать новый meal plan с нуля
3. По умолчанию — hard regen (проще, консистентнее)

**Detection of out-of-sync:**
```sql
SELECT mp.id, mp.training_plan_id, p.id as current_active_plan_id
FROM meal_plans mp
JOIN clients c ON mp.client_id = c.id
LEFT JOIN plans p ON p.client_id = c.id AND p.status = 'active'
WHERE mp.training_plan_id != p.id OR mp.training_plan_id IS NULL
```

Такие `meal_plans` помечать `status='stale'` — клиенту показывать алерт, что план питания устарел.

---

## 4. Контракт интеграции (детально)

### 4.1 Training day macros vs rest day macros

**Базовая формула:**
```
daily_baseline = TDEE + deficit/surplus  # baseline = rest day

training_day_kcal = daily_baseline + training_bonus_kcal
rest_day_kcal = daily_baseline

# training_bonus_kcal по intensity тренировки:
#   Zone 2 cardio 30-45 min → +150-250 kcal
#   Strength 45-60 min → +200-300 kcal
#   HIIT 20-30 min → +150-200 kcal
#   Heavy strength 60-90 min → +300-400 kcal
```

**Macro shift:** на training day **+углеводы**, НЕ белок (белок константа для MPS):
```
P_constant (оба дня) = 1.8-2.2 g/kg bodyweight (по goal)
F_rest = 1.0 g/kg
F_training = 0.8 g/kg  (чуть ниже, освобождает kcal для carbs)
C_rest = (rest_kcal - P*4 - F*9) / 4
C_training = (training_kcal - P*4 - F_training*9) / 4
```

Result: training day C ≈ rest day C × 1.3-1.5.

### 4.2 Meal slot mapping vs training time

Из `client_intake.constraints.preferred_time`:
- `morning` training → breakfast легкий, pre_workout 1h до, post_workout 30min-1h после, lunch спустя 2h
- `afternoon` training → breakfast/lunch обычные, pre_workout 1-2h до (обычно lunch+2h), post_workout ужин 1-2h после
- `evening` training → breakfast/lunch/snack обычные, pre_workout lunch-2h / snack, post_workout dinner

Nutrition skill должен сгенерировать meal slots с **конкретными временами** (не просто «breakfast/lunch/dinner»).

### 4.3 Pre-workout meal требования
- 20-30g P + 40-60g slow C (oats, rice, sweet potato, яблоко+орех пасту) + **низкий F** (<15g, т.к. fat замедляет опорожнение желудка)
- Timing: 1-2 часа до тренировки
- Если тренировка в 6 утра — вариант liquid (shake) 30 мин до

### 4.4 Post-workout meal требования
- 30-40g P + 40-80g fast C (рис, картофель, банан, рисовая лапша) + low-moderate F
- Timing: 0-2 часа после — "anabolic window" миф в классическом виде, но meal в пределах 2h оптимизирует recovery
- Для rehab-клиентов (Andrey) — добавить collagen 10-15g + витамин С (ускоряет соединительную ткань healing)

---

## 5. Cross-skill rules

### 5.1 Goal consistency

`intake.goals.primary` должен совпадать в training + nutrition, **либо** явный override в metadata:

| Training goal | Default Nutrition goal | Allowed override |
|---|---|---|
| hypertrophy | hypertrophy (+200-400 kcal surplus) | recomp (–100 to +100) |
| strength | hypertrophy (+200 kcal) | maintenance |
| weight_loss | weight_loss (–300-500 kcal) | recomp |
| recomposition | recomp (±100) | weight_loss (осторожно) |
| endurance | endurance (high carb) | — |
| rehab | maintenance | — (нельзя deficit в rehab) |
| general_fitness | maintenance | weight_loss |
| powerbuilding | hypertrophy (+300) | recomp |

Если nutrition-сессия хочет override — явно в metadata: `"goal_override_reason": "клиент хочет сначала сбросить 5kg, потом hypertrophy"`.

### 5.2 Training days consistency

`intake.constraints.training_days_per_week` определяет:
- Training skill: количество training sessions в split
- Nutrition skill: сколько дней в 7-дневном цикле имеют `is_training_day=true`

Если training skill сгенерировал 3 дня, а nutrition пытается 4 — ошибка. Self-audit в nutrition должен сверять count.

### 5.3 Timeline consistency

`intake.goals.timeline_weeks` — длина обоих планов. Default 4 недели.

Nutrition план длиннее training (например, 28 дней при training 4×7=28) — OK.
Nutrition план короче training — ошибка, регенерировать.

### 5.4 Injuries relevance

| Injury code | Training impact | Nutrition impact |
|---|---|---|
| hernia_lumbar | full profile 2.1 | none |
| shoulder_impingement | profile 2.3 | none |
| knee_arthritis | profile 2.4 | + omega-3 10g+ (anti-inflammatory) |
| diastasis_recti | profile 2.6 | + protein 2.0-2.4 g/kg (connective tissue) |
| hypertension | profile 2.7 | + low sodium (<2g/day), DASH diet |
| pregnancy_t1/t2/t3 | profile 2.9 | + iron 27mg, folate 600mcg, DHA 200mg, avoid raw fish/undercooked meat |
| elderly_65plus | profile 2.8 | + protein 1.2-1.6 g/kg (sarcopenia prevention), vitamin D 1000-2000 IU |
| post_partum | — | + galactagogues если кормит, iron, calcium |

Nutrition skill должен читать `intake.injuries[]` и применять соответствующие nutrition mods.

---

## 6. HTML / output coordination

### 6.1 MVP (сейчас): два отдельных HTML

```
docs/andrey.html              (training plan, уже есть)
docs/andrey_nutrition.html    (meal plan, nutrition сгенерирует)
```

Клиент получает 2 ссылки. Template из training (`training_plan_v4.html`) не меняется. Nutrition создаёт свой (`meal_plan_v1.html`).

### 6.2 Future (v2+): объединённый HTML с табами

```
docs/andrey_full.html
  ├─ Tab: Тренировки (iframe andrey.html)
  ├─ Tab: Питание (iframe andrey_nutrition.html)
  ├─ Tab: Закупки (aggregated shopping list)
  └─ Tab: Прогресс (history log + graphs — ещё дальше)
```

Не делать сейчас — сначала стабилизировать оба skill-а по отдельности.

### 6.3 Общий watermark / branding

Оба HTML используют:
- Цвета: `#B7EFFF / #575757`
- Шрифт: Nunito
- Watermark: ArishaFit
- Футер: лого + номер страницы
- Legal disclaimer блок в конце

Nutrition skill скопирует эти элементы из `training-skill/templates/training_plan_v4.html` и адаптирует для meal_plan_v1.html.

---

## 7. Failure modes + fallbacks

### 7.1 Intake не полный

```python
# Nutrition Phase 0
if not intake.get("lifestyle", {}).get("dietary_preferences"):
    # default = omnivore, no restrictions
    intake["lifestyle"]["dietary_preferences"] = {
        "vegetarian": False, "vegan": False, "gluten_free": False,
        "no_sugar": False, "no_flour": False, "lactose_free": False,
        "allergies": []
    }
    print("[WARN] dietary_preferences missing, using omnivore default")
```

### 7.2 Training plan отсутствует

```python
active_plan = get_active_training_plan(client_id)
if active_plan is None:
    print("[INFO] No active training plan, generating nutrition as nutrition-only")
    training_day_dates = set()  # пусто → все дни rest
else:
    training_day_dates = {plan_day.date for plan_day in active_plan.days}
```

### 7.3 Аллерген пропущен в generation

Self-audit **обязателен** — walk через все meal_plan_meals.recipe.ingredients[].food.allergens[] vs intake.lifestyle.dietary_preferences.allergies[]:
```python
for meal in meal_plan.meals:
    recipe = get_recipe(meal.recipe_id)
    for ing in recipe.ingredients:
        food = get_food(ing.food_id)
        forbidden = set(food.allergens) & set(client.allergies)
        if forbidden:
            raise SafetyViolation(f"Allergen {forbidden} in {recipe.name_ru}, day {meal.day}")
```

Один allergen violation = блокер всей генерации. Нельзя отдать клиенту план с аллергеном.

### 7.4 KBZHU mismatch (kcal != P*4 + F*9 + C*4)

Self-audit:
```python
for meal in meal_plan.meals:
    recipe = get_recipe(meal.recipe_id)
    calc_kcal = recipe.total_protein_g * 4 + recipe.total_carb_g * 4 + recipe.total_fat_g * 9
    if abs(calc_kcal - recipe.total_kcal) / recipe.total_kcal > 0.05:
        warn(f"Recipe {recipe.id} kcal={recipe.total_kcal} but formula={calc_kcal:.0f}")
```

5% tolerance. Если больше — в DB ошибка, править вручную.

---

## 8. Migration / versioning

### 8.1 Schema versions

- `client_intake_schema` v1.0.0 → существующий (training-only compatible)
- `client_intake_schema` v1.1.0 → nutrition расширения (добавит `preferences.nutrition`)
- `plan_schema` v1 (training JSON) → stable
- `meal_plan_schema` v1 → nutrition создаст

Backward compat: новая версия должна читать старые intake без nutrition полей, используя defaults.

### 8.2 DB migrations

```
db/init/001_training_schema.sql    (уже есть через миграции 001 core)
db/init/002_nutrition_schema.sql   (nutrition-сессия создаст)
db/init/003_integration_fks.sql    (в ту же сессию — добавит FK meal_plans.training_plan_id, meal_plan_days.training_day_ref)
```

Не скатывать всё в один SQL файл — migration должна быть инкрементальной.

### 8.3 Сессии разработки

Рекомендованный порядок:
1. **Session N (текущая)** — nutrition Priority 1+2 (DB schema + USDA/CKBN import)
2. **Session N+1** — nutrition Priority 3+4 (SKILL.md + seed recipes)
3. **Session N+2** — nutrition Priority 5+6 (Andrey example + HTML render) + **integration QA**
4. **Session N+3** — combined client test: generate training + nutrition для нового клиента end-to-end, fix bugs

---

## 9. Чек-лист интеграции (для nutrition-сессии)

В nutrition-skill/SKILL.md **явно документировать** следующее:

- [ ] Phase 0.2: «read active training plan from `plans` table»
- [ ] Phase 0.3: «build `date → training_day_id` mapping»
- [ ] Phase 1: формула macro shift training vs rest
- [ ] Phase 2: training day meals включают pre_workout + post_workout slots
- [ ] Phase 3 self-audit: training day kcal > rest day kcal
- [ ] Phase 3 self-audit: 100% allergen compliance
- [ ] Phase 3 self-audit: kcal ≈ P*4 + F*9 + C*4 ±5%
- [ ] Phase 3 self-audit: variety (recipe repeats < 3×/28 days)
- [ ] Phase 4: migrate_meal_plan_to_db.py пишет `training_plan_id` в `meal_plans`
- [ ] Phase 4: каждый `meal_plan_days.training_day_ref` либо указывает на `days.id`, либо NULL

В training-skill/SKILL.md **не менять** — training не зависит от nutrition.

---

## 10. Merge sequence после nutrition готов

Когда оба skill стабильны, в training-skill/SKILL.md добавить короткую секцию:

```markdown
# PART 6. Integration with Nutrition Skill

Training plan — primary, nutrition — secondary и зависит от training.
См. `nutrition-skill/SKILL.md` для генерации meal plan.
Связь: `meal_plans.training_plan_id → plans.id`,
`meal_plan_days.training_day_ref → days.id`.

Порядок: training first, nutrition second. См.
`docs/skill_integration_design.md`.
```

Одна страница, минимум ссылок — training не должен знать как именно nutrition работает.

---

## 11. Ключевые файлы для nutrition-сессии (reference)

- `training-skill/SKILL.md` — структура skill (Parts, frontmatter, hard rules) — **копировать стиль**
- `training-skill/templates/client_intake_schema.json` — intake контракт — **не менять структуру, только расширять preferences.nutrition**
- `training-skill/templates/example_andrey_intake.json` — целевой клиент для первого example
- `db/models.py` — SQLAlchemy модели — **добавить новые, не менять существующие**
- `db/session.py` — session factory — **использовать как есть**
- `scripts/migrate_json_to_db.py` — паттерн migration — **скопировать и адаптировать для meal plan**
- `scripts/fill_template.py` — HTML render — **паттерн для fill_meal_template.py**
- `training-skill/assets/info_boxes.json` — info_boxes — **расширить или параллельный файл**
- `docs/nutrition_skill_next_session_prompt.md` — план сессий для nutrition

---

## 12. Открытые вопросы (decide перед start)

1. **Рецепты с картинками** — где брать? USDA не содержит, OpenFoodFacts спорно. Варианты:
   - DALL-E генерировать (дорого, не всегда адекватно)
   - Ссылки на источники рецептов (Povarenok.ru, AllRecipes, etc.)
   - Клиенту без картинок (MVP) — только описание + источник
   - **Рекомендация для MVP:** без картинок, только `recipe_url` на оригинал

2. **Мультиязычный meal plan?** — На данный момент только RU. EN оставить на потом.

3. **Nutrition plan длина** — 28 дней стандарт. 14 дней опция для новых клиентов?
   - **Рекомендация:** 28 дней всегда (4 недели × 7), совпадает с training mesocycle

4. **Автоматический regen при weight change?** — Если клиент теряет 5kg, macros должны пересчитаться. Триггер?
   - **Рекомендация:** manual trigger на данном этапе (клиент звонит тренеру), позже автомат

5. **Приватность данных о еде?** — `meal_plans` содержит medical-sensitive data (diseases через DB). Retention policy?
   - **Рекомендация:** следовать той же политике что и training plans (152-ФЗ compliance, уже встроено)

---

**Last updated:** 2026-04-23 по результатам сессии с commits 05935cf → e446e7e.
**Next review:** после завершения nutrition Priority 1+2 в параллельной сессии.
