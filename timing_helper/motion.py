"""Robust motion fitting over a time window, independent of capture FPS."""
from dataclasses import dataclass
import numpy as np


@dataclass
class Motion:
    time: float
    position: float
    velocity: float
    rms: float
    span: float

    def crossing(self, target):
        return self.time+(target-self.position)/self.velocity


def fit_motion(samples, window=.22, noise_floor=.65):
    if len(samples) < 3:
        return None
    data = np.asarray(samples, dtype=float)
    data = data[data[:, 0] >= data[-1, 0]-window]
    if len(data) < 3 or data[-1, 0]-data[0, 0] < .014:
        return None
    origin = data[-1, 0]
    times = data[:, 0]-origin
    positions = data[:, 1]
    weights = np.ones(len(data))
    for _ in range(3):
        total = weights.sum()
        tm, pm = weights @ times/total, weights @ positions/total
        centered = times-tm
        denom = weights @ (centered*centered)
        if denom < 1e-9:
            return None
        velocity = float((weights*centered) @ (positions-pm)/denom)
        position = float(pm-velocity*tm)
        residual = positions-(position+velocity*times)
        scale = max(noise_floor, float(np.median(np.abs(residual-np.median(residual))))*1.4826)
        weights = np.minimum(1., 1.8*scale/np.maximum(np.abs(residual), 1e-6))
    rms = float(np.sqrt(weights @ (residual*residual)/weights.sum()))
    return Motion(float(origin), position, velocity, rms, float(data[-1, 0]-data[0, 0]))


def add_sample(samples, timestamp, position):
    if samples:
        old_time, old_position = samples[-1]
        if timestamp <= old_time:
            return
        # A repeated desktop/cursor frame is not a fresh motion observation.
        if position == old_position and timestamp-old_time < .04:
            return
    samples.append((timestamp, position))
