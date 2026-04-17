# ArishaFit — Архитектура веб-приложения

## Обзор

Веб-приложение для создания персонализированных фитнес-планов (тренировки + питание).
Два модуля работают ОТДЕЛЬНО — клиент может купить один или оба.

---

## СТЕК ТЕХНОЛОГИЙ

```
Frontend:  Next.js 14 (App Router) + TypeScript + Tailwind CSS
Backend:   Next.js API Routes (serverless)
БД:        SQLite (Prisma ORM) — локально, без сервера
Картинки:  Free Exercise DB (public domain, 870+ упражнений)
PDF:       Puppeteer (как уже работает для Андрея)
Деплой:    Vercel (бесплатный план) или локально
```

### Почему этот стек:
- **Next.js** — один проект = и фронт и бэк, без настройки серверов
- **SQLite** — не нужен отдельный сервер БД, файл рядом с проектом
- **Prisma** — типизированная работа с БД, миграции
- **Tailwind** — быстрая стилизация, тёмная тема бесплатно

---

## СТРУКТУРА ПРОЕКТА

```
arishafit/
├── prisma/
│   └── schema.prisma          # Схема БД
│   └── seed.ts                # Загрузка начальных данных
│
├── src/
│   ├── app/                   # Next.js App Router
│   │   ├── page.tsx           # Главная (лендинг или дашборд)
│   │   │
│   │   ├── trainer/           # 👩‍💼 ПАНЕЛЬ ТРЕНЕРА
│   │   │   ├── clients/       # Список клиентов
│   │   │   │   ├── page.tsx          # Список всех клиентов
│   │   │   │   ├── new/page.tsx      # Новая анкета клиента
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx      # Карточка клиента
│   │   │   │       ├── training/     # Генератор тренировок
│   │   │   │       └── nutrition/    # Генератор питания
│   │   │   │
│   │   │   ├── exercises/     # База упражнений
│   │   │   │   ├── page.tsx          # Каталог с фильтрами
│   │   │   │   └── [id]/page.tsx     # Карточка упражнения
│   │   │   │
│   │   │   └── meals/         # База блюд
│   │   │       ├── page.tsx          # Каталог блюд
│   │   │       └── [id]/page.tsx     # Карточка блюда
│   │   │
│   │   └── api/               # API Routes
│   │       ├── clients/
│   │       ├── exercises/
│   │       ├── meals/
│   │       ├── training/generate/
│   │       ├── nutrition/generate/
│   │       └── export/pdf/
│   │
│   ├── components/            # React компоненты
│   │   ├── ui/                # Базовые UI (кнопки, карточки, чекбоксы)
│   │   ├── forms/             # Формы (анкета, фильтры)
│   │   ├── training/          # Компоненты тренировок
│   │   ├── nutrition/         # Компоненты питания
│   │   └── export/            # Компоненты экспорта/превью
│   │
│   ├── lib/                   # Бизнес-логика
│   │   ├── db.ts              # Prisma client
│   │   ├── calculators/
│   │   │   ├── bmr.ts         # BMR по Mifflin-St Jeor
│   │   │   ├── tdee.ts        # TDEE = BMR × активность
│   │   │   └── macros.ts      # КБЖУ: белок, жиры, углеводы
│   │   │
│   │   ├── generators/
│   │   │   ├── training.ts    # Генератор тренировочного плана
│   │   │   ├── nutrition.ts   # Генератор плана питания
│   │   │   ├── shopping.ts    # Генератор списка закупок
│   │   │   └── mesocycle.ts   # Логика мезоцикла (4 нед + деload)
│   │   │
│   │   ├── filters/
│   │   │   ├── safety.ts      # Фильтр по травмам/ограничениям
│   │   │   └── equipment.ts   # Фильтр по оборудованию
│   │   │
│   │   └── validators/
│   │       ├── macros.ts      # Валидация КБЖУ ±10%
│   │       └── meals.ts       # Валидация блюд (правила из memory)
│   │
│   └── data/                  # Статические данные
│       ├── exercises.json     # Скачанная база Free Exercise DB
│       └── meals.json         # Наша база блюд
│
├── public/
│   └── exercises/             # Картинки упражнений (JPG)
│
└── templates/
    └── pdf/                   # HTML-шаблоны для PDF экспорта
        ├── training.html      # Шаблон плана тренировок
        ├── nutrition.html     # Шаблон плана питания
        └── combined.html      # Комбо-шаблон
```

