"""Filesystem-native command interface."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from .audio import mix, synthesize
from .score import Score, dump, compile_score, inspect_midi


def main(argv=None):
    parser = argparse.ArgumentParser(description="Explicit orchestral scores and controlled audio renders")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Observe type 0/1 MIDI without guessing musical roles")
    inspect.add_argument("--midi", type=Path, required=True)
    inspect.add_argument("--output", type=Path, required=True)
    score = commands.add_parser("score", help="Validate and compile an authored JSON score")
    score.add_argument("--score", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    synth = commands.add_parser("synthesize", help="Render explicitly mapped SF2/SFZ articulation stems")
    synth.add_argument("--bundle", type=Path, required=True)
    synth.add_argument("--instruments", type=Path, required=True)
    synth.add_argument("--output", type=Path, required=True)
    mixing = commands.add_parser("mix", help="Render and LUFS-match mono stems; SOFA enables hall variants")
    mixing.add_argument("--scene", type=Path, required=True)
    mixing.add_argument("--sofa", type=Path)
    mixing.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            if args.output.exists():
                raise FileExistsError(args.output)
            report = inspect_midi(args.midi)
            dump(args.output, report)
        elif args.command == "score":
            report = compile_score(Score.model_validate_json(args.score.read_text()), args.output)
        elif args.command == "synthesize":
            report = synthesize(args.bundle, args.instruments, args.output)
        else:
            report = mix(args.scene, args.output, args.sofa)
        print(json.dumps({"command": args.command, "output": str(args.output), "status": "complete",
                          "summary": report.get("files", report.get("parts", {}))}, allow_nan=False))
        return 0
    except (ValueError, OSError, EOFError, subprocess.SubprocessError) as exc:
        error = {"command": args.command, "error": type(exc).__name__, "detail": str(exc)}
        if isinstance(exc, subprocess.CalledProcessError):
            error.update(returncode=exc.returncode, stdout=exc.stdout, stderr=exc.stderr)
        print(json.dumps(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
