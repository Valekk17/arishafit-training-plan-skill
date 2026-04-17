# Инструкция для Claude Code
# ================================
# Скопируй весь этот файл и вставь в Claude Code как промт.
# Или запусти: cat PROMPT.md | claude
# ================================

## Задача

Сгенерировать премиальный PDF-документ — персональный план тренировок и питания.

## Что нужно сделать

### 1. Установить зависимости
```bash
pip install weasyprint requests Pillow
# Если WeasyPrint не ставится, альтернатива:
# npm install puppeteer
```

### 2. Скачать картинки упражнений

Скачай по одной качественной картинке для каждого упражнения из списка ниже. 
Источники (в порядке приоритета):
- simplyfitness.com (лучшее качество, SVG-иллюстрации)
- musclewiki.com
- WorkoutLabs 
- Unsplash (фото)

Список упражнений и ссылок на simplyfitness:

```
incline_dumbbell_press    https://www.simplyfitness.com/pages/incline-dumbbell-bench-press
pec_deck                  https://www.simplyfitness.com/pages/peck-deck
chest_press_machine       https://www.simplyfitness.com/pages/chest-press-machine
cable_rope_pushdown       https://www.simplyfitness.com/pages/cable-rope-puschdown
parallel_dips             https://www.simplyfitness.com/pages/parallel-dip-bar
plank                     https://www.simplyfitness.com/pages/plank
barbell_bench_press       https://www.simplyfitness.com/pages/barbell-bench-press
cable_crossover           https://www.simplyfitness.com/pages/cable-crossover
overhead_triceps          https://www.simplyfitness.com/pages/dumbbell-overhead-triceps-extension
push_ups                  https://www.simplyfitness.com/pages/push-ups
leg_press                 https://www.simplyfitness.com/pages/leg-press
leg_extension             https://www.simplyfitness.com/pages/leg-extension
lying_leg_curl            https://www.simplyfitness.com/pages/lying-leg-curl
bulgarian_split_squat     https://www.simplyfitness.com/pages/bodyweight-bulgarian-split-squat
standing_calf_raise       https://www.simplyfitness.com/pages/standing-calf-raise
hip_thrust                https://www.simplyfitness.com/pages/barbell-hip-thrust
hack_squat                https://www.simplyfitness.com/pages/hack-squat
lunge                     https://www.simplyfitness.com/pages/lunge
seated_leg_curl           https://www.simplyfitness.com/pages/seated-leg-curl
seated_calf_raise         https://www.simplyfitness.com/pages/seated-calf-raise
dumbbell_shoulder_press   https://www.simplyfitness.com/pages/dumbbell-shoulder-press
dumbbell_lateral_raise    https://www.simplyfitness.com/pages/dumbbell-lateral-raise
dumbbell_front_raise      https://www.simplyfitness.com/pages/dumbbell-front-raise
incline_dumbbell_curl     https://www.simplyfitness.com/pages/incline-dumbbell-curl
hammer_curl               https://www.simplyfitness.com/pages/hammer-curl
smith_shoulder_press      https://www.simplyfitness.com/pages/smith-machine-shoulder-press
cable_lateral_raise       https://www.simplyfitness.com/pages/cable-one-arm-lateral-raise
rear_delt_fly             https://www.simplyfitness.com/pages/high-cable-rear-delt-fly
cable_curl                https://www.simplyfitness.com/pages/straight-bar-low-pulley-cable-curl
concentration_curl        https://www.simplyfitness.com/pages/dumbbell-concentration-curl
incline_barbell_press     https://www.simplyfitness.com/pages/incline-barbell-bench-press
dumbbell_fly              https://www.simplyfitness.com/pages/dumbbell-fly
triceps_pressdown         https://www.simplyfitness.com/pages/triceps-pressdown
ez_barbell_curl           https://www.simplyfitness.com/pages/ez-barbell-curl
dumbbell_bench_press      https://www.simplyfitness.com/pages/dumbbell-bench-press
bent_over_lateral_raise   https://www.simplyfitness.com/pages/bent-over-lateral-raise
preacher_curl             https://www.simplyfitness.com/pages/ez-barbell-preacher-curl
```

Зайди на каждую страницу, найди картинку упражнения (обычно это SVG или PNG иллюстрация), скачай в папку `images/`.

### 3. Сгенерировать PDF

Возьми файл `plan_andrey.html` (приложен ниже или используй из этого же каталога) и:

1. Замени все ссылки «📸 Как делать →» на встроенные картинки `<img>` из папки `images/`
2. Каждое упражнение должно выглядеть как карточка: слева картинка ~120x90px, справа описание
3. Адаптируй CSS под печать (белый фон, тёмный текст, @media print)
4. Конвертируй в PDF через WeasyPrint или Puppeteer
5. Проверь что текст не обрезается, все слова влезают

Если не получается скачать картинки с simplyfitness — используй:
- musclewiki.com/exercises 
- wger.de (open source, Apache 2.0 лицензия)
- или нарисуй качественные SVG-иллюстрации сам (минималистичный стиль, чёрные контуры на белом фоне)

### 4. Требования к качеству PDF

- A4 формат
- Шрифт с поддержкой кириллицы (Roboto, PT Sans, Noto Sans)
- Каждое упражнение — карточка с картинкой
- Описание простым языком без терминов
- Для каждого упражнения указаны: подходы × повторения, отдых, на что обращать внимание
- Текст полностью читаем, ничего не обрезано
- Цветовое кодирование: оранжевый = тренировки, бирюзовый = питание
- Красные пометки для предупреждений (грыжа, ограничения)

## Данные клиента

