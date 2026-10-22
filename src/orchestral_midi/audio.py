"""External engines, explicit provenance, and linear level-matched audio outputs."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Annotated, Literal

import numpy as np
from pydantic import Field, model_validator
import soundfile as sf

from .acoustics import Hrtf, add_fractional, build_brir, convolve_pair, image_paths
from .score import Contract, Identifier, Score, dump

Positive = Annotated[float, Field(gt=0)]
Vector = Annotated[list[float], Field(min_length=3, max_length=3)]
Absorption = Annotated[list[Annotated[float, Field(ge=0, le=1)]], Field(min_length=3, max_length=3)]


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command, timeout=180):
    return subprocess.run([str(x) for x in command], capture_output=True, text=True, check=True, timeout=timeout)


class Patch(Contract):
    engine: Literal["sf2", "sfz"]
    preset: str
    library: Annotated[str, Field(min_length=1)]
    license: Annotated[str, Field(min_length=1)]
    ambience: Annotated[str, Field(min_length=1)]
    gain_db: Annotated[float, Field(ge=-90, le=18)] = 0.
    asset_manifest: str | None = None


class Instruments(Contract):
    sample_rate: Annotated[int, Field(ge=16000, le=96000)] = 48000
    tail_seconds: Annotated[float, Field(ge=0, le=30)] = 6.
    fluidsynth: str = "fluidsynth"
    sfizz: str = "sfizz_render"
    parts: dict[Identifier, dict[Identifier, Patch]]


def synthesize(bundle, config_path, output):
    bundle, config_path, output = Path(bundle), Path(config_path), Path(output)
    score = Score.model_validate_json((bundle / "score.json").read_text())
    config = Instruments.model_validate_json(config_path.read_text())
    if set(config.parts) != {p.id for p in score.parts}:
        raise ValueError("Instrument configuration must cover exactly the score parts")
    for part in score.parts:
        if set(config.parts[part.id]) != {n.articulation for n in part.notes}:
            raise ValueError(f"Part {part.id}: every articulation requires an explicit patch")
        for patch in config.parts[part.id].values():
            if not (config_path.parent / patch.preset).is_file():
                raise ValueError(f"Missing local preset for {part.id}")
            if patch.asset_manifest is not None and not (config_path.parent / patch.asset_manifest).is_file():
                raise ValueError(f"Missing asset inventory for {part.id}")
    output.mkdir(parents=True, exist_ok=False)
    frames = round((score.duration_seconds() + config.tail_seconds) * config.sample_rate)
    report = {"sample_rate": config.sample_rate, "score_sha256": digest(bundle / "score.json"), "parts": {}}
    for part in score.parts:
        stem = np.zeros(frames)
        provenance = {}
        for articulation, patch in config.parts[part.id].items():
            midi_path = bundle / "parts" / f"{part.id}.{articulation}.mid"
            raw = output / f"{part.id}.{articulation}.raw.wav"
            preset = (config_path.parent / patch.preset).resolve()
            if patch.engine == "sf2":
                command = [config.fluidsynth, "-ni", "-R", "0", "-C", "0", "-g", "0.2",
                           "-r", config.sample_rate, "-T", "wav", "-F", raw, preset, midi_path]
            else:
                command = [config.sfizz, "--sfz", preset, "--midi", midi_path, "--wav", raw,
                           "--samplerate", config.sample_rate, "--polyphony", "64"]
            proc = run(command)
            (output / f"{part.id}.{articulation}.log").write_text(proc.stdout + proc.stderr)
            wave, rate = sf.read(raw, always_2d=True)
            if (rate != config.sample_rate or wave.shape[1] not in (1, 2) or not np.isfinite(wave).all()
                    or not np.any(wave) or np.max(np.abs(wave)) >= .999):
                raise ValueError(f"Part {part.id}/{articulation}: empty, clipped, or invalid engine output")
            if len(wave) > frames and np.max(np.abs(wave[frames:]), initial=0) > 1e-4:
                raise ValueError("Configured tail_seconds truncates audible release; increase it")
            mono = wave.mean(axis=1)
            if not np.any(mono):
                raise ValueError("Stereo-to-mono cancellation produced an empty stem")
            subset = [n for n in part.notes if n.articulation == articulation]
            first_onset = score.seconds_at(min(n.start for n in subset))
            last_onset = score.seconds_at(max(n.start for n in subset))
            if len(mono) <= int(last_onset * config.sample_rate):
                raise ValueError(f"Part {part.id}/{articulation}: render ends before final scheduled onset")
            before = max(0, int(first_onset * config.sample_rate) - 2)
            # Some integer-WAV renderers represent digital silence one LSB
            # below zero. Allow two quantization steps, not audible early notes.
            floor = {"PCM_16": 2 ** -14, "PCM_24": 2 ** -22, "PCM_32": 2 ** -30}.get(
                sf.info(raw).subtype, 1e-7)
            if np.max(np.abs(mono[:before]), initial=0) > max(floor, np.max(np.abs(mono)) * 1e-4):
                raise ValueError(f"Part {part.id}/{articulation}: renderer did not preserve leading silence")
            count = min(frames, len(mono))
            stem[:count] += mono[:count] * 10 ** (patch.gain_db / 20)
            executable = shutil.which(str(command[0]))
            inventory = config_path.parent / patch.asset_manifest if patch.asset_manifest else None
            provenance[articulation] = {
                **patch.model_dump(exclude={"preset", "asset_manifest"}), "preset_name": preset.name,
                "preset_sha256": digest(preset), "midi_sha256": digest(midi_path),
                "asset_manifest_sha256": digest(inventory) if inventory else None,
                "renderer_name": Path(str(command[0])).name,
                "renderer_sha256": digest(executable) if executable else None,
                "settings": {"sample_rate": config.sample_rate, "polyphony": 64} if patch.engine == "sfz"
                else {"sample_rate": config.sample_rate, "gain": .2, "reverb": False, "chorus": False}}
        if np.max(np.abs(stem)) >= .999:
            raise ValueError(f"Part {part.id}: summed articulation stems clip; reduce patch gain_db")
        target = output / f"{part.id}.wav"
        sf.write(target, stem, config.sample_rate, subtype="PCM_24")
        report["parts"][part.id] = {"stem": target.name, "sha256": digest(target), "articulations": provenance}
    dump(output / "manifest.json", report)
    return report


class Room(Contract):
    size_m: Vector = [22., 30., 12.]
    speed_m_s: Annotated[float, Field(ge=300, le=380)] = 343.
    reflection_order: Annotated[int, Field(ge=0, le=8)] = 3
    reflection_plane: Literal["full", "horizontal"] = "full"
    wall_absorption_bands: Annotated[list[Absorption], Field(min_length=6, max_length=6)] = [[.25, .35, .5]] * 6
    air_loss_per_m_bands: Vector = [.0001, .0005, .002]
    rt60_bands_s: Vector = [1.6, 1.4, 1.0]
    late_start_s: Annotated[float, Field(ge=.01, le=.5)] = .08
    transition_s: Annotated[float, Field(gt=0, le=.5)] = .04
    late_to_direct_db: Annotated[float, Field(ge=-60, le=12)] = -6.
    diffuse_directions: Annotated[int, Field(ge=2, le=128)] = 16

    @model_validator(mode="after")
    def dimensions(self):
        if (any(x <= 0 or x > 200 for x in self.size_m) or any(x < 0 for x in self.air_loss_per_m_bands)
                or any(not .05 <= x <= 10 for x in self.rt60_bands_s)):
            raise ValueError("Invalid room dimensions, air loss, or RT60")
        if self.transition_s > 1.5 * min(self.rt60_bands_s):
            raise ValueError("Tail transition must not exceed 1.5 times shortest band RT60")
        return self


class Listener(Contract):
    position_m: Vector
    yaw_deg: float = 0.


class Source(Contract):
    id: Identifier
    stem: str
    position_m: Vector
    gain_db: Annotated[float, Field(ge=-90, le=24)] = 0.
    library: Annotated[str, Field(min_length=1)]
    license: Annotated[str, Field(min_length=1)]
    ambience: Annotated[str, Field(min_length=1)]
    provenance_manifest: str | None = None


class Scene(Contract):
    sample_rate: Annotated[int, Field(ge=16000, le=96000)] = 48000
    seed: Annotated[int, Field(ge=0)] = 42
    target_lufs: Annotated[float, Field(ge=-40, le=-10)] = -20.
    peak_ceiling_dbtp: Annotated[float, Field(ge=-12, le=-1)] = -3.
    room: Room = Field(default_factory=Room)
    listener: Listener
    sources: Annotated[list[Source], Field(min_length=1, max_length=64)]

    @model_validator(mode="after")
    def placement(self):
        if len({s.id for s in self.sources}) != len(self.sources):
            raise ValueError("Source IDs must be unique")
        for source in self.sources:
            image_paths(self.room.size_m, source.position_m, self.listener.position_m, 0,
                        max_seconds=10, speed=self.room.speed_m_s)
        return self


def loudness(path):
    proc = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
                "-af", "loudnorm=I=-20:TP=-3:LRA=11:print_format=json", "-f", "null", "-"])
    payload, _ = json.JSONDecoder().raw_decode(proc.stderr[proc.stderr.rfind("{"):])
    values = {"integrated_lufs": float(payload["input_i"]), "true_peak_dbtp": float(payload["input_tp"])}
    if not all(np.isfinite(x) for x in values.values()):
        raise ValueError("Audio is silent or too short for integrated loudness measurement")
    return values


def mix(scene_path, output, sofa=None):
    scene_path, output = Path(scene_path), Path(output)
    scene = Scene.model_validate_json(scene_path.read_text())
    spec, fs = scene.model_dump(), scene.sample_rate
    hrtf = Hrtf(sofa, fs) if sofa is not None else None
    stems = []
    for source in scene.sources:
        path = scene_path.parent / source.stem
        wave, rate = sf.read(path, always_2d=True)
        if (rate != fs or wave.shape[1] != 1 or not np.isfinite(wave).all()
                or not np.any(wave) or np.max(np.abs(wave)) >= .999):
            raise ValueError(f"Source {source.id}: requires nonempty unclipped mono stem at scene sample rate")
        stems.append((wave[:, 0] * 10 ** (source.gain_db / 20), digest(path)))
    output.mkdir(parents=True, exist_ok=False)
    max_frames = max(len(wave) for wave, _ in stems)
    max_delay = np.linalg.norm(scene.room.size_m) / scene.room.speed_m_s * fs
    stereo = np.zeros((2, max_frames + int(max_delay) + 2))
    variants, paths = {}, {}
    source_report = []
    for index, (source, (wave, sha)) in enumerate(zip(scene.sources, stems)):
        delta = np.asarray(source.position_m) - scene.listener.position_m
        distance = np.linalg.norm(delta)
        direction = np.asarray([delta[0], delta[1], 0.])
        pan = delta[0] / max(np.linalg.norm(direction), 1e-15)
        gains = np.sqrt(np.array([1 - pan, 1 + pan]) / 2) / distance
        add_fractional(stereo, gains[:, None] * wave[None, :], distance / scene.room.speed_m_s * fs)
        if hrtf is not None:
            pairs, paths[source.id] = build_brir(hrtf, spec, source.model_dump(), scene.seed + index)
            for name, pair in pairs.items():
                if name not in variants:
                    variants[name] = np.zeros((max_frames + pair.shape[1] - 1, 2))
                contribution = convolve_pair(wave, pair)
                variants[name][:len(contribution)] += contribution
        provenance = scene_path.parent / source.provenance_manifest if source.provenance_manifest else None
        if provenance is not None:
            inventory = json.loads(provenance.read_text())
            if inventory.get("parts", {}).get(source.id, {}).get("sha256") != sha:
                raise ValueError(f"Source {source.id}: synthesis manifest does not match stem hash")
        source_report.append({**source.model_dump(exclude={"stem", "provenance_manifest"}),
                              "stem_name": Path(source.stem).name, "sha256": sha, "frames": len(wave),
                              "provenance_manifest_sha256": digest(provenance) if provenance else None})
    variants["stereo"] = stereo.T
    length = max(len(wave) for wave in variants.values())
    initial, premeasurement_gain_db = {}, {}
    for name, wave in variants.items():
        wave = np.pad(wave, ((0, length - len(wave)), (0, 0)))
        peak = float(np.max(np.abs(wave)))
        if not np.isfinite(peak) or peak == 0:
            raise ValueError("Mix is silent or nonfinite")
        # Low-level raw mixes can hit EBU R128's absolute gate. Measure with
        # safe whole-mix headroom first; this never normalizes individual stems.
        calibration = .5 / peak
        premeasurement_gain_db[name] = float(20 * np.log10(calibration))
        wave = wave * calibration
        variants[name] = wave
        # FLOAT intermediates retain headroom; only final writes are quantized.
        path = output / f"{name}.raw.wav"
        sf.write(path, wave, fs, subtype="FLOAT")
        initial[name] = loudness(path)
    common_target = min([scene.target_lufs] + [v["integrated_lufs"] + scene.peak_ceiling_dbtp
                                             - v["true_peak_dbtp"] - .1 for v in initial.values()])
    files = {}
    for name, wave in variants.items():
        gain_db = common_target - initial[name]["integrated_lufs"]
        path = output / f"{name}.wav"
        sf.write(path, wave * 10 ** (gain_db / 20), fs, subtype="PCM_24")
        measured = loudness(path)
        if (abs(measured["integrated_lufs"] - common_target) > .15
                or measured["true_peak_dbtp"] > scene.peak_ceiling_dbtp):
            raise ValueError("Final PCM loudness/true-peak verification failed")
        files[name] = {**measured, "gain_db": gain_db + premeasurement_gain_db[name],
                       "sha256": digest(path), "frames": length}
    report = {"sample_rate": fs, "requested_lufs": scene.target_lufs, "matched_lufs": common_target,
              "peak_ceiling_dbtp": scene.peak_ceiling_dbtp, "scene_sha256": digest(scene_path),
              "sofa_sha256": digest(sofa) if sofa else None, "sources": source_report,
              "model": "Rectangular image-source early paths + statistical directional late tail; fixed head",
              "files": files, "paths": paths}
    dump(output / "manifest.json", report)
    return report
