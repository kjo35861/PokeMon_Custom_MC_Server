"""Offline-testable vision and timing; this module never sends keyboard input."""
from dataclasses import dataclass, field
from collections import deque
import cv2
import numpy as np
from motion import fit_motion, add_sample
from burst import BurstController


def wood_mask(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (10, 24, 120), (40, 175, 255))


def find_board(bgr):
    """Return the largest wide, mostly uninterrupted wooden board."""
    mask = wood_mask(bgr)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 13), np.uint8))
    candidates = []
    for contour in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        x, y, w, h = cv2.boundingRect(contour)
        if w >= bgr.shape[1] * .3 and h >= bgr.shape[0] * .08 and 2.5 < w / h < 7:
            coverage = np.count_nonzero(wood_mask(bgr[y:y+h, x:x+w])) / (w * h)
            if coverage > .68:
                candidates.append((w*h, (x, y, w, h)))
    return max(candidates, default=(0, None))[1]


def board_visible(bgr):
    # Menus and result overlays dim the wood; an unrelated Minecraft screen
    # must not enable keyboard input simply because the window title matches.
    h, w = bgr.shape[:2]
    if h < 30 or w < 100:
        return False
    mask = wood_mask(bgr)
    bottom = mask[int(h*.68):int(h*.94), int(w*.04):int(w*.95)]
    top = mask[:max(1, int(h*.16))]
    return (np.count_nonzero(mask) / mask.size > .72
            and np.count_nonzero(top) / top.size > .72
            and np.count_nonzero(bottom) / bottom.size > .76)


@dataclass
class Candy:
    x: float
    y: float
    size: float
    source: str = 'motion'


def find_action_markers(bgr):
    """The common red slash prompt, independent of the ingredient's sprite."""
    h, w = bgr.shape[:2]
    y0, y1 = int(h*.43), int(h*.65)
    hsv = cv2.cvtColor(bgr[y0:y1], cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, 70, 110), (11, 255, 255))
    mask |= cv2.inRange(hsv, (170, 70, 110), (179, 255, 255))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((2, 3), np.uint8))
    result = []
    for contour in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
        x, y, cw, ch = cv2.boundingRect(contour)
        if not (.07*h < cw < .50*h and 1.6 < cw/max(ch, 1) < 9):
            continue
        if cv2.contourArea(contour) < max(8, cw*ch*.22):
            continue
        result.append(Candy(x+cw/2, h*.35, cw, 'marker'))
    return sorted(result, key=lambda c: c.x)


