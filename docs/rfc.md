# Technical RFC: Art/Science Contract

**Status**: Scaffold only; exact schemas and CLI flags will be finalized on the feature branch.

**Stack**: Python >=3.11, uv, mido, numpy, scipy, h5py, soundfile, pytest.

## Interface Contract

1. **Art (`score`)**: Authored scores use absolute integer ticks with explicit tempo and time-signature maps. Parts declare roles, ranges, playable note lengths, and articulations; musical decisions about phrases, harmony, climax and thinning remain explicit human/agent work. Arbitrary MIDI roles are never auto-guessed.
2. **Science (`synthesize`, `mix`)**: Render mono stems from explicit instrument configuration, recording sample ambience and per-part library provenance. Mix generated or external stems independently of Art. Use rectangular image-source early reflections plus an explicitly statistical tail and measured SOFA HRIRs for fixed-head headphone rendering. Produce matched-level A/B outputs and a JSON manifest. Generic HRTFs do not guarantee front externalization.

## Planned CLI

- `inspect`: MIDI tracks/channels, tempo/meter maps, pitch/duration statistics without guessing roles.
- `score`: Authored tick-based JSON to ensemble and per-part articulation MIDI.
- `synthesize`: Score bundle + explicit SF2/SFZ configuration to mono stems and provenance.
- `mix`: Mono stems + scene + optional measured SOFA to stereo and headphone hall mixes.
