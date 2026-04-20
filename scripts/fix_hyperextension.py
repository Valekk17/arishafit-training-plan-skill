#!/usr/bin/env python3
"""
Фикс: убрать rUXfn3R (Гиперэкстензия в тренажёре) из v6 плана.

Причина: 2 грыжи L4-L5 у клиента, одна после операции без улучшения.
Нагруженное разгибание позвоночника (даже «STRICT hip hinge only») —
это компромисс, который зависит от самоконтроля под усталостью.
Не подходит для послеоперационного клиента без клинического улучшения.

Что меняем:
1. W1 Day B slot 4: rUXfn3R → Krmb3cB (обратная гиперэкстензия в Хаммере)
2. W3 Day B slot 4: Krmb3cB → vM5YS2g (обратная гиперэкстензия на фитболе — ротация)
3. W4 Day B slot 4: rUXfn3R → Krmb3cB (дилоуд-параметры)
4. Все alternatives где rUXfn3R → Krmb3cB

В итоге в плане не остаётся ни одной классической гиперэкстензии.
Все варианты — reverse hyper (тело фиксировано, ноги двигаются) или
cable pull-through (hip hinge без осевой нагрузки).
"""
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V6_PATH = ROOT / 'training-skill' / 'output' / 'plan_andrey_v6.json'


def gif(eid): return f"https://static.exercisedb.dev/media/{eid}.gif"


# ==========================================================================
# MAIN REPLACEMENTS
# ==========================================================================

def krmb3cb_main_w1():
    """W1 Day B slot 4 — основа, замена rUXfn3R."""
    return {
        "exerciseId": "Krmb3cB",
        "nameRu": "Обратная гиперэкстензия в Хаммере",
        "sets": 3,
        "reps": "12-15",
        "rest_sec": 45,
        "rpe": "7",
        "tips": (
            "🎯 v6 обновление: традиционная гиперэкстензия (rUXfn3R) заменена. Для клиента с "
            "грыжами L4-L5 (одна после операции) даже «strict» версия — слишком большой риск. "
            "Здесь — обратная гиперэкстензия: тело фиксировано, двигаются ТОЛЬКО ноги. Поясница "
            "имеет минимальный рычаг нагрузки. "
            "📊 Ложись в тренажёр животом на подушку, руки хватают за ручки сверху, ноги "
            "свисают. Отталкивайся пятками: поднимай ноги до ПАРАЛЛЕЛИ с полом. На пике — "
            "сжатие ягодиц 1с, НЕ выше параллели. Медленный возврат 3с. Темп 2-1-3. Выдох на "
            "подъёме. Без отягощения на W1 или минимум веса в стеке."
        ),
        "warning": (
            "🚫 КРИТИЧНО: НИКОГДА выше параллели. Когда ноги идут выше линии таза — поясница "
            "автоматически переразгибается = прямая провокация L4-L5. Если тренажёр позволяет "
            "больше амплитуды ВНИЗ — это ОК (работает тазобедренный hinge), но ВВЕРХ — строго "
            "до параллели с полом. Контроль без рывков, без инерции."
        ),
        "gifUrl": gif("Krmb3cB"),
        "alternatives": [
            {
                "exerciseId": "vM5YS2g",
                "nameRu": "Обратная гиперэкстензия на фитболе",
                "tips": "На фитболе — более нестабильная поверхность, больше работы кора. "
                        "Живот на мяче, руки в пол для опоры, поднимай ноги до параллели.",
                "warning": "Мяч не должен катиться — найди баланс перед началом. Не выше параллели.",
                "gifUrl": gif("vM5YS2g")
            },
            {
                "exerciseId": "OM46QHm",
                "nameRu": "Тяга между ног на блоке с канатом",
                "tips": "Cable pull-through — альтернативный safe hinge. Встань спиной к нижнему "
                        "блоку, канат между ног. Выталкивай таз вперёд за счёт ягодиц.",
                "warning": "Спина как ДОСКА. Движение только в тазобедренных, позвоночник не гнётся.",
                "gifUrl": gif("OM46QHm")
            },
        ],
    }


def vm5ys2g_main_w3():
    """W3 Day B slot 4 — ротация, замена Krmb3cB на W3 для разнообразия."""
    return {
        "exerciseId": "vM5YS2g",
        "nameRu": "Обратная гиперэкстензия на фитболе",
        "sets": 3,
        "reps": "12-15",
        "rest_sec": 45,
        "rpe": "7.5",
        "tips": (
            "Ротация на W3 — тот же safe паттерн (reverse hyper), но на фитболе: нестабильная "
            "поверхность добавляет работу кора. Ложись животом на мяч так, чтобы бёдра были на "
            "центре мяча, руки упираются в пол перед тобой (как в упоре лёжа, но корпус на "
            "мяче). Ноги прямые, стопы вместе. Поднимай обе ноги до ПАРАЛЛЕЛИ с полом за счёт "
            "ягодиц и задней поверхности бедра. Пауза 1с со сжатием ягодиц. Медленное "
            "опускание 3с. Темп 2-1-3."
        ),
        "warning": (
            "🚫 КРИТИЧНО: всё то же правило — не выше параллели. Плюс на фитболе: мяч не должен "
            "катиться. Если видишь что мяч уплывает — переставь руки шире, уменьши амплитуду. "
            "Если баланс сложен — вернись на Krmb3cB (в Хаммере). Никаких рывков."
        ),
        "gifUrl": gif("vM5YS2g"),
        "alternatives": [
            {
                "exerciseId": "Krmb3cB",
                "nameRu": "Обратная гиперэкстензия в Хаммере",
                "tips": "База reverse hyper — в Хаммере стабильная опора, меньше кор, проще контроль.",
                "warning": "Не выше параллели. Сжатие ягодиц на пике.",
                "gifUrl": gif("Krmb3cB")
            },
            {
                "exerciseId": "OM46QHm",
                "nameRu": "Тяга между ног на блоке с канатом",
                "tips": "Cable pull-through как альтернативный safe hinge если тренажёр занят.",
                "warning": "Спина как доска. Только тазобедренный hinge, без изгибов позвоночника.",
                "gifUrl": gif("OM46QHm")
            },
        ],
    }


