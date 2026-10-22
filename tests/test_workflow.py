"""Numerical contracts tested without external musical assets or downloads."""

import copy
import json
from pathlib import Path
import shutil
import subprocess

import h5py
import mido
import numpy as np
import pytest
import soundfile as sf

from orchestral_midi.acoustics import Hrtf, add_fractional, band_parts, build_brir, head_direction, image_paths
from orchestral_midi.audio import Scene, mix, synthesize
from orchestral_midi.cli import main
from orchestral_midi.score import Score, compile_score, dump, inspect_midi

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def score_data():
    return json.loads((ROOT / "examples/score.json").read_text())


def make_sofa(path, fs=16000):
    with h5py.File(path, "w") as f:
        f.attrs["SOFAConventions"] = "SimpleFreeFieldHRIR"
        f["Data.SamplingRate"] = [fs]
        f["Data.Delay"] = [[0., 0.]]
        f["ListenerView"] = [[1., 0., 0.]]
        f["ListenerUp"] = [[0., 0., 1.]]
        f["ListenerPosition"] = [[0., 0., 0.]]
        f["ReceiverPosition"] = np.array([[0., .09, 0.], [0., -.09, 0.]])[:, :, None]
        for name in ("ListenerView", "ListenerPosition", "ReceiverPosition"):
            f[name].attrs["Type"] = "cartesian"
        for name in ("ListenerPosition", "ReceiverPosition"):
            f[name].attrs["Units"] = "metre"
        f["SourcePosition"] = [[0., 0., 1.], [90., 0., 1.], [270., 0., 1.]]
        f["SourcePosition"].attrs.update(Type="spherical", Units="degree, degree, metre")
        ir = np.zeros((3, 2, 8))
        ir[0, :, 0] = 1.
        ir[1, 0, 0], ir[1, 1, 3] = 1., .7
        ir[2, 0, 3], ir[2, 1, 0] = .7, 1.
        f["Data.IR"] = ir
    return path


def scene_data(stem="tone.wav"):
    return {"sample_rate": 16000, "room": {"size_m": [10., 12., 6.], "rt60_bands_s": [.2, .2, .15],
                                          "diffuse_directions": 4},
            "listener": {"position_m": [5., 4., 1.3]},
            "sources": [{"id": "test", "stem": stem, "position_m": [4., 8., 1.3],
                         "library": "Synthetic sine", "license": "Original test fixture", "ambience": "None"}]}


def test_score_roundtrip_and_articulation_timeline(tmp_path, score_data):
    score = Score.model_validate(score_data)
    report = compile_score(score, tmp_path / "bundle")
    observed = inspect_midi(tmp_path / "bundle/ensemble.mid")
    assert observed["tempos"] == score_data["tempos"]
    assert observed["meters"] == score_data["meters"]
    assert observed["duration_s"] == pytest.approx(8.6)
    assert report["duration_s"] == pytest.approx(8.6)
    assert observed["end_tick"] == score.end_tick
    for channel, part in zip(("0", "1"), score.parts):
        assert observed["channels"][channel]["notes"] == [n.model_dump(exclude={"articulation"}) for n in part.notes]
        for articulation, filename in report["parts"][part.id]["midi"].items():
            subset = inspect_midi(tmp_path / "bundle" / filename)
            assert subset["tempos"] == observed["tempos"]
            assert subset["meters"] == observed["meters"]
            assert subset["duration_s"] == pytest.approx(8.6)
            assert subset["channels"]["0"]["notes"] == [n.model_dump(exclude={"articulation"})
                                                        for n in part.notes if n.articulation == articulation]


@pytest.mark.parametrize("mutation", ["overlap", "range", "ticks", "duplicate", "meter", "polyphony", "end"])
def test_score_rejects_ambiguous_or_invalid_input(score_data, mutation):
    data = copy.deepcopy(score_data)
    if mutation == "overlap":
        data["parts"][0]["notes"].append({"start": 1, "end": 300, "pitch": 67, "velocity": 60})
    elif mutation == "range":
        data["parts"][0]["range"] = [72, 84]
    elif mutation == "ticks":
        data["parts"][0]["notes"][0]["start"] = 0.5
    elif mutation == "duplicate":
        data["parts"][1]["id"] = "melody"
    elif mutation == "meter":
        data["meters"][0]["denominator"] = 3
    elif mutation == "polyphony":
        data["parts"][0]["notes"].append({"start": 1, "end": 300, "pitch": 70, "velocity": 60})
    else:
        data["end_tick"] = 100
    with pytest.raises(ValueError):
        Score.model_validate(data)


