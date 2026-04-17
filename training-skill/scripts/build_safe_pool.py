"""
build_safe_pool.py — Pre-generation DB validator + safe pool builder
Version: 1.0 (2026-04-09)

Usage:
    python build_safe_pool.py --conditions fibromyalgia
    python build_safe_pool.py --conditions "hypertension_grade_3,COPD,knee_OA_grade_1"
    python build_safe_pool.py --conditions hypermobility_EDS --output safe_pool_T18.json

Purpose:
    1. Loads exercise_db_final.json (1500 entries, original untouched)
    2. Applies exercise_db_patches.json (hand-curated by Opus)
       - Global blacklist (20 elite gymnastic IDs)
       - Conditional forbidden IDs (by client condition)
       - nameRu overrides (fixes misleading/duplicate names)
       - Intent flags (bicep exercise labeled as leg etc.)
    3. Filters by client conditions (excludes condition-specific forbidden)
    4. Writes safe_pool_{hash}.json — the exercise pool the training skill should use

Input files (required):
    exercisedb_data/exercise_db_final.json
    exercisedb_data/exercise_db_patches.json

Output:
    Safe pool JSON with schema:
    {
      "meta": { "generated": iso, "conditions": [...], "total_in": 1500, "total_out": N, "excluded_by": {...} },
      "exercises": [ ...filtered & patched entries... ]
    }

DOES NOT MODIFY the original DB. All patches are applied in memory only.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

# Windows cp1251 console fix
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Allow running from any cwd
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "exercisedb_data", "exercise_db_final.json")
PATCHES_PATH = os.path.join(PROJECT_ROOT, "exercisedb_data", "exercise_db_patches.json")
GIFS_DIR = os.path.join(PROJECT_ROOT, "exercisedb_data", "gifs_hd")
GIFS_DIR_LEGACY = os.path.join(PROJECT_ROOT, "exercisedb_data", "gifs")


def load_db():
    """Load the main exercise database."""
    if not os.path.exists(DB_PATH):
        print(f"ERROR: DB not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(DB_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)
    return {e["exerciseId"]: e for e in entries}


def load_patches():
    """Load hand-curated patches."""
    if not os.path.exists(PATCHES_PATH):
        print(f"ERROR: Patches not found at {PATCHES_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(PATCHES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_condition_keys(client_condition, patches):
    """Given a client condition (e.g., 'knee_OA_grade_1'), find all matching keys in patches.conditional_forbidden.

    Matching rules:
    - exact match
    - prefix match (e.g., 'knee_OA_grade_1' matches 'knee_OA_any_grade' because both start with 'knee_OA')
    - 'any_grade' keys match any grade of the same condition
    - grade-specific keys match their grade plus higher grades (e.g., 'hypertension_grade_2' matches clients with grade 2 OR grade 3)
    """
    cond_forbidden = patches.get("conditional_forbidden", {})
    cond_lower = client_condition.strip().lower()
    matched_keys = set()

    # 1. Exact match
    if cond_lower in cond_forbidden:
        matched_keys.add(cond_lower)

    # 2. "any_grade" match
    for key in cond_forbidden:
        if key == "_description":
            continue
        key_lower = key.lower()
        # Strip grade suffix for base comparison
        cond_base = cond_lower
        key_base = key_lower
        # Check: client has "knee_OA_grade_1", key is "knee_OA_any_grade" → match
        if "any_grade" in key_base:
            key_stem = key_base.replace("_any_grade", "")
            if cond_base.startswith(key_stem):
                matched_keys.add(key)

    # 3. HTN grade cascade (client grade N matches patches for grade N and lower)
    # e.g., HTN grade 3 is ALSO HTN grade 2 → match both patches
    import re
    m = re.match(r"(.+?)_grade_(\d+)", cond_lower)
    if m:
        stem = m.group(1)
        client_grade = int(m.group(2))
        for key in cond_forbidden:
            if key == "_description":
                continue
            km = re.match(rf"{re.escape(stem)}_grade_(\d+)(?:_plus)?", key)
            if km:
                key_grade = int(km.group(1))
                if client_grade >= key_grade:
                    matched_keys.add(key)

    # 4. Fallback: substring containment (loose match)
    for key in cond_forbidden:
        if key == "_description":
            continue
        if key.lower() in cond_lower or cond_lower in key.lower():
            matched_keys.add(key)

    return matched_keys


def collect_pattern_exclusions(patches, conditions):
    """v1.2: Collect movement patterns to exclude based on client conditions.
    Returns set of patterns. Used to filter exercises whose movementPatterns intersect."""
    excluded_patterns = set()
    pattern_reasons = []  # list of (pattern, condition, reason)
    rules = patches.get("exclude_by_pattern_if_condition", {}).get("rules", [])
    cond_set_lower = {c.strip().lower() for c in conditions}
    for rule in rules:
        rule_conds = {c.lower() for c in rule.get("conditions", [])}
        # Match if any client condition matches any rule condition (loose substring match)
        matched = False
        for client_cond in cond_set_lower:
            for rc in rule_conds:
                if client_cond == rc or client_cond in rc or rc in client_cond:
                    matched = True
                    break
            if matched:
                break
        if matched:
            for p in rule.get("exclude_patterns", []):
                excluded_patterns.add(p)
                pattern_reasons.append((p, rule_conds, rule.get("reason", "")))
    return excluded_patterns, pattern_reasons


def collect_forbidden_ids(patches, conditions):
    """Given client conditions list, collect all forbidden exerciseIds."""
    forbidden = set()
    reasons = {}  # id -> list of reasons

    # Global blacklist (always excluded)
    for eid, reason in patches.get("global_blacklist", {}).get("ids", {}).items():
        if eid.startswith("_"):
            continue
        forbidden.add(eid)
        reasons.setdefault(eid, []).append(f"global_blacklist: {reason}")

    # DB quality blacklist (broken GIFs, etc.)
    for eid, reason in patches.get("db_quality_blacklist", {}).get("ids", {}).items():
        if eid.startswith("_"):
            continue
        forbidden.add(eid)
        reasons.setdefault(eid, []).append(f"db_quality: {reason}")

    # Conditional forbidden (only if client has that condition)
    cond_forbidden = patches.get("conditional_forbidden", {})
    for cond in conditions:
        matched_keys = resolve_condition_keys(cond, patches)
        for key in matched_keys:
            cond_map = cond_forbidden.get(key, {})
            for eid, reason in cond_map.items():
                if eid.startswith("_"):
                    continue
                forbidden.add(eid)
                reasons.setdefault(eid, []).append(f"condition[{cond}→{key}]: {reason}")

    return forbidden, reasons


def apply_name_overrides(entry, patches):
    """Apply nameRu overrides from patches."""
    overrides = patches.get("name_overrides", {})
    eid = entry.get("exerciseId")
    if eid in overrides and eid != "_description":
        new_name = overrides[eid]
        if new_name and not new_name.startswith("_"):
            entry["_original_nameRu"] = entry.get("nameRu")
            entry["nameRu"] = new_name
            entry["_name_patched"] = True
    return entry


def apply_level_overrides(entry, patches):
    """Add level metadata from patches."""
    level_map = patches.get("level_overrides", {})
    eid = entry.get("exerciseId")
    for level, ids in level_map.items():
        if level.startswith("_"):
            continue
        if eid in ids:
            entry["_level_patched"] = level
            break
    return entry


def apply_intent_flags(entry, patches):
    """Attach intent warnings to flagged entries."""
    flags = patches.get("intent_flags", {}).get("flagged", {})
    eid = entry.get("exerciseId")
    if eid in flags:
        entry["_intent_flag"] = flags[eid]
    return entry


def has_valid_gif(entry):
    """Verify that local media file exists (HD WebP preferred, legacy GIF fallback)."""
    if not entry.get("hasGif"):
        return False
    eid = entry.get("exerciseId")
    # Check HD WebP first
    for ext in (".webp", ".png", ".gif"):
        hd_path = os.path.join(GIFS_DIR, f"{eid}{ext}")
        if os.path.exists(hd_path):
            return True
    # Legacy GIF fallback
    legacy_path = os.path.join(GIFS_DIR_LEGACY, f"{eid}.gif")
    return os.path.exists(legacy_path)


def validate_nameRu(nameRu):
    """Check that nameRu is meaningful: >15 chars or in approved short list."""
    if not nameRu:
        return False, "nameRu is null"
    approved_short = {"Dead Bug (жук)", "Bird-Dog", "Pallof Press"}
    if nameRu in approved_short:
        return True, "approved_short"
    if len(nameRu) < 15:
        return False, f"too_short ({len(nameRu)}chars)"
    prepositions = ["с ", "на ", "для ", "со ", "по ", "к ", "в ", "из "]
    lowered = nameRu.lower()
    if any(lowered.startswith(p) for p in prepositions):
        return False, "starts_with_preposition"
    return True, "ok"


def build_safe_pool(conditions, verbose=True):
    """Main pipeline: DB → patches → condition filter → safe pool."""
    db = load_db()
    patches = load_patches()

    forbidden_ids, reasons = collect_forbidden_ids(patches, conditions)
    excluded_patterns, pattern_reasons = collect_pattern_exclusions(patches, conditions)

    # Collect position-based exclusions (v1.5)
    excluded_position_ids = set()
    pos_rules = patches.get("exclude_by_pattern_if_condition", {}).get("exclude_verified_positions", [])
    verified = patches.get("verified_positions", {})
    cond_set_lower = {c.strip().lower() for c in conditions}
    for rule in pos_rules:
        rule_conds = {c.lower() for c in rule.get("conditions", [])}
        matched = any(
            cc == rc or cc in rc or rc in cc
            for cc in cond_set_lower for rc in rule_conds
        )
        if matched:
            for pos in rule.get("exclude_positions", []):
                for eid in verified.get(pos, []):
                    excluded_position_ids.add(eid)

    stats = {
        "total_in_db": len(db),
        "excluded_global_blacklist": 0,
        "excluded_db_quality": 0,
        "excluded_conditional": 0,
        "excluded_pattern": 0,
        "excluded_position": 0,
        "excluded_no_gif": 0,
        "excluded_invalid_nameRu": 0,
        "included": 0,
        "patched_name": 0,
        "patched_level": 0,
        "intent_flagged": 0,
    }

    out = []
    excluded = {}

    for eid, entry in db.items():
        # Make a shallow copy so we don't modify the in-memory DB cache
        e = dict(entry)

        # 1. Forbidden check
        if eid in forbidden_ids:
            reason_list = reasons.get(eid, [])
            excluded[eid] = reason_list
            for r in reason_list:
                if "global_blacklist" in r:
                    stats["excluded_global_blacklist"] += 1
                    break
                if "db_quality" in r:
                    stats["excluded_db_quality"] += 1
                    break
                if "condition" in r:
                    stats["excluded_conditional"] += 1
                    break
            continue

        # 1b. Pattern-based exclusion (v1.2)
        ex_patterns = set(e.get("movementPatterns", []))
        forbidden_patterns_intersect = ex_patterns & excluded_patterns
        if forbidden_patterns_intersect:
            excluded[eid] = [f"pattern_excluded: {sorted(forbidden_patterns_intersect)}"]
            stats["excluded_pattern"] += 1
            continue

        # 1c. Position-based exclusion (v1.5 — uses visual GIF verification)
        if eid in excluded_position_ids:
            excluded[eid] = ["position_excluded: verified GIF shows dangerous body position for client condition"]
            stats["excluded_position"] += 1
            continue

        # 2. Apply patches first (so nameRu is corrected before validation)
        e = apply_name_overrides(e, patches)
        e = apply_level_overrides(e, patches)
        e = apply_intent_flags(e, patches)

        if e.get("_name_patched"):
            stats["patched_name"] += 1
        if e.get("_level_patched"):
            stats["patched_level"] += 1
        if e.get("_intent_flag"):
            stats["intent_flagged"] += 1

        # 3. GIF validity check
        if not has_valid_gif(e):
            excluded[eid] = ["no_valid_gif"]
            stats["excluded_no_gif"] += 1
            continue

        # 4. nameRu validation (after patch)
        valid, validation_reason = validate_nameRu(e.get("nameRu"))
        if not valid:
            excluded[eid] = [f"invalid_nameRu: {validation_reason}"]
            stats["excluded_invalid_nameRu"] += 1
            continue

        out.append(e)
        stats["included"] += 1

    result = {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "generator": "build_safe_pool.py v1.0",
            "conditions": list(conditions),
            "stats": stats,
            "patches_version": patches.get("_meta", {}).get("version", "unknown"),
        },
        "exercises": out,
        "excluded": excluded,
    }

    if verbose:
        print(f"\n==== Safe Pool Build Report ====")
        print(f"Conditions: {conditions}")
        print(f"Total DB entries: {stats['total_in_db']}")
        print(f"Excluded:")
        print(f"  Global blacklist: {stats['excluded_global_blacklist']}")
        print(f"  DB quality (broken): {stats['excluded_db_quality']}")
        print(f"  Conditional ID (by client): {stats['excluded_conditional']}")
        print(f"  Pattern excluded (v1.2 by client): {stats['excluded_pattern']}")
        if excluded_patterns:
            print(f"    Patterns: {sorted(excluded_patterns)}")
        print(f"  Position excluded (v1.5 GIF-verified): {stats['excluded_position']}")
        print(f"  No valid GIF: {stats['excluded_no_gif']}")
        print(f"  Invalid nameRu: {stats['excluded_invalid_nameRu']}")
        print(f"Included in pool: {stats['included']}")
        print(f"Patched names applied: {stats['patched_name']}")
        print(f"Level overrides applied: {stats['patched_level']}")
        print(f"Intent-flagged entries: {stats['intent_flagged']}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Build a safe exercise pool for a client")
    parser.add_argument("--conditions", type=str, default="",
                        help="Comma-separated client conditions (e.g., 'hypertension_grade_3,COPD,knee_OA_grade_1')")
    parser.add_argument("--output", type=str, default=None,
                        help="Output file path (default: auto-generated based on condition hash)")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = parser.parse_args()

    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()] if args.conditions else []

    result = build_safe_pool(conditions, verbose=not args.quiet)

    if args.output:
        output_path = args.output
    else:
        if conditions:
            h = hashlib.md5(",".join(sorted(conditions)).encode()).hexdigest()[:8]
            output_path = f"safe_pool_{h}.json"
        else:
            output_path = "safe_pool_general.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Safe pool written to: {output_path}")
    print(f"  File size: {os.path.getsize(output_path) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
