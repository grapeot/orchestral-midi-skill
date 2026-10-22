---
name: orchestral-midi
description: Scaffold skill for explicit orchestral score authoring (Art) and controlled stereo/headphone hall rendering (Science).
---

# Orchestral MIDI

**Scaffold status**: The CLI is planned, not yet executable. See the [Art/Science contract](../../docs/rfc.md).

## Core Contract

- **Art**: Author explicit integer-tick scores with tempo/meter maps, musical roles, playable ranges, phrase and climax intent, thinning/voice leading, and articulations. GM swaps, blind doubling, jitter and reverb cannot replace arrangement decisions.
- **Science**: Render SF2/FluidSynth or SFZ/sfizz mono stems with per-part library and ambience disclosure, or accept external stems. Compare stereo with measured-HRIR fixed-head hall rendering using image-source reflections plus a statistical late tail. Level-match and audit; do not invent listening conclusions.
- **Local overlay**: Find personal sample libraries, SOFA assets and machine aliases in the user's workspace routing/overlay, not this repository.
