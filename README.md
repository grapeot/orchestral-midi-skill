# orchestral-midi-skill

A Python toolkit and coding-agent skill for turning musical material into explicitly authored orchestral scores (Art) and controlled stereo/binaural hall renders (Science). The `orchestral-midi` CLI is a deterministic compiler and acoustic renderer for authored score JSON, not an automatic arbitrary MIDI arranger.

## Core Principle: Art vs. Science

- **[Art](skills/orchestral-midi/art.md)**: Explicit score authoring in integer ticks: MIDI inspection without assumed roles, phrase/tempo/meter maps, voice leading, register ranges, preserved same-pitch re-attacks, pacing across repeated themes, and explicit articulations. Lead / motion / bass is a starting reduction, not a universal law.
- **[Science](skills/orchestral-midi/science.md)**: Repeatable SF2 (FluidSynth) and SFZ (sfizz) mono stem synthesis with per-part library and ambience disclosure, rectangular image-source early reflections, a calibrated statistical late tail, measured-SOFA binaural convolution, and linear whole-mix LUFS/true-peak matching. External mono stems can enter `mix` without `score`.

## Installation & External Binaries

Requires Python >=3.11 and `uv`. External binaries are invoked as needed: `ffmpeg` for `mix`, `fluidsynth` for SF2, and `sfizz_render` for SFZ. No implicit asset downloads, network calls, or credentials are used.

```bash
uv venv
source .venv/bin/activate
uv pip install -e '.[dev]'
```

## CLI Usage & Example Configuration

```bash
# Compile an original authored score, then inspect its MIDI
orchestral-midi score --score examples/score.json --output outputs/score
orchestral-midi inspect --midi outputs/score/ensemble.mid --output outputs/inspection.json

# Copy/edit the instrument example with your own licensed library paths
cp examples/instruments.example.json examples/instruments.local.json
orchestral-midi synthesize --bundle outputs/score --instruments examples/instruments.local.json --output outputs/stems

# Edit scene provenance to match your instruments; SOFA enables direct/early/hall variants
orchestral-midi mix --scene examples/scene.json --sofa /path/to/measured.sofa --output outputs/listening
```

Relative `preset` and `stem` paths resolve from their JSON file's parent directory. Record each library's license and built-in sample ambience. See [examples](examples/score.json) and the [technical contract](docs/rfc.md) for fields, defaults, and output manifests. Omit `--sofa` for stereo-only output.

Every output target must be new. Success exits `0` with a JSON summary; handled failures exit `2` with JSON errors and may leave partial files/logs. A render is complete only after its `manifest.json` is written. Generic HRTFs and a static head do not guarantee headphone front externalization; musical quality remains a listening judgment.

## One-Root Agent Installation

1. Hand `https://github.com/grapeot/orchestral-midi-skill` to your coding agent (Codex, Claude Code, Cursor, or OpenCode).
2. The installer reads the target workspace `AGENTS.md` / `CLAUDE.md` and `WORKSPACE.md`, exposing **only** the single root skill `skills/orchestral-midi/SKILL.md` in the workspace skill index or agent instructions.
3. Keep personal sample library paths, SOFA files, and machine aliases in a local workspace overlay outside this repository.

## License Boundary

Code and documentation are MIT-licensed. This does not cover external musical assets; no SF2/SFZ libraries, copyrighted MIDI, or SOFA datasets are bundled. Supply properly licensed local assets.
