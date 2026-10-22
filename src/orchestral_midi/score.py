"""Explicit score contracts and MIDI observation; no automatic orchestration."""

from collections import defaultdict, deque
import json
from pathlib import Path
from typing import Annotated

import mido
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


Tick = Annotated[int, Field(ge=0)]
Pitch = Annotated[int, Field(ge=0, le=127)]
Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,47}$")]


class Tempo(Contract):
    tick: Tick
    microseconds_per_beat: Annotated[int, Field(ge=1, le=16777215)]


class Meter(Contract):
    tick: Tick
    numerator: Annotated[int, Field(ge=1, le=255)]
    denominator: Annotated[int, Field(ge=1, le=128)]

    @model_validator(mode="after")
    def power_of_two(self):
        if self.denominator & (self.denominator - 1):
            raise ValueError("Meter denominator must be a power of two")
        return self


class Note(Contract):
    start: Tick
    end: Tick
    pitch: Pitch
    velocity: Annotated[int, Field(ge=1, le=127)]
    articulation: Identifier = "sustain"

    @model_validator(mode="after")
    def duration(self):
        if self.end <= self.start:
            raise ValueError("Note end must follow start")
        return self


class Part(Contract):
    id: Identifier
    role: Annotated[str, Field(min_length=1)]
    program: Pitch = 48
    range: Annotated[list[Pitch], Field(min_length=2, max_length=2)]
    max_polyphony: Annotated[int, Field(ge=1, le=32)] = 1
    notes: Annotated[list[Note], Field(min_length=1)]

    @model_validator(mode="after")
    def playable(self):
        low, high = self.range
        if low > high or any(not low <= n.pitch <= high for n in self.notes):
            raise ValueError(f"Part {self.id}: notes outside declared range")
        active = {}
        for note in sorted(self.notes, key=lambda n: (n.start, n.pitch)):
            active = {pitch: end for pitch, end in active.items() if end > note.start}
            if note.pitch in active:
                raise ValueError(f"Part {self.id}: overlapping same-pitch notes obscure re-attacks")
            active[note.pitch] = note.end
            if len(active) > self.max_polyphony:
                raise ValueError(f"Part {self.id}: exceeds declared polyphony")
        return self


class Score(Contract):
    title: Annotated[str, Field(min_length=1)]
    decisions: Annotated[str, Field(min_length=1)]
    ticks_per_beat: Annotated[int, Field(ge=24, le=32767)] = 480
    end_tick: Annotated[int, Field(ge=1)]
    tempos: Annotated[list[Tempo], Field(min_length=1)]
    meters: Annotated[list[Meter], Field(min_length=1)]
    parts: Annotated[list[Part], Field(min_length=1, max_length=15)]

    @model_validator(mode="after")
    def timeline(self):
        for mapping in (self.tempos, self.meters):
            ticks = [item.tick for item in mapping]
            if ticks[0] != 0 or ticks != sorted(set(ticks)) or ticks[-1] >= self.end_tick:
                raise ValueError("Tempo/meter maps must start at 0, increase uniquely, and precede end_tick")
        if len({p.id for p in self.parts}) != len(self.parts):
            raise ValueError("Part IDs must be unique")
        if any(n.end > self.end_tick for p in self.parts for n in p.notes):
            raise ValueError("All notes must end by end_tick")
        return self

    def duration_seconds(self):
        return self.seconds_at(self.end_tick)

    def seconds_at(self, tick):
        return sum(mido.tick2second(min(stop, tick) - t.tick, self.ticks_per_beat, t.microseconds_per_beat)
                   for t, stop in zip(self.tempos, [x.tick for x in self.tempos[1:]] + [self.end_tick])
                   if t.tick < tick)


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def meta_events(score):
    return ([(t.tick, 0, mido.MetaMessage("set_tempo", tempo=t.microseconds_per_beat)) for t in score.tempos]
            + [(m.tick, 0, mido.MetaMessage("time_signature", numerator=m.numerator,
                                        denominator=m.denominator)) for m in score.meters])


