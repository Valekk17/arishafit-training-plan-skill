#!/usr/bin/env python3
"""
Финальный фикс дыхания + скорости анимации:

1. Блоки BREATHE (cooldown) — убираем NKJ8o6x item совсем.
   Breathing — это не упражнение с анимацией, это техника в статичной
   позе. Оставляем только label блока + описание текстом через info_box.
   Одновременно добавляем description в сам блок, чтобы фаза не была
   пустой визуально.

2. NKJ8o6x animation — замедляем до 250ms/frame (3s loop вместо 1.2s).
   Pelvic tilt — медленное контролируемое движение, текущие 100ms/кадр
   выглядят как судорога.

3. Regenerate mp4 с медленной скоростью.
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


def slow_animation(exercise_id, new_frame_duration_ms=250):
    """Пересохранить webp с новой длительностью кадра."""
    src = GIFS_HD / f'{exercise_id}.webp'
    if not src.exists():
        print(f"[WARN] {src} not found")
        return False

    im = Image.open(src)
    n = im.n_frames
    frames = []
    for i in range(n):
        im.seek(i)
        frames.append(im.copy().convert('RGBA'))
    im.close()

    frames[0].save(
        src,
        save_all=True, append_images=frames[1:],
        duration=new_frame_duration_ms, loop=0,
        format='WEBP', quality=92,
    )
    total = n * new_frame_duration_ms
    print(f"[OK] {exercise_id}: {n} frames x {new_frame_duration_ms}ms = {total}ms loop")
    return True


def regen_mp4(exercise_id, target_fps=4):
    """Regenerate mp4 with specific fps (4 fps = 250ms/frame)."""
    src_webp = GIFS_HD / f'{exercise_id}.webp'
    mp4_out = MP4_DIR / f'{exercise_id}.mp4'
    mp4_paused = MP4_PAUSED_DIR / f'{exercise_id}.mp4'

    # Extract frames to temp folder, then ffmpeg image sequence
    im = Image.open(src_webp)
    tmp_dir = ROOT / 'exercisedb_data' / 'tmp' / f'{exercise_id}_frames'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for i in range(im.n_frames):
        im.seek(i)
        im.copy().convert('RGB').save(tmp_dir / f'f{i:03d}.png')
    im.close()

    for out in (mp4_out, mp4_paused):
        out.parent.mkdir(exist_ok=True, parents=True)
        cmd = [
            'ffmpeg', '-y', '-loglevel', 'error',
            '-framerate', str(target_fps),
            '-i', str(tmp_dir / 'f%03d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=720:720',
            '-r', str(target_fps),
            '-movflags', '+faststart',
            str(out),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"[OK] {out.name} regenerated ({target_fps} fps)")
        except subprocess.CalledProcessError as e:
            print(f"[ERR] {out}: {e.stderr.decode()[:200]}")

    # Cleanup
    for p in tmp_dir.glob('*.png'):
        p.unlink(missing_ok=True)
    tmp_dir.rmdir()


def remove_breathing_items():
    """Убрать NKJ8o6x item из BREATHE блоков, добавить description в info_box."""
    v6 = json.loads(V6_PATH.read_text(encoding='utf-8'))
    removed = 0

    for ctype in ('strength', 'cardio'):
        for block in v6.get('cooldowns', {}).get(ctype, {}).get('blocks', []):
            if block.get('phase') == 'breathe':
                before = len(block.get('items', []))
                # Extract tips text from the item (для сохранения контента)
                for it in block.get('items', []):
                    if it.get('exerciseId') == 'NKJ8o6x':
                        # Save tips as block's description
                        tips_text = it.get('tips', '') or ''
                        if tips_text and not block.get('description'):
                            block['description'] = tips_text
                # Drop NKJ8o6x items
                block['items'] = [
                    it for it in block.get('items', [])
                    if it.get('exerciseId') != 'NKJ8o6x'
                ]
                removed += before - len(block['items'])
                print(f"[RM] cooldown/{ctype}/breathe: removed {before - len(block['items'])} items, saved tips as description")

    V6_PATH.write_text(
        json.dumps(v6, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8'
    )
    print(f"Total removed breathing items: {removed}")


def main():
    print("=" * 60)
    print("1. SLOW DOWN NKJ8o6x animation (100ms -> 250ms per frame)")
    print("=" * 60)
    slow_animation('NKJ8o6x', new_frame_duration_ms=250)
    regen_mp4('NKJ8o6x', target_fps=4)

    print()
    print("=" * 60)
    print("2. REMOVE NKJ8o6x from BREATHE blocks (save tips as description)")
    print("=" * 60)
    remove_breathing_items()

    print()
    print("DONE. Next: migrate + render + push.")


if __name__ == '__main__':
    main()
