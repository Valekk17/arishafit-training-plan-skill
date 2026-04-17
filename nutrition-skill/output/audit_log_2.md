# Audit Log — Тест-2
**Date:** 2026-03-28
**Goal:** fat_loss
**Conditions:** IBS (Irritable Bowel Syndrome) — Low-FODMAP protocol required
**Age/Sex:** 35F | 163cm | 71kg | 3x/week mixed cardio+strength

---

## TDEE Calculation
- BMR (Mifflin-St Jeor, Female): 10×71 + 6.25×163 − 5×35 − 161 = **1393 kcal**
- Activity multiplier: 1.55 (moderate, 3x/week)
- TDEE: 1393 × 1.55 = **2159 kcal**
- Deficit: −400 kcal/day (safe range, <750 kcal limit)
- Training day target: **1809 kcal** | Rest day target: **1709 kcal**
- Protein: **156g** (2.2g/kg × 71kg)
- Fat: **64g** (0.9g/kg)
- Carbs training: **152g** | Carbs rest: **127g**

---

## Iteration 1

### Trainer Issues Found
1. **MAJOR** — Rice appearing as primary carb dish on all 3 training days in Week 1 (Days 1, 3, 5) — exceeds 4x/week variety rule per NSCA guidelines
2. **MINOR** — Avocado portion specified as "1/8 плода" — imprecise, needed explicit grams (30г) for accurate Low-FODMAP compliance
3. **MINOR** — Weeks 2–4 were summarized only (theme + recipe list), not full 7-day plans — reduces completeness

### Doctor Issues Found
1. **MAJOR (CRITICAL)** — Day 4 dinner recipe listed 150г broccoli but Monash University Low-FODMAP limit is strictly 75г per serving — this was a direct FODMAP protocol violation risk
2. **MAJOR** — Fiber content not explicitly calculated — risk assessment for IBS 25g/day cap was absent
3. **MINOR** — Magnesium supplement note did not differentiate between IBS-D (diarrhea-predominant, may worsen with magnesium) and IBS-C (constipation-predominant, magnesium beneficial)
4. **MINOR** — Probiotic warning mentioned inulin/FOS but did not address lactose in capsule excipients

### Scores — Iteration 1
| Dimension | Score |
|-----------|-------|
| Safety | 7/10 |
| Completeness | 7/10 |
| Practicality | 9/10 |
| Medical accuracy | 7/10 |

**Status: FAILED — 3 dimensions below 8. Fixes required.**

### Fixes Applied — Iteration 1

**FIX 1 (CRITICAL — Medical):** Corrected Day 4 dinner recipe from "150г брокколи" to strictly "75г брокколи" with explicit note: "СТРОГО не более 75г — Low-FODMAP лимит Monash University". Dish name updated to include "(варёной, 75г max)" as a visual reminder.

**FIX 2 (MAJOR — Trainer):** Changed Day 5 Завтрак from "яичный омлет + рисовая каша" to "яичный омлет + гречневая каша". This breaks the rice-as-main-dish streak: Week 1 now has rice as a main carb dish only on Days 1 (завтрак + обед) and Day 3 (обед) = 3 instances, within the 4x/week limit.

**FIX 3 (MAJOR — Doctor):** Added explicit fiber estimate to safety_notes in nutrition_params: "~18–22g/day (verified within 25g cap)" with component breakdown (spinach 2g, carrots 3g, berries 3g, nuts 2g, grains 8g, vegetables avg 2–4g). Added broccoli 75g cap enforcement confirmation to safety notes.

**FIX 4 (MAJOR — Completeness):** Expanded Weeks 2–4 from theme summaries to full 7-day plans with complete meal breakdowns. All 28 days now have individual meal entries with calories, macros, recipes, and fodmap_safe flags:
- Week 2 (Days 8–14): Seafood focus — salmon poké, prawn bake, cod fish cakes, tuna-quinoa salad
- Week 3 (Days 15–21): Turkey & alternative grains — polenta, millet, cornmeal porridge, turkey stir-fry (without onion/garlic)
- Week 4 (Days 22–28): Best-of mix + rice flour pancakes + rice noodle chicken soup + meal prep Sunday
- Full shopping lists added for all 4 weeks

**FIX 5 (MINOR — Doctor):** Expanded magnesium supplement note to include IBS subtype guidance: "При СРК с диареей (IBS-D) — начинать с малых доз 100–150 мг и оценивать реакцию ЖКТ. При СРК с запором (IBS-C) — магний особенно полезен."

---

## Iteration 2 — Post-Fix Re-Audit

### Trainer Re-Audit

**Macro accuracy:**
- Training days: 1809–1812 kcal (±3% target) — PASS
- Rest days: 1709–1711 kcal (±3% target) — PASS
- Protein: 156–157g/day (±5% of 156g target) — PASS
- Safety floor: all days >1700 kcal > 1200 kcal women's minimum — PASS

**Goal alignment:**
- Pre/post-workout meals on all 12 training days across 28 days — PASS
- Carb distribution: +25g on training vs rest days — PASS
- Progressive weekly themes (Foundation → Seafood → Turkey → Best-of) — PASS

**Variety:**
- Week 1: 7 protein sources (chicken breast, chicken thighs, turkey, salmon, cod, eggs, tuna) — PASS
- Week 2: 6 protein sources (salmon, trout, cod, tuna, prawns, eggs) — PASS
- Week 3: 5 protein sources (turkey, chicken thighs, eggs, salmon, cod) — PASS
- Week 4: 6 protein sources (chicken breast, salmon, trout, cod, turkey, eggs) — PASS
- Carb sources each week: 5–7 different types — PASS
- Rice as main carb dish: max 3x/week in any week — PASS