def krmb3cb_main_w4():
    """W4 Day B slot 4 — дилоуд, замена rUXfn3R с параметрами W1 × 50%."""
    ex = krmb3cb_main_w1()
    ex["sets"] = 2
    ex["reps"] = "12-15"
    ex["rest_sec"] = 60
    ex["rpe"] = "5-6"
    ex["tips"] = (
        "🎯 Дилоуд — обратная гиперэкстензия в Хаммере с минимальными параметрами (2 подхода, "
        "без веса). Тело фиксировано, ноги двигаются до параллели с полом, не выше. Темп "
        "2-1-3 со сжатием ягодиц на пике. Цель — поддержать нейромышечный паттерн, не "
        "нагрузить."
    )
    ex["warning"] = (
        "🚫 Дилоуд — никакого веса. Только body weight. Строго до параллели, без рывков. Если "
        "чувствуешь любой дискомфорт — замена на OM46QHm cable pull-through."
    )
    return ex


# ==========================================================================
# ALTERNATIVE REPLACEMENT — чем заменяем rUXfn3R в alternatives
# ==========================================================================

def krmb3cb_as_alternative():
    """Dict для alternatives где был rUXfn3R."""
    return {
        "exerciseId": "Krmb3cB",
        "nameRu": "Обратная гиперэкстензия в Хаммере",
        "tips": (
            "Safe hinge: тело фиксировано в тренажёре, двигаются только ноги до параллели с "
            "полом. Ягодицы сжимай на пике 1с. Без рывков."
        ),
        "warning": (
            "🚫 Амплитуда выше параллели — КРАСНАЯ ЗОНА (переразгибание поясницы). "
            "Останавливайся когда корпус и бёдра на одной линии."
        ),
        "gifUrl": gif("Krmb3cB"),
    }


# ==========================================================================
# MAIN
# ==========================================================================

def main():
    v6 = json.loads(V6_PATH.read_text(encoding='utf-8'))

    # Подсчёт до
    count_ruxfn3r_before = json.dumps(v6).count('rUXfn3R')
    print(f"rUXfn3R до правки: {count_ruxfn3r_before} раз")

    # 1. W1 Day B slot 4: замена main rUXfn3R → Krmb3cB
    v6['weeks'][0]['days'][2]['exercises'][4] = krmb3cb_main_w1()

    # 2. W3 Day B slot 4: замена main Krmb3cB → vM5YS2g (ротация)
    v6['weeks'][2]['days'][2]['exercises'][4] = vm5ys2g_main_w3()

    # 3. W4 Day B slot 4: замена main rUXfn3R → Krmb3cB (дилоуд)
    v6['weeks'][3]['days'][2]['exercises'][4] = krmb3cb_main_w4()

    # 4. Во всех alternatives: rUXfn3R → Krmb3cB (унифицированный альт)
    replaced_alts = 0

    def walk_and_replace(obj):
        nonlocal replaced_alts
        if isinstance(obj, dict):
            if 'alternatives' in obj and isinstance(obj['alternatives'], list):
                new_alts = []
                seen_ids = set()
                for alt in obj['alternatives']:
                    if not isinstance(alt, dict):
                        new_alts.append(alt)
                        continue
                    if alt.get('exerciseId') == 'rUXfn3R':
                        new_alt = krmb3cb_as_alternative()
                        # Избегаем дублирования в одном списке
                        if new_alt['exerciseId'] not in seen_ids and new_alt['exerciseId'] != obj.get('exerciseId'):
                            new_alts.append(new_alt)
                            seen_ids.add(new_alt['exerciseId'])
                        replaced_alts += 1
                    else:
                        if alt.get('exerciseId') not in seen_ids:
                            new_alts.append(alt)
                            seen_ids.add(alt.get('exerciseId'))
                obj['alternatives'] = new_alts
            for v in obj.values():
                walk_and_replace(v)
        elif isinstance(obj, list):
            for item in obj:
                walk_and_replace(item)

    walk_and_replace(v6)
    print(f"Заменено rUXfn3R в alternatives: {replaced_alts}")

    # Обновить v6 changes в program
    v6['program']['v6_changes'] = (
        v6['program'].get('v6_changes', '') +
        " v6.1 (фикс гиперэкстензии): rUXfn3R (Гиперэкстензия в тренажёре) убрана из плана "
        "полностью — и как main, и из всех alternatives. Причина: 2 грыжи L4-L5, одна после "
        "операции без улучшения — нагруженное разгибание позвоночника противопоказано даже в "
        "«strict» версии. Замена: W1/W4 — Krmb3cB (reverse hyper в Хаммере), W3 — vM5YS2g "
        "(reverse hyper на фитболе, для ротации), W2 — OM46QHm (cable pull-through, без "
        "изменений). Все 4 недели — safe hip hinge без осевой нагрузки и без загрузки "
        "позвоночника в разгибании."
    )

    # Подсчёт после
    count_ruxfn3r_after = json.dumps(v6).count('rUXfn3R')
    print(f"rUXfn3R после правки: {count_ruxfn3r_after} раз")

    V6_PATH.write_text(
        json.dumps(v6, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8'
    )
    size_kb = V6_PATH.stat().st_size / 1024
    print(f"[OK] v6 updated: {V6_PATH} ({size_kb:.0f} KB)")


if __name__ == '__main__':
    main()
