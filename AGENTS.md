# AGENTS.md

## Language & Public Repository Rules

- Write all code, comments, commit messages, and documentation in English.
- Keep third-party SF2/SFZ libraries, samples, copyrighted MIDI, and SOFA/HRTF files outside the repository. Code MIT licensing does not license external assets. Use synthetic in-test fixtures.

## Python Environment (`uv`)

- Target Python >=3.11 (`mido`, `numpy`, `scipy`, `h5py`, `soundfile`, `pytest`).
- Check for `.venv/` in the repository root first; if missing, run `uv venv`. Activate `.venv` before running Python tools; install packages with `uv pip install`.

## Git & Branch Protection

- Require explicit user authorization before commits, pushes, or pull request actions. Stage specific task files only.
- `master` is the default branch: pull request required, admin enforcement enabled, 0 required approvals. Implementation happens on feature branches; never bypass protection.

## Project Layout & Delivery Discipline

- `docs/{prd,rfc,test,working}.md` holds requirements, architecture, verification, and progress. `skills/orchestral-midi/SKILL.md` is the only root skill. Runtime code lives in `src/orchestral_midi/`; tests in `tests/`.
- Update `docs/working.md` as work progresses and verify changes before delivery. Do not claim scaffolded features work until implemented and verified.