def test_repeated_pitch_attacks_survive(tmp_path, score_data):
    score_data["parts"][0]["notes"] = [{"start": t, "end": t + 240, "pitch": 67, "velocity": 60}
                                       for t in (0, 240, 480)]
    compile_score(Score.model_validate(score_data), tmp_path / "bundle")
    notes = inspect_midi(tmp_path / "bundle/ensemble.mid")["channels"]["0"]["notes"]
    assert [n["start"] for n in notes] == [0, 240, 480]


def test_type_zero_channels_and_rejected_type_two(tmp_path):
    path = tmp_path / "type0.mid"
    midi = mido.MidiFile(type=0)
    midi.tracks.append(mido.MidiTrack([mido.Message("note_on", channel=2, note=60, velocity=70),
                                      mido.Message("note_on", channel=5, note=64, velocity=60),
                                      mido.Message("note_off", channel=2, note=60, time=240),
                                      mido.Message("note_off", channel=5, note=64)]))
    midi.save(path)
    assert set(inspect_midi(path)["channels"]) == {"2", "5"}
    midi.type = 2
    midi.save(path)
    with pytest.raises(ValueError, match="synchronous"):
        inspect_midi(path)


def test_image_source_geometry_and_head_axes():
    paths = image_paths([10, 12, 6], [4, 8, 1.3], [5, 4, 1.3], 1)
    assert len(paths) == 7
    assert paths[0].distance == pytest.approx(np.sqrt(17))
    assert sum(sum(p.hits) == 1 for p in paths) == 6
    assert np.allclose(head_direction([0, 1, 0], 0), [1, 0, 0])
    assert np.allclose(head_direction([1, 0, 0], 0), [0, -1, 0])
    assert np.allclose(head_direction([0, 1, 0], 90), [0, -1, 0])


def test_filter_complement_and_paired_fractional_delay():
    wave = np.random.default_rng(0).standard_normal((2, 100))
    assert np.allclose(band_parts(wave, 16000).sum(axis=0), wave)
    buffer = np.zeros((2, 8))
    add_fractional(buffer, np.array([[1., 0], [0, 1.]]), 2.25)
    assert np.allclose(buffer[0, 2:4], [.75, .25])
    assert np.allclose(buffer[1, 3:5], [.75, .25])


@pytest.mark.parametrize("fault", ["rate", "delay", "units", "orientation", "receivers", "nan",
                                  "receiver_type", "listener_origin", "missing"])
def test_sofa_rejects_unsupported_conventions(tmp_path, fault):
    path = make_sofa(tmp_path / "test.sofa")
    with h5py.File(path, "r+") as f:
        if fault == "rate":
            f["Data.SamplingRate"][0] = 48000
        elif fault == "delay":
            f["Data.Delay"][0, 1] = 1
        elif fault == "units":
            f["SourcePosition"].attrs["Units"] = "radian, radian, metre"
        elif fault == "orientation":
            f["ListenerView"][:] = [[0, 1, 0]]
        elif fault == "receivers":
            f["ReceiverPosition"][:] *= -1
        elif fault == "nan":
            f["Data.IR"][0, 0, 0] = float("nan")
        elif fault == "receiver_type":
            f["ReceiverPosition"].attrs["Type"] = "spherical"
        elif fault == "listener_origin":
            f["ListenerPosition"][0, 0] = 1
        else:
            del f["ListenerPosition"]
    with pytest.raises(ValueError):
        Hrtf(path, 16000)


