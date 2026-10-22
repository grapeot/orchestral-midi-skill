# Working Status & Log

## Current Status

Implemented explicit score compilation, articulation synthesis, and controlled stereo/SOFA mixing. Offline suite: 29 passed; Ruff passed. Real FluidSynth + sfizz 1.2.3 + SADIE II D2 smoke completed. Independent follow-up review closed the original blocker and identified no remaining release blocker within its scope.

## Changelog

### 2026-10-22

- Initialized English documentation, package skeleton, and package-import CI check.
- Implemented `inspect`, `score`, `synthesize`, `mix`, strict schemas, numerical tests and original example.
- Verified real8.6s score ->14.6s stems ->four aligned839967-frame outputs at-20.00LUFS each.
- Fixed quiet-mix absolute loudness gating with whole-mix premeasurement calibration.
- Addressed independent review: premature/shifted render checks, restricted SOFA geometry, input-error reporting, transition limits, renderer/inventory/provenance fingerprints.
- Replaced scaffold documentation with implemented contracts and root skill routing to Art and Science guides.

## Lessons Learned

- Decouple score decisions and acoustics so scoring flaws and spatial DSP bugs can be isolated.
- Preserve real meter changes and repeated same-pitch attacks; neither fixed four-beat grouping nor merging adjacent re-attacks is musically neutral.
- Spiccato needs a genuine articulation patch; clipping sustain note duration is not equivalent.
- Disclose mixed libraries and recorded room ambience per part.
- Generic HRTFs do not guarantee front externalization; level-matched listening is separate from numerical validation.
- Nonempty engine output can still be truncated; test last-onset coverage and late-articulation leading silence.
- Some integer-WAV engines encode silence one LSB below zero; timing checks need format-aware tolerance.
- A top-level SFZ hash does not identify referenced samples/includes; inventory provenance must be explicit.