---

## СХЕМА БАЗЫ ДАННЫХ

```prisma
// prisma/schema.prisma

// ===== КЛИЕНТЫ =====

model Client {
  id            Int       @id @default(autoincrement())
  name          String
  age           Int
  height        Int       // см
  weight        Float     // кг
  gender        Gender
  goal          Goal
  frequency     Int       // тренировок в неделю (3-4)
  place         Place     // зал/дом
  experience    Experience

  // Травмы и ограничения
  injuries      ClientInjury[]

  // Оборудование (что есть у клиента)
  equipment     ClientEquipment[]

  // Питание
  allergies     String?       // аллергии (текст)
  excludedFoods String?       // исключённые продукты
  supplements   String?       // добавки

  // Рассчитанные параметры
  bmr           Float?
  tdee          Float?
  targetKcalTrain  Float?    // ккал в тренировочный день
  targetKcalRest   Float?    // ккал в день отдыха
  targetProtein    Float?    // г белка
  targetFat        Float?    // г жиров
  targetCarbsTrain Float?    // г углеводов (трен)
  targetCarbsRest  Float?    // г углеводов (отдых)

  // Связи
  trainingPlans TrainingPlan[]
  nutritionPlans NutritionPlan[]

  notes         String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
}

enum Gender { MALE FEMALE }
enum Goal { WEIGHT_LOSS RECOMPOSITION MUSCLE_GAIN MAINTENANCE }
enum Place { GYM HOME MIXED }
enum Experience { BEGINNER INTERMEDIATE ADVANCED }

// ===== ТРАВМЫ =====

model Injury {
  id          Int       @id @default(autoincrement())
  name        String    // "Грыжа L4-L5", "Травма колена"
  nameEn      String    // "Herniated disc L4-L5"
  bodyPart    String    // "spine", "knee", "shoulder"

  // Какие паттерны движений запрещены
  bannedPatterns  InjuryBannedPattern[]

  clients     ClientInjury[]
}

model InjuryBannedPattern {
  id         Int     @id @default(autoincrement())
  injuryId   Int
  injury     Injury  @relation(fields: [injuryId], references: [id])
  pattern    String  // "axial_load", "back_flexion", "pull", "rotation_under_load"
  reason     String  // "Осевая нагрузка на позвоночник"
}

model ClientInjury {
  id        Int     @id @default(autoincrement())
  clientId  Int
  client    Client  @relation(fields: [clientId], references: [id])
  injuryId  Int
  injury    Injury  @relation(fields: [injuryId], references: [id])
  severity  Int     @default(1) // 1-3: лёгкая, средняя, серьёзная
  notes     String?
}

// ===== ОБОРУДОВАНИЕ =====

model Equipment {
  id       Int      @id @default(autoincrement())
  name     String   // "Штанга", "Гантели"
  nameEn   String   // "Barbell", "Dumbbell"
  slug     String   @unique // "barbell", "dumbbell"
  icon     String?  // эмодзи или иконка

  exercises ExerciseEquipment[]
  clients   ClientEquipment[]
}

model ClientEquipment {
  id          Int       @id @default(autoincrement())
  clientId    Int
  client      Client    @relation(fields: [clientId], references: [id])
  equipmentId Int
  equipment   Equipment @relation(fields: [equipmentId], references: [id])
}

// ===== УПРАЖНЕНИЯ =====

model Exercise {
  id              Int      @id @default(autoincrement())
  name            String   // "Жим гантелей на наклонной скамье"
  nameEn          String   // "Incline Dumbbell Press"
  slug            String   @unique
  sourceId        String?  // ID из Free Exercise DB

  // Классификация
  category        ExCategory  // STRENGTH, STRETCHING, CARDIO...
  force           Force?      // PUSH, PULL, STATIC
  mechanic        Mechanic?   // COMPOUND, ISOLATION
  level           Level       // BEGINNER, INTERMEDIATE, EXPERT

  // Мышцы
  primaryMuscles  ExerciseMuscle[]
  secondaryMuscles ExerciseMuscle[]

  // Оборудование
  equipment       ExerciseEquipment[]

  // Безопасность — какие паттерны движения задействованы
  movementPatterns String[] // ["axial_load", "back_flexion", "pull"]
  // Если у клиента травма с banned pattern = это упражнение отфильтруется

  // Контент
  instructions    String[]  // пошаговая техника
  warnings        String[]  // ⚠️ предупреждения
  tips            String[]  // советы по технике

  // Картинки
  imageStart      String?   // путь к фото начальной позиции
  imageEnd        String?   // путь к фото конечной позиции

  // Альтернативы
  alternatives    ExerciseAlternative[] @relation("main")
  alternativeOf   ExerciseAlternative[] @relation("alt")

  // Использование в планах
  planExercises   PlanExercise[]

  createdAt       DateTime @default(now())
}

enum ExCategory { STRENGTH STRETCHING CARDIO PLYOMETRICS POWERLIFTING STRONGMAN CORE WARMUP }
enum Force { PUSH PULL STATIC }
enum Mechanic { COMPOUND ISOLATION }
enum Level { BEGINNER INTERMEDIATE EXPERT }

model ExerciseMuscle {
  id         Int      @id @default(autoincrement())
  exerciseId Int
  exercise   Exercise @relation(fields: [exerciseId], references: [id])
  muscle     String   // "chest", "quadriceps", "abdominals"
  isPrimary  Boolean  @default(true)
}

model ExerciseEquipment {
  id          Int       @id @default(autoincrement())
  exerciseId  Int
  exercise    Exercise  @relation(fields: [exerciseId], references: [id])
  equipmentId Int
  equipment   Equipment @relation(fields: [equipmentId], references: [id])
}

model ExerciseAlternative {
  id            Int      @id @default(autoincrement())
  exerciseId    Int
  exercise      Exercise @relation("main", fields: [exerciseId], references: [id])
  alternativeId Int
  alternative   Exercise @relation("alt", fields: [alternativeId], references: [id])
}

// ===== ПЛАН ТРЕНИРОВОК =====

model TrainingPlan {
  id        Int      @id @default(autoincrement())
  clientId  Int
  client    Client   @relation(fields: [clientId], references: [id])

  weeks     Int      @default(4)  // кол-во недель
  hasDeload Boolean  @default(true)

  days      TrainingDay[]

  status    PlanStatus @default(DRAFT)
  createdAt DateTime   @default(now())
  updatedAt DateTime   @updatedAt
}

model TrainingDay {
  id        Int           @id @default(autoincrement())
  planId    Int
  plan      TrainingPlan  @relation(fields: [planId], references: [id])

  week      Int           // неделя (1-5)
  day       Int           // день (1-4)
  type      DayType       // UPPER, LOWER, CARDIO_CORE, FULL_BODY
  title     String        // "Верх тела — жимовые"

  warmup    String?       // описание разминки
  cooldown  String?       // описание заминки

  exercises PlanExercise[]
}

enum DayType { UPPER LOWER CARDIO_CORE FULL_BODY REST }
enum PlanStatus { DRAFT REVIEW APPROVED EXPORTED }

model PlanExercise {
  id           Int          @id @default(autoincrement())
  dayId        Int
  day          TrainingDay  @relation(fields: [dayId], references: [id])
  exerciseId   Int
  exercise     Exercise     @relation(fields: [exerciseId], references: [id])

  order        Int          // порядок в дне
  sets         Int          // подходы
  reps         String       // "10-12" или "30 сек"
  rest         String       // "60-90 сек"
  rpe          Float?       // RPE 6-8
  weight       String?      // "60-70% от макс" или "начать с 20кг"
  notes        String?      // доп. заметки
}

// ===== БЛЮДА И ПИТАНИЕ =====

model Meal {
  id            Int      @id @default(autoincrement())
  name          String   // "Шакшука с овощами"
  category      MealCategory // BREAKFAST, LUNCH, DINNER...
  cookingTime   Int?     // минут
  recipeUrl     String?  // ссылка на рецепт

  // КБЖУ на порцию
  calories      Float
  protein       Float
  fat           Float
  carbs         Float

  // Ингредиенты
  ingredients   MealIngredient[]

  // Инструкция
  instructions  String[] // пошаговая готовка (краткая)

  // Метаданные
  tags          String[] // ["высокобелковый", "быстрый", "без глютена"]
  proteinSource String?  // "chicken", "fish", "eggs", "cottage_cheese"
  carbSource    String?  // "buckwheat", "rice", "oatmeal", "bulgur"

  // Использование в планах
  planMeals     PlanMeal[]

  createdAt     DateTime @default(now())
}

enum MealCategory {
  BREAKFAST
  SNACK_1       // перекус утренний
  LUNCH
  PRE_WORKOUT   // до тренировки
  POST_WORKOUT  // после тренировки
  SNACK_2       // полдник
  DINNER
  BEFORE_BED    // перед сном (казеин/творог)
}

model MealIngredient {
  id         Int    @id @default(autoincrement())
  mealId     Int
  meal       Meal   @relation(fields: [mealId], references: [id])
  name       String // "Куриная грудка"
  amount     Float  // 150
  unit       String // "г", "мл", "шт", "ч.л."
  calories   Float  // КБЖУ этого ингредиента
  protein    Float
  fat        Float
  carbs      Float
  category   IngredientCategory // для списка закупок
}

enum IngredientCategory {
  PROTEIN     // мясо, рыба, яйца, творог
  CARBS       // крупы, овощи крахмалистые
  FATS        // масла, орехи, авокадо
  VEGETABLES  // овощи и зелень
  DAIRY       // молочка
  OTHER       // специи, приправы
}

// ===== ПЛАН ПИТАНИЯ =====

model NutritionPlan {
  id        Int      @id @default(autoincrement())
  clientId  Int
  client    Client   @relation(fields: [clientId], references: [id])

  weeks     Int      @default(4)
  days      NutritionDay[]

  // Списки закупок
  shoppingLists ShoppingList[]

  status    PlanStatus @default(DRAFT)
  createdAt DateTime   @default(now())
  updatedAt DateTime   @updatedAt
}

model NutritionDay {
  id         Int            @id @default(autoincrement())
  planId     Int
  plan       NutritionPlan  @relation(fields: [planId], references: [id])

  week       Int            // неделя (1-4)
  dayNumber  Int            // день (1-7)
  isTraining Boolean        // тренировочный день?

  meals      PlanMeal[]

  // Итого за день (рассчитывается)
  totalCalories  Float?
  totalProtein   Float?
  totalFat       Float?
  totalCarbs     Float?
}

model PlanMeal {
  id         Int           @id @default(autoincrement())
  dayId      Int
  day        NutritionDay  @relation(fields: [dayId], references: [id])
  mealId     Int
  meal       Meal          @relation(fields: [mealId], references: [id])

  timing     MealCategory  // когда есть
  order      Int           // порядок
  portion    Float         @default(1.0) // множитель порции

  // Альтернатива
  altMealId  Int?          // ID альтернативного блюда
}

// ===== ЗАКУПКИ =====

model ShoppingList {
  id      Int            @id @default(autoincrement())
  planId  Int
  plan    NutritionPlan  @relation(fields: [planId], references: [id])
  week    Int            // неделя

  items   ShoppingItem[]
}

model ShoppingItem {
  id         Int           @id @default(autoincrement())
  listId     Int
  list       ShoppingList  @relation(fields: [listId], references: [id])
  name       String        // "Куриная грудка"
  amount     Float         // 2.5
  unit       String        // "кг"
  category   IngredientCategory
}
```

