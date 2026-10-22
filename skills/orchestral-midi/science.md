# Science: Synthesis, Acoustics & Level-Matched Mixing

See [SKILL.md](SKILL.md) for commands and the [RFC](../../docs/rfc.md) for fields. Science accepts generated or external mono stems independently of Art.

## Articulation Patches, Ambience & Stem Integrity

- Every articulation needs an explicit patch. Spiccato is a bounced short-bow articulation, neither clipped sustain nor synonymous with staccato. Mapping one preset to two keys is technically allowed but does not create a real short bow.
- Record library/license/ambience per patch and source. Already-wet recordings followed by mono-summing and artificial room reflections can smear attacks and imaging; choose/disclose sources accordingly. State exactly which parts use upgraded libraries.
- Duplicating samples with jitter/detuning does not manufacture independent players and can introduce comb filtering or phase coloration.
- FluidSynth disables reverb/chorus; sfizz uses polyphony64. Stereo sample output deliberately averages to mono, with no resampling/time-stretching. Explicit patch gain preserves inter-part decisions; no per-track peak normalization occurs.
- Raw and summed stems must stay below0.999 peak. Check final-onset coverage and late-articulation leading silence; format-aware tolerance accommodates integer-WAV silence bias. These are sanity checks, not proof every note sounds correctly. Keep audible release within the configured tail budget.
- Fingerprints cover top-level preset, MIDI, renderer binary/settings and output. For SFZ dependencies, supply an external `asset_manifest`; without it referenced samples/includes are not inventoried. Review generated logs and provenance before sharing local identifiers.

## Shared Geometry, Coordinates & Model

- Stereo/direct/early/hall share source geometry, gains, inverse-distance attenuation and fractional propagation delay. Retain full impulse-response tails and pad to a common frame count.
- World +Y front/+X right/+Z up; SOFA +X front/+Y left/+Z up. Positive yaw turns the binaural head left; stereo remains world-stage panning. The supported SOFA subset requires scene-matched rate, zero Data.Delay, origin listener, standard view/up, spherical degree source positions and Cartesian metre receivers left then right. Lookup selects nearest measured direction and keeps ear pairs together.
- Six walls ordered x-/x+/y-/y+/z-/z+, each with low/mid/high absorption across causal complementary500/4000Hz bands. Apply sqrt(1-absorption) per hit, inverse distance and empirical exponential air loss, not a humidity-aware ISO solver.
- Image-source paths fade out relative to direct arrival across the early/late transition. Horizontal mode suppresses floor/ceiling paths and samples horizontal diffuse directions; it is a diagnostic approximation, not an equivalent full3D room.
- The seeded late tail uses independent directional noise, per-band RT60 envelopes and explicit integrated late/direct calibration. It is a statistical model, not a solved physical room. Generic HRTFs and static head position limit externalization; direct HRIR alone may remain in-head.

## Quiet-Mix Calibration & Linear LUFS Matching

- Very quiet raw mixes can hit EBU R128's absolute gate. Each variant first receives whole-mix safe-headroom calibration to float peak0.5 before initial measurement; final reported gain includes that calibration.
- Lower the common target if necessary to satisfy every variant's true-peak ceiling. Use linear whole-mix gain, no limiter/compression; verify final PCM within0.15LU. Numerical/metadata QA does not prove musical quality or front externalization.
