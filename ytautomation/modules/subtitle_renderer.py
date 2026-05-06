from __future__ import annotations

import random
import textwrap
from typing import Any

try:
    from moviepy import ColorClip, CompositeVideoClip, TextClip
except Exception:
    from moviepy.editor import ColorClip, CompositeVideoClip, TextClip  # type: ignore

from ytautomation.core.moviepy_compat import set_duration, set_opacity, set_position, set_start


SUBTITLE_WRAP_CHARS = 40
SUBTITLE_FONT_SIZE = 54
SUBTITLE_WIDTH_RATIO = 0.85
SUBTITLE_BG_WIDTH_RATIO = 0.9
SUBTITLE_Y_RATIO = 0.25
SUBTITLE_BG_PADDING_Y = 34
SUBTITLE_STROKE_WIDTH = 5
SUBTITLE_SHADOW_STROKE_WIDTH = 7
SUBTITLE_SHADOW_OFFSET = (5, 6)
SUBTITLE_SHADOW_OPACITY = 0.65
SUBTITLE_FONTS = ("Impact", "Arial-Bold", "Arial Bold", "Arial", "DejaVuSans-Bold", None)
SUBTITLE_COLORS = (
    "white",
    "yellow",
    "cyan",
    "lime",
    "magenta",
    "orange",
    "deepskyblue",
    "hotpink",
)
CHARACTER_A_X_RATIO = 0.02
CHARACTER_A_Y_RATIO = 0.19
CHARACTER_B_X_MARGIN_RATIO = 0.02
CHARACTER_B_Y_RATIO = 0.31


def _get_attr_or_key(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)


def _get_optional_attr_or_key(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _timeline_segments(timeline: Any) -> list[Any]:
    return _get_attr_or_key(timeline, "segments")


def _script_line(script: Any, index: int) -> Any:
    if isinstance(script, dict) and "lines" in script:
        return script["lines"][index]
    if hasattr(script, "lines"):
        return script.lines[index]
    return script[index]


def _wrap_subtitle_text(text: str) -> str:
    lines = textwrap.wrap(text.strip(), width=SUBTITLE_WRAP_CHARS)
    return "\n".join(lines) if lines else text


def _make_text_clip(
    text: str,
    W: int,
    color: str,
    stroke_color: str = "black",
    stroke_width: int = SUBTITLE_STROKE_WIDTH,
) -> TextClip:
    base_kwargs = {
        "color": color,
        "stroke_color": stroke_color,
        "stroke_width": stroke_width,
        "method": "caption",
        "size": (int(W * SUBTITLE_WIDTH_RATIO), None),
    }

    last_error: Exception | None = None
    for font in SUBTITLE_FONTS:
        align_variants = ({"align": "center"}, {"text_align": "center"}, {})
        for align_kwargs in align_variants:
            kwargs = {**base_kwargs, **align_kwargs}
            if font is not None:
                kwargs["font"] = font

            for text_key in ("text", "txt"):
                text_kwargs = {**kwargs, text_key: text}
                try:
                    return TextClip(fontsize=SUBTITLE_FONT_SIZE, **text_kwargs)
                except TypeError:
                    try:
                        return TextClip(font_size=SUBTITLE_FONT_SIZE, **text_kwargs)
                    except Exception as exc:
                        last_error = exc
                except Exception as exc:
                    last_error = exc

    raise RuntimeError("Unable to create subtitle TextClip") from last_error


def _speaker_order(timeline: Any) -> list[str]:
    speakers: list[str] = []
    for segment in _timeline_segments(timeline):
        speaker = str(_get_attr_or_key(segment, "speaker"))
        if speaker not in speakers:
            speakers.append(speaker)
    return speakers


def _speaker_colors(speakers: list[str]) -> dict[str, str]:
    colors = list(SUBTITLE_COLORS)
    random.shuffle(colors)
    return {speaker: colors[index % len(colors)] for index, speaker in enumerate(speakers)}


def _subtitle_position(speaker: str, speakers: list[str], W: int, H: int, bg_w: int) -> tuple[int, int]:
    if speakers and speaker == speakers[0]:
        return int(W * CHARACTER_A_X_RATIO), int(H * CHARACTER_A_Y_RATIO)
    if len(speakers) > 1 and speaker == speakers[1]:
        return W - bg_w - int(W * CHARACTER_B_X_MARGIN_RATIO), int(H * CHARACTER_B_Y_RATIO)
    return int((W - bg_w) / 2), int(H * SUBTITLE_Y_RATIO)


def build_subtitle_clips(timeline, script, W, H):
    subtitle_clips = []
    speakers = _speaker_order(timeline)
    speaker_colors = _speaker_colors(speakers)

    for fallback_index, segment in enumerate(_timeline_segments(timeline)):
        index = int(_get_optional_attr_or_key(segment, "index", fallback_index))
        start = float(_get_attr_or_key(segment, "start_sec"))
        duration = float(_get_attr_or_key(segment, "duration_sec"))
        speaker = str(_get_attr_or_key(segment, "speaker"))
        text = _get_attr_or_key(_script_line(script, index), "text")

        wrapped_text = _wrap_subtitle_text(text)
        txt_clip = _make_text_clip(wrapped_text, W, speaker_colors.get(speaker, "white"))
        shadow_clip = _make_text_clip(
            wrapped_text,
            W,
            "black",
            stroke_color="black",
            stroke_width=SUBTITLE_SHADOW_STROKE_WIDTH,
        )
        shadow_clip = set_opacity(shadow_clip, SUBTITLE_SHADOW_OPACITY)
        bg_w = int(W * SUBTITLE_BG_WIDTH_RATIO)
        bg_h = txt_clip.h + SUBTITLE_BG_PADDING_Y
        bg_x, bg_y = _subtitle_position(speaker, speakers, W, H, bg_w)
        text_x = bg_x + int((bg_w - txt_clip.w) / 2)
        text_y = bg_y + int(SUBTITLE_BG_PADDING_Y / 2)
        shadow_x = text_x + SUBTITLE_SHADOW_OFFSET[0]
        shadow_y = text_y + SUBTITLE_SHADOW_OFFSET[1]
        bg = ColorClip(
            size=(bg_w, bg_h),
            color=(0, 0, 0),
        )
        bg = set_opacity(bg, 0.55)

        subtitle = CompositeVideoClip(
            [
                set_position(bg, (bg_x, bg_y)),
                set_position(shadow_clip, (shadow_x, shadow_y)),
                set_position(txt_clip, (text_x, text_y)),
            ],
            size=(W, H),
        )
        subtitle = set_start(subtitle, start)
        subtitle = set_duration(subtitle, duration)
        subtitle_clips.append(subtitle)

    return subtitle_clips
