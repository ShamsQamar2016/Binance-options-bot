"""Битта сериал қисмини йиғиш: видео кадрлар + дубляж + субтитр + титрлар + мусиқа → episode.mp4"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from dubbing import audio_duration, cyr_to_lat, synthesize
from series_planner import EpisodeScript, SeriesPlan
from video import generate_clip

FPS = 24
LINE_GAP = 0.35      # репликалар орасидаги пауза (сония)
LEAD_IN = 0.4        # кадр бошланиб, биринчи репликагача
TAIL = 0.5           # охирги репликадан кейин

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _size(aspect: str) -> tuple[int, int]:
    return {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (1080, 1080)}[aspect]


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg хатоси:\n{' '.join(cmd)}\n{result.stderr[-2000:]}")


def _font(work: Path) -> str | None:
    """Шрифтни иш папкасига нусхалаймиз — ffmpeg да йўл (C:\\...) муаммоси бўлмаслиги учун."""
    for candidate in [os.environ.get("FONT_FILE", "")] + FONT_CANDIDATES:
        if candidate and Path(candidate).exists():
            shutil.copy(candidate, work / "font.ttf")
            return "font.ttf"
    return None


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def _sub_text(text: str) -> str:
    return cyr_to_lat(text) if os.environ.get("SUBTITLE_SCRIPT", "cyrillic") == "latin" else text


class EpisodeBuilder:
    def __init__(self, plan: SeriesPlan, voices: dict, episode_dir: Path, aspect: str = "16:9"):
        self.plan = plan
        self.voices = voices
        self.dir = episode_dir
        self.aspect = aspect
        self.w, self.h = _size(aspect)
        self.appearance = {c.id: c.appearance for c in plan.characters}
        for sub in ("clips", "audio", "parts"):
            (self.dir / sub).mkdir(parents=True, exist_ok=True)
        self.subs: list[tuple[float, float, str]] = []
        self.clock = 0.0

    # ---------- овоз ----------

    def _voice_lines(self, key: str, lines) -> list[tuple[Path, float, str, bool]]:
        result = []
        for i, line in enumerate(lines, 1):
            path = self.dir / "audio" / f"{key}_{i:02d}.mp3"
            if not path.exists():
                voice = self.voices.get(line.speaker) or self.voices["narrator"]
                synthesize(line.text, voice, line.emotion, path)
            result.append((path, audio_duration(path), line.text, line.speaker == "narrator"))
        return result

    def _mix_audio(self, voiced, length: float, out: Path) -> None:
        """Репликаларни вақт бўйича жойлаштириб, битта аудио трек ясайди ва субтитр вақтларини ёзади."""
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-t", f"{length:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        filters, labels, t = [], ["[0:a]"], LEAD_IN
        for n, (path, dur, text, is_narrator) in enumerate(voiced, 1):
            cmd += ["-i", str(path)]
            delay = int(t * 1000)
            filters.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={delay}|{delay}[a{n}]")
            labels.append(f"[a{n}]")
            caption = _sub_text(text)
            self.subs.append((self.clock + t, self.clock + t + dur, f"<i>{caption}</i>" if is_narrator else caption))
            t += dur + LINE_GAP
        filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first[out]")
        cmd += ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "aac", "-b:a", "192k", str(out)]
        _run(cmd)

    @staticmethod
    def _speech_length(voiced) -> float:
        if not voiced:
            return 0.0
        return LEAD_IN + sum(d for _, d, _, _ in voiced) + LINE_GAP * (len(voiced) - 1) + TAIL

    # ---------- қисмлар ----------

    def _shot(self, shot) -> Path:
        part = self.dir / "parts" / f"shot_{shot.number:02d}.mp4"
        voiced = self._voice_lines(f"s{shot.number:02d}", shot.lines)

        clip = self.dir / "clips" / f"shot_{shot.number:02d}.mp4"
        if not clip.exists():
            looks = "; ".join(self.appearance[c] for c in shot.characters_in_shot if c in self.appearance)
            prompt = (
                f"{shot.video_prompt}\n"
                f"Setting: {self.plan.era_and_setting}\n"
                + (f"Characters: {looks}\n" if looks else "")
                + f"Style: {self.plan.visual_style}. Photorealistic, natural human motion, no text on screen."
            )
            print(f"    🎥 кадр {shot.number}: {shot.description}")
            generate_clip(prompt, clip, duration=shot.duration_seconds, aspect_ratio=self.aspect)

        length = max(audio_duration(clip), self._speech_length(voiced))
        audio = self.dir / "audio" / f"shot_{shot.number:02d}_mix.m4a"
        self._mix_audio(voiced, length, audio)

        # Видео овоздан қисқа бўлса — охирги кадрни ушлаб турамиз; ўлчам ва FPS ни бир хиллаймиз
        vf = (f"scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h},"
              f"fps={FPS},tpad=stop_mode=clone:stop_duration=30,format=yuv420p")
        _run(["ffmpeg", "-y", "-i", str(clip), "-i", str(audio), "-map", "0:v:0", "-map", "1:a",
              "-vf", vf, "-t", f"{length:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
              "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(part)])
        self.clock += length
        return part

    def _card(self, name: str, lines_text: list[str], narration: str, min_len: float = 3.5) -> Path:
        """Қора фонда ёзув (бош/охирги титр) + диктор овози."""
        from series_planner import Line

        part = self.dir / "parts" / f"{name}.mp4"
        voiced = self._voice_lines(name, [Line(speaker="narrator", text=narration, emotion="calm")]) if narration else []
        length = max(min_len, self._speech_length(voiced) + 0.5)
        audio = self.dir / "audio" / f"{name}_mix.m4a"
        self._mix_audio(voiced, length, audio)

        font = _font(self.dir)
        vf = "format=yuv420p"
        if font:
            draws = []
            for i, text in enumerate(lines_text):
                (self.dir / f"{name}_{i}.txt").write_text(_sub_text(text), encoding="utf-8")
                size = int(self.h * (0.075 if i == 0 else 0.045))
                y = f"(h/2)-{size}" if i == 0 else f"(h/2)+{int(size * 1.2 * i)}"
                draws.append(f"drawtext=fontfile={font}:textfile={name}_{i}.txt:fontcolor=white:"
                             f"fontsize={size}:x=(w-text_w)/2:y={y}:alpha='min(1,t/0.8)'")
            vf = ",".join(draws) + ",format=yuv420p"
        _run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={self.w}x{self.h}:r={FPS}:d={length:.3f}",
              "-i", str(audio.resolve()), "-vf", vf, "-t", f"{length:.3f}",
              "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
              str(part.relative_to(self.dir))], cwd=self.dir)
        self.clock += length
        return part

    # ---------- йиғиш ----------

    def build(self, script: EpisodeScript, music: Path | None = None) -> Path:
        parts = [self._card(
            "intro",
            [self.plan.series_title.upper(), f"{script.number}-қисм. «{script.title}»"],
            script.recap,
        )]
        for shot in script.shots:
            parts.append(self._shot(shot))
        parts.append(self._card("outro", ["Давоми эртага..."], script.next_episode_teaser, min_len=3.0))

        # Субтитрлар
        srt = self.dir / "subs.srt"
        srt.write_text("\n".join(
            f"{i}\n{_srt_time(a)} --> {_srt_time(b)}\n{text}\n" for i, (a, b, text) in enumerate(self.subs, 1)
        ), encoding="utf-8")

        concat_list = self.dir / "parts.txt"
        concat_list.write_text("".join(f"file 'parts/{p.name}'\n" for p in parts), encoding="utf-8")
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "parts.txt", "-c", "copy", "joined.mp4"], cwd=self.dir)

        # Якуний ўтиш: субтитр + фон мусиқаси + овоз баландлигини меъёрлаш
        burn = os.environ.get("BURN_SUBTITLES", "1") == "1"
        cmd = ["ffmpeg", "-y", "-i", "joined.mp4"]
        if music:
            cmd += ["-stream_loop", "-1", "-i", str(Path(music).resolve())]
            afilter = ("[1:a]volume=0.12,afade=t=in:d=2[m];"
                       "[0:a][m]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5[a]")
        else:
            afilter = "[0:a]loudnorm=I=-16:TP=-1.5[a]"
        vfilter = ("[0:v]subtitles=subs.srt:force_style='FontName=DejaVu Sans,FontSize=16,"
                   "Outline=2,Shadow=0,MarginV=36'[v]") if burn else "[0:v]null[v]"
        cmd += ["-filter_complex", f"{vfilter};{afilter}", "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", "episode.mp4"]
        _run(cmd, cwd=self.dir)
        (self.dir / "joined.mp4").unlink(missing_ok=True)
        return self.dir / "episode.mp4"