---

## ПОТОКИ ДАННЫХ

### Поток 1: Создание клиента

```
[Анкета клиента] → Форма в браузере
                  → POST /api/clients
                  → Автоматический расчёт:
                    - BMR = 10×вес + 6.25×рост − 5×возраст + 5 (муж)
                    - TDEE = BMR × 1.55 (3-4 тренировки)
                    - Тренировочный: TDEE - 500
                    - Отдых: TDEE - 800
                    - Белок: 2г × вес
                    - Жиры: 0.8г × вес
                    - Углеводы: остаток
                  → Сохранение в БД
                  → Redirect → Карточка клиента
```

### Поток 2: Генерация плана тренировок

```
Карточка клиента → Кнопка "Создать план тренировок"
                 → Система читает:
                   1. Травмы клиента → banned patterns
                   2. Оборудование клиента → доступные упражнения
                   3. Цель и частоту → структура сплита
                 → Автоматический подбор:
                   1. Фильтр: убрать ВСЕ упражнения с banned patterns
                   2. Фильтр: оставить только с доступным оборудованием
                   3. Подбор по группам мышц (верх/низ/кор)
                   4. Прогрессия по неделям (RPE, веса)
                   5. Деload неделя 5
                 → Превью в браузере (с картинками!)
                 → Тренер может:
                   - Заменить упражнение (выбор из отфильтрованных)
                   - Изменить подходы/повторы
                   - Добавить/убрать упражнения
                   - Добавить заметки
                 → Кнопка "Утвердить" → статус APPROVED
                 → Кнопка "Экспорт PDF"
```

