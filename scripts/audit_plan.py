#!/usr/bin/env python3
"""
Полный аудит плана Андрея v6:
- Все exerciseId в БД + медиа-файлы на месте
- Безопасность для L4-L5 грыжи (axial load, extension, flexion под весом)
- Качество tips/warnings (двойные emoji, недосказ, стиль)
- Консистентность названий = анимация = описание
- Прогрессивная перегрузка (RPE/веса растут W1→W3, падают в W4)
- Ротация (разные упражнения между неделями)
- Остатки rUXfn3R, cuKYxhu
"""
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
V6_PATH = ROOT / 'training-skill' / 'output' / 'plan_andrey_v6.json'
DB_PATH = ROOT / 'exercisedb_data' / 'exercise_db_final.json'
GIFS_HD = ROOT / 'exercisedb_data' / 'gifs_hd'
MP4_DIR = ROOT / 'exercisedb_data' / 'mp4'

# Red-flag exerciseIds (must not appear)
FORBIDDEN_IDS = {
    'rUXfn3R': 'Гиперэкстензия в тренажёре — удалена в v6',
    'cuKYxhu': 'Наклон таза стоя — БД mapping broken',
    '10Z2DXU': 'Жим ногами 45° — вызвал дискомфорт у Андрея',
}

# Keywords indicating forbidden patterns for L4-L5
UNSAFE_PATTERNS = {
    'axial': ['back squat', 'barbell squat', 'squat with barbell', 'overhead press standing', 'military press', 'deadlift'],
    'flexion': ['toe touch', 'sit-up', 'sit up', 'crunch', 'roman chair', 'good morning'],
    'extension': ['hyperextension', 'back extension machine', 'superman', 'cobra'],
    'rotation': ['russian twist', 'wood chop', 'cable twist'],
    'high_impact': ['jumping', 'box jump', 'burpee', 'running'],
}


def load_plan_and_db():
    plan = json.loads(V6_PATH.read_text(encoding='utf-8'))
    db_list = json.loads(DB_PATH.read_text(encoding='utf-8'))
    db = {e['exerciseId']: e for e in db_list}
    return plan, db


def walk_exercises(plan):
    """Итерирует все ссылки на exerciseId в плане. Yields (location, item_dict)."""
    # Warmups
    for wtype in ('strength', 'cardio'):
        for bi, block in enumerate(plan.get('warmups', {}).get(wtype, {}).get('blocks', [])):
            for ii, item in enumerate(block.get('items', [])):
                yield f"warmup/{wtype}/{block.get('phase')}/item{ii}", item

    # Cooldowns
    for ctype in ('strength', 'cardio'):
        for bi, block in enumerate(plan.get('cooldowns', {}).get(ctype, {}).get('blocks', [])):
            for ii, item in enumerate(block.get('items', [])):
                yield f"cooldown/{ctype}/{block.get('phase')}/item{ii}", item

    # Main exercises in weeks/days
    for week in plan.get('weeks', []):
        wn = week.get('week_number', '?')
        for day in week.get('days', []):
            dn = day.get('day_number', '?')
            for ei, ex in enumerate(day.get('exercises', [])):
                yield f"W{wn}/D{dn}/main{ei}", ex
                for ai, alt in enumerate(ex.get('alternatives', []) or []):
                    yield f"W{wn}/D{dn}/main{ei}/alt{ai}", alt


def check_forbidden(plan):
    issues = []
    for loc, item in walk_exercises(plan):
        eid = item.get('exerciseId', '')
        if eid in FORBIDDEN_IDS:
            issues.append(('CRITICAL', loc, f"Forbidden exerciseId {eid}: {FORBIDDEN_IDS[eid]}"))
    return issues


def check_db_refs(plan, db):
    issues = []
    for loc, item in walk_exercises(plan):
        eid = item.get('exerciseId', '')
        if not eid:
            # ok — reserved slots
            continue
        if eid not in db:
            issues.append(('ERR', loc, f"exerciseId {eid} NOT in exercise_db_final.json"))
            continue
        # Check media files exist
        webp = GIFS_HD / f'{eid}.webp'
        mp4 = MP4_DIR / f'{eid}.mp4'
        if not webp.exists() and not mp4.exists():
            issues.append(('WARN', loc, f"{eid}: no media file in gifs_hd or mp4"))
    return issues


def check_emoji_doubles(plan):
    issues = []
    for loc, item in walk_exercises(plan):
        for field in ('tips', 'warning'):
            txt = item.get(field, '') or ''
            # Check for multiple emoji at start
            emojis_at_start = re.match(r'^([\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE00-\uFE0F\s]+)', txt)
            if emojis_at_start:
                grp = emojis_at_start.group(1).strip()
                # Count non-whitespace emoji chars (simplified: count length)
                emoji_chars = [c for c in grp if ord(c) > 0x2500]
                if len(emoji_chars) >= 2:
                    issues.append(('WARN', loc, f"{field} starts with multiple emoji: {grp!r}"))
    return issues


def check_unsafe_patterns(plan, db):
    issues = []
    for loc, item in walk_exercises(plan):
        eid = item.get('exerciseId', '')
        if not eid or eid not in db:
            continue
        en = (db[eid].get('nameEn', '') or '').lower()
        ru = (db[eid].get('nameRu', '') or '').lower()
        combined = f"{en} {ru}"
        for category, kws in UNSAFE_PATTERNS.items():
            for kw in kws:
                if kw in combined:
                    issues.append(('WARN', loc, f"Potential unsafe pattern ({category}): {eid} — {en}"))
    return issues


