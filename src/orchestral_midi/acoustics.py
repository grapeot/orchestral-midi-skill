"""Rectangular image paths, paired measured HRIRs, and a statistical diffuse tail."""

from dataclasses import dataclass
from itertools import product

import h5py
import numpy as np
from scipy.signal import butter, fftconvolve, lfilter
from scipy.spatial import cKDTree


@dataclass(frozen=True)
class ImagePath:
    distance: float
    direction: np.ndarray
    hits: tuple[int, ...]


def image_paths(size, source, listener, order, max_seconds=0.3, speed=343.0):
    size, source, listener = [np.asarray(x, dtype=float) for x in (size, source, listener)]
    if size.shape != (3,) or not np.isfinite(size).all() or np.any(size <= 0):
        raise ValueError("Room size must contain three finite positive dimensions")
    for point in (source, listener):
        if point.shape != (3,) or not np.isfinite(point).all() or np.any(point <= 0) or np.any(point >= size):
            raise ValueError("Source and listener must be strictly inside room")
    if np.linalg.norm(source - listener) < 0.2:
        raise ValueError("Source must be at least 0.2 m from listener")
    if not isinstance(order, int) or not 0 <= order <= 8 or speed <= 0 or max_seconds <= 0:
        raise ValueError("Invalid image-path limits")
    paths = []
    for grid in product(range(-order, order + 1), repeat=3):
        if sum(map(abs, grid)) > order:
            continue
        image, hits = [], []
        for m, length, value in zip(grid, size, source):
            image.append(m * length + (value if m % 2 == 0 else length - value))
            low = (abs(m) + int(m < 0)) // 2
            hits.extend((low, abs(m) - low))
        delta = np.asarray(image) - listener
        distance = float(np.linalg.norm(delta))
        if distance / speed <= max_seconds:
            paths.append(ImagePath(distance, delta / distance, tuple(hits)))
    return sorted(paths, key=lambda p: p.distance)


def head_direction(direction, yaw_degrees):
    """World +Y forward/+X right; SOFA +X forward/+Y left; positive yaw turns left."""
    x, y, z = direction
    yaw = np.deg2rad(yaw_degrees)
    return np.array([y * np.cos(yaw) - x * np.sin(yaw),
                     -x * np.cos(yaw) - y * np.sin(yaw), z])


def text(value):
    return value.decode() if isinstance(value, bytes) else str(value)


class Hrtf:
    def __init__(self, path, fs):
        with h5py.File(path, "r") as f:
            required = {"Data.SamplingRate", "Data.Delay", "Data.IR", "SourcePosition", "ReceiverPosition",
                        "ListenerPosition", "ListenerView", "ListenerUp"}
            if not required.issubset(f.keys()):
                raise ValueError("SOFA is missing required coordinate or impulse-response datasets")
            if text(f.attrs.get("SOFAConventions", "")) != "SimpleFreeFieldHRIR":
                raise ValueError("Requires SimpleFreeFieldHRIR SOFA")
            if not np.all(np.asarray(f["Data.SamplingRate"]) == fs):
                raise ValueError("SOFA sample rate differs from scene")
            if np.any(f["Data.Delay"][:] != 0):
                raise ValueError("Only SOFA Data.Delay=0 is supported")
            source = f["SourcePosition"]
            if text(source.attrs.get("Type", "")) != "spherical":
                raise ValueError("Requires spherical source positions")
            if text(source.attrs.get("Units", "")).replace(" ", "") not in (
                    "degree,degree,metre", "degree,degree,meter"):
                raise ValueError("SourcePosition units must be degree, degree, metre")
            for key in ("ReceiverPosition", "ListenerPosition", "ListenerView", "ListenerUp"):
                # ListenerUp is a dimensionless vector in ListenerView's
                # coordinate system; SADIE omits a separate Type attribute.
                default = "cartesian" if key == "ListenerUp" else ""
                if text(f[key].attrs.get("Type", default)) != "cartesian":
                    raise ValueError(f"Requires Cartesian {key}")
            for key in ("ReceiverPosition", "ListenerPosition"):
                if text(f[key].attrs.get("Units", "")) not in ("metre", "meter"):
                    raise ValueError(f"Requires {key} in metres")
            position = np.asarray(f["ListenerPosition"])
            if position.size != 3 or not np.allclose(position, 0):
                raise ValueError("Only a single listener at the SOFA origin is supported")
            for key, expected in (("ListenerView", [1, 0, 0]), ("ListenerUp", [0, 0, 1])):
                if key not in f or not np.allclose(np.asarray(f[key]).reshape(-1, 3), expected):
                    raise ValueError(f"Requires standard SOFA {key} orientation")
            receivers = np.asarray(f["ReceiverPosition"]).reshape(2, 3)
            if not np.isfinite(receivers).all() or not (receivers[0, 1] > 0 > receivers[1, 1]):
                raise ValueError("Unknown receiver order; requires left then right")
            positions = np.asarray(source)
            self.ir = np.asarray(f["Data.IR"], dtype=float)
        if (positions.ndim != 2 or positions.shape[1] != 3 or not np.isfinite(positions).all()
                or np.any(np.abs(positions[:, 1]) > 90) or np.any(positions[:, 2] <= 0)
                or self.ir.ndim != 3 or self.ir.shape[:2] != (len(positions), 2)
                or self.ir.shape[-1] < 1 or not np.isfinite(self.ir).all() or not np.any(self.ir)):
            raise ValueError("Invalid SOFA position/IR arrays")
        az, el = np.deg2rad(positions[:, :2]).T
        self.tree = cKDTree(np.column_stack((np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el))))
        self.fs = fs

    def lookup(self, direction):
        direction = np.asarray(direction, dtype=float)
        norm = np.linalg.norm(direction)
        if direction.shape != (3,) or not np.isfinite(direction).all() or norm == 0:
            raise ValueError("Direction must be a finite nonzero vector")
        _, index = self.tree.query(direction / norm)
        return self.ir[index]


