#!/usr/bin/env python3
"""
Откат прошлого «костыля» со static-фреймами:

1. Восстанавливаем анимации NKJ8o6x и cuKYxhu. Оригинальные 720x720
   webp потеряны (я их перезаписал static). CDN даёт только 180x180,
   апскейлим до 720 через LANCZOS — для плоского вектор-стиля
   ExerciseDB работает приемлемо.

2. Переименовываем в плане — чтобы названия одного и того же
   exerciseId в разных контекстах чётко отличались:
   - NKJ8o6x в warmup ACTIVATE → «Наклон таза лёжа — активация кора»
   - NKJ8o6x в cooldown BREATHE → «Диафрагмальное дыхание в позе наклон таза лёжа»

3. Для cuKYxhu (warmup MOBILIZE) — оставляем «Наклон таза стоя»,
   анимация соответствует названию.

После:
  python scripts/migrate_json_to_db.py --wipe --plan training-skill/output/plan_andrey_v6.json
  python training-skill/scripts/fill_template.py --plan training-skill/output/plan_andrey_v6.json --output training-skill/output/andrey_v6_rendered.html
  cp training-skill/output/andrey_v6_rendered.html docs/andrey.html
"""
import json
import subprocess
from pathlib import Path
from PIL import Image
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
V6_PATH = ROOT / 'training-skill' / 'output' / 'plan_andrey_v6.json'
GIFS_HD = ROOT / 'exercisedb_data' / 'gifs_hd'
MP4_DIR = ROOT / 'exercisedb_data' / 'mp4'
MP4_PAUSED_DIR = ROOT / 'exercisedb_data' / 'mp4_paused'
TMP = ROOT / 'exercisedb_data' / 'tmp'
TMP.mkdir(exist_ok=True)


def download_cdn(exercise_id):
    """Скачать original gif из ExerciseDB CDN (180x180)."""
    url = f"https://static.exercisedb.dev/media/{exercise_id}.gif"
    out = TMP / f"{exercise_id}.gif"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/gif,image/*,*/*;q=0.8',
            'Referer': 'https://exercisedb.dev/',
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            out.write_bytes(resp.read())
        return out
    except Exception as e:
        print(f"  [ERR] download {exercise_id}: {e}")
        return None


def restore_animation(exercise_id):
    """GIF 180x180 animated → upscale 720x720 LANCZOS → animated WebP 720x720."""
    src = download_cdn(exercise_id)
    if not src:
        return False

    im = Image.open(src)
    n = im.n_frames
    print(f"  [{exercise_id}] source: {im.size}, {n} frames")

    frames = []
    duration = im.info.get('duration', 100)
    for i in range(n):
        im.seek(i)
        frame = im.copy().convert('RGBA')
        # Upscale до 720x720 через LANCZOS (качественно для плоской вектор-графики)
        frame = frame.resize((720, 720), Image.LANCZOS)
        frames.append(frame)

    out_webp = GIFS_HD / f'{exercise_id}.webp'
    frames[0].save(
        out_webp,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        format='WEBP',
        quality=92,
    )
    print(f"  [OK] {out_webp.name} -> 720x720 animated ({n} frames)")

    # Чистим временный файл (закрыть PIL-хэндл сначала)
    im.close()
    try:
        src.unlink(missing_ok=True)
    except PermissionError:
        pass  # Windows sometimes holds file briefly — not critical
    return True


def regenerate_mp4_from_webp(exercise_id):
    """Из animated webp → mp4 (animated) + mp4_paused (animated copy)."""
    src_webp = GIFS_HD / f'{exercise_id}.webp'
    mp4_out = MP4_DIR / f'{exercise_id}.mp4'
    mp4_paused_out = MP4_PAUSED_DIR / f'{exercise_id}.mp4'

    if not src_webp.exists():
        return False

    im = Image.open(src_webp)
    n = im.n_frames
    # Средняя длительность кадра
    durations = []
    for i in range(n):
        im.seek(i)
        durations.append(im.info.get('duration', 100))
    avg_dur = sum(durations) / len(durations) if durations else 100
    fps = max(5, min(30, round(1000 / avg_dur) if avg_dur > 0 else 10))

    # PNG-поток → GIF → ffmpeg → mp4
    tmp_gif = src_webp.with_suffix('.tmp.gif')
    frames = []
    for i in range(n):
        im.seek(i)
        frames.append(im.copy().convert('RGB'))
    frames[0].save(
        tmp_gif, save_all=True, append_images=frames[1:],
        duration=durations, loop=0,
    )

    for out_path in (mp4_out, mp4_paused_out):
        out_path.parent.mkdir(exist_ok=True, parents=True)
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-i', str(tmp_gif),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-vf', f'fps={fps},scale=720:720',
            '-movflags', '+faststart',
            str(out_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"  [OK] {out_path.name} regenerated (fps {fps})")
        except subprocess.CalledProcessError as e:
            print(f"  [ERR] {out_path}: {e.stderr.decode()[:200]}")
        except FileNotFoundError:
            print("  [ERR] ffmpeg not found in PATH")
            tmp_gif.unlink(missing_ok=True)
            return False

    tmp_gif.unlink(missing_ok=True)
    return True


def rename_uses_in_plan():
    """Переименовать использование NKJ8o6x в плане для ясности."""
    v6 = json.loads(V6_PATH.read_text(encoding='utf-8'))
    renamed = 0

    # WARMUP blocks
    for wtype in ('strength', 'cardio'):
        blocks = v6.get('warmups', {}).get(wtype, {}).get('blocks', [])
        for block in blocks:
            phase = block.get('phase', '')
            for item in block.get('items', []):
                if item.get('exerciseId') == 'NKJ8o6x':
                    old = item.get('nameRu', '')
                    if phase == 'activate':
                        item['nameRu'] = 'Наклон таза лёжа — активация кора'
                        renamed += 1
                        print(f"  [RENAME] warmup/{wtype}/{phase}: {old} -> {item['nameRu']}")

    # COOLDOWN blocks
    for ctype in ('strength', 'cardio'):
        blocks = v6.get('cooldowns', {}).get(ctype, {}).get('blocks', [])
        for block in blocks:
            phase = block.get('phase', '')
            for item in block.get('items', []):
                if item.get('exerciseId') == 'NKJ8o6x':
                    old = item.get('nameRu', '')
                    if phase == 'breathe':
                        item['nameRu'] = 'Диафрагмальное дыхание в позе «наклон таза лёжа»'
                        renamed += 1
                        print(f"  [RENAME] cooldown/{ctype}/{phase}: {old} -> {item['nameRu']}")

    print(f"  Total renames: {renamed}")
    V6_PATH.write_text(
        json.dumps(v6, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8'
    )


def main():
    print("=" * 60)
    print("RESTORE: NKJ8o6x animation (CDN 180 -> LANCZOS 720)")
    print("=" * 60)
    restore_animation('NKJ8o6x')
    regenerate_mp4_from_webp('NKJ8o6x')

    print()
    print("=" * 60)
    print("RESTORE: cuKYxhu animation (CDN 180 -> LANCZOS 720)")
    print("=" * 60)
    restore_animation('cuKYxhu')
    regenerate_mp4_from_webp('cuKYxhu')

    print()
    print("=" * 60)
    print("RENAME: NKJ8o6x uses in plan for clarity")
    print("=" * 60)
    rename_uses_in_plan()

    print()
    print("=" * 60)
    print("DONE. Next: migrate + render + push.")
    print("=" * 60)


if __name__ == '__main__':
    main()