**Practicality:**
- All recipes under 30 minutes — PASS
- Travel plan with fastfood/canteen/convenience store options — PASS
- IBS-specific travel tips included — PASS
- Meal prep Sunday plan (Day 28) with 4-container batch cooking — PASS

**No Trainer Issues Found**

### Doctor Re-Audit

**Low-FODMAP protocol compliance:**
- Wheat/rye: zero presence in plan — PASS
- Onion/garlic: explicitly excluded from all recipes; cooking notes confirm this — PASS
- Legumes (beans, chickpeas, lentils): zero presence — PASS
- Lactose: all dairy is lactose-free; hard cheeses used (parmesan/cheddar = <0.1g lactose/serving) — PASS
- Apples/pears/stone fruits (peaches, plums, cherries): zero presence — PASS
- Cashews/pistachios: zero; only almonds (Low-FODMAP), walnuts (Low-FODMAP), pumpkin seeds (Low-FODMAP) — PASS
- Honey/agave/sorbitol: not in plan (maple syrup in Day 4 and Day 28 is pure maple syrup, Low-FODMAP at 1 tbsp) — PASS

**Portion-sensitive foods verified:**
- Broccoli: strictly 75g, cooked only, with Monash reference — PASS
- Avocado: 30g (1/8 fruit) in all instances — PASS
- Banana: 1/2 ripe in all pre-workout uses — PASS
- Pumpkin: 75g max noted — PASS

**Fiber:** ~18–22g/day estimate documented — within 25g IBS initial cap — PASS

**Deficit safety:** −400 kcal/day — well within −750 kcal safe limit — PASS

**Protein safety:** 2.2g/kg = 156g — well below 3.0g/kg kidney threshold — PASS

**Supplements — IBS-safe stack:**
- Rice protein isolate (no lactose, no inulin) — PASS
- Omega-3 fish oil (anti-inflammatory) — PASS
- Magnesium glycinate/citrate with IBS-subtype caveat — PASS
- Probiotics (L. rhamnosus GG or B. infantis — evidenced for IBS) with capsule filler warning — PASS
- Vitamin D3 — PASS
- Marine collagen (gut barrier support relevant to IBS) — PASS

**Disclaimer:** verbatim mandatory disclaimer present — PASS

**No Doctor Issues Found**

### Scores — Iteration 2
| Dimension | Score | Notes |
|-----------|-------|-------|
| Safety | 9/10 | Zero red flags; all FODMAP limits enforced; deficit safe; disclaimer present |
| Completeness | 9/10 | All 28 days fully detailed; 4 shopping lists; supplements; travel plan; meal prep |
| Practicality | 9/10 | <30 min recipes; IBS travel tips; Sunday meal prep; canteen guidance |
| Medical accuracy | 9/10 | Full Low-FODMAP Monash University compliance; all condition rules applied |

**Status: PASSED ✅ — All scores ≥ 8. Stopping at Iteration 2.**

---

## Final Scores
| Safety | Completeness | Practicality | Medical accuracy |
|--------|-------------|-------------|-----------------|
| **9/10** | **9/10** | **9/10** | **9/10** |

**Overall: 36/40 (90%)**
**Status: PASSED ✅**

---

## Summary of Changes Across Iterations

| Iteration | Key Change | Impact |
|-----------|-----------|--------|
| 1 → 2 | Fixed broccoli dose: 150г → 75г (Monash Low-FODMAP limit) | Medical accuracy: 7 → 9 |
| 1 → 2 | Rotated Day 5 Завтрак от рисовой каши к гречневой | Trainer/variety compliance |
| 1 → 2 | Added fiber estimate (~18–22г/day) to safety notes | Safety: 7 → 9 |
| 1 → 2 | Expanded Weeks 2–4 from summaries to full 28-day plans | Completeness: 7 → 9 |
| 1 → 2 | Added IBS subtype caveat to magnesium supplement | Medical accuracy improvement |

---

## Low-FODMAP Compliance Summary

| Category | Status |
|----------|--------|
| Grains | Rice, buckwheat, GF oats, quinoa, millet, polenta, rice flour — all SAFE |
| Proteins | Chicken, turkey, salmon, cod, trout, tuna, prawns, eggs — all SAFE |
| Dairy | Lactose-free milk/yogurt, hard cheeses only — SAFE |
| Vegetables | Spinach, carrots, zucchini, bell pepper, tomatoes, cucumber, potatoes — all SAFE |
| Fruits | Blueberries, strawberries, raspberries, mandarin, lemon, lime, banana (1/2) — SAFE |
| Nuts | Almonds, walnuts, pumpkin seeds — SAFE (cashews/pistachios excluded) |
| Fats | Olive oil, sesame oil (small), almond butter — SAFE |
| Excluded | Onion, garlic, wheat, rye, legumes, lactose, apples, pears, stone fruits, cashews, pistachios, honey, agave, sorbitol |

---

## Disclaimer
«Данный план питания носит информационно-консультационный характер и не является медицинской рекомендацией. Перед началом любой диеты проконсультируйтесь с врачом. Автор — сертифицированный тренер, не врач. Результаты индивидуальны. © ArishaFit»
