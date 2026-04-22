# Следующая сессия — точка продолжения

Последний коммит: `19b211c` (2026-04-22).

## 🔒 plan_andrey_v7 — ЗАМОРОЖЕН

**Отправлен клиенту 2026-04-22. НЕ трогать больше.**

- Файл: `training-skill/output/plan_andrey_v7.json`
- Рендер: `docs/andrey.html` → https://valekk17.github.io/arishafit-training-plan-skill/andrey.html
- Git tag: `andrey-v7-delivered`

Если клиент вернётся с правками — **только через отдельную версию** (v8 или другой файл). Не перезаписывать v7.

### Краткое описание v7 (для контекста будущих планов)
- Клиент: Андрей, 36y, 102kg, грыжи L4-L5 (одна post-op без улучшения), weight_loss, intermediate, 3 training days
- Split: **Push / Cardio+Light / Pull+Legs** (3-day body-part split)
- 4 недели × 3 дня × 6-7 упражнений = 72 слота, с ротацией W1 база → W2 оборудование → W3 углы/unilateral → W4 deload 50%
- Warmups per-split: push 16 мин / pull_legs 18 мин / cardio 9 мин
- Объём per muscle / week: MEV-MAV для weight-loss (грудь 8, спина 8, плечи 7, квадр 7, бицепс/трицепс по 6, ягодицы 6, кор 6)

### Ключевые правила safety, усвоенные на v6 → v7 (в SKILL.md + memory):
1. `rUXfn3R` классическая гиперэкстензия — FORBIDDEN при post-op грыже
2. `ZuPXtCK` «Гакк в Смите» — FORBIDDEN (Смит-присед = осевая)
3. `DFGXwZr` World's Greatest Stretch — FORBIDDEN для post-op (thoracic rotation «протекает» в lumbar)
4. `cuKYxhu` «Наклон таза стоя» — удалён из БД (mapping name↔gif сломан)
5. Ягодичный мост — обязательный валик под гриф, прямая линия не гипер-мост

---

## 📋 Возможные будущие направления

### 1. Research новой БД упражнений
- `docs/research_prompt_exercise_db.md` — промт готов для Claude Deep Research
- Цель — расширить 1500 упражнений до 3000+, добавить bird dog / pregnancy / pilates / йогу
- Если решим расширять — миграция новой БД в Postgres + rebuild exercise_db_final.json

### 2. План питания для Андрея
- Отдельный skill (nutrition) — не частично SKILL.md
- Структура: 4 недели меню, подходящая к тренировочному графику, учёт weight_loss + MEV объёма

### 3. Следующий клиент
- Можно реиспользовать SKILL.md как есть
- Если профиль без грыжи — раскрыть больше exerciseId (squat/deadlift/overhead free weights unlocked)

### 4. Улучшения инфраструктуры
- GitHub Pages → собственный домен
- FastAPI backend в production (Railway/Fly.io) для мульти-клиентской выдачи планов
- Authentication для приватных планов клиентов

---

## Git workflow reminder

```bash
cd C:/Users/morod/fitness-andrey
git status
git log --oneline -5    # последние коммиты
git tag -l              # список тегов (включая andrey-v7-delivered)
```

---

## Skill hard rules (краткое)

1. **Только Opus генерирует планы.** Скрипты — транспорт (SQL query, merge, migrate, render).
2. **Postgres — источник правды.** `psql arishafit` или `SQLAlchemy` для запросов.
3. **UNIT rule**: exerciseId ↔ nameRu ↔ gifUrl ↔ tips ↔ warning — неделимая единица.
4. **Safety-проверка это работа Opus**, не keyword-match скрипта.
5. **Static reference pose exception**: `hasAnimation: false` → план override имени.

Полные правила в `training-skill/SKILL.md` (372 строки, оптимизирован в 19b211c).