### Поток 3: Генерация плана питания

```
Карточка клиента → Кнопка "Создать план питания"
                 → Система читает:
                   1. КБЖУ цели (уже рассчитаны)
                   2. Исключённые продукты
                   3. Аллергии
                   4. Тренировочные/нетренировочные дни (из плана тренировок)
                 → Автоматическая генерация 28 дней:
                   Для каждого дня:
                   1. Определить тип дня (тренировка/отдых)
                   2. Установить целевые КБЖУ
                   3. Подобрать 6 приёмов пищи из базы блюд:
                      - Ротация белков по неделям (курица→рыба→говядина→индейка)
                      - Ротация гарниров (гречка→рис→булгур→киноа)
                      - Ротация способов готовки
                   4. Проверить сумму КБЖУ ±10% от цели
                   5. Если не сходится → скорректировать граммовку
                   6. Для каждого блюда → 1-2 альтернативы
                 → Превью в браузере
                 → Тренер может:
                   - Заменить блюдо
                   - Скорректировать граммовку
                   - Проверить КБЖУ (показывается в реальном времени)
                 → Автогенерация списков закупок (по неделям)
                 → Кнопка "Утвердить" → "Экспорт PDF"
```

### Поток 4: Экспорт в PDF

```
Утверждённый план → Кнопка "Экспорт"
                  → Выбор: Тренировки / Питание / Комбо
                  → Рендер HTML по шаблону:
                    - Дизайн ArishaFit (голубой фон, Nunito, водяной знак)
                    - Картинки упражнений inline (base64)
                    - Юридические дисклеймеры (ФЗ-323, ФЗ-152, ФЗ-2300-1)
                    - Футер с лого
                  → Puppeteer → PDF
                  → Скачивание / отправка клиенту
```