class UniversalDetector:
    """Combine a shared action prompt with color-agnostic foreground motion.

    Moving beat lines are too narrow to count as ingredients. A short warmup
    applies only to the motion fallback; action prompts work immediately.
    """
    def __init__(self):
        self.background = cv2.createBackgroundSubtractorMOG2(
            history=150, varThreshold=24, detectShadows=False)
        self.background.setBackgroundRatio(.8)
        self.started = None
        self.last_time = None

    def detect(self, bgr, now):
        h, w = bgr.shape[:2]
        y0, y1 = int(h*.08), int(h*.47)
        lane = bgr[y0:y1]
        if self.started is None:
            self.started = now
        dt = 1/60 if self.last_time is None else max(.001, now-self.last_time)
        self.last_time = now
        mask = self.background.apply(lane, learningRate=min(.05, dt/1.2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        found = find_action_markers(bgr)
        if now-self.started > .55:
            for contour in cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
                x, y, cw, ch = cv2.boundingRect(contour)
                if not (.04*h < cw < .55*h and .055*h < ch < .46*h):
                    continue
                if not (.28 < cw/max(ch, 1) < 3.0):
                    continue
                if cv2.contourArea(contour) < max(25, cw*ch*.22):
                    continue
                center = x+cw/2
                # Prefer the stable common marker if both detectors find a note.
                if any(abs(center-c.x) < max(cw, c.size)*.8 for c in found):
                    continue
                found.append(Candy(center, h*.35, cw))
        return sorted(found, key=lambda c: c.x)


@dataclass
class Track:
    ident: int
    x: float
    y: float
    last_seen: float
    armed: bool
    fired: bool = False
    samples: deque = field(default_factory=lambda: deque(maxlen=48))
    source: str = 'motion'
    model: object = None

    @property
    def velocity(self):
        return self.model.velocity if self.model is not None else 0.


class NoteTracker:
    def __init__(self, width, height, target_x):
        self.width, self.height, self.target_x = width, height, target_x
        self.tracks = []
        self.next_id = 1
        self.last_trigger = -100.
        self.plans = []

    def reset(self):
        self.tracks.clear()
        self.last_trigger = -100.
        self.plans = []

    def update(self, candies, now, lead_seconds=0.):
        self.tracks = [t for t in self.tracks if now-t.last_seen < .24]
        self.plans = []
        unmatched = list(self.tracks)
        observed = []
        for candy in candies:
            options = []
            for t in unmatched:
                predicted = t.x + t.velocity * (now-t.last_seen)
                dx, dy = abs(candy.x-predicted), abs(candy.y-t.y)
                if dx < max(self.width*.035, candy.size*.9) and dy < self.height*.22:
                    options.append((dx + dy*.6, t))
            if options:
                t = min(options, key=lambda option: option[0])[1]
                unmatched.remove(t)
            else:
                t = Track(self.next_id, candy.x, candy.y, now,
                          candy.x > self.target_x+self.width*.02)
                self.next_id += 1
                self.tracks.append(t)
                t.source = candy.source
            if candy.source != t.source:
                if t.source == 'marker' and candy.source == 'motion' and now-t.last_seen < .08:
                    # Avoid a jump from the common prompt's center to food art.
                    observed.append(t)
                    continue
                t.samples.clear()
                t.source = candy.source
            t.x, t.y, t.last_seen = candy.x, candy.y, now
            add_sample(t.samples, now, candy.x)
            t.model = fit_motion(t.samples)
            observed.append(t)

        triggers = []
        for t in self.tracks:
            speed = t.velocity
            if t.fired or not t.armed or speed >= -self.width*.045:
                continue
            if now-t.last_seen > .12 or t.model is None:
                continue
            due = t.model.crossing(self.target_x)
            eta = due-now
            if -.05 <= eta <= .18 and t.model.rms < max(4., self.width*.009):
                self.plans.append({'id': t.ident, 'deadline': due, 'time': now,
                                   'observed': t.samples[-1][0], 'velocity': speed,
                                   'eta_ms': eta*1000, 'rms': t.model.rms})
            if -.09 <= eta <= lead_seconds and now-self.last_trigger >= .012:
                t.fired = True
                self.last_trigger = now
                triggers.append({'id': t.ident, 'time': now, 'x': t.x,
                                 'velocity': speed, 'eta_ms': eta*1000})
        return triggers


class TimingEngine:
    def __init__(self, width, height, target_x):
        self.tracker = NoteTracker(width, height, target_x)
        self.detector = UniversalDetector()
        self.active = False
        self.burst = BurstController()
        self.cancelled_ids = set()
        self._plans = []

    @property
    def plans(self):
        return self._plans

    def process(self, board, timestamp, lead_seconds=0., input_time=None):
        self.active = board_visible(board)
        self.cancelled_ids = set()
        self._plans = []
        if not self.active:
            self.tracker.reset()
            self.detector = UniversalDetector()
            self.burst = BurstController()
            return [], []
        self.burst.update(board, timestamp, input_time=input_time)
        candies = self.detector.detect(board, timestamp)
        events = self.tracker.update(candies, timestamp, lead_seconds)
        if self.burst.visible:
            # The strip is one mash window, not many ordinary food notes. It
            # can leave small moving fragments that would otherwise press Space
            # again. Keep future normal notes queued for after this window.
            self.cancelled_ids = {t.ident for t in self.tracker.tracks
                                  if t.model is not None and t.velocity < 0
                                  and t.model.crossing(self.tracker.target_x) <= timestamp+.045}
        self._plans = [p for p in self.tracker.plans if p['id'] not in self.cancelled_ids]
        self._plans.extend(self.burst.plans)
        return [e for e in events if e['id'] not in self.cancelled_ids], candies
