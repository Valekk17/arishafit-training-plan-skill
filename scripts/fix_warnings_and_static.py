#!/usr/bin/env python3
"""
Фикс трёх проблем:

1. Двойные эмодзи ⚠️ 🚫 в warnings.
   Template автоматически добавляет ⚠️ префикс к warning при рендере панели.
   Убираем 🚫 из начала warnings в v6.json (тавтология).

2. Анимация cuKYxhu (Наклон таза стоя) не соответствует названию —
   показывает наклон корпуса вперёд. Меняем на 1-кадровый webp + mp4
   (статичная поза «стоя нейтрально» вместо лживой анимации).

3. NKJ8o6x (Диафрагмальное дыхание лёжа) — анимация показывает
   glute bridge, не исходную позу дыхания. Аналогично: статичный 1 кадр
   с позы «лёжа на спине, колени согнуты» — реальная стартовая позиция
   для дыхательной практики.

После запуска нужно:
  python scripts/migrate_json_to_db.py --wipe --plan training-skill/output/plan_andrey_v6.json
  python training-skill/scripts/fill_template.py --plan training-skill/output/plan_andrey_v6.json --output training-skill/output/andrey_v6_rendered.html
  cp training-skill/output/andrey_v6_rendered.html docs/andrey.html
"""
import json
import subprocess
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
V6_PATH = ROOT / 'training-skill' / 'output' / 'plan_andrey_v6.json'
GIFS_HD = ROOT / 'exercisedb_data' / 'gifs_hd'
MP4_DIR = ROOT / 'exercisedb_data' / 'mp4'
MP4_PAUSED_DIR = ROOT / 'exercisedb_data' / 'mp4_paused'


def strip_emoji_prefix_from_warnings():
    """Убираем ведущие 🚫 (и пробелы после) из всех warnings в v6."""
    v6 = json.loads(V6_PATH.read_text(encoding='utf-8'))
    total_fixed = 0

    def walk(obj):
        nonlocal total_fixed
        if isinstance(obj, dict):
            w = obj.get('warning')
            if isinstance(w, str):
                # Убираем 🚫 и любой пробел/emoji variant-selector после
                if w.startswith('🚫'):
                    new_w = w[1:].lstrip(' \ufe0f\u200d')
                    obj['warning'] = new_w
                    total_fixed += 1
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(v6)
    print(f"[1/3] Stripped 'no-entry' prefix from warnings: {total_fixed}")

    V6_PATH.write_text(
        json.dumps(v6, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8'
    )


def make_static_webp(exercise_id, frame_idx=0):
    """Заменяем webp на 1-кадровую версию (визуально статика)."""
    src = GIFS_HD / f'{exercise_id}.webp'
    if not src.exists():
        print(f"  [WARN] {src} не найден — пропуск")
        return False

    im = Image.open(src)
    im.seek(frame_idx)
    # Сохраняем как single-frame webp, заменяя оригинал
    im.save(src, 'WEBP', lossless=False, quality=92)
    print(f"  [OK] {exercise_id}.webp -> 1 frame (idx {frame_idx})")
    return True


def regenerate_mp4_for(exercise_id):
    """Перегенерируем mp4 и mp4_paused из статичного webp."""
    src_webp = GIFS_HD / f'{exercise_id}.webp'
    mp4_out = MP4_DIR / f'{exercise_id}.mp4'
    mp4_paused_out = MP4_PAUSED_DIR / f'{exercise_id}.mp4'

    if not src_webp.exists():
        return

    # Экспортируем 1 кадр как PNG
    im = Image.open(src_webp)
    im.seek(0)
    tmp_png = src_webp.with_suffix('.tmp.png')
    im.save(tmp_png, 'PNG')

    # Из PNG → MP4 с длительностью 2с (ffmpeg loop)
    for out_path in (mp4_out, mp4_paused_out):
        out_path.parent.mkdir(exist_ok=True, parents=True)
        # -loop 1 -i png — зацикливаем кадр
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-loop', '1', '-i', str(tmp_png),
            '-c:v', 'libx264',
            '-t', '2',           # длительность 2 сек
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=720:720',
            '-movflags', '+faststart',
            str(out_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"  [OK] {out_path.name} перегенерирован (2s static)")
        except subprocess.CalledProcessError as e:
            print(f"  [ERR] {out_path}: {e.stderr.decode()[:200]}")
        except FileNotFoundError:
            print("  [ERR] ffmpeg не найден в PATH — пропуск mp4")
            tmp_png.unlink(missing_ok=True)
            return False

    tmp_png.unlink(missing_ok=True)
    return True


def main():
    print("=" * 60)
    print("FIX 1: warnings (strip leading 'no-entry' emoji)")
    print("=" * 60)
    strip_emoji_prefix_from_warnings()

    print()
    print("=" * 60)
    print("FIX 2 + 3: static frames for cuKYxhu and NKJ8o6x")
    print("=" * 60)
    print("\n[2/3] cuKYxhu (standing pelvic tilt) -> static neutral pose")
    make_static_webp('cuKYxhu', frame_idx=0)
    regenerate_mp4_for('cuKYxhu')

    print("\n[3/3] NKJ8o6x (lying pelvic tilt / breathing) -> static pose 'lying, knees bent'")
    make_static_webp('NKJ8o6x', frame_idx=0)
    regenerate_mp4_for('NKJ8o6x')

    print()
    print("=" * 60)
    print("DONE. Next: migrate + render + push.")
    print("=" * 60)


if __name__ == '__main__':
    main()