---

## АЛГОРИТМ ФИЛЬТРАЦИИ УПРАЖНЕНИЙ (КЛЮЧЕВОЙ)

```typescript
// lib/filters/safety.ts

function filterExercises(
  allExercises: Exercise[],
  clientInjuries: Injury[],
  clientEquipment: Equipment[]
): Exercise[] {

  // 1. Собрать все banned patterns из травм клиента
  const bannedPatterns = clientInjuries
    .flatMap(injury => injury.bannedPatterns)
    .map(bp => bp.pattern);
  // Пример для грыжи L4-L5: ["axial_load", "back_flexion", "pull", "rotation_under_load"]

  // 2. Собрать slugs оборудования клиента
  const availableEquipment = clientEquipment.map(e => e.slug);
  // Пример: ["barbell", "dumbbell", "cable", "machine", "bench", "body_only"]

  // 3. Фильтрация
  return allExercises.filter(exercise => {
    // Проверка безопасности: ни один паттерн упражнения не в banned
    const isSafe = !exercise.movementPatterns
      .some(pattern => bannedPatterns.includes(pattern));

    // Проверка оборудования: хотя бы одно оборудование доступно
    const hasEquipment = exercise.equipment
      .some(eq => availableEquipment.includes(eq.slug));

    return isSafe && hasEquipment;
  });
}
```

