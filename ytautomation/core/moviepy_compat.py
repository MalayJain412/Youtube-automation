from __future__ import annotations

"""Compatibility imports for MoviePy.

MoviePy v2 removed the `moviepy.editor` convenience module and renamed several
core methods:
- subclip -> subclipped
- set_start -> with_start
- set_duration -> with_duration
- set_position -> with_position
- resize -> resized
- set_audio -> with_audio

This shim provides common symbols + small wrappers so the rest of the codebase
can use a stable API.
"""

from typing import Any


def _import_from_moviepy_v2() -> dict[str, Any]:
    from moviepy import (  # type: ignore
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        ImageClip,
        VideoFileClip,
    )
    from moviepy.video.fx import Crop as _Crop  # type: ignore

    def crop(clip, x1=None, y1=None, x2=None, y2=None):
        return _Crop(x1=x1, y1=y1, x2=x2, y2=y2).apply(clip)

    return {
        "AudioFileClip": AudioFileClip,
        "CompositeAudioClip": CompositeAudioClip,
        "CompositeVideoClip": CompositeVideoClip,
        "ImageClip": ImageClip,
        "VideoFileClip": VideoFileClip,
        "crop": crop,
    }


def _import_from_moviepy_v1() -> dict[str, Any]:
    from moviepy.editor import (  # type: ignore
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        ImageClip,
        VideoFileClip,
    )
    from moviepy.video.fx.all import crop  # type: ignore

    return {
        "AudioFileClip": AudioFileClip,
        "CompositeAudioClip": CompositeAudioClip,
        "CompositeVideoClip": CompositeVideoClip,
        "ImageClip": ImageClip,
        "VideoFileClip": VideoFileClip,
        "crop": crop,
    }


try:
    _symbols = _import_from_moviepy_v1()
except Exception:
    _symbols = _import_from_moviepy_v2()


AudioFileClip = _symbols["AudioFileClip"]
CompositeAudioClip = _symbols["CompositeAudioClip"]
CompositeVideoClip = _symbols["CompositeVideoClip"]
ImageClip = _symbols["ImageClip"]
VideoFileClip = _symbols["VideoFileClip"]
crop = _symbols["crop"]


def subclip(clip, start: float, end: float):
    if hasattr(clip, "subclip"):
        return clip.subclip(start, end)
    if hasattr(clip, "subclipped"):
        return clip.subclipped(start, end)
    raise AttributeError("Clip does not support subclip/subclipped")


def set_start(clip, t: float):
    if hasattr(clip, "set_start"):
        return clip.set_start(t)
    if hasattr(clip, "with_start"):
        return clip.with_start(t)
    raise AttributeError("Clip does not support set_start/with_start")


def set_duration(clip, t: float):
    if hasattr(clip, "set_duration"):
        return clip.set_duration(t)
    if hasattr(clip, "with_duration"):
        return clip.with_duration(t)
    raise AttributeError("Clip does not support set_duration/with_duration")


def set_position(clip, pos, relative: bool = False):
    if hasattr(clip, "set_position"):
        return clip.set_position(pos, relative=relative)
    if hasattr(clip, "with_position"):
        return clip.with_position(pos, relative=relative)
    raise AttributeError("Clip does not support set_position/with_position")


def set_opacity(clip, opacity: float):
    if hasattr(clip, "set_opacity"):
        return clip.set_opacity(opacity)
    if hasattr(clip, "with_opacity"):
        return clip.with_opacity(opacity)
    raise AttributeError("Clip does not support set_opacity/with_opacity")


def add_margin(clip, **kwargs):
    if hasattr(clip, "margin"):
        return clip.margin(**kwargs)
    if hasattr(clip, "with_margin"):
        return clip.with_margin(**kwargs)

    try:
        from moviepy.video.fx import Margin as _Margin  # type: ignore

        return _Margin(**kwargs).apply(clip)
    except Exception:
        pass

    try:
        from moviepy.video.fx.all import margin as _margin  # type: ignore

        return _margin(clip, **kwargs)
    except Exception:
        pass

    try:
        from moviepy.video.fx.margin import margin as _margin  # type: ignore

        return _margin(clip, **kwargs)
    except Exception:
        pass

    return clip


def resize(clip, *, newsize=None, height: int | None = None):
    if hasattr(clip, "resize"):
        return clip.resize(newsize=newsize, height=height)
    if hasattr(clip, "resized"):
        if height is not None:
            return clip.resized(height=height)
        if newsize is not None:
            # MoviePy v2 uses new_size keyword
            return clip.resized(new_size=newsize)
        return clip
    raise AttributeError("Clip does not support resize/resized")


def set_audio(video_clip, audio_clip):
    if hasattr(video_clip, "set_audio"):
        return video_clip.set_audio(audio_clip)
    if hasattr(video_clip, "with_audio"):
        return video_clip.with_audio(audio_clip)
    raise AttributeError("Video clip does not support set_audio/with_audio")
