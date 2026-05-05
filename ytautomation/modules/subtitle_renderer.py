from __future__ import annotations

import textwrap
from typing import Any

try:
    from moviepy import ColorClip, CompositeVideoClip, TextClip
except Exception:
    from moviepy.editor import ColorClip, CompositeVideoClip, TextClip  # type: ignore

from ytautomation.core.moviepy_compat import set_duration, set_opacity, set_position, set_start


SUBTITLE_WRAP_CHARS = 40
SUBTITLE_FONT_SIZE = 60
SUBTITLE_WIDTH_RATIO = 0.85
SUBTITLE_BG_WIDTH_RATIO = 0.9
SUBTITLE_Y_RATIO = 0.25
SUBTITLE_BG_PADDING_Y = 30
SUBTITLE_FONTS = ("Arial-Bold", "Arial Bold", "Arial", "DejaVuSans-Bold", None)


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


def _make_text_clip(text: str, W: int) -> TextClip:
    base_kwargs = {
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 4,
        "method": "caption",
        "size": (int(W * SUBTITLE_WIDTH_RATIO), None),
    }

    last_error: Exception | None = None
    for font in SUBTITLE_FONTS:
        kwargs = dict(base_kwargs)
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


def build_subtitle_clips(timeline, script, W, H):
    subtitle_clips = []
    subtitle_y = int(H * SUBTITLE_Y_RATIO)

    for fallback_index, segment in enumerate(_timeline_segments(timeline)):
        index = int(_get_optional_attr_or_key(segment, "index", fallback_index))
        start = float(_get_attr_or_key(segment, "start_sec"))
        duration = float(_get_attr_or_key(segment, "duration_sec"))
        text = _get_attr_or_key(_script_line(script, index), "text")

        txt_clip = _make_text_clip(_wrap_subtitle_text(text), W)
        bg = ColorClip(
            size=(int(W * SUBTITLE_BG_WIDTH_RATIO), txt_clip.h + SUBTITLE_BG_PADDING_Y),
            color=(0, 0, 0),
        )
        bg = set_opacity(bg, 0.5)

        subtitle = CompositeVideoClip(
            [
                set_position(bg, ("center", subtitle_y)),
                set_position(txt_clip, ("center", subtitle_y)),
            ],
            size=(W, H),
        )
        subtitle = set_start(subtitle, start)
        subtitle = set_duration(subtitle, duration)
        subtitle_clips.append(subtitle)

    return subtitle_clips
