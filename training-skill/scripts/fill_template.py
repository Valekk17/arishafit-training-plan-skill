"""
fill_template.py — Заполняет HTML-шаблон данными тренировочного плана.

Вход: plan.json (сгенерированный Opus) + training_plan.html (шаблон)
Выход: готовый HTML файл с base64 GIF'ами и водяными знаками

Использование:
    python fill_template.py --plan plan.json --output output/andrey_plan.html
"""

import json
import base64
import os
import sys
import argparse
from datetime import datetime


TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "training_plan_v4.html")
GIFS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "exercisedb_data", "gifs")
GIFS_HD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "exercisedb_data", "gifs_hd")
MP4_PAUSED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "exercisedb_data", "mp4_paused")
MP4_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "exercisedb_data", "mp4")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
INFO_BOXES_PATH = os.path.join(ASSETS_DIR, "info_boxes.json")


def load_info_boxes():
    """Загрузить библиотеку справок."""
    if os.path.exists(INFO_BOXES_PATH):
        with open(INFO_BOXES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def render_info_btn(info_id):
    """Кнопка '?' рядом с элементом — раскрывает справку."""
    if not info_id:
        return ""
    return f'<button class="info-btn" data-info="{info_id}" title="Научная справка">?</button>'

# Перевод целей
GOAL_RU = {
    "weight_loss": "Похудение / Рекомпозиция",
    "hypertrophy": "Набор мышечной массы",
    "strength": "Развитие силы",
    "endurance": "Мышечная выносливость",
    "maintenance": "Поддержание формы",
}


def media_to_base64(gif_url, gif_local_path, use_relative=False):
    """Вернуть src для медиа. Если use_relative=True — относительный путь к HD WebP.

    Поддерживаемые форматы gif_url:
    - https://... — HTTP URL (ищем в gifs_hd/ и gifs/ по имени, иначе CDN fallback)
    - assets/*.svg|.png — локальные ассеты (иллюстрации вне ExerciseDB, напр. дыхание)
    - data:... — уже data URI, возвращаем как есть
    """
    # 0. Уже data URI — вернуть как есть (напр. inline SVG)
    if gif_url and gif_url.startswith("data:"):
        return gif_url

    # 1. Локальный ассет (assets/breathing_lying.svg и т.п.)
    if gif_url and gif_url.startswith("assets/"):
        asset_path = os.path.join(ASSETS_DIR, os.path.basename(gif_url))
        if os.path.exists(asset_path):
            ext = os.path.splitext(asset_path)[1].lower()
            mime_map = {".svg": "image/svg+xml", ".png": "image/png",
                        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
            mime = mime_map.get(ext, "application/octet-stream")
            with open(asset_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return f"data:{mime};base64,{data}"
        # ассет не найден → пустая строка (лучше fallback в панели)
        return ""

    exercise_id = ""
    if gif_url:
        fname = gif_url.split("/")[-1]
        exercise_id = fname.replace(".gif", "")

    # 1. MP4 с запечёнными паузами (приоритет — паузы на ключевых позах внутри файла,
    #    JS для пауз не нужен, всё через natural playback)
    if exercise_id:
        paused_path = os.path.join(MP4_PAUSED_DIR, exercise_id + ".mp4")
        if os.path.exists(paused_path):
            if use_relative:
                return f"../../exercisedb_data/mp4_paused/{exercise_id}.mp4"
            with open(paused_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return f"data:video/mp4;base64,{data}"

    # 2. Обычные MP4 без пауз (fallback)
    if exercise_id:
        mp4_path = os.path.join(MP4_DIR, exercise_id + ".mp4")
        if os.path.exists(mp4_path):
            if use_relative:
                return f"../../exercisedb_data/mp4/{exercise_id}.mp4"
            with open(mp4_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return f"data:video/mp4;base64,{data}"

    # 2. HD WebP/PNG fallback — относительный путь или base64
    if exercise_id:
        for ext in (".webp", ".png", ".gif"):
            hd_path = os.path.join(GIFS_HD_DIR, exercise_id + ext)
            if os.path.exists(hd_path):
                if use_relative:
                    # Относительный путь от output/ до gifs_hd/
                    return f"../../exercisedb_data/gifs_hd/{exercise_id}{ext}"
                else:
                    mime = "image/webp" if ext == ".webp" else ("image/png" if ext == ".png" else "image/gif")
                    with open(hd_path, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")
                    return f"data:{mime};base64,{data}"

    # 2. Оригинальный GIF — base64 (или CDN fallback)
    if gif_url:
        fname = gif_url.split("/")[-1]
        local_path = os.path.join(GIFS_DIR, fname)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/gif;base64,{data}"
        return gif_url  # CDN fallback

    if gif_local_path:
        local_path = os.path.join(GIFS_DIR, os.path.basename(gif_local_path))
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return f"data:image/gif;base64,{data}"

    return ""


def render_client_fields(client):
    """Рендер полей клиента — v3 info-card стиль."""
    fields = []
    field_map = [
        ("Имя", client.get("name", "—")),
        ("Возраст", f"{client.get('age', '—')} лет"),
        ("Рост", f"{client.get('height_cm', '—')} см"),
        ("Вес", f"{client.get('weight_kg', '—')} кг"),
        ("Опыт", {"beginner": "Начинающий", "intermediate": "Средний", "advanced": "Продвинутый"}.get(client.get("experience"), "—")),
        ("Цель", GOAL_RU.get(client.get("goal"), client.get("goal", "—"))),
    ]
    for label, value in field_map:
        fields.append(f'<div class="info-card"><div class="label">{label}</div><div class="value">{value}</div></div>')
    return "\n    ".join(fields)


def render_medical_warning(client):
    """Рендер предупреждения — v3 alert стиль.

    Ожидаемая структура details (строка): предложения разделены точками.
    Всё содержимое кроме последнего предложения — основной текст;
    постоянная приписка «Программа адаптирована…» рендерится отдельной строкой
    меньшим шрифтом как пометка.
    """
    injuries = client.get("injuries", [])
    details = (client.get("injury_details", "") or "").strip()
    if not injuries and not details:
        return ""
    text = details or ", ".join(injuries)
    return f"""
  <div class="alert alert-warning">
    <span class="alert-icon">⚠️</span>
    <div class="alert-body">
      <strong class="alert-title">Медицинские ограничения</strong>
      <p>{text}</p>
      <p class="alert-note">Программа адаптирована. Противопоказанные упражнения исключены.</p>
    </div>
  </div>"""


def render_overview(program, client):
    """Рендер обзора программы — полноценные читаемые фразы без сокращений."""
    training_days = client.get("training_days", 3)
    weeks = program.get("weeks", 4)
    deload_week = program.get("deload_week", 4)
    goal_ru = GOAL_RU.get(client.get("goal"), client.get("goal", "—"))

    # Русские склонения
    def weeks_word(n):
        if n % 10 == 1 and n % 100 != 11: return "неделя"
        if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14): return "недели"
        return "недель"

    def days_word(n):
        if n % 10 == 1 and n % 100 != 11: return "день"
        if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14): return "дня"
        return "дней"

    items = [
        (f"{training_days} {days_word(training_days)} в неделю", "частота тренировок"),
        (f"{weeks} {weeks_word(weeks)}", "длительность программы"),
        (goal_ru, "главная цель"),
        (f"Неделя {deload_week} — разгрузка", "активное восстановление"),
    ]
    html = ""
    for value, label in items:
        html += f"""
    <div class="stat-card">
      <div class="num">{value}</div>
      <div class="label">{label}</div>
    </div>"""
    return html


USE_RELATIVE = False  # глобальный флаг, устанавливается в main()
EXERCISES_DATA = {}  # накапливается при рендере, вставляется в HTML как JSON
PHASE_DATA = {}     # данные warmup/cooldown-item-ов: { key: {name,gif,tips,warn,reps,details} }

def _derive_gif_url(entry):
    """Вернуть gifUrl. Если в entry только exerciseId — собрать URL из ID."""
    url = entry.get("gifUrl", "") or ""
    if url:
        return url
    eid = entry.get("exerciseId", "")
    if eid:
        return f"https://static.exercisedb.dev/media/{eid}.gif"
    return ""


def _is_video_src(src):
    """Проверка: это видео (MP4) или статическая картинка?"""
    if not src:
        return False
    return src.startswith("data:video/") or src.endswith(".mp4")


def _render_media_tag(src, css_class, alt=""):
    """Рендер <video> для MP4 или <img> для картинок. Пустой src → заглушка."""
    if not src:
        return f'<div class="{css_class}" style="background:var(--border-light)"></div>'
    if _is_video_src(src):
        # autoplay + loop + muted + playsinline = поведение как у GIF (iOS/Android совместимо)
        return (
            f'<video class="{css_class}" autoplay loop muted playsinline preload="metadata">'
            f'<source src="{src}" type="video/mp4"></video>'
        )
    alt_attr = f' alt="{alt}"' if alt else ' alt=""'
    return f'<img class="{css_class}" src="{src}"{alt_attr} loading="lazy">'


def render_exercise(ex, order, week_num, day_num):
    """Рендер упражнения — v4 компактная строка. Данные в EXERCISES_DATA."""
    main_url = _derive_gif_url(ex)
    gif_src = media_to_base64(main_url, ex.get("gifLocalPath"), use_relative=USE_RELATIVE)
    # CDN fallback если нет локального
    if not gif_src and main_url:
        gif_src = main_url
    ex_key = f"w{week_num}d{day_num}e{order}"
    name = ex.get("nameRu", ex.get("nameEn", "—"))

    tags_html = ""
    if ex.get("sets") and ex.get("reps"):
        tags_html += f'<span class="tag tag-primary">{ex["sets"]} × {ex["reps"]}</span>'
    if ex.get("rest_sec"):
        tags_html += f'<span class="tag">⏱ {ex["rest_sec"]}с</span>'
    if ex.get("rpe"):
        tags_html += f'<span class="tag tag-rpe">RPE {ex["rpe"]}</span>'
    if ex.get("tempo"):
        tags_html += f'<span class="tag">Темп {ex["tempo"]}</span>'

    alts = ex.get("alternatives", [])
    alts_data = []
    for a in alts:
        alt_url = _derive_gif_url(a)
        alt_gif = media_to_base64(alt_url, a.get("gifLocalPath", ""), use_relative=USE_RELATIVE)
        if not alt_gif and alt_url:
            alt_gif = alt_url  # CDN fallback
        # Триада НЕРАЗДЕЛИМА: nameRu + gif + tips + warning идут вместе
        alts_data.append({
            "nameRu": a.get("nameRu", a.get("name", "")),
            "gif": alt_gif,
            "tips": a.get("tips", "") or "",
            "warn": a.get("warning", "") or "",
        })

    EXERCISES_DATA[ex_key] = {
        "name": name,
        "gif": gif_src,
        "tagsHtml": tags_html,
        "tips": ex.get("tips", ""),
        "warn": ex.get("warning", "") or "",
        "alts": alts_data,
        "restSec": ex.get("rest_sec", 0) or 0,
    }

    return f"""
    <div class="exercise" data-key="{ex_key}" style="--i:{order-1}" onclick="openPanel('{ex_key}')">
      <input type="checkbox" class="ex-check" data-key="{ex_key}" onclick="event.stopPropagation()">
      <div class="ex-num">{order}</div>
      <div class="ex-main">
        <div class="ex-name">{name}</div>
        <div class="ex-tags">{tags_html}</div>
      </div>
      <div class="ex-chevron">&#x203A;</div>
    </div>"""


def render_warmup_item(item, week_num, day_num, block_phase, item_idx, scope=None):
    """Рендер одного элемента разминки — карточка с GIF + название + reps.

    scope — опциональный префикс ключа, чтобы общая секция не коллидила с дневными.
    """
    exercise_id = item.get("exerciseId", "")
    name = item.get("nameRu", item.get("name", ""))
    reps = item.get("reps") or item.get("duration") or ""
    details = item.get("details", "")
    tips = item.get("tips", "") or ""
    warning = item.get("warning", "") or ""

    # Уникальный ключ для открытия панели
    if scope:
        item_key = f"{scope}-{block_phase}-{item_idx}"
    else:
        item_key = f"wu-w{week_num}-d{day_num}-{block_phase}-{item_idx}"

    # GIF — либо из gifUrl, либо derive из exerciseId
    gif_url = item.get("gifUrl") or ""
    if not gif_url and exercise_id:
        gif_url = f"https://static.exercisedb.dev/media/{exercise_id}.gif"
    gif_src = media_to_base64(gif_url, "") if gif_url else ""

    sub_text = reps or details or ""

    # Сохраняем в PHASE_DATA (для openWarmupPanel)
    PHASE_DATA[item_key] = {
        "name": name,
        "gif": gif_src,
        "reps": reps,
        "details": details,
        "tips": tips,
        "warn": warning,
    }

    media_tag = _render_media_tag(gif_src, "phase-item-gif", alt=name)

    return f"""
      <div class="phase-item" data-key="{item_key}" onclick="openPhaseItem('{item_key}')">
        {media_tag}
        <div class="phase-item-body">
          <div class="phase-item-name">{name}</div>
          <div class="phase-item-reps">{sub_text}</div>
        </div>
      </div>"""


def render_warmup_block(block, week_num, day_num, scope=None):
    """Рендер одного блока разминки (raise / mobilize / potentiate).

    scope — опциональный префикс для ключей элементов (общая секция).
    """
    phase = block.get("phase", "mobilize")
    label = block.get("label", "")
    duration = block.get("duration_min", "")
    items = block.get("items", [])

    icon_map = {
        "raise": ("🔥", "Raise", "raise"),
        "mobilize": ("🔄", "Mobilize", "mobilize"),
        "potentiate": ("💪", "Potentiate", "potentiate"),
    }
    icon, default_label, css_cls = icon_map.get(phase, ("🔄", "Mobilize", "mobilize"))
    display_label = label or default_label

    # Все фазы рендерятся одинаково — карточки с gif + название + reps.
    # Potentiate имеет свою цветовую акцентуацию через модификатор .warmup-items--potentiate
    items_html = "".join(
        render_warmup_item(it, week_num, day_num, phase, idx, scope=scope)
        for idx, it in enumerate(items)
    )
    mod_cls = f" phase-items--{phase}" if phase == "potentiate" else ""
    body = f"""
      <div class="phase-items{mod_cls}">{items_html}
      </div>"""

    return f"""
    <div class="warmup-block">
      <div class="warmup-block-header">
        <span class="warmup-block-icon {css_cls}">{icon}</span>
        <span>{display_label}</span>
        <span class="warmup-block-duration">{duration} мин</span>
      </div>{body}
    </div>"""


def render_warmup(warmup, week_num, day_num):
    """Рендер разминки — если есть blocks → структурированный, иначе fallback."""
    blocks = warmup.get("blocks") or []
    total_min = warmup.get("total_min") or warmup.get("duration_min") or 10

    # Fallback на старый формат (description-only)
    if not blocks:
        description = warmup.get("description", "Кардио + суставная гимнастика")
        return f"""
    <div class="phase phase-warm">
      <span class="phase-icon">🔥</span>
      <span><span class="phase-label">Разминка ({total_min} мин)</span> — {description}</span>
    </div>"""

    blocks_html = "".join(render_warmup_block(b, week_num, day_num) for b in blocks)
    return f"""
    <div class="warmup-container">
      <div class="warmup-header">
        <span class="warmup-header-icon">🔥</span>
        <span>Разминка</span>
        <span class="warmup-header-total">{total_min} мин</span>
      </div>
      {blocks_html}
    </div>"""


def render_cooldown_block(block, week_num, day_num, scope=None):
    """Рендер одного блока заминки (downregulate / stretch / breathe).

    scope — опциональный префикс для ключей (общая секция).
    """
    phase = block.get("phase", "stretch")
    label = block.get("label", "")
    duration = block.get("duration_min", "")
    items = block.get("items", [])

    icon_map = {
        "downregulate": ("🧘", "Снижение пульса", "downregulate"),
        "stretch": ("🪢", "Растяжка", "stretch"),
        "breathe": ("💨", "Дыхание", "breathe"),
    }
    icon, default_label, css_cls = icon_map.get(phase, ("🪢", "Растяжка", "stretch"))
    display_label = label or default_label

    items_html = "".join(
        render_warmup_item(it, week_num, day_num, f"cd-{phase}", idx, scope=scope)
        for idx, it in enumerate(items)
    )
    body = f"""
      <div class="phase-items">{items_html}
      </div>"""

    return f"""
    <div class="cooldown-block">
      <div class="cooldown-block-header">
        <span class="cooldown-block-icon {css_cls}">{icon}</span>
        <span>{display_label}</span>
        <span class="cooldown-block-duration">{duration} мин</span>
      </div>{body}
    </div>"""


def render_cooldown(cooldown, week_num, day_num):
    """Рендер заминки — если есть blocks → структурированная, иначе fallback."""
    blocks = cooldown.get("blocks") or []
    total_min = cooldown.get("total_min") or cooldown.get("duration_min") or 7

    if not blocks:
        description = cooldown.get("description", "Растяжка + дыхание")
        return f"""
    <div class="phase phase-cool">
      <span class="phase-icon">🧊</span>
      <span><span class="phase-label">Заминка ({total_min} мин)</span> — {description}</span>
    </div>"""

    blocks_html = "".join(render_cooldown_block(b, week_num, day_num) for b in blocks)
    return f"""
    <div class="cooldown-container">
      <div class="cooldown-header">
        <span class="cooldown-header-icon">🧊</span>
        <span>Заминка</span>
        <span class="cooldown-header-total">{total_min} мин</span>
      </div>
      {blocks_html}
    </div>"""


def render_shared_prepost_section(plan_data):
    """Общая секция «Разминка и заминка» с табами силовой/кардио."""
    warmups = plan_data.get("warmups") or {}
    cooldowns = plan_data.get("cooldowns") or {}
    if not warmups and not cooldowns:
        return ""

    def tabs(kind, data, block_renderer):
        if not data:
            return ""
        tab_labels = {"strength": "Силовой день", "cardio": "Кардио-день"}
        tabs_html = ""
        content_html = ""
        first = True
        for t, obj in data.items():
            blocks = obj.get("blocks", [])
            total_min = obj.get("total_min") or obj.get("duration_min") or ""
            label = tab_labels.get(t, t)
            active = " active" if first else ""
            hidden = "" if first else " hidden"
            tabs_html += f'<button class="pp-tab{active}" data-pp-kind="{kind}" data-pp-type="{t}">{label} · {total_min} мин</button>'
            # Уникальный scope на каждую комбинацию kind+type — чтобы ключи не коллидили
            scope = f"shared-{kind}-{t}"
            inner_blocks = "".join(block_renderer(b, 0, 0, scope=scope) for b in blocks)
            content_html += (
                f'<div class="pp-content"{hidden} data-pp-kind="{kind}" data-pp-type="{t}">'
                f'{inner_blocks}</div>'
            )
            first = False
        return f'<div class="pp-tabs">{tabs_html}</div>{content_html}'

    warmup_tabs = tabs("warmup", warmups, render_warmup_block)
    cooldown_tabs = tabs("cooldown", cooldowns, render_cooldown_block)

    # Справки на уровне секций — берутся из plan_data
    warmup_info_btn = render_info_btn(plan_data.get("warmups_info_box"))
    cooldown_info_btn = render_info_btn(plan_data.get("cooldowns_info_box"))

    # pp-head оставляем кликабельным div'ом (не button) — чтобы можно было вложить info-btn
    warmup_card = f"""
    <div class="pp-card" data-pp-card="warmup" data-expanded="false">
      <div class="pp-head" data-pp-toggle="warmup" role="button" tabindex="0">
        <span class="pp-icon">🔥</span>
        <div class="pp-title">
          <div class="pp-heading">Разминка перед тренировкой{warmup_info_btn}</div>
          <div class="pp-sub">10–15 мин · обязательно, не пропускать</div>
        </div>
        <span class="pp-chevron">▼</span>
      </div>
      <div class="pp-body">{warmup_tabs}</div>
    </div>""" if warmup_tabs else ""

    cooldown_card = f"""
    <div class="pp-card" data-pp-card="cooldown" data-expanded="false">
      <div class="pp-head" data-pp-toggle="cooldown" role="button" tabindex="0">
        <span class="pp-icon">🧊</span>
        <div class="pp-title">
          <div class="pp-heading">Заминка после тренировки{cooldown_info_btn}</div>
          <div class="pp-sub">6–10 мин · растяжка, дыхание, снижение пульса</div>
        </div>
        <span class="pp-chevron">▼</span>
      </div>
      <div class="pp-body">{cooldown_tabs}</div>
    </div>""" if cooldown_tabs else ""

    return f'<div class="pp-cards">{warmup_card}{cooldown_card}</div>'


def render_day_pre_post(day):
    """Маленький блок в дне: ссылки на общую разминку/заминку."""
    wu_type = day.get("warmup_type")
    cd_type = day.get("cooldown_type")
    if not wu_type and not cd_type:
        return ""
    type_label = {"strength": "силовой", "cardio": "кардио"}.get(wu_type or cd_type, "")
    return f"""
      <div class="day-prepost">
        <a class="day-prepost-link" href="#warmup-cooldown" data-type="{wu_type or ''}">
          <span class="dp-icon">🔥</span><span class="dp-text">Разминка ({type_label})</span><span class="dp-arrow">→</span>
        </a>
        <a class="day-prepost-link" href="#warmup-cooldown" data-type="{cd_type or ''}" data-section="cooldown">
          <span class="dp-icon">🧊</span><span class="dp-text">Заминка ({type_label})</span><span class="dp-arrow">→</span>
        </a>
      </div>"""


def render_day(day, week_num):
    """Рендер дня — v4 с progress ring и completion banner."""
    day_num = day.get("day_number", 1)

    exercises_html = ""
    for i, ex in enumerate(day.get("exercises", []), 1):
        exercises_html += render_exercise(ex, i, week_num, day_num)

    pre_post_html = render_day_pre_post(day)

    n_ex = len(day.get("exercises", []))

    # Избегаем задвоения "День N: День N — ..."
    day_name_ru = day.get('nameRu', day.get('name', ''))
    # Если nameRu уже начинается с "День N" — не префиксируем снова
    if day_name_ru.strip().lower().startswith(f"день {day_num}"):
        heading = day_name_ru
    else:
        heading = f"День {day_num}: {day_name_ru}"

    info_btn = render_info_btn(day.get("info_box"))

    return f"""
  <div class="day-card">
    <div class="day-top">
      <div class="day-top-left">
        <h3>{heading}{info_btn}</h3>
        <span class="day-badge">{day.get('name', '')}</span>
      </div>
      <div class="day-ring-wrap">
        <svg class="day-ring" width="28" height="28" viewBox="0 0 28 28">
          <circle class="day-ring-bg" cx="14" cy="14" r="12"/>
          <circle class="day-ring-fill" cx="14" cy="14" r="12"/>
        </svg>
        <span class="day-progress-text">0/{n_ex}</span>
      </div>
      <button class="day-toggle">−</button>
    </div>
    <div class="day-body">
      <button class="day-reset">↺ Сбросить день</button>
      {pre_post_html}
      {exercises_html}
      <div class="day-complete-banner">🎉 День выполнен! Отличная работа!</div>
    </div>
  </div>"""


def render_week(week):
    """Рендер недели — v4 как tab content."""
    wn = week.get('week_number', 1)
    days_html = ""
    for day in week.get("days", []):
        days_html += render_day(day, wn)

    # Убираем задвоение focus в h2 и week-desc: h2 показываем только номер, focus идёт одним блоком в desc
    focus_text = week.get('focus', '')
    info_btn = render_info_btn(week.get("info_box"))
    return f"""
<div class="week-content {'active' if wn == 1 else ''}" id="week{wn}">
  <div class="week-banner">
    <button class="week-toggle" title="Свернуть/развернуть неделю">−</button>
    <div class="week-num">Неделя {wn}</div>
    <h2>{f'Неделя {wn}'}{info_btn}</h2>
    <div class="week-desc">{focus_text}</div>
  </div>
  {days_html}
</div>"""


def fill_template(plan_data):
    """Заполнить HTML шаблон данными плана."""
    global EXERCISES_DATA, PHASE_DATA
    EXERCISES_DATA = {}  # сбрасываем перед каждым рендером
    PHASE_DATA = {}

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    client = plan_data.get("client", {})
    program = plan_data.get("program", {})
    weeks = plan_data.get("weeks", [])

    # Count totals
    total_exercises = 0
    total_sets = 0
    for week in weeks:
        if week.get("week_number", 1) == 1:  # count only week 1
            for day in week.get("days", []):
                for ex in day.get("exercises", []):
                    total_exercises += 1
                    total_sets += ex.get("sets", 0)

    # Plan ID для версионирования localStorage (чтобы swap'ы от старого плана не влияли на новый)
    import hashlib
    plan_signature = (
        client.get("name", "") + "_" +
        program.get("split_type", "") + "_" +
        str(program.get("weeks", 4)) + "_" +
        str(len(weeks))
    )
    # Добавляем первые exerciseIds для уникальности
    first_ids = []
    for w in weeks[:2]:
        for d in w.get("days", [])[:2]:
            for ex in d.get("exercises", [])[:2]:
                first_ids.append(str(ex.get("exerciseId", "")))
    plan_signature += "_" + "_".join(first_ids)
    plan_id = hashlib.md5(plan_signature.encode()).hexdigest()[:12]

    # Замены
    html = html.replace("{{plan_id}}", plan_id)
    html = html.replace("{{plan_title}}", "Тренировочный план")
    html = html.replace("{{client_name}}", client.get("name", "Клиент"))
    html = html.replace("{{plan_weeks}}", str(program.get("weeks", 4)))
    html = html.replace("{{training_days}}", str(client.get("training_days", "?")))
    html = html.replace("{{goal_ru}}", GOAL_RU.get(client.get("goal"), client.get("goal", "")))
    html = html.replace("{{total_exercises}}", str(total_exercises))
    html = html.replace("{{total_sets}}", str(total_sets))
    html = html.replace("{{year}}", str(datetime.now().year))
    html = html.replace("{{date}}", datetime.now().strftime("%d.%m.%Y"))

    # Клиент
    html = html.replace("{{client_fields}}", render_client_fields(client))
    html = html.replace("{{medical_warning}}", render_medical_warning(client))

    # Обзор программы
    html = html.replace("{{program_overview_items}}", render_overview(program, client))

    # Week tabs
    tabs_html = ""
    for week in weeks:
        wn = week.get("week_number", 1)
        active = "active" if wn == 1 else ""
        tabs_html += f'<button class="week-tab {active}" data-week="week{wn}">Неделя {wn}</button>\n'
    html = html.replace("{{week_tabs}}", tabs_html)

    # Недели — наполняет EXERCISES_DATA и PHASE_DATA
    weeks_html = ""
    for week in weeks:
        weeks_html += render_week(week)
    html = html.replace("{{weeks_content}}", weeks_html)

    # Общая секция разминки/заминки — тоже наполняет PHASE_DATA (shared-*)
    # ВАЖНО: рендерим ДО инъекции phase_data_json, иначе shared-items пропадут
    html = html.replace("{{warmup_cooldown_block}}", render_shared_prepost_section(plan_data))

    # Теперь инжектируем накопленные данные в JS-константы
    exercises_json = json.dumps(EXERCISES_DATA, ensure_ascii=False)
    html = html.replace("{{exercise_data_json}}", exercises_json)

    phase_json = json.dumps(PHASE_DATA, ensure_ascii=False)
    html = html.replace("{{phase_data_json}}", phase_json)

    # Библиотека справок
    info_boxes = load_info_boxes()
    info_json = json.dumps(info_boxes, ensure_ascii=False)
    html = html.replace("{{info_boxes_json}}", info_json)

    return html


def main():
    global USE_RELATIVE
    parser = argparse.ArgumentParser(description="Fill HTML template with training plan data")
    parser.add_argument("--plan", required=True, help="Path to plan JSON")
    parser.add_argument("--output", default="output/plan.html", help="Output HTML path")
    parser.add_argument("--hd", action="store_true", help="Use relative paths for HD WebP (no base64 embed)")

    args = parser.parse_args()
    USE_RELATIVE = args.hd

    with open(args.plan, "r", encoding="utf-8") as f:
        plan_data = json.load(f)

    print(f"Filling template with plan for {plan_data.get('client', {}).get('name', '?')}...")
    if USE_RELATIVE:
        print("Mode: MP4/HD WebP via relative paths")
    else:
        print("Mode: base64 embedded MP4 (приоритет) + PNG для статичных ассетов")

    html = fill_template(plan_data)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    size_mb = os.path.getsize(args.output) / 1024 / 1024
    print(f"Saved: {args.output} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
