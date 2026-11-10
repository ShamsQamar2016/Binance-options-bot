"""Битта қисмни йиғиш: вертикал 1080×1920, YouTube Shorts ва Instagram Reels учун.

Ҳар кадр учун:  русча овоз → калит расм (эталонлар билан) → расмдан видео → лаб синхрони (гапираётган
юз кўринса) → кадр қисми.  Кейин бутун қисм учун алоҳида товуш йўлаклари йиғилади:
  dialogue  — репликалар (ўз вақтида),
  foley     — кадр эффектлари (SFX),
  ambience  — жой муҳити (бир жойдаги кадрлар остида узлуксиз),
  music     — қисм мусиқаси (реплика пайтида автоматик пасаяди),
сўнг ранг (grade), русча субтитр, бош титр ва охирги «Продолжение следует…» қўшилади.

Ҳамма оралиқ файллар сақланади: қайта ишга туширилганда тайёрлари қайта ясалмайди (пул тежалади).
  clips/shot_NN.png  — калит расм   (ўчирсангиз — янгиси ва видео ҳам қайта ясалади)
  clips/shot_NN.mp4  — видео         (ўчирсангиз — фақат видео қайта ясалади)
  audio/…            — реплика овозлари (матн ўзгарса, автоматик янгиланади)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import sound
import visuals
from dubbing import audio_duration, synthesize
from fileutil import FFMPEG_TIMEOUT, PROBE_TIMEOUT
from series_planner import Character, EpisodeScript, Line, Location, SeriesPlan, Shot

logger = logging.getLogger(__name__)

W, H, FPS = 1080, 1920, 24
LEAD_IN = 0.3        # кадр бошидан биринчи репликагача
LINE_GAP = 0.3       # репликалар орасидаги пауза
TAIL = 0.45          # охирги репликадан кейин
MAX_STRETCH = 1.3    # видео нутқдан қисқа бўлса, шунча мартагача секинлаштирилади
SHORTS_LIMIT = 179.0 # Shorts/Reels: 3 дақиқадан кам

VOLUME = {"foley": 0.6, "ambience": 0.22, "music": 0.3}

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


# ----------------------------- ffmpeg ёрдамчилари -----------------------------

def _run(cmd: list[str], cwd: Path | None = None, timeout: int = FFMPEG_TIMEOUT) -> None:
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffmpeg {timeout} сонияда тугамади (тўхтатилди):\n{' '.join(cmd)[:2000]}")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg хатоси:\n{' '.join(cmd)[:3000]}\n{result.stderr[-3000:]}")


def media_duration(path: Path) -> float:
    return audio_duration(path)


def has_audio(path: Path) -> bool:
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                             "stream=index", "-of", "csv=p=0", str(path)], capture_output=True, text=True,
                            timeout=PROBE_TIMEOUT)
    return bool(result.stdout.strip())


def _sha(*parts) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:10]


@dataclass
class Placed:
    """Товуш йўлагига жойлаштириладиган файл."""
    path: Path
    start: float
    length: float | None = None
    fade_in: float = 0.0
    fade_out: float = 0.0
    volume: float = 1.0
    loop: bool = False


def place_track(items: list[Placed], total: float, out: Path) -> Path:
    """Файлларни вақт бўйича битта стерео WAV йўлагига жойлаштиради (узунлиги total)."""
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    filters, labels = [], ["[0:a]"]
    for k, it in enumerate(items, 1):
        if it.loop:
            cmd += ["-stream_loop", "-1"]
        cmd += ["-i", str(it.path)]
        chain = f"[{k}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
        if it.length:
            chain += f",atrim=0:{it.length:.3f},asetpts=PTS-STARTPTS"
        if it.fade_in:
            chain += f",afade=t=in:st=0:d={it.fade_in:.2f}"
        if it.fade_out and it.length:
            chain += f",afade=t=out:st={max(0.0, it.length - it.fade_out):.3f}:d={it.fade_out:.2f}"
        if it.volume != 1.0:
            chain += f",volume={it.volume:.3f}"
        ms = max(0, int(round(it.start * 1000)))
        chain += f",adelay={ms}|{ms}"
        filters.append(chain + f"[a{k}]")
        labels.append(f"[a{k}]")
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=first,"
                   f"atrim=0:{total:.3f}[out]")
    cmd += ["-filter_complex", ";".join(filters), "-map", "[out]", "-c:a", "pcm_s16le", str(out)]
    _run(cmd)
    return out


# ----------------------------- Субтитрлар (ASS) -----------------------------

def _ass_time(t: float) -> str:
    cs = max(0, int(round(t * 100)))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _ass_text(text: str) -> str:
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def _caption_chunks(text: str, max_chars: int) -> list[str]:
    """Матнни аввал гап, кейин вергул, охири сўз чегарасидан max_chars дан қисқа бўлакларга бўлади."""
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = [text]
    for pattern in (r"(?<=[.!?…])\s+", r"(?<=[,;:])\s+|\s+(?=[—–]\s)", r"\s+"):
        parts = [p for p in re.split(pattern, text) if p]
        if len(parts) > 1:
            break
    if len(parts) == 1:
        return parts
    chunks: list[str] = []
    for p in parts:
        if chunks and len(chunks[-1]) + 1 + len(p) <= max_chars:
            chunks[-1] += " " + p
        else:
            chunks.append(p)
    out: list[str] = []
    for c in chunks:
        out += _caption_chunks(c, max_chars) if len(c) > max_chars and c != text else [c]
    return out


def split_caption(text: str, start: float, end: float, max_chars: int = 42) -> list[tuple[float, float, str]]:
    """Репликани экранда кўпи билан 2 қатор бўладиган субтитрларга бўлади (вақт белгилар сонига қараб)."""
    chunks = _caption_chunks(" ".join(text.split()), max_chars)
    total = sum(len(c) for c in chunks) or 1
    out, t = [], start
    for c in chunks:
        d = (end - start) * len(c) / total
        out.append((t, t + d, c))
        t += d
    return out


# ----------------------------- Эталонлар -----------------------------

def ref_path(serial_dir: Path, key: str) -> Path:
    if key.startswith("@"):
        return serial_dir / "refs" / f"loc_{key[1:]}.png"
    return serial_dir / "refs" / f"{key}.png"


def ensure_references(plan: SeriesPlan, serial_dir: Path, redo: set[str] = frozenset(),
                      workers: int = 4) -> list[tuple[str, Path]]:
    """Барча персонаж ва жойлар учун эталон расмлар (йўқларини ясайди). [(изоҳ, файл)] қайтаради."""
    jobs: list[tuple[str, Character | Location, Path, str]] = []
    for c in plan.characters:
        jobs.append((c.id, c, ref_path(serial_dir, c.id), f"{c.name} — {c.role}"))
    for loc in plan.locations:
        jobs.append(("@" + loc.id, loc, ref_path(serial_dir, "@" + loc.id), f"📍 {loc.name}"))
    for key, _, path, _ in jobs:
        if key in redo or key.lstrip("@") in redo:
            path.unlink(missing_ok=True)
    missing = [(key, item, path) for key, item, path, _ in jobs if not path.exists()]

    def make(job):
        key, item, path = job
        print(f"🖼  Эталон: {key}")
        path.parent.mkdir(parents=True, exist_ok=True)
        visuals.make_reference(plan, item, path)

    if missing:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(make, missing))
    return [(caption, path) for _, _, path, caption in jobs if path.exists()]


# ----------------------------- Қисм йиғувчи -----------------------------

@dataclass
class Voiced:
    path: Path
    dur: float
    text: str
    speaker: str
    offset: float = 0.0


@dataclass
class ShotResult:
    shot: Shot
    part: Path
    length: float
    lines: list[Voiced]
    foley: Path | None = None
    start: float = 0.0
    lipsynced: bool = False
    notes: list[str] = field(default_factory=list)


class EpisodeBuilder:
    def __init__(self, plan: SeriesPlan, voices: dict, serial_dir: Path, episode_dir: Path):
        self.plan = plan
        self.voices = voices
        self.serial_dir = serial_dir
        self.dir = episode_dir
        self.locations = {loc.id: loc for loc in plan.locations}
        self.workers = max(1, int(os.environ.get("VISUAL_WORKERS", "4")))
        for sub in ("clips", "audio", "sound", "parts"):
            (self.dir / sub).mkdir(parents=True, exist_ok=True)
        (serial_dir / "sound").mkdir(parents=True, exist_ok=True)

    # ---------- овоз ----------

    def _voice(self, speaker: str) -> dict:
        return self.voices.get(speaker) or self.voices["narrator"]

    def voice_lines(self, key: str, lines: list[Line]) -> list[Voiced]:
        voiced: list[Voiced] = []
        # Овоз файли номида овозга таъсир қиладиган ҳамма созламалар бор: бирортаси ўзгарса,
        # реплика янгидан ясалади ва бир қисмда эски ва янги овоз аралашиб қолмайди.
        settings = (os.environ.get("ELEVENLABS_MODEL", "eleven_v3"), os.environ.get("ELEVENLABS_LANGUAGE_CODE", "ru"))
        t = LEAD_IN
        for i, line in enumerate(lines, 1):
            voice = self._voice(line.speaker)
            tag = _sha(line.text, line.delivery, voice.get("voice_id"), voice.get("stability", 0.5),
                       voice.get("similarity_boost", 0.75), *settings)
            path = self.dir / "audio" / f"{key}_{i:02d}_{tag}.mp3"
            if not path.exists():
                synthesize(line.text, voice, line.delivery, path)
            v = Voiced(path, audio_duration(path), line.text, line.speaker, t)
            t += v.dur + LINE_GAP
            voiced.append(v)
        return voiced

    @staticmethod
    def speech_length(voiced: list[Voiced]) -> float:
        return voiced[-1].offset + voiced[-1].dur + TAIL if voiced else 0.0

    # ---------- кадр ----------

    def refs_for(self, shot: Shot) -> list[tuple[str, Path]]:
        keys = list(shot.characters_in_shot) + ([f"@{shot.location_id}"] if shot.location_id else [])
        return [(k, p) for k in keys if (p := ref_path(self.serial_dir, k)).exists()]

    def keyframe(self, shot: Shot) -> Path:
        path = self.dir / "clips" / f"shot_{shot.number:02d}.png"
        if not path.exists():
            print(f"    🖼  кадр {shot.number}: {shot.description}")
            visuals.make_keyframe(self.plan, shot, self.refs_for(shot), path)
        return path

    def _ambience(self, location_id: str) -> Path | None:
        loc = self.locations.get(location_id)
        if not loc or not loc.ambience:
            return None
        path = self.serial_dir / "sound" / f"amb_{location_id}.mp3"
        if not path.exists():
            try:
                sound.ambience(loc.ambience, path)
            except Exception as exc:
                logger.warning("Муҳит товуши ясалмади (%s): %s", location_id, exc)
                return None
        return path

    def build_shot(self, shot: Shot) -> ShotResult:
        n = shot.number
        voiced = self.voice_lines(f"s{n:02d}", shot.lines)
        speech = self.speech_length(voiced)
        length = max(float(shot.duration_seconds), speech)
        key = self.keyframe(shot)

        clip = self.dir / "clips" / f"shot_{n:02d}.mp4"
        native = os.environ.get("VIDEO_NATIVE_AUDIO", "0") == "1" and not shot.lines
        if not clip.exists() or clip.stat().st_mtime < key.stat().st_mtime:
            seconds = visuals.clip_seconds(length)
            print(f"    🎥 кадр {n}: видео {seconds:g} с")
            amb = self.locations[shot.location_id].ambience if shot.location_id in self.locations else ""
            visuals.make_clip(self.plan, shot, key, seconds, clip, native, amb)
        clip_len = media_duration(clip)

        result = ShotResult(shot, self.dir / "parts" / f"shot_{n:02d}.mp4", length, voiced)
        video = clip
        if shot.speaker_on_screen and os.environ.get("LIPSYNC", "1") == "1":
            mine = [v for v in voiced if v.speaker == shot.speaker_on_screen]
            if mine:
                lips_len = max(clip_len, speech)
                lips = place_track([Placed(v.path, v.offset) for v in mine], lips_len,
                                   self.dir / "audio" / f"shot_{n:02d}_lips.wav")
                synced = self.dir / "clips" / f"shot_{n:02d}_ls_{_sha(hashlib.sha1(lips.read_bytes()).hexdigest(), clip.stat().st_mtime)}.mp4"
                if not synced.exists():
                    print(f"    👄 кадр {n}: лаб синхрони")
                    visuals.lipsync(clip, lips, synced)
                video = synced
                result.lipsynced = True

        vlen = media_duration(video)
        # Кадр узунлиги: нутқ видеога сиғса — видеодан узун бўлмайди (қотиб қолган кадр бўлмаслиги учун,
        # масалан script.json да duration оширилган, видео эса аввал қисқароқ ясалган бўлса).
        # Нутқ сиғмаса — видео секинлаштирилади (лаб синхрони йўқ кадрда), охири ушлаб турилади.
        length = min(length, vlen) if speech <= vlen else speech
        result.length = length
        factor = 1.0
        if not result.lipsynced and length > vlen:
            factor = min(MAX_STRETCH, length / vlen)
        if length > vlen * factor + 0.05:
            result.notes.append(f"видео {vlen:.1f}с, нутқ {speech:.1f}с — охирги кадр ушлаб турилади")
        vf = (f"setpts={factor:.4f}*PTS,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"setsar=1,fps={FPS},tpad=stop_mode=clone:stop_duration=30,format=yuv420p")
        _run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-an", "-vf", vf, "-t", f"{length:.3f}",
              "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-r", str(FPS), str(result.part)])

        # Эффектлар: видео моделининг ўз товуши ёки ElevenLabs SFX
        if native and has_audio(clip):
            result.foley = self.dir / "sound" / f"shot_{n:02d}_native.wav"
            _run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-vn", "-ac", "2", "-ar", "48000", str(result.foley)])
        elif shot.sound:
            sfx = self.dir / "sound" / f"shot_{n:02d}_sfx_{_sha(shot.sound, round(length, 1))}.mp3"
            if not sfx.exists():
                try:
                    sound.sound_effect(shot.sound, length, sfx)
                except Exception as exc:
                    logger.warning("SFX ясалмади (кадр %s): %s", n, exc)
            result.foley = sfx if sfx.exists() else None
        return result

    # ---------- раскадровка ----------

    def storyboard(self, script: EpisodeScript) -> Path:
        """Фақат калит расмлар (арзон): видеога пул сарфлашдан олдин кўриб чиқиш учун."""
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            list(ex.map(self.keyframe, script.shots))
        rows = math.ceil(len(script.shots) / 6)
        out = self.dir / "storyboard.jpg"
        font = next((f for f in [os.environ.get("FONT_FILE", "")] + FONT_CANDIDATES if f and Path(f).exists()), None)
        if font:
            shutil.copy(font, self.dir / "sheet_font.ttf")
        sheet = self.dir / "sheet"
        shutil.rmtree(sheet, ignore_errors=True)
        sheet.mkdir()
        # Ҳар расмга кадрнинг ҳақиқий рақами ёзилади (сценарийдан кадр ўчирилган бўлса ҳам тўғри)
        for i, shot in enumerate(script.shots, 1):
            label = (f",drawtext=fontfile=sheet_font.ttf:text='{int(shot.number)}':x=12:y=10:fontsize=44:"
                     "fontcolor=white:borderw=3:bordercolor=black") if font else ""
            _run(["ffmpeg", "-y", "-v", "error", "-i", f"clips/shot_{shot.number:02d}.png",
                  "-vf", f"scale=270:480{label}", "-q:v", "3", f"sheet/{i:03d}.jpg"], cwd=self.dir)
        _run(["ffmpeg", "-y", "-v", "error", "-framerate", "1", "-i", "sheet/%03d.jpg",
              "-vf", f"tile=6x{rows}:padding=6:margin=6", "-frames:v", "1", "-q:v", "3", out.name], cwd=self.dir)
        shutil.rmtree(sheet, ignore_errors=True)
        return out

    # ---------- йиғиш ----------

    def build(self, script: EpisodeScript, is_last: bool = False, music_file: Path | None = None) -> Path:
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            results = list(ex.map(self.build_shot, script.shots))
        t = 0.0
        for r in results:
            r.start = t
            t += r.length
            for note in r.notes:
                print(f"    ⚠️  кадр {r.shot.number}: {note}")
        shots_end = t

        # Охирги лавҳа: «Продолжение следует…» ва диктор жумласи
        teaser = self.voice_lines("end", [Line(speaker="narrator", text=script.next_episode_teaser, delivery="")]) \
            if script.next_episode_teaser else []
        end_len = max(3.5, (self.speech_length(teaser) + 0.6) if teaser else 0.0)
        end_part = self._end_card(results[-1].part, end_len)
        total = shots_end + end_len
        if total > SHORTS_LIMIT:
            print(f"   ⚠️  Қисм {total:.0f} сония — Shorts/Reels 3 дақиқадан узунини қабул қилмайди. "
                  "Сценарийни қисқартиринг (script.json) ёки --minutes ни камайтиринг.")

        # Видео
        (self.dir / "parts.txt").write_text(
            "".join(f"file 'parts/{p.name}'\n" for p in [r.part for r in results] + [end_part]), encoding="utf-8")
        _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "parts.txt", "-c", "copy",
              "video_raw.mp4"], cwd=self.dir)

        # Товуш йўлаклари
        dialogue = [Placed(v.path, r.start + v.offset) for r in results for v in r.lines]
        dialogue += [Placed(v.path, shots_end + v.offset + 0.2) for v in teaser]
        place_track(dialogue, total, self.dir / "dialogue.wav")
        foley = [Placed(r.foley, r.start, r.length, 0.05, 0.25, VOLUME["foley"]) for r in results if r.foley]
        place_track(foley, total, self.dir / "foley.wav")
        place_track(self._ambience_runs(results, shots_end), total, self.dir / "ambience.wav")
        music = music_file or self._music(script, total)

        self._subtitles(script, results, teaser, shots_end, total, is_last)
        out = self._final_mix(total, music)
        self._timeline(script, results, total)
        print(f"   ✓ {total:.0f} сония, {len(results)} кадр, "
              f"{sum(r.lipsynced for r in results)} тасида лаб синхрони")
        return out

    def _end_card(self, last_part: Path, length: float) -> Path:
        still = self.dir / "parts" / "last.png"
        _run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.2", "-i", str(last_part), "-frames:v", "1",
              "-update", "1", str(still)])
        out = self.dir / "parts" / "end.mp4"
        _run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(still), "-t", f"{length:.3f}",
              "-vf", f"scale={W}:{H},gblur=sigma=14,eq=brightness=-0.16:saturation=0.55,format=yuv420p",
              "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-r", str(FPS), str(out)])
        return out

    def _ambience_runs(self, results: list[ShotResult], shots_end: float) -> list[Placed]:
        """Бир жойдаги кетма-кет кадрлар остида узлуксиз муҳит товуши (чегараларда силлиқ ўтиш)."""
        runs: list[list] = []
        for r in results:
            if runs and runs[-1][0] == r.shot.location_id:
                runs[-1][2] = r.start + r.length
            else:
                runs.append([r.shot.location_id, r.start, r.start + r.length])
        items = []
        for i, (loc, start, end) in enumerate(runs):
            path = self._ambience(loc)
            if not path:
                continue
            if i == len(runs) - 1:
                end = shots_end + 2.0  # охирги лавҳада ҳам секин сўнади
            s = max(0.0, start - 0.4)
            length = end - s + 0.4
            items.append(Placed(path, s, length, 0.4 if i else 0.0, 0.8, VOLUME["ambience"], loop=True))
        return items

    def _music(self, script: EpisodeScript, total: float) -> Path | None:
        if os.environ.get("MUSIC", "1") != "1" or not script.music_prompt:
            return None
        prompt = f"{script.music_prompt}. Style: {self.plan.music_style}. Instrumental film score, no vocals."
        path = self.dir / "sound" / f"music_{_sha(prompt, round(total))}.mp3"
        if path.exists():
            return path
        print("    🎵 мусиқа басталанмоқда...")
        return sound.music(prompt, total + 2, path)

    def _font(self) -> tuple[str, str]:
        """(шрифт номи, fontsdir параметри). FONT_FILE берилса — ўша файл ишлатилади."""
        name = os.environ.get("SUB_FONT", "")
        file = os.environ.get("FONT_FILE", "")
        if file and Path(file).exists():
            fonts = self.dir / "fonts"
            fonts.mkdir(exist_ok=True)
            shutil.copy(file, fonts / Path(file).name)
            if not name:
                probe = subprocess.run(["fc-scan", "--format", "%{family[0]}", file], capture_output=True, text=True,
                                       timeout=PROBE_TIMEOUT) \
                    if shutil.which("fc-scan") else None
                name = (probe.stdout.strip() if probe and probe.returncode == 0 else "") or Path(file).stem
            return name, ":fontsdir=fonts"
        return name or ("Arial" if os.name == "nt" else "DejaVu Sans"), ""

    def _subtitles(self, script: EpisodeScript, results: list[ShotResult], teaser: list[Voiced],
                   shots_end: float, total: float, is_last: bool) -> None:
        font, _ = self._font()
        margin = int(os.environ.get("SUB_MARGIN", "520"))  # пастдан: Shorts/Reels тугмалари ва ёзуви тагида қолмасин
        head = (
            "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n"
            "ScaledBorderAndShadow: yes\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
            "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
            "MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Sub,{font},62,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,4,1.5,2,90,90,{margin},204\n"
            f"Style: Narr,{font},58,&H00E8F0F5,&H000000FF,&H00101010,&H80000000,0,-1,0,0,100,100,0,0,1,4,1.5,2,90,90,{margin},204\n"
            f"Style: Title,{font},92,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,5,2,8,70,70,250,204\n"
            f"Style: Episode,{font},56,&H00E0E0E0,&H000000FF,&H00101010,&H80000000,0,0,0,0,100,100,1,0,1,4,1.5,8,70,70,370,204\n"
            f"Style: End,{font},70,&H00FFFFFF,&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,4,2,5,80,80,0,204\n"
            "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        events = []

        def add(a: float, b: float, style: str, text: str, fx: str = "") -> None:
            events.append(f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},{style},,0,0,0,,{fx}{_ass_text(text)}")

        def caption(text: str, a: float, b: float, style: str) -> None:
            pieces = split_caption(text, a, b)
            for i, (s, e, chunk) in enumerate(pieces):
                add(s, e + (0.15 if i == len(pieces) - 1 else 0.0), style, chunk)  # охиргиси бироз узоқроқ

        if os.environ.get("BURN_SUBTITLES", "1") == "1":
            for r in results:
                for v in r.lines:
                    a = r.start + v.offset
                    caption(v.text, a, a + v.dur, "Narr" if v.speaker == "narrator" else "Sub")
            for v in teaser:
                a = shots_end + v.offset + 0.2
                caption(v.text, a, a + v.dur, "Narr")
        title_end = min(3.4, results[0].length if results else 3.4)
        add(0.15, title_end, "Title", self.plan.series_title.upper(), r"{\fad(300,400)}")
        add(0.35, title_end, "Episode", f"Серия {script.number} · «{script.title}»", r"{\fad(300,400)}")
        add(shots_end + 0.1, total, "End", "Конец" if is_last else "Продолжение следует…", r"{\fad(400,300)}")
        (self.dir / "subs.ass").write_text(head + "\n".join(events) + "\n", encoding="utf-8")

    def _final_mix(self, total: float, music: Path | None) -> Path:
        _, fontsdir = self._font()
        grade = ""
        if os.environ.get("GRADE", "film") == "film":
            # Барча кадрларга ягона «кино» ранги: бироз контраст, юмшоқ виньетка, енгил плёнка доначаси
            grade = "eq=contrast=1.05:saturation=0.95:gamma=0.98,vignette=PI/5,noise=c0s=3:c0f=t,"
        vf = (f"[0:v]{grade}subtitles=subs.ass{fontsdir},fade=t=in:st=0:d=0.25,"
              f"fade=t=out:st={max(0.0, total - 0.5):.3f}:d=0.5,format=yuv420p[v]")
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", "video_raw.mp4", "-i", "dialogue.wav", "-i", "foley.wav",
               "-i", "ambience.wav"]
        if music:
            cmd += ["-stream_loop", "-1", "-i", str(Path(music).resolve())]
            af = (
                "[1:a]asplit=2[dlg][sc];"
                f"[4:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=0:{total:.3f},"
                f"asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.5,afade=t=out:st={max(0.0, total - 2.5):.3f}:d=2.5,"
                f"volume={VOLUME['music']}[m0];"
                "[sc]aformat=sample_fmts=fltp:channel_layouts=stereo[sc2];"
                "[m0][sc2]sidechaincompress=threshold=0.015:ratio=8:attack=20:release=450[mus];"
                "[dlg][2:a][3:a][mus]amix=inputs=4:normalize=0:duration=first,"
            )
        else:
            af = "[1:a][2:a][3:a]amix=inputs=3:normalize=0:duration=first,"
        af += "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
        # Аввал вақтинчалик файлга ёзилади: жараён узилса, чала видео «тайёр қисм» бўлиб қолмайди
        tmp = self.dir / "episode.tmp.mp4"
        tmp.unlink(missing_ok=True)
        cmd += ["-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
                "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
                "-r", str(FPS), "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart",
                tmp.name]
        try:
            _run(cmd, cwd=self.dir)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        if media_duration(tmp) < total - 1.0:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Йиғилган видео кутилганидан қисқа чиқди ({total:.1f} с бўлиши керак эди)")
        os.replace(tmp, self.dir / "episode.mp4")
        return self.dir / "episode.mp4"

    def _timeline(self, script: EpisodeScript, results: list[ShotResult], total: float) -> None:
        data = {
            "episode": script.number, "duration": round(total, 2),
            "shots": [{
                "shot": r.shot.number, "start": round(r.start, 2), "length": round(r.length, 2),
                "type": r.shot.shot_type, "location": r.shot.location_id, "lipsync": r.lipsynced,
                "lines": [{"at": round(r.start + v.offset, 2), "speaker": v.speaker, "text": v.text} for v in r.lines],
            } for r in results],
        }
        (self.dir / "timeline.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