def test_brir_determinism_tail_energy_and_horizontal_paths(tmp_path):
    hrtf = Hrtf(make_sofa(tmp_path / "test.sofa"), 16000)
    scene = Scene.model_validate(scene_data()).model_dump()
    scene["room"]["reflection_plane"] = "horizontal"
    a, paths = build_brir(hrtf, scene, scene["sources"][0], 42)
    b, _ = build_brir(hrtf, scene, scene["sources"][0], 42)
    assert np.array_equal(a["hall"], b["hall"])
    assert all(sum(p["wall_hits"][4:]) == 0 for p in paths)
    late = a["hall"] - a["early"]
    assert np.sum(late ** 2) / np.sum(a["direct"] ** 2) == pytest.approx(10 ** (-6 / 10))
    assert not np.any(a["direct"][:, :int(np.sqrt(17) / 343 * 16000)])


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg is required for LUFS integration")
def test_external_stems_to_level_matched_hall(tmp_path):
    fs = 16000
    t = np.arange(fs * 4) / fs
    wave = .00008 * np.sin(2 * np.pi * 440 * t) * np.minimum(t * 10, 1)
    sf.write(tmp_path / "tone.wav", wave, fs, subtype="FLOAT")
    dump(tmp_path / "scene.json", scene_data())
    sofa = make_sofa(tmp_path / "test.sofa")
    report = mix(tmp_path / "scene.json", tmp_path / "mix", sofa)
    assert set(report["files"]) == {"stereo", "direct", "early", "hall"}
    assert len({entry["frames"] for entry in report["files"].values()}) == 1
    assert report["files"]["hall"]["frames"] > len(wave) + 16000 * .3
    for entry in report["files"].values():
        assert abs(entry["integrated_lufs"] - report["matched_lufs"]) <= .15
        assert entry["true_peak_dbtp"] <= -3
    assert (tmp_path / "mix/manifest.json").is_file()
    with pytest.raises(FileExistsError):
        mix(tmp_path / "scene.json", tmp_path / "mix", sofa)


@pytest.mark.parametrize("fault", [None, "truncated", "shifted", "quantized_silence"])
def test_synthesis_articulation_routing_and_provenance(tmp_path, score_data, monkeypatch, fault):
    score = Score.model_validate(score_data)
    compile_score(score, tmp_path / "bundle")
    (tmp_path / "fake.sfz").write_text("Synthetic engine fixture; not an instrument")
    patch = {"engine": "sfz", "preset": "fake.sfz", "library": "Fixture", "license": "Original", "ambience": "None"}
    dump(tmp_path / "instruments.json", {"sample_rate": 16000, "parts": {
        "melody": {"sustain": patch}, "inner": {"sustain": patch, "spiccato": patch}}})
    calls = []

    def fake_engine(command):
        calls.append(command)
        target = command[command.index("--wav") + 1]
        midi_path = command[command.index("--midi") + 1]
        notes = inspect_midi(midi_path)["channels"]["0"]["notes"]
        wave = np.zeros((round(score.duration_seconds() * 16000), 2))
        for note in notes:
            start = round(score.seconds_at(note["start"]) * 16000)
            end = round(score.seconds_at(note["end"]) * 16000)
            wave[start:end] = .01
        if fault == "truncated":
            wave = np.ones((160, 2)) * .01
        elif fault == "shifted":
            wave[:160] = .01
        elif fault == "quantized_silence":
            wave[wave == 0] = -1 / 32768
        sf.write(target, wave, 16000, subtype="PCM_16" if fault == "quantized_silence" else "FLOAT")
        return subprocess.CompletedProcess(command, 0, "fixture engine", "")

    monkeypatch.setattr("orchestral_midi.audio.run", fake_engine)
    if fault in ("truncated", "shifted"):
        with pytest.raises(ValueError, match="scheduled onset|leading silence"):
            synthesize(tmp_path / "bundle", tmp_path / "instruments.json", tmp_path / "stems")
        assert not (tmp_path / "stems/manifest.json").exists()
        return
    result = synthesize(tmp_path / "bundle", tmp_path / "instruments.json", tmp_path / "stems")
    assert len(calls) == 3
    assert set(result["parts"]["inner"]["articulations"]) == {"sustain", "spiccato"}
    stem, rate = sf.read(tmp_path / "stems/inner.wav")
    assert rate == 16000 and len(stem) == round(14.6 * 16000)
    assert stem[0] == pytest.approx(.01, abs=1e-4)
    raw, _ = sf.read(tmp_path / "stems/inner.spiccato.raw.wav")
    assert np.max(np.abs(raw[:80000])) <= 2 / 32768
    assert np.max(np.abs(raw[80000:])) > .001


def test_incompatible_tail_transition_is_rejected():
    data = scene_data()
    data["room"].update(rt60_bands_s=[.05, .05, .05], transition_s=.5)
    with pytest.raises(ValueError, match="Tail transition"):
        Scene.model_validate(data)


def test_cli_reports_validation_error_without_writing_bundle(tmp_path, capsys):
    dump(tmp_path / "invalid.json", {"parts": []})
    assert main(["score", "--score", str(tmp_path / "invalid.json"), "--output", str(tmp_path / "bundle")]) == 2
    assert "ValidationError" in capsys.readouterr().err
    assert not (tmp_path / "bundle").exists()
