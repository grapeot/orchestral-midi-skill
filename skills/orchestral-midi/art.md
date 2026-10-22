# Art: Orchestral Arrangement & Score Authoring

See [SKILL.md](SKILL.md) for commands and the [RFC](../../docs/rfc.md) for schemas. The CLI compiles authored score JSON; score decisions remain human/agent work.

## Inspect Source MIDI Without Guessing Roles

- Use `inspect` to observe Type0/1 MIDI PPQ, tempo/meter maps, notes, programs and controllers. Inspect register, density and phrase structure before assigning musical roles; do not hardcode source channels.
- The compiler authors notes, programs and maps only. It does not implement CC11 envelopes, pitch bend, bank select, sustain pedal, or harmony inference. Translate these deliberately into durations/velocities/articulations, or render external DAW stems for `mix`. Do not mistake the inspection report for lossless roundtrip support.

## Map Form, Meter, Tempo & Pacing

- Author tempo/meter maps from tick0; preserve real metric changes rather than forcing every bar into four beats.
- Keep alternating or ostinato accompaniment aligned to the intended grid. Rounding onsets during thinning can introduce accidental syncopation.
- Avoid spending the climax on the first statement. A repeated theme can gain momentum later: soft single-line lead with sustained inner notes, then sparse spiccato pulses and firmer velocities. Follow the actual piece rather than impose this arc universally.
- On longer works, render a meaningful20–30s excerpt covering a phrase or texture transition before extending the full arrangement. This is iteration guidance, not a mandatory approval gate.

## Roles, Voice Leading, Articulation & Playability

- Reducing a dense source to one lead, one motion layer and one stable bass is a useful starting discipline against muddy tutti doubling, not a universal orchestration rule.
- Declare ranges, separate registers and split divisi or contrasting bowings into independent parts. `max_polyphony` is a simultaneous-note cap, not proof of fingerboard or instrument-technique playability.
- Preserve same-pitch re-attacks with `end <= next.start`; overlapping attacks are rejected. Leave musically appropriate bow/breath separation instead of joining every repetition into one long note.
- Velocity, duration and articulation must serve phrase intent; record rationale in `decisions`. Dynamics, CC11 and timing curves cannot rescue implausible notes, bad registers or incorrect articulations. Program swaps, blind doubling and jitter do not replace arrangement.