def track(events, end_tick):
    result, last = mido.MidiTrack(), 0
    for tick, priority, message in sorted(events, key=lambda e: (e[0], e[1])):
        result.append(message.copy(time=tick - last))
        last = tick
    result.append(mido.MetaMessage("end_of_track", time=end_tick - last))
    return result


def note_events(notes, channel):
    return [(tick, priority, mido.Message(kind, channel=channel, note=n.pitch, velocity=velocity))
            for n in notes for tick, priority, kind, velocity in
            [(n.start, 2, "note_on", n.velocity), (n.end, 1, "note_off", 0)]]


def compile_score(score, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "parts").mkdir()
    ensemble = mido.MidiFile(type=1, ticks_per_beat=score.ticks_per_beat)
    ensemble.tracks.append(track(meta_events(score), score.end_tick))
    manifest = {"duration_s": score.duration_seconds(), "parts": {}}
    channels = [n for n in range(16) if n != 9]
    for channel, part in zip(channels, score.parts):
        preamble = [(0, 0, mido.MetaMessage("track_name", name=part.id)),
                    (0, 0, mido.Message("program_change", channel=channel, program=part.program))]
        ensemble.tracks.append(track(preamble + note_events(part.notes, channel), score.end_tick))
        files = {}
        for articulation in sorted({n.articulation for n in part.notes}):
            midi = mido.MidiFile(type=0, ticks_per_beat=score.ticks_per_beat)
            events = meta_events(score) + [(0, 0, mido.Message("program_change", program=part.program))]
            events += note_events([n for n in part.notes if n.articulation == articulation], 0)
            midi.tracks.append(track(events, score.end_tick))
            relative = f"parts/{part.id}.{articulation}.mid"
            midi.save(output / relative)
            files[articulation] = relative
        manifest["parts"][part.id] = {"role": part.role, "notes": len(part.notes), "midi": files}
    ensemble.save(output / "ensemble.mid")
    dump(output / "score.json", score.model_dump())
    dump(output / "manifest.json", manifest)
    return manifest


def inspect_midi(path):
    midi = mido.MidiFile(path)
    if midi.type == 2 or midi.ticks_per_beat <= 0:
        raise ValueError("Only synchronous type 0/1 MIDI with PPQ timing is supported")
    result = {"type": midi.type, "ticks_per_beat": midi.ticks_per_beat,
              "duration_s": midi.length, "tempos": [], "meters": [], "channels": {}, "warnings": []}
    active, channels, tick = defaultdict(deque), {}, 0
    for msg in mido.merge_tracks(midi.tracks):
        tick += msg.time
        if msg.type == "set_tempo":
            result["tempos"].append({"tick": tick, "microseconds_per_beat": msg.tempo})
        elif msg.type == "time_signature":
            result["meters"].append({"tick": tick, "numerator": msg.numerator, "denominator": msg.denominator})
        if not hasattr(msg, "channel"):
            continue
        channel = channels.setdefault(msg.channel, {"notes": [], "programs": [], "controllers": []})
        if msg.type == "program_change":
            channel["programs"].append({"tick": tick, "program": msg.program})
        elif msg.type == "control_change":
            channel["controllers"].append({"tick": tick, "control": msg.control, "value": msg.value})
        elif msg.type == "note_on" and msg.velocity:
            active[msg.channel, msg.note].append((tick, msg.velocity))
        elif msg.type in ("note_off", "note_on"):
            pending = active[msg.channel, msg.note]
            if pending:
                start, velocity = pending.popleft()
                channel["notes"].append({"start": start, "end": tick, "pitch": msg.note, "velocity": velocity})
            else:
                result["warnings"].append(f"Unmatched note-off at tick {tick}, channel {msg.channel}")
    result["end_tick"] = tick
    for (channel, pitch), pending in active.items():
        if pending:
            result["warnings"].append(f"Unclosed notes: channel {channel}, pitch {pitch}, count {len(pending)}")
    for channel, data in channels.items():
        data["notes"].sort(key=lambda n: (n["start"], n["pitch"]))
        result["channels"][str(channel)] = data
    return result
