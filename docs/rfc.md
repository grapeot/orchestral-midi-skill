# Technical RFC: Art/Science Contract

**Status**: Implemented in `src/orchestral_midi/{score,audio,acoustics,cli}.py`.

**Stack**: Python >=3.11, uv, pydantic, mido, numpy, scipy, h5py, soundfile, pytest; external ffmpeg, fluidsynth, sfizz_render.

## Interface Contract

1. **Art (`score`)**: Authored scores use absolute integer ticks with explicit tempo and time-signature maps. Parts declare roles, ranges, playable note lengths, and articulations; musical decisions about phrases, harmony, climax and thinning remain explicit human/agent work. Arbitrary MIDI roles are never auto-guessed.
2. **Science (`synthesize`, `mix`)**: Render mono stems from explicit instrument configuration, recording sample ambience and per-part library provenance. Mix generated or external stems independently of Art. Use rectangular image-source early reflections plus an explicitly statistical tail and measured SOFA HRIRs for fixed-head headphone rendering. Produce matched-level A/B outputs and a JSON manifest. Generic HRTFs do not guarantee front externalization.

## CLI & Execution Contract

- `inspect`: MIDI tracks/channels, tempo/meter maps, pitch/duration statistics without guessing roles.
- `score`: Authored tick-based JSON to ensemble and per-part articulation MIDI.
- `synthesize`: Score bundle + explicit SF2/SFZ configuration to mono stems and provenance.
- `mix`: Mono stems + scene + optional measured SOFA to stereo and headphone hall mixes.