def check_rotation(plan):
    """Ротация упражнений между неделями Day A и Day B."""
    issues = []
    # Collect exercises[0..2] (main slots) across weeks for each day
    by_day = defaultdict(list)  # (day_number, slot_idx) -> [exerciseIds per week]
    for week in plan.get('weeks', []):
        wn = week.get('week_number', '?')
        for day in week.get('days', []):
            dn = day.get('day_number', '?')
            if dn == 2:  # Cardio day — skip
                continue
            for ei, ex in enumerate(day.get('exercises', [])[:3]):  # First 3 slots
                by_day[(dn, ei)].append((wn, ex.get('exerciseId', '')))

    # Show rotation across W1/W2/W3 (W4 = W1 deload so same is OK)
    for (dn, ei), weeks_list in by_day.items():
        w1_3 = [eid for wn, eid in weeks_list if wn in (1, 2, 3)]
        if len(set(w1_3)) == 1 and w1_3:
            issues.append(('INFO', f"D{dn}/slot{ei}",
                          f"Same exerciseId across W1-W3: {w1_3[0]} (OK if keystone)"))
    return issues


def check_progression(plan):
    issues = []
    # Check RPE progression: W1 → W2 → W3 ↑, W4 = deload ↓
    rpe_by_week = defaultdict(list)
    for week in plan.get('weeks', []):
        wn = week.get('week_number', '?')
        for day in week.get('days', []):
            if day.get('day_number') == 2:
                continue
            for ex in day.get('exercises', []):
                rpe = ex.get('rpe', '')
                # Extract numeric RPE (handle "7", "7.5", "7-8" etc)
                m = re.search(r'\d+(?:\.\d+)?', str(rpe))
                if m:
                    rpe_by_week[wn].append(float(m.group()))

    w1_avg = sum(rpe_by_week.get(1, [])) / max(1, len(rpe_by_week.get(1, [])))
    w2_avg = sum(rpe_by_week.get(2, [])) / max(1, len(rpe_by_week.get(2, [])))
    w3_avg = sum(rpe_by_week.get(3, [])) / max(1, len(rpe_by_week.get(3, [])))
    w4_avg = sum(rpe_by_week.get(4, [])) / max(1, len(rpe_by_week.get(4, [])))

    print(f"  Avg RPE: W1={w1_avg:.1f}  W2={w2_avg:.1f}  W3={w3_avg:.1f}  W4={w4_avg:.1f}")
    if not (w1_avg <= w2_avg <= w3_avg):
        issues.append(('WARN', 'progression', f"RPE should grow W1≤W2≤W3: {w1_avg:.1f}/{w2_avg:.1f}/{w3_avg:.1f}"))
    if w4_avg >= w1_avg:
        issues.append(('WARN', 'progression/deload', f"W4 deload should be LOWER than W1: W1={w1_avg:.1f} W4={w4_avg:.1f}"))
    return issues


def check_name_animation_match(plan, db):
    """Проверить что plan nameRu соответствует DB nameRu (с учётом исключения для hasAnimation=False)."""
    issues = []
    for loc, item in walk_exercises(plan):
        eid = item.get('exerciseId', '')
        plan_name = (item.get('nameRu') or '').strip()
        if not eid or eid not in db:
            continue
        db_name = (db[eid].get('nameRu') or '').strip()
        has_anim = db[eid].get('hasAnimation', True)

        if not has_anim:
            # Static reference — plan name takes priority; nothing to check
            continue

        # For animated exercises: plan name should == DB name OR DB name + (qualifier)
        # Remove common suffixes/qualifiers
        cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', plan_name).strip()
        # Also strip « — » postfix
        cleaned = re.sub(r'\s+[—-]\s+.*$', '', cleaned).strip()

        if cleaned and db_name and cleaned.lower() != db_name.lower():
            issues.append(('INFO', loc,
                          f"Plan name '{plan_name}' differs from DB name '{db_name}' (eid={eid})"))
    return issues


def main():
    plan, db = load_plan_and_db()
    print(f"Plan: {V6_PATH.name}")
    print(f"DB: {len(db)} упражнений")
    print()

    all_issues = []

    checks = [
        ("1. Forbidden exerciseIds (rUXfn3R/cuKYxhu/10Z2DXU)", check_forbidden, (plan,)),
        ("2. All exerciseId → DB + media exist", check_db_refs, (plan, db)),
        ("3. No double emoji at tips/warning start", check_emoji_doubles, (plan,)),
        ("4. Unsafe patterns for L4-L5", check_unsafe_patterns, (plan, db)),
        ("5. Rotation across weeks", check_rotation, (plan,)),
        ("6. RPE progression W1→W3 + W4 deload", check_progression, (plan,)),
        ("7. Plan name == DB name (for animated)", check_name_animation_match, (plan, db)),
    ]

    for title, func, args in checks:
        print(f"=== {title} ===")
        issues = func(*args)
        if not issues:
            print("  OK — no issues")
        for severity, loc, msg in issues:
            print(f"  [{severity}] {loc}: {msg}")
            all_issues.append((severity, loc, msg))
        print()

    print("=" * 60)
    print(f"SUMMARY: {len(all_issues)} issues")
    sev_count = defaultdict(int)
    for s, _, _ in all_issues:
        sev_count[s] += 1
    for s in ('CRITICAL', 'ERR', 'WARN', 'INFO'):
        if sev_count[s]:
            print(f"  {s}: {sev_count[s]}")


if __name__ == '__main__':
    main()
