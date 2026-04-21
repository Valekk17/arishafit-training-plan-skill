#!/usr/bin/env python3
"""
Создать кастомную БД-запись `pose_supine_knees_bent` со статичной
картинкой (лёжа на полу, колени согнуты — нейтральная поза для
pelvic tilt activation и диафрагмального дыхания).

Источник картинки: frame 0 MP4 NKJ8o6x (это и есть стартовая поза).

Обновить план:
- Warmup strength ACTIVATE: NKJ8o6x -> pose_supine_knees_bent (static)
  Имя в плане: «Наклон таза лёжа — активация кора»
- Cooldown strength BREATHE: добавить item с pose_supine_knees_bent
  Имя: «Диафрагмальное дыхание лёжа»
- Cooldown cardio BREATHE: аналогично

Текстовое описание (которое было вместо item для breathe) — перенести
обратно в tips item'а.
"""
import json
import sys
import subprocess
from pathlib import Path
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
V6_PATH = ROOT / 'training-skill' / 'output' / 'plan_andrey_v6.json'
DB_PATH = ROOT / 'exercisedb_data' / 'exercise_db_final.json'
GIFS_HD = ROOT / 'exercisedb_data' / 'gifs_hd'
MP4_DIR = ROOT / 'exercisedb_data' / 'mp4'
MP4_PAUSED_DIR = ROOT / 'exercisedb_data' / 'mp4_paused'

CUSTOM_ID = 'pose_supine_knees_bent'
SOURCE_MP4 = MP4_DIR / 'NKJ8o6x.mp4'

PELVIC_TILT_TIPS = (
    "КРИТИЧНО: при грыже L4-L5 это твоя база безопасности — делай каждый день, даже в "
    "дилоуд. Лёжа на спине, колени согнуты, стопы на полу. Активно прижми поясницу к полу, "
    "напрягая нижний пресс — держи 2 сек. Расслабь. **Движение минимальное — таз чуть "
    "подкручивается, это не мост**. Даёт нейромышечный шаблон «нейтральный таз под нагрузкой» — "
    "нужен для Dead Bug, ягодичного моста, жима ногами."
)
PELVIC_TILT_WARNING = (
    "Работаем ЛЕГКО — цель почувствовать нижний пресс и ягодицы, а не устать. **Никакого "
    "подъёма таза вверх (это не glute bridge)** — только прижимание поясницы к полу. Не "
    "задерживай дыхание, дыши ровно через нос."
)

BREATH_TIPS_STRENGTH = (
    "Лёжа на спине, колени согнуты, стопы на полу. Одна ладонь на груди, вторая на животе. "
    "**Вдох через нос 4 сек** — поднимается ТОЛЬКО живот, грудь неподвижна. **Пауза 2 сек** "
    "на задержке. **Выдох через рот 6 сек** — живот опускается. Это переключает ANS с "
    "симпатики (стресс силовой) на парасимпатику (восстановление) — ускоряет выход кортизола "
    "и засыпание."
)
BREATH_WARNING = (
    "Если кружится голова — дыши мельче, укороти выдох. НЕ включай пресс на выдохе, живот "
    "опускается пассивно. При грыже L4-L5 диафрагмальное дыхание улучшает стабилизацию "
    "ядра — это бонус помимо релаксации."
)
BREATH_TIPS_CARDIO = (
    "После Zone 2 кардио дыхание остаётся частым и грудным. Лёжа на спине, колени согнуты. "
    "Ладонь на животе. **Вдох через нос 4 сек** — живот поднимается. **Пауза 2 сек**. "
    "**Выдох через рот 6 сек**. Переключаешься в парасимпатику, снижается ЧСС покоя."
)
BREATH_WARNING_CARDIO = (
    "Если кружится голова — дыши мельче. Ровное спокойное дыхание, без натуги."
)


def step1_extract_frame():
    """Извлечь frame 0 из NKJ8o6x.mp4 -> сохранить как webp + mp4."""
    if not SOURCE_MP4.exists():
        print(f"[ERR] {SOURCE_MP4} not found — нужна HQ NKJ8o6x")
        return False

    tmp_png = ROOT / 'exercisedb_data' / 'tmp_frame0.png'
    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-i', str(SOURCE_MP4),
        '-vframes', '1',
        str(tmp_png)
    ], check=True)

    # Save as single-frame webp
    im = Image.open(tmp_png).convert('RGBA')
    webp_out = GIFS_HD / f'{CUSTOM_ID}.webp'
    im.save(webp_out, format='WEBP', quality=95)
    print(f"[OK] {webp_out.relative_to(ROOT)} ({im.size[0]}×{im.size[1]})")

    # Static MP4 — 2с петля того же кадра (для template video tag)
    for out in (MP4_DIR / f'{CUSTOM_ID}.mp4', MP4_PAUSED_DIR / f'{CUSTOM_ID}.mp4'):
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error',
            '-loop', '1', '-t', '2',
            '-i', str(tmp_png),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=720:720',
            '-r', '2',
            '-movflags', '+faststart',
            str(out)
        ], check=True)
        print(f"[OK] {out.relative_to(ROOT)}")

    tmp_png.unlink(missing_ok=True)
    return True


