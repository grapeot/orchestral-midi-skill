---
name: orchestral-midi
description: Author explicit orchestral scores (Art), synthesize SF2/SFZ articulations, and render LUFS-matched stereo/SOFA binaural hall mixes (Science).
---

# Orchestral MIDI

Turn musical material or MIDI into deliberately authored orchestral scores and controlled stereo/headphone renders. The CLI compiles authored JSON; it does not automatically arrange arbitrary MIDI.

## Focused Guides & Reference Routing

- **[Art](art.md)**: Read before interpreting source MIDI or authoring scores. Roles, phrases, meter, voice leading, ranges, repetition pacing, re-attacks and articulations.
- **[Science](science.md)**: Read before choosing patches, stems, room or SOFA. Sample ambience, genuine short bow, coordinate conventions, reflection/tail model and level matching.
- **[Technical contract](../../docs/rfc.md)** and **[examples](../../examples/score.json)**: Exact fields, defaults and manifest outputs. Resolve links against this file's canonical repository directory if installed by symlink.

## Setup & CLI

```bash
uv venv
source .venv/bin/activate
uv pip install -e '.[dev]'
orchestral-midi inspect --midi SOURCE.mid --output inspection.json
orchestral-midi score --score examples/score.json --output outputs/score
orchestral-midi synthesize --bundle outputs/score --instruments CONFIG --output outputs/stems
orchestral-midi mix --scene examples/scene.json --sofa /path/to/measured.sofa --output outputs/listening
```

External binaries: ffmpeg for mix, fluidsynth for SF2, sfizz_render for SFZ. No automatic downloads. Relative paths resolve from their config's parent; output targets must be new. Exit0 writes JSON success; handled failures exit2 with details and may leave partial files. Verify completion manifest before proceeding. Personal sample paths, SOFA locations and machine aliases belong in the user's workspace overlay/routing.

## Acceptance

1. Valid explicit score with musical `decisions`, tempo/meter maps, declared ranges/polyphony and preserved same-pitch attacks. On longer works, test a meaningful20–30s excerpt when practical.
2. Every articulation explicitly mapped, library/license/ambience disclosed, render timing checked, raw/summed stems unclipped, audible releases retained. Fingerprint inputs and disclose SFZ inventory limitations.
3. Completed mix manifest and common-length PCM24 WAVs, matched within0.15LU of `matched_lufs`, below the true-peak ceiling, full convolution tails intact.
4. Numerical checks and human listening are distinct. Do not claim musical quality or headphone front externalization from metrics alone.
