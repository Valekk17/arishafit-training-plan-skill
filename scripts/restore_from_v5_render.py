#!/usr/bin/env python3
"""
Восстановить HQ MP4 для NKJ8o6x из старого рендера v5 (который был сделан
ДО моего «static-костыля» и содержит оригинальные HQ base64-анимации).

Логика: PHASE_DATA[key] = {..., gif: 'data:video/mp4;base64,XXXX'} в JS-блоке
HTML. Ищем base64 по позиции:
1. В текущем v6 HTML находим base64 для NKJ8o6x (плохой апскейл 180→720)
2. Смотрим его JS-ключ / позицию в PHASE_DATA
3. По тому же ключу достаём base64 из v5 HTML (HQ оригинал)
4. Декодируем в NKJ8o6x.mp4 (перезаписываем плохую копию)
5. Извлекаем frames → пересоздаём webp
"""
import re
import sys
import base64
import subprocess
import hashlib
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
V5_HTML = ROOT / 'training-skill' / 'output' / 'andrey_v5_rendered.html'
V6_HTML = ROOT / 'training-skill' / 'output' / 'andrey_v6_rendered.html'
MP4_OUT = ROOT / 'exercisedb_data' / 'mp4' / 'NKJ8o6x.mp4'
MP4_PAUSED_OUT = ROOT / 'exercisedb_data' / 'mp4_paused' / 'NKJ8o6x.mp4'
WEBP_OUT = ROOT / 'exercisedb_data' / 'gifs_hd' / 'NKJ8o6x.webp'
TMP_DIR = ROOT / 'exercisedb_data' / 'tmp'


def find_phase_data_entries(html):
    """Возвращает список (key, gif_b64) — ищет data-key="..." блоки с
    inline <video><source src="data:video/mp4;base64,...">."""
    entries = []
    pattern = re.compile(
        r'data-key="([^"]+)"[^>]*>.*?<source src="data:video/mp4;base64,([A-Za-z0-9+/=]+)"',
        re.DOTALL
    )
    for m in pattern.finditer(html):
        entries.append((m.group(1), m.group(2)))
    return entries


def main():
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    print("Читаю HTML файлы...")
    v5_html = V5_HTML.read_text(encoding='utf-8')
    v6_html = V6_HTML.read_text(encoding='utf-8')

    v5_entries = find_phase_data_entries(v5_html)
    v6_entries = find_phase_data_entries(v6_html)
    print(f"v5: {len(v5_entries)} PHASE_DATA entries with video")
    print(f"v6: {len(v6_entries)} PHASE_DATA entries with video")

    # Все keys в обоих должны совпадать для warmup/cooldown ACTIVATE блоков
    # NKJ8o6x — в warmup ACTIVATE и cooldown BREATHE. В v6 я удалил из BREATHE.
    # Нахожу keys в v5 которые содержат "activate" и имеют базу с большим size (HQ vs upscale)

    # Идём иначе: сравниваем v5 и v6 по ключам. Если base64 отличаются = это наш случай
    v5_map = dict(v5_entries)
    v6_map = dict(v6_entries)
    common_keys = set(v5_map) & set(v6_map)
    print(f"Common keys: {len(common_keys)}")

    differing = []
    for k in common_keys:
        if v5_map[k] != v6_map[k]:
            differing.append((k, v5_map[k], v6_map[k]))
    print(f"Differing entries (v5 HQ vs v6 bad): {len(differing)}")
    for k, v5b, v6b in differing:
        print(f"  {k}: v5={len(v5b)}B, v6={len(v6b)}B")

    # ЯВНО выбираем ключ для NKJ8o6x — он был в warmup strength activate, первый item
    target_key = 'shared-warmup-strength-activate-0'
    if target_key not in v5_map:
        print(f"[ERR] key {target_key} not found in v5 HTML")
        return
    hq_b64 = v5_map[target_key]
    print(f"\nHQ base64 for {target_key}: {len(hq_b64)} chars (~{len(hq_b64)*3//4} bytes decoded)")

    # Декодируем в mp4
    mp4_bytes = base64.b64decode(hq_b64)
    print(f"Decoded MP4: {len(mp4_bytes)} bytes")

    MP4_OUT.parent.mkdir(parents=True, exist_ok=True)
    MP4_OUT.write_bytes(mp4_bytes)
    MP4_PAUSED_OUT.parent.mkdir(parents=True, exist_ok=True)
    MP4_PAUSED_OUT.write_bytes(mp4_bytes)
    print(f"[OK] Восстановлен: {MP4_OUT}")
    print(f"[OK] Восстановлен: {MP4_PAUSED_OUT}")

    # Извлекаем frames из HQ MP4 → пересоздаём webp
    frames_dir = TMP_DIR / 'NKJ8o6x_frames'
    frames_dir.mkdir(exist_ok=True)
    for p in frames_dir.glob('*.png'):
        p.unlink()

    subprocess.run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-i', str(MP4_OUT),
        str(frames_dir / 'f%03d.png')
    ], check=True)

    png_files = sorted(frames_dir.glob('*.png'))
    print(f"Extracted {len(png_files)} frames to webp")

    frames = [Image.open(p).convert('RGBA') for p in png_files]
    # Preserve original FPS — 10fps ≈ 100ms/frame (original ExerciseDB timing)
    frame_duration_ms = 100
    frames[0].save(
        WEBP_OUT,
        save_all=True, append_images=frames[1:],
        duration=frame_duration_ms, loop=0,
        format='WEBP', quality=92,
    )
    print(f"[OK] Restored: {WEBP_OUT} ({len(frames)} frames / {frame_duration_ms}ms each)")

    # Cleanup
    for p in frames_dir.glob('*.png'):
        p.unlink()
    frames_dir.rmdir()

    print("\nDONE. Next: migrate + render.")


if __name__ == '__main__':
    main()