```
Имя: Андрей
Возраст: 36 лет
Рост: 176 см
Вес: 100-104 кг
Грыжа L4-L5 (одна удалена, одна осталась)
Ограничение: ТЯНУТЬ НЕЛЬЗЯ, ТОЛКАТЬ МОЖНО
Цель: рекомпозиция (убрать жир, нарастить мышцы)
График: 3-4 дня/нед, частые командировки
Место: тренажёрный зал
Не ест: хлеб, мучное, сахар
Добавки: витамины, BCAA, изолят, иногда протеин
Пожелания: не повторять упражнения чтобы не надоело
```

## Структура PDF (8-10 страниц)

### Стр. 1 — Обложка
Имя, параметры, цель, ограничения, предупреждение про грыжу

### Стр. 2-3 — Блок 1 (Недели 1-2): День 1 — Грудь + Трицепс + Пресс
Два варианта (A и B), чередуются понедельно:

**Вариант A:**
1. Жим гантелей на наклонной (30°) — 4×10, отдых 90с
   Описание: Ложишься на скамью с наклоном ~30 градусов. Берёшь гантели, выжимаешь вверх от груди. Лопатки сведены, поясница прижата к скамье.
2. Сведение в Pec Deck — 3×12, отдых 60с
   Описание: Садишься в тренажёр, спина прижата. Сводишь руки перед собой. Задержка 1 сек в крайней точке.
3. Жим от груди в тренажёре сидя — 3×12, отдых 60с
4. Разгибания на блоке (канат) — 3×15, отдых 45с
5. Отжимания на брусьях — 3×8-12, отдых 60с (⚠️ если болит спина — замени на жим в тренажёре)
6. Планка на локтях — 3×30-40с (⚠️ поясница нейтральная!)

**Вариант B:**
1. Жим штанги лёжа — 4×8, отдых 2 мин
2. Жим гантелей наклонная 45° — 3×10, отдых 90с
3. Кроссовер верхние блоки — 3×15, отдых 45с
4. Французский жим гантелью 1 рукой — 3×12/рука, 45с
5. Отжимания от пола (ноги на лавке) — 3× до отказа
6. Скручивания на фитболе — 3×15

### Стр. 4 — День 2 — Ноги + Икры
**Вариант A:**
1. Жим ногами (ступни высоко, спина прижата!) — 4×12, 90с
2. Разгибание ног сидя — 3×15, 45с
3. Сгибание ног лёжа — 3×12, 60с
4. Болгарские выпады с гантелями — 3×10/нога, 60с
5. Подъём на носки стоя — 4×15, 45с
6. Ягодичный мостик со штангой — 3×12

**Вариант B:**
1. Гакк-приседания — 4×10, 90с
2. Выпады назад с гантелями — 3×10/нога, 60с
3. Сгибание ног сидя — 3×12, 60с
4. Разгибание одной ногой — 3×12/нога, 45с
5. Подъём на носки сидя — 4×20, 30с

### Стр. 5 — День 3 — Плечи + Бицепс + Пресс
**Вариант A:**
1. Жим гантелей сидя (спина прижата к спинке!) — 4×10, 90с
2. Разводка в стороны — 3×15, 45с
3. Подъём гантелей перед собой — 3×12/рука, 45с
4. Бицепс сидя на наклонной — 3×12, 60с
5. Молотковые сгибания — 3×12, 45с
6. Dead Bug — 3×10/сторона (⚠️ поясница прижата к полу!)

**Вариант B:**
1. Жим в тренажёре на плечи — 4×12, 60с
2. Разводка в кроссовере (нижний блок) — 3×15, 45с
3. Обратные разводки (задняя дельта) — 3×15, 45с
4. Бицепс на блоке — 3×12, 60с
5. Концентрированный подъём — 3×10/рука, 45с
6. Боковая планка — 3×20с/сторона

### Стр. 5 — День 4 (опционально) — Кардио + Кор
Нед 1: Эллиптик 30 мин + планка + Bird Dog + скручивания на блоке
Нед 2: Велотренажёр 25 мин интервалы + Dead Bug + вакуум

### Стр. 6-7 — Блок 2 (Недели 3-4)
День 1 — Верх жимовой: жим штанги наклонная 4×8, жим Арнольда 3×10, брусья с весом 3×8, разводка лёжа 3×12, разгибание блок 3×15, бицепс EZ 3×10
День 2 — Ноги силовой: жим ногами узкая 4×8, широкая 3×12, разгибание дроп-сет 3×15, носки 5×12
День 3 — Верх объёмный: жим гантелей гориз 4×12, кроссовер нижние 3×15, Хаммер плечи 3×12, задняя дельта 3×15, суперсет бицепс+трицепс 3×12+12
День 4 — Кардио: дорожка с наклоном 30 мин + растяжка 10 мин

### Стр. 8 — Прогрессия + что делать если пропустил
Таблица прогрессии (недели 1-2 / 3-4 / 5+)
Пропустил 1 день / 1 неделю / 2+ недели — инструкции

### Стр. 9 — Питание
КБЖУ: 2500 ккал трен / 2200 отдых. Б:200, Ж:80, У:230/170
Идеальный день: 6 приёмов с описанием
Замены: завтраки / обеды / ужины — по 3 варианта
Аварийный план: фастфуд / магазин / столовая

### Стр. 10 — Закупка + Добавки
Таблица продуктов на неделю (белок/углеводы/жиры/овощи)
Таблица добавок (изолят, BCAA, витамины, ДОБАВИТЬ: омега-3 2-3г/день, магний 400мг/ночь, опционально креатин 5г/день)

## Финальная проверка

После генерации PDF, открой его и проверь:
1. Все слова читаемы, ничего не обрезано
2. Картинки на месте и видны
3. Таблицы не выходят за границы страницы
4. Кириллица отображается корректно
5. Цвета и стили выглядят премиально