def step2_add_db_entry():
    """Добавить запись в exercise_db_final.json."""
    db = json.loads(DB_PATH.read_text(encoding='utf-8'))
    if any(e.get('exerciseId') == CUSTOM_ID for e in db):
        print(f"[SKIP] {CUSTOM_ID} уже в БД")
        return
    db.append({
        "exerciseId": CUSTOM_ID,
        "nameEn": "supine hook-lying pose (static reference)",
        "nameRu": "Поза лёжа с согнутыми коленями",
        "instructions": [
            "Lie on your back on the floor.",
            "Bend knees 90°, feet flat on floor, shoulder-width apart.",
            "Arms relaxed by sides, palms down.",
            "Maintain neutral spine (small natural arch in lower back).",
            "Breathe normally through the nose.",
        ],
        "targetMuscles": ["abs"],
        "bodyParts": ["waist"],
        "equipments": ["body weight"],
        "secondaryMuscles": ["lower back"],
        "movementPatterns": ["posture"],
        "hasAnimation": False,
    })
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[OK] Добавлено в БД: {CUSTOM_ID} ({len(db)} упражнений всего)")


def step3_update_plan():
    """Заменить NKJ8o6x -> pose_supine_knees_bent в ACTIVATE блоках +
    добавить items в BREATHE блоки с этим же ID."""
    v6 = json.loads(V6_PATH.read_text(encoding='utf-8'))

    # 3a. Warmup strength ACTIVATE: заменить NKJ8o6x на pose_supine_knees_bent
    changes = []
    for wtype in ('strength', 'cardio'):
        for block in v6.get('warmups', {}).get(wtype, {}).get('blocks', []):
            if block.get('phase') != 'activate':
                continue
            for it in block.get('items', []):
                if it.get('exerciseId') == 'NKJ8o6x':
                    it['exerciseId'] = CUSTOM_ID
                    it['nameRu'] = "Наклон таза лёжа — активация кора"
                    it['gifUrl'] = f"https://static.exercisedb.dev/media/{CUSTOM_ID}.gif"
                    # Tips уже есть — можно оставить или обновить
                    it['tips'] = PELVIC_TILT_TIPS
                    it['warning'] = PELVIC_TILT_WARNING
                    changes.append(f"warmup/{wtype}/activate: NKJ8o6x -> {CUSTOM_ID}")

    # 3b. Cooldown BREATHE: добавить item с pose_supine_knees_bent
    for ctype in ('strength', 'cardio'):
        for block in v6.get('cooldowns', {}).get(ctype, {}).get('blocks', []):
            if block.get('phase') != 'breathe':
                continue
            # Удалить description, добавить item
            desc = block.pop('description', '')  # перенесём в tips
            if not block.get('items'):
                block['items'] = []
            block['items'].append({
                "exerciseId": CUSTOM_ID,
                "nameRu": "Диафрагмальное дыхание лёжа",
                "reps": "12 циклов (2 мин)",
                "tips": BREATH_TIPS_STRENGTH if ctype == 'strength' else BREATH_TIPS_CARDIO,
                "warning": BREATH_WARNING if ctype == 'strength' else BREATH_WARNING_CARDIO,
                "gifUrl": f"https://static.exercisedb.dev/media/{CUSTOM_ID}.gif",
            })
            changes.append(f"cooldown/{ctype}/breathe: +item {CUSTOM_ID}")

    V6_PATH.write_text(
        json.dumps(v6, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8'
    )
    print("[OK] Plan updated:")
    for c in changes:
        print(f"  - {c}")


def main():
    print("=" * 60)
    print("1. Extract frame 0 of NKJ8o6x -> static media files")
    print("=" * 60)
    if not step1_extract_frame():
        return

    print()
    print("=" * 60)
    print("2. Add custom DB entry: pose_supine_knees_bent")
    print("=" * 60)
    step2_add_db_entry()

    print()
    print("=" * 60)
    print("3. Update plan: use custom ID in ACTIVATE + BREATHE")
    print("=" * 60)
    step3_update_plan()

    print()
    print("DONE. Next: render + push.")


if __name__ == '__main__':
    main()