Every command requires a new `--output` target. Success exits `0` with `{command, output, status: "complete", summary}` on stdout. Handled input/I/O/subprocess failures exit `2` with `{command, error, detail}` on stderr; engine failures also include returncode/stdout/stderr. Partial outputs may remain after failure; completion requires `manifest.json` (or inspect's output JSON).

| Command | Required flags | Output |
|---|---|---|
| inspect | `--midi FILE --output FILE` | Type, PPQ, duration, end tick, tempo/meter maps, channels with notes/programs/controllers, warnings. Type 2 and SMPTE timing rejected. |
| score | `--score FILE --output DIR` | `ensemble.mid`, `parts/<part>.<art>.mid`, canonical `score.json`, `manifest.json`. |
| synthesize | `--bundle DIR --instruments FILE --output DIR` | `<part>.wav` PCM24 mono, articulation raw WAVs/logs, provenance `manifest.json`. |
| mix | `--scene FILE --output DIR`, optional `--sofa FILE` | `stereo.wav`; with SOFA also `direct.wav`, `early.wav`, `hall.wav`; float intermediates and manifest. All final files share frame count. |

## Data Models

Examples: `examples/{score,instruments.example,scene}.json`. Pydantic contracts are strict, reject extra fields and nonfinite numbers. Derive exact JSON Schemas using `Score.model_json_schema()`, `Instruments.model_json_schema()`, and `Scene.model_json_schema()`; there is no schema CLI.

| Model | Fields & invariants |
|---|---|
| Score | `title`, `decisions`, `ticks_per_beat` (24..32767, default480), `end_tick`, nonempty `tempos`, `meters`, 1..15 `parts`. Tempo/meter maps start at0, increase uniquely, precede end tick. |
| Tempo / Meter | `{tick, microseconds_per_beat}` / `{tick, numerator, denominator}`. Denominator power of two, <=128. Timing is absolute integer ticks. |
| Part / Note | Part `{id, role, program, range:[low,high], max_polyphony, notes}`. Note `{start,end,pitch,velocity,articulation}`. Positive duration, velocity1..127, MIDI pitches0..127 within declared range. Default articulation sustain, max_polyphony1. Same-pitch overlaps rejected. IDs match `^[a-z][a-z0-9_-]{0,47}$`. |
| Instruments / Patch | `sample_rate`16000..96000 default48000, `tail_seconds`0..30 default6, engine executable names, `parts[id][articulation]`. Every patch declares `engine` sf2/sfz, `preset`, `library`, `license`, `ambience`, optional `gain_db` default0 and `asset_manifest`. Keys must exactly match score parts/articulations. |
| Scene / Source | Sample rate, `seed`, `target_lufs` default-20, `peak_ceiling_dbtp` default-3, `room`, `listener:{position_m,yaw_deg}`, 1..64 `sources`. Each source has `id`, `stem`, `position_m`, `gain_db`, `library`, `license`, `ambience`, optional `provenance_manifest`. Sources/listener strictly inside room and >=0.2m apart. |
| Room | Defaults22x30x12m, speed343m/s, reflection_order3 (0..8), full/horizontal plane, six wall absorption triplets, air-loss triplet, RT60 triplet [1.6,1.4,1.0]s, late_start0.08s, transition0.04s, late/direct-6dB, 16 diffuse directions. Transition <=1.5 times shortest RT60. |

## Synthesis & Provenance

Programs are zero-based, SF2 bank0; ensemble channels skip GM percussion channel9. Each articulation MIDI uses channel0 and the full score tempo/meter timeline. `inspect` observes controllers, but the authored compiler emits notes/programs/maps only; pedal, banks, bends, CC envelopes and expression require deliberate translation or external DAW stems.

Preset and optional inventory paths resolve relative to instrument JSON; stems and optional provenance paths relative to scene JSON. FluidSynth disables reverb/chorus with gain0.2; sfizz uses polyphony64. Output must be finite, nonempty, rate-matched, and raw peak<0.999. Stereo engine outputs average to mono. Reject renders ending before the final scheduled onset or sounding before their first onset (with quantization tolerance). Silent end-of-track padding may be added; this is a timing sanity check, not proof every instrument played every note. Reject audible release >1e-4 beyond the requested tail budget.

Manifests fingerprint score, MIDI, top-level preset, renderer binary/settings, and stem. For SFZ, a preset hash alone does **not** cover sample/include dependencies. Supply `asset_manifest` pointing to an externally generated dependency inventory to fingerprint that inventory; the toolkit does not parse or validate every SFZ dependency. Source `provenance_manifest` optionally links synthesis metadata by hash and verifies its part stem hash. Binary hashes identify executables, not every linked library. Generated logs/manifests can contain local filenames or user-entered attribution; review them before sharing.

## Acoustics & Loudness

World +X right/+Y front/+Z up rotates into SOFA +X front/+Y left/+Z up; positive yaw turns left. Stereo uses world-stage panning, independent of head yaw. Both stereo and binaural variants share distance gain and fractional propagation delay.

SOFA support is restricted to SimpleFreeFieldHRIR, scene-matched rate, Data.Delay=0, spherical source positions in degrees/degrees/metres, single origin listener, standard Cartesian view/up, Cartesian metre receivers left then right. ListenerUp may inherit ListenerView's Cartesian system. HRIR lookup is nearest-direction, selecting both ears together; no interpolation or resampling.

Walls ordered x-/x+/y-/y+/z-/z+; causal complementary low/mid/high bands split at500/4000Hz. Reflections apply sqrt(1-absorption) per hit, inverse-distance gain, and empirical exponential air loss. The late tail is seeded directional noise with per-band RT60 and explicit integrated late/direct calibration, not a solved room simulation. Horizontal mode suppresses floor/ceiling paths and samples a horizontal diffuse field.

Each variant is whole-mix calibrated to a float peak0.5 before FFmpeg loudness measurement, avoiding its absolute gate on quiet raw mixes. Linear gain matches every output to a common target; lower that target if any true peak would exceed the ceiling, with0.1dB margin. Verify final PCM within0.15LU and below the ceiling. No limiter/compression or per-stem normalization is used. Preserve the full convolution tail and pad variants to a common length.