### Паттерны движений (movement patterns)

| Паттерн | Описание | Пример упражнений |
|---------|----------|-------------------|
| `axial_load` | Осевая нагрузка на позвоночник | Приседания со штангой, жим стоя |
| `back_flexion` | Сгибание поясницы под весом | Становая тяга, наклоны |
| `back_extension` | Разгибание поясницы под весом | Гиперэкстензия с весом |
| `rotation_under_load` | Ротация корпуса под нагрузкой | Русские скручивания с весом |
| `pull_vertical` | Вертикальная тяга | Подтягивания, тяга верхнего блока |
| `pull_horizontal` | Горизонтальная тяга | Тяга гантели в наклоне |
| `push_vertical` | Вертикальный жим | Жим гантелей сидя |
| `push_horizontal` | Горизонтальный жим | Жим лёжа |
| `hip_hinge` | Сгибание в тазобедренном | Румынская тяга |
| `squat` | Приседание | Приседания в тренажёре |
| `lunge` | Выпады | Болгарские сплит-приседы |
| `knee_flexion` | Сгибание колена | Сгибания ног |
| `overhead` | Руки над головой | Жим над головой |
| `impact` | Ударная нагрузка | Прыжки, бег |

---

## ТИПИЧНЫЕ КОНФИГУРАЦИИ ТРАВМ

### Грыжа L4-L5 (Андрей)
```json
{
  "name": "Грыжа L4-L5",
  "bannedPatterns": [
    "axial_load",
    "back_flexion",
    "back_extension",
    "rotation_under_load",
    "pull_vertical",
    "pull_horizontal",
    "hip_hinge"
  ]
}
```
**Результат:** остаются только жимы, изоляция, тренажёры с опорой спины, кор (планка, Dead Bug).

### Травма колена
```json
{
  "name": "Травма колена",
  "bannedPatterns": [
    "squat",
    "lunge",
    "impact",
    "knee_flexion"
  ]
}
```

### Травма плеча
```json
{
  "name": "Травма плеча",
  "bannedPatterns": [
    "overhead",
    "push_vertical",
    "pull_vertical"
  ]
}
```

---

## ОБОРУДОВАНИЕ (полный список для галочек)

