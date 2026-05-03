from __future__ import annotations

import logging
from pathlib import Path

from ytautomation.core.moviepy_compat import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    crop,
    resize,
    set_audio,
    set_duration,
    set_position,
    set_start,
    subclip,
)

from ytautomation.core.errors import ValidationError
from ytautomation.core.io import write_model
from ytautomation.core.models import RenderPlan, TimelineArtifact
from ytautomation.core.settings import Settings

logger = logging.getLogger(__name__)

AVATAR_HEIGHT_RATIO = 0.325
AVATAR_BOTTOM_OFFSET_RATIO = 0.05


def _center_crop_to_aspect(clip: VideoFileClip, target_w: int, target_h: int) -> VideoFileClip:
    target_aspect = target_w / target_h
    current_aspect = clip.w / clip.h

    if abs(current_aspect - target_aspect) < 1e-3:
        return clip

    if current_aspect > target_aspect:
        # too wide: crop width
        new_w = int(clip.h * target_aspect)
        x1 = int((clip.w - new_w) / 2)
        x2 = x1 + new_w
        return crop(clip, x1=x1, x2=x2)

    # too tall: crop height
    new_h = int(clip.w / target_aspect)
    y1 = int((clip.h - new_h) / 2)
    y2 = y1 + new_h
    return crop(clip, y1=y1, y2=y2)


def render_video(
    timeline: TimelineArtifact,
    gameplay_path: Path,
    gameplay_start_sec: float,
    output_path: Path,
    settings: Settings,
) -> RenderPlan:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = timeline.total_duration_sec

    base = VideoFileClip(str(gameplay_path))
    try:
        if base.duration < gameplay_start_sec + total:
            raise ValidationError("Gameplay clip is shorter than required after start offset")

        clip = subclip(base, gameplay_start_sec, gameplay_start_sec + total)
        clip = _center_crop_to_aspect(clip, settings.output_width, settings.output_height)
        clip = resize(clip, newsize=(settings.output_width, settings.output_height))

        overlay_clips = []
        audio_clips = []

        if not timeline.segments:
            raise ValidationError("Timeline has no segments")

        left_speaker = timeline.segments[0].speaker
        avatar_height = int(settings.output_height * AVATAR_HEIGHT_RATIO)
        avatar_bottom_offset = int(settings.output_height * AVATAR_BOTTOM_OFFSET_RATIO)

        for seg in timeline.segments:
            if not seg.avatar_path.exists():
                raise ValidationError(f"Missing avatar image: {seg.avatar_path}")

            img = ImageClip(str(seg.avatar_path))
            img = resize(img, height=avatar_height)
            y = settings.output_height - img.h - avatar_bottom_offset
            pos = (0, y) if seg.speaker == left_speaker else (settings.output_width - img.w, y)
            img = set_start(img, seg.start_sec)
            img = set_duration(img, seg.duration_sec)
            img = set_position(img, pos)

            overlay_clips.append(img)

            a = AudioFileClip(str(seg.audio_path))
            a = set_start(a, seg.start_sec)
            audio_clips.append(a)

        final = CompositeVideoClip([clip] + overlay_clips)
        final = set_audio(final, CompositeAudioClip(audio_clips))

        logger.info("Writing video: %s", output_path)
        final.write_videofile(str(output_path), fps=settings.fps, audio_codec="aac")

        for a in audio_clips:
            a.close()
        for i in overlay_clips:
            i.close()
        final.close()
        clip.close()
    finally:
        base.close()

    plan = RenderPlan(
        job_id=timeline.job_id,
        gameplay_path=gameplay_path,
        gameplay_start_sec=gameplay_start_sec,
        total_duration_sec=total,
        output_path=output_path,
    )

    write_model(output_path.parent / "render_plan.json", plan)
    return plan
