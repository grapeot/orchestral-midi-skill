# Verification & Test Boundaries

Run `pytest -q` and `ruff check src tests` in the activated project environment. Automated tests use synthetic temporary fixtures with no bundled musical assets or network calls. FFmpeg is needed for the mixing integration test; without it that test explicitly skips.

## Art

Tests compile the original8.6s example with tempo changes and4/4 ->2/4 ->4/4, preserve maps and re-attacks, separate Type0 channels, reject Type2 and invalid score mutations, and verify CLI failure reporting without creating a bundle.

## Science

Tests cover event-timed mocked-engine articulation routing, premature/shifted render rejection and integer-WAV silence tolerance; image-path geometry, axis conversion, complementary filters, fractional delays, SOFA coordinate rejection, deterministic late/direct energy and invalid transitions. A local FFmpeg integration mixes a very quiet synthetic external stem through synthetic SOFA and checks full tails, common lengths, LUFS, peak, and no overwrite. These do not establish bandwise physical room accuracy.

## Real-Asset Smoke Verification

Locally verified with user-supplied external assets: the original8.6s score rendered through FluidSynth/GeneralUser GS melody and sfizz1.2.3/VSCO2CE viola sustain and spiccato, yielding14.6s mono stems including6s release allowance. SADIE II D2/KEMAR48kHz mixing produced four aligned839967-frame outputs (~17.50s): stereo/direct/early/hall each-20.00LUFS, true peaks-10.03/-9.64/-9.25/-9.32dBTP.

The external-asset smoke is not part of downloadable default tests and does not prove musical quality or front externalization. Automated engine routing uses a mock; it is not described as real instrument integration.