```typescript
const EQUIPMENT_LIST = [
  // Базовое (зал)
  { slug: "barbell", name: "Штанга", nameEn: "Barbell", icon: "🏋️" },
  { slug: "dumbbell", name: "Гантели", nameEn: "Dumbbell", icon: "💪" },
  { slug: "cable", name: "Блочный тренажёр (кроссовер)", nameEn: "Cable", icon: "🔗" },
  { slug: "machine", name: "Тренажёры (силовые)", nameEn: "Machine", icon: "⚙️" },

  // Скамьи
  { slug: "bench", name: "Скамья (горизонтальная)", nameEn: "Flat Bench", icon: "🪑" },
  { slug: "incline_bench", name: "Скамья (наклонная)", nameEn: "Incline Bench", icon: "📐" },

  // Свободные веса
  { slug: "kettlebell", name: "Гири", nameEn: "Kettlebell", icon: "🔔" },
  { slug: "medicine_ball", name: "Медбол", nameEn: "Medicine Ball", icon: "⚾" },
  { slug: "ez_bar", name: "EZ-гриф", nameEn: "EZ-Bar / SZ-Bar", icon: "〰️" },

  // Кардио
  { slug: "treadmill", name: "Беговая дорожка", nameEn: "Treadmill", icon: "🏃" },
  { slug: "elliptical", name: "Эллиптический тренажёр", nameEn: "Elliptical", icon: "🔄" },
  { slug: "stationary_bike", name: "Велотренажёр", nameEn: "Stationary Bike", icon: "🚴" },
  { slug: "rowing_machine", name: "Гребной тренажёр", nameEn: "Rowing Machine", icon: "🚣" },

  // Домашнее
  { slug: "body_only", name: "Без оборудования (вес тела)", nameEn: "Body Only", icon: "🧍" },
  { slug: "resistance_band", name: "Резинки / эспандеры", nameEn: "Resistance Band", icon: "🔴" },
  { slug: "pull_up_bar", name: "Турник", nameEn: "Pull-up Bar", icon: "⬆️" },
  { slug: "gym_mat", name: "Коврик", nameEn: "Gym Mat", icon: "🟩" },
  { slug: "foam_roller", name: "Пенный ролик", nameEn: "Foam Roller", icon: "🧻" },
  { slug: "swiss_ball", name: "Фитбол", nameEn: "Swiss Ball", icon: "🟡" },

  // Специальное
  { slug: "dip_station", name: "Брусья", nameEn: "Dip Station", icon: "⏸️" },
  { slug: "smith_machine", name: "Смит-машина", nameEn: "Smith Machine", icon: "🔲" },
  { slug: "leg_press", name: "Жим ногами (тренажёр)", nameEn: "Leg Press", icon: "🦵" },
  { slug: "lat_pulldown", name: "Верхняя тяга (тренажёр)", nameEn: "Lat Pulldown", icon: "⬇️" },
];
```

---

## ФАЗЫ РЕАЛИЗАЦИИ

### Фаза 1: Фундамент (неделя 1)
1. Инициализация Next.js проекта
2. Настройка Prisma + SQLite
3. Скачивание Free Exercise DB (870+ упражнений)
4. Скрипт обогащения: русские названия, movement patterns, предупреждения
5. Seed базы данных
6. Базовый UI: список упражнений с фильтрами

### Фаза 2: Тренировки (неделя 2)
1. Форма анкеты клиента
2. Калькулятор BMR/TDEE
3. Система травм и banned patterns
4. Алгоритм фильтрации упражнений
5. Генератор мезоцикла (4 нед + деload)
6. UI: конструктор плана тренировок

### Фаза 3: Питание (неделя 3)
1. База блюд (200+ рецептов с КБЖУ)
2. Калькулятор макросов
3. Генератор 28-дневного меню
4. Валидатор КБЖУ (±10%)
5. Генератор списков закупок
6. UI: конструктор плана питания

### Фаза 4: Экспорт + Аудит (неделя 4)
1. HTML шаблоны для PDF (дизайн ArishaFit)
2. Puppeteer генерация PDF
3. Встроенный аудит (тренер + нутрициолог + юрист)
4. Юридические дисклеймеры
5. Тестирование на данных Андрея

### Фаза 5: Полировка (неделя 5)
1. Адаптивный дизайн (мобильный)
2. Кабинет клиента (опционально)
3. Деплой на Vercel
4. Документация

---

## ПРЕИМУЩЕСТВА ПЕРЕД СТАРЫМ ПОДХОДОМ

| Было (Андрей) | Стало (ArishaFit App) |
|---|---|
| 15+ раундов аудита | Автоматический аудит в реальном времени |
| 50+ fix-скриптов | Редактирование в UI |
| 7MB HTML с base64 | Лёгкий PDF по шаблону |
| 1 клиент = 1 неделя работы | 1 клиент = 30 минут |
| Ручной подбор упражнений | Автофильтр по травмам и оборудованию |
| Ручной расчёт КБЖУ | Автокалькулятор |
| Ручная проверка закупок | Автогенерация |
| Нет масштабирования | Неограниченное количество клиентов |