def band_parts(wave, fs):
    low = lfilter(*butter(1, 500, fs=fs), wave, axis=-1)
    below_high = lfilter(*butter(1, 4000, fs=fs), wave, axis=-1)
    return np.stack((low, below_high - low, wave - below_high))


def add_fractional(buffer, wave, at):
    start = int(np.floor(at))
    fraction = at - start
    if start < 0 or start + wave.shape[-1] + 1 > buffer.shape[-1]:
        raise ValueError("Impulse-response buffer too small")
    buffer[..., start:start + wave.shape[-1]] += (1 - fraction) * wave
    buffer[..., start + 1:start + wave.shape[-1] + 1] += fraction * wave


def smoothstep(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


def build_brir(hrtf, scene, source, seed):
    room, listener, fs = scene["room"], scene["listener"], hrtf.fs
    speed = room["speed_m_s"]
    tail_seconds = 1.5 * max(room["rt60_bands_s"]) + 0.1
    travel = np.linalg.norm(room["size_m"]) / speed
    frames = int(fs * (tail_seconds + travel + room["late_start_s"] + .2)) + hrtf.ir.shape[-1] + 2
    direct, early = np.zeros((2, frames)), np.zeros((2, frames))
    distance = np.linalg.norm(np.asarray(source["position_m"]) - listener["position_m"])
    paths = image_paths(room["size_m"], source["position_m"], listener["position_m"],
                        room["reflection_order"], distance / speed + room["late_start_s"] + room["transition_s"], speed)
    first = paths[0]
    absorption = np.asarray(room["wall_absorption_bands"])
    log = []
    for path in paths:
        order = sum(path.hits)
        if room["reflection_plane"] == "horizontal" and sum(path.hits[4:]):
            continue
        relative = (path.distance - first.distance) / speed
        weight = 1. if order == 0 else 1 - smoothstep((relative - room["late_start_s"]) / room["transition_s"])
        if weight <= 0:
            continue
        direction = head_direction(path.direction, listener["yaw_deg"])
        pair = np.pad(hrtf.lookup(direction), ((0, 0), (0, int(.04 * fs))))
        gains = np.prod((1 - absorption) ** (np.asarray(path.hits)[:, None] / 2), axis=0)
        gains *= np.exp(-np.asarray(room["air_loss_per_m_bands"]) * path.distance)
        wave = np.sum(band_parts(pair, fs) * gains[:, None, None], axis=0) * weight / path.distance
        add_fractional(direct if order == 0 else early, wave, path.distance / speed * fs)
        log.append({"distance_m": path.distance, "delay_s": path.distance / speed,
                    "relative_delay_s": relative, "wall_hits": list(path.hits), "arrival_sofa": direction.tolist()})
    tail_frames = int(tail_seconds * fs)
    seconds = np.arange(tail_frames) / fs
    envelope = np.exp(-np.log(1000) * seconds[None, :] / np.asarray(room["rt60_bands_s"])[:, None])
    tail = np.zeros((2, tail_frames + hrtf.ir.shape[-1] - 1))
    rng = np.random.default_rng(seed)
    count = room["diffuse_directions"]
    for index in range(count):
        horizontal = room["reflection_plane"] == "horizontal"
        z = 0. if horizontal else 1 - 2 * (index + .5) / count
        angle = 2 * np.pi * (index + .5) / count if horizontal else index * np.pi * (3 - np.sqrt(5))
        direction = [np.sqrt(1 - z * z) * np.cos(angle), np.sqrt(1 - z * z) * np.sin(angle), z]
        wave = np.sum(band_parts(rng.standard_normal(tail_frames), fs) * envelope, axis=0)
        pair = hrtf.lookup(direction)
        for ear in range(2):
            tail[ear] += fftconvolve(wave, pair[ear]) / np.sqrt(count)
    t = np.arange(tail.shape[-1]) / fs
    tail *= (smoothstep(t / room["transition_s"]) *
             (1 - smoothstep((t - tail_seconds + .1) / .1)))[None, :]
    late = np.zeros_like(direct)
    add_fractional(late, tail, (first.distance / speed + room["late_start_s"]) * fs)
    target = np.sum(direct ** 2) * 10 ** (room["late_to_direct_db"] / 10)
    late *= np.sqrt(target / max(np.sum(late ** 2), 1e-30))
    return {"direct": direct, "early": direct + early, "hall": direct + early + late}, log


def convolve_pair(mono, pair):
    return np.column_stack([fftconvolve(mono, ear) for ear in pair])
