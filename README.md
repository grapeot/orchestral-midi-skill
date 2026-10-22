# orchestral-midi-skill

For musicians and coding agents turning MIDI into deliberately arranged orchestral parts and controlled stereo/headphone hall renders.

## Status: Scaffold Only

This repository currently provides architecture and skill specifications. The Python package and `orchestral-midi` CLI (`inspect`, `score`, `synthesize`, `mix`) will be implemented on a feature branch; exact JSON schemas and CLI flags will be finalized there.

## Core Principle: Art vs. Science

Art and Science are decoupled and independently testable:
- **Art (Arrangement & Score)**: Explicit human/agent score decisions in integer ticks: musical roles, instrument ranges, phrases, harmony, repetition and climax, texture thinning and voice leading, real meter changes, playable note lengths, and genuine articulations. Spiccato is a distinct bow articulation, neither a chopped sustain patch nor synonymous with staccato. Swapping GM programs, doubling parts, randomizing timing, or adding reverb is not a substitute for these decisions.
- **Science (Synthesis & Acoustics)**: Repeatable MIDI timing, SF2 (FluidSynth) or SFZ (sfizz) dry-ish mono stems with built-in sample ambience disclosed, explicit per-part library provenance, source positions, rectangular image-source early reflections, an explicitly statistical late tail, fixed-head measured HRIR binaural rendering, level-matched A/B outputs, and auditable manifests. Generic HRTFs do not guarantee front externalization. Science accepts external mono stems independently of Art.

## One-Root Agent Installation Protocol

1. Hand `https://github.com/grapeot/orchestral-midi-skill` to your coding agent (Codex, Claude Code, Cursor, or OpenCode).
2. The installer reads the target workspace `AGENTS.md` / `CLAUDE.md` and `WORKSPACE.md`, exposing **only** the single root skill `skills/orchestral-midi/SKILL.md` in the workspace skill index or agent instructions.
3. Keep personal sample library paths, SOFA files, and machine aliases in a local workspace overlay outside this repository.

## License Boundary

Code and documentation are MIT-licensed. The MIT license does not cover external assets; no third-party samples, SF2/SFZ instruments, copyrighted MIDI files, or HRTF/SOFA datasets are bundled.
