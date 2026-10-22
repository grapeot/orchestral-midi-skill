# Planned Validation

No test or listening outcomes are asserted as completed in this scaffold. Automated tests will generate synthetic temporary fixtures without bundled MIDI, instruments, or SOFA datasets.

## Art

Verify tick positions, real meter changes, and tempo maps. Enforce explicit roles, playable ranges and positive note lengths. Verify dedicated articulation MIDI routing, preserving repeated note attacks rather than merging them into a sustain.

## Science

Verify mixing accepts external mono WAVs without score compilation. Check engine and per-part provenance, image-path delays/gains, statistical tail energy, SOFA coordinates and validation, complete convolution tails, matched levels and manifests. Tests measure numerical behavior; listening remains human evaluation.

External instrument integration is opt-in and requires locally supplied assets and binaries. Its absence must not be reported as successful instrument integration.
