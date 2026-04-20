"""
Готовит контекст-файл для Opus чтобы он написал plan_andrey_v6.json
без необходимости browse БД. Фильтрует упражнения по паттернам с учётом
L4-L5 restrictions.
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent

db = json.loads((ROOT / "exercisedb_data" / "exercise_db_final.json").read_text(encoding="utf-8"))
by_id = {e["exerciseId"]: e for e in db if e.get("hasAnimation")}

def matches_keywords(ex, *groups_any):
    """matches_keywords(ex, ['chest', 'грудь'], ['lever', 'рычаж']) →
    AND между группами, OR внутри группы."""
    n = (ex.get("nameEn", "") + " " + ex.get("nameRu", "")).lower()
    instr = " ".join(ex.get("instructions", [""])[:2]).lower()
    text = n + " " + instr
    return all(any(kw in text for kw in g) for g in groups_any)


# ==== POOLS ПО СЛОТАМ ====

pools = {
    # Push-H: жимы на грудь с опорой на спинку
    "push_h_machine": [],    # рычажные/смитинг
    "push_h_cable": [],      # кроссовер / cable fly
    "push_h_incline": [],    # incline варианты

    # Pull-V: тяги сверху
    "pull_v_wide": [],        # широкий хват
    "pull_v_reverse": [],     # обратный хват
    "pull_v_cable_pullover": [],

    # Squat safe for L4-L5 (no sled 45)
    "squat_safe_seated": [],   # seated lever leg press
    "squat_safe_hack": [],     # hack squat machine
    "leg_extension": [],
    "lying_leg_curl": [],
    "split_squat_smith": [],

    # Pull-H: тяги горизонтальные
    "pull_h_cable": [],
    "pull_h_machine_lever": [],
    "pull_h_one_arm": [],

    # Push-V: жимы плеч
    "push_v_machine": [],
    "push_v_lateral": [],     # боковые махи
    "push_v_dumbbell_supported": [],  # гантели с опорой спины

    # Hinge
    "hinge_glute_bridge": [],
    "hinge_cable_pullthrough": [],
    "hinge_reverse_hyper": [],
    "hinge_safe_hyperextension": [],  # правильная форма

    # Core
    "core_side_plank": [],
    "core_bird_dog": [],
    "core_pallof": [],
    "core_dead_bug": [],
}


for ex in by_id.values():
    eid = ex["exerciseId"]
    en = ex["nameEn"].lower()

    # Push-H
    if "chest press" in en and "lever" in en: pools["push_h_machine"].append(ex)
    if "cable" in en and ("fly" in en or "crossover" in en) and "chest" in en: pools["push_h_cable"].append(ex)
    if "incline" in en and ("chest" in en or "press" in en): pools["push_h_incline"].append(ex)

    # Pull-V
    if "lat pulldown" in en and ("wide" in en or ("reverse" not in en and "close" not in en and "neutral" not in en)):
        pools["pull_v_wide"].append(ex)
    if "lat pulldown" in en and ("reverse" in en or "underhand" in en or "supinated" in en):
        pools["pull_v_reverse"].append(ex)
    if "pullover" in en and "cable" in en: pools["pull_v_cable_pullover"].append(ex)

    # Squat safe (без sled 45°)
    if "leg press" in en and ("seated" in en or "lever seated" in en) and "alternate" not in en and "one leg" not in en and "sled" not in en:
        pools["squat_safe_seated"].append(ex)
    if "hack squat" in en or ("sled" in en and "squat" in en):
        pools["squat_safe_hack"].append(ex)
    if "leg extension" in en and "one" not in en and "single" not in en:
        pools["leg_extension"].append(ex)
    if "leg curl" in en and "lying" in en:
        pools["lying_leg_curl"].append(ex)
    if "split squat" in en and ("smith" in en or "dumbbell" in en):
        pools["split_squat_smith"].append(ex)

    # Pull-H
    if ("cable" in en or "seated row" in en) and "row" in en and "one" not in en and "single" not in en:
        pools["pull_h_cable"].append(ex)
    if "row" in en and "lever" in en:
        pools["pull_h_machine_lever"].append(ex)
    if "row" in en and ("one arm" in en or "single arm" in en):
        pools["pull_h_one_arm"].append(ex)

    # Push-V
    if ("shoulder press" in en or "overhead press" in en) and "lever" in en:
        pools["push_v_machine"].append(ex)
    if "lateral raise" in en and ("machine" in en or "lever" in en or "cable" in en):
        pools["push_v_lateral"].append(ex)
    if "shoulder press" in en and "dumbbell" in en and "seated" in en:
        pools["push_v_dumbbell_supported"].append(ex)

    # Hinge
    if ("glute bridge" in en or "hip thrust" in en) and "barbell" in en and "one" not in en:
        pools["hinge_glute_bridge"].append(ex)
    if "pull through" in en or "pull-through" in en: pools["hinge_cable_pullthrough"].append(ex)
    if "reverse hyper" in en: pools["hinge_reverse_hyper"].append(ex)
    if "hyperextension" in en or "back extension" in en:
        pools["hinge_safe_hyperextension"].append(ex)

    # Core
    if "side plank" in en or "side bridge" in en:
        pools["core_side_plank"].append(ex)
    if "bird dog" in en or "bird-dog" in en:
        pools["core_bird_dog"].append(ex)
    if "pallof" in en:
        pools["core_pallof"].append(ex)
    if "dead bug" in en or "deadbug" in en:
        pools["core_dead_bug"].append(ex)


# Сократим до 3 лучших в каждом пуле (приоритет: supported_back, machine)
output = {}
for pool_name, items in pools.items():
    # Ранжируем: preference to leverage machines with supported back
    ranked = sorted(items, key=lambda ex: (
        "machine" in ex["nameEn"].lower() or "lever" in ex["nameEn"].lower(),
        "seated" in ex["nameEn"].lower(),
        "supported" in str(ex.get("bodyParts", [])).lower(),
    ), reverse=True)
    output[pool_name] = [{
        "exerciseId": ex["exerciseId"],
        "nameRu": ex["nameRu"],
        "nameEn": ex["nameEn"],
        "equipments": ex.get("equipments", []),
        "targetMuscles": ex.get("targetMuscles", []),
    } for ex in ranked[:6]]

(ROOT / "training-skill" / "output" / "_v6_candidates.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

# Stats
for k, v in output.items():
    print(f"{k:<30} {len(v)} candidates")
print()
print("Записано: training-skill/output/_v6_candidates.json")
