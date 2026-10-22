# Working Status & Log

## Current Status

Scaffold complete; CLI implementation pending on a feature branch.

## Changelog

### 2026-10-22

- Initialized English documentation, package skeleton, and package-import CI check.

## Lessons Learned

- Decouple score decisions and acoustics so scoring flaws and spatial DSP bugs can be isolated.
- Preserve real meter changes and repeated same-pitch attacks; neither fixed four-beat grouping nor merging adjacent re-attacks is musically neutral.
- Spiccato needs a genuine articulation patch; clipping sustain note duration is not equivalent.
- Disclose mixed libraries and recorded room ambience per part.
- Generic HRTFs do not guarantee front externalization; level-matched listening is separate from numerical validation.
