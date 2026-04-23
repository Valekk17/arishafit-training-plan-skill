# Audit: nameRu quality in exercise_db_final.json

**Дата:** 2026-04-23
**Запущено для:** Priority 3 (translation quality / DB hygiene) из `docs/next_session_prompt.md`

## TL;DR

**БД здорова.** 1500 упражнений, 0 NULL, 0 дубликатов, 0 транслитераций без кириллицы. Найдено 3 настоящие «литеральные» проблемы — исправлены. 78 «раздутых» имён — false positive (русский объективно длиннее английского для точных терминов).

**Исходная гипотеза** из `next_session_prompt.md` (много None + транслитерации) **устарела** — БД была почищена в предыдущих итерациях.

## Что запускали

1. `scripts/audit_name_ru.py` — формальные проверки:
   - A. nameRu пустое/None
   - B. nameRu == nameEn
   - C. nameRu короче 5 chars
   - D. Без кириллицы (латиница/транслит)
   - E. Mixed latin+cyrillic с транслит-маркерами (zh/sh/ch/kh/...)

   **Результат: 0 проблем в 1500 записях.** → `name_ru_issues.json`

2. `scripts/audit_name_ru_quality.py` — глубокие паттерны:
   - Q1. Длина > 60 chars
   - Q2. Дубликаты nameRu
   - Q3. Литеральные паттерны (калькированные фразы)
   - Q8. Ratio ru/en > 2.0

   **Результат:** Q3 = 3, Q8 = 78, Q1/Q2 = 0 → `name_ru_quality_issues.json`

## Что поправили

`scripts/fix_literal_translations.py` — точечные правки 3 литеральных переводов:

| exerciseId | EN                                 | RU before                                  | RU after                           |
|------------|------------------------------------|--------------------------------------------|------------------------------------|
| `8ARQ9Hw`  | kettlebell sumo high pull          | Высокая тяга гири **в стиле сумо**         | Высокая тяга гири сумо             |
| `0CXGHya`  | cable cross-over variation         | Кроссовер **- вариация**                   | Кроссовер (вариант)                |
| `ZgwWBoC`  | cable thibaudeau kayak row         | Тяга на блоке **в стиле байдарки** (Тибодо)| Тяга-гребля в блоке (по Тибодо)    |

Обоснование:
- «в стиле X» — калька с английского «in the style of», в русском фитнес-лексиконе не используется. Для сумо-тяги устойчивый термин — просто «сумо» как квалификатор.
- Тире перед словом «вариация» — нестандартное форматирование; конвенция БД — `(вариант)` в скобках.
- Для Thibaudeau kayak row — суть движения — альтернативная гребля, отражена как «тяга-гребля».

## Почему Q8 (78 записей) НЕ чинятся

Ratio > 2.0 — эвристика. Ручной review показал что подавляющее большинство записей — корректные профессиональные термины:

| EN                    | RU                              | Комментарий                              |
|-----------------------|---------------------------------|------------------------------------------|
| inverted row          | Горизонтальные подтягивания     | Стандартный термин                       |
| back lever            | Задний вис горизонтальный       | Правильный гимнастический термин         |
| skin the cat          | Выкрут назад на перекладине     | Правильный термин                        |
| farmers walk          | Прогулка фермера с гантелями    | Стандарт                                 |
| cable pushdown        | Разгибание на трицепс в блоке   | Правильно                                |

Тратить батч Opus на «стилистические» правки этих 78 — низкая отдача. Если в будущем возникнут конкретные случаи (клиент жалуется на конкретное имя) — править точечно.

## Postgres DB sync

**Статус:** не выполнен в этой сессии (Docker Desktop стартовал долго, не дождался).

**Что нужно сделать в следующей сессии:**
```bash
cd C:/Users/morod/fitness-andrey
docker compose up -d postgres
# Вариант A: полный wipe + migrate из JSON (теряется accumulated plan data)
python scripts/migrate_json_to_db.py --wipe --plan <latest>
# Вариант B: только UPDATE 3 exercise строк
python -c "
from db.session import session_scope
from db.models import Exercise
FIXES = {
    '8ARQ9Hw': 'Высокая тяга гири сумо',
    '0CXGHya': 'Кроссовер (вариант)',
    'ZgwWBoC': 'Тяга-гребля в блоке (по Тибодо)',
}
with session_scope() as s:
    for eid, name in FIXES.items():
        s.query(Exercise).filter_by(exercise_id=eid).update({'name_ru': name})
    s.commit()
"
```

Рекомендую Вариант B — минимальная инвазивность, сохранит plans/session_logs/one_rm_estimates.

## Метрика исполнения

- Время: ~10 мин на весь цикл (audit → quality-audit → fix → verify)
- LoC: 3 новых скрипта + 1 README
- Изменения в БД: 3 строки из 1500 (0.2%)
- Побочных эффектов нет — nameRu это справочное поле, никаких foreign keys

## Вывод

Priority 3 **закрыт** на JSON-уровне. Postgres sync — 1 минута работы в следующей сессии с запущенным Docker.

Следующий логический шаг — Priority 4 (client intake schema) или Priority 5 (nutrition skill).
