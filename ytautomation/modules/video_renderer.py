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
from ytautomation.core.models import RenderPlan, ScriptArtifact, TimelineArtifact
from ytautomation.core.settings import Settings
from ytautomation.modules.subtitle_renderer import build_subtitle_clips

logger = logging.getLogger(__name__)

ACTIVE_AVATAR_HEIGHT_RATIO = 0.325
INACTIVE_SCALE = 0.6
TRANSITION_SEC = 0.35
AVATAR_BOTTOM_MARGIN_RATIO = 0.05


def _center_crop_to_aspect(clip: VideoFileClip, target_w: int, target_h: int) -> VideoFileClip:
    target_aspect = target_w / target_h
    current_aspect = clip.w / clip.h

    if abs(current_aspect - target_aspect) < 1e-3:
        return clip

    if current_aspect > target_aspect:
        new_w = int(clip.h * target_aspect)
        x1 = int((clip.w - new_w) / 2)
        x2 = x1 + new_w
        return crop(clip, x1=x1, x2=x2)

    new_h = int(clip.w / target_aspect)
    y1 = int((clip.h - new_h) / 2)
    y2 = y1 + new_h
    return crop(clip, y1=y1, y2=y2)


def _smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def _speaker_order(timeline: TimelineArtifact) -> list[str]:
    speakers: list[str] = []
    for segment in timeline.segments:
        if segment.speaker not in speakers:
            speakers.append(segment.speaker)
    return speakers


def _avatar_paths_by_speaker(timeline: TimelineArtifact) -> dict[str, Path]:
    avatar_paths: dict[str, Path] = {}
    for segment in timeline.segments:
        avatar_paths.setdefault(segment.speaker, segment.avatar_path)
    return avatar_paths


def _active_segment_index(timeline: TimelineArtifact, t: float) -> int:
    if t <= timeline.segments[0].start_sec:
        return 0

    for index, segment in enumerate(timeline.segments):
        start = segment.start_sec
        end = segment.start_sec + segment.duration_sec
        if start <= t < end:
            return index

    return len(timeline.segments) - 1


def _make_scale_function(timeline: TimelineArtifact):
    def get_scale(t: float, speaker_name: str) -> float:
        index = _active_segment_index(timeline, t)
        segment = timeline.segments[index]
        previous = timeline.segments[index - 1] if index > 0 else None

        if previous and previous.speaker != segment.speaker:
            elapsed = t - segment.start_sec
            transition = min(TRANSITION_SEC, max(0.05, segment.duration_sec * 0.5))

            if 0.0 <= elapsed < transition:
                progress = _smoothstep(elapsed / transition)
                if speaker_name == segment.speaker:
                    return INACTIVE_SCALE + ((1.0 - INACTIVE_SCALE) * progress)
                if speaker_name == previous.speaker:
                    return 1.0 - ((1.0 - INACTIVE_SCALE) * progress)

        return 1.0 if speaker_name == segment.speaker else INACTIVE_SCALE

    return get_scale


def _avatar_position(
    side: str,
    base_w: int,
    base_h: int,
    output_w: int,
    output_h: int,
    get_scale,
    speaker: str,
):
    def position(t: float) -> tuple[int, int]:
        scale = get_scale(t, speaker)
        scaled_w = int(base_w * scale)
        scaled_h = int(base_h * scale)
        bottom_margin = int(output_h * AVATAR_BOTTOM_MARGIN_RATIO)
        x = 0 if side == "left" else output_w - scaled_w
        y = output_h - scaled_h - bottom_margin
        return x, y

    return position


def render_video(
    timeline: TimelineArtifact,
    script: ScriptArtifact,
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

        if not timeline.segments:
            raise ValidationError("Timeline has no segments")

        speakers = _speaker_order(timeline)
        avatar_paths = _avatar_paths_by_speaker(timeline)
        get_scale = _make_scale_function(timeline)

        avatar_clips = []
        avatar_height = int(settings.output_height * ACTIVE_AVATAR_HEIGHT_RATIO)

        for index, speaker in enumerate(speakers[:2]):
            avatar_path = avatar_paths[speaker]
            if not avatar_path.exists():
                raise ValidationError(f"Missing avatar image: {avatar_path}")

            side = "left" if index == 0 else "right"
            avatar = ImageClip(str(avatar_path))
            avatar = resize(avatar, height=avatar_height)
            base_w = avatar.w
            base_h = avatar.h
            avatar = resize(avatar, newsize=lambda t, speaker=speaker: get_scale(t, speaker))
            avatar = set_duration(avatar, total)
            avatar = set_position(
                avatar,
                _avatar_position(
                    side=side,
                    base_w=base_w,
                    base_h=base_h,
                    output_w=settings.output_width,
                    output_h=settings.output_height,
                    get_scale=get_scale,
                    speaker=speaker,
                ),
            )
            avatar_clips.append(avatar)

        subtitle_clips = build_subtitle_clips(timeline, script, settings.output_width, settings.output_height)

        audio_clips = []
        for segment in timeline.segments:
            audio = AudioFileClip(str(segment.audio_path))
            audio = set_start(audio, segment.start_sec)
            audio_clips.append(audio)

        final = CompositeVideoClip([clip] + avatar_clips + subtitle_clips)
        final = set_audio(final, CompositeAudioClip(audio_clips))

        logger.info("Writing video: %s", output_path)
        final.write_videofile(str(output_path), fps=settings.fps, audio_codec="aac")

        for audio in audio_clips:
            audio.close()
        for avatar in avatar_clips:
            avatar.close()
        for subtitle in subtitle_clips:
            subtitle.close()
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
