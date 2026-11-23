"""Oven minigame: identify its HUD, then time the shrinking cyan/gold cues.

No food sprite is used. The shared controls and colored target frames are
independent of the recipe. Alignment compensation is calibrated from footage.
"""
from collections import deque
from pathlib import Path
import sys

import cv2
import numpy as np
from motion import fit_motion, add_sample


def normalized(frame):
    height, width = frame.shape[:2]
    return cv2.resize(frame, (round(width*540/height), 540))


class GrillSignature:
    _templates = None

    def __init__(self):
        self.preferred_template = None
        if GrillSignature._templates is None:
            base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
            raw = cv2.imdecode(np.frombuffer((base/'assets'/'grill_controls.png').read_bytes(), np.uint8),
                               cv2.IMREAD_GRAYSCALE)
            if raw is None:
                raise RuntimeError('굽기 감지 자료를 읽을 수 없습니다.')
            GrillSignature._templates = [cv2.resize(raw, None, fx=s, fy=s,
                                                  interpolation=cv2.INTER_NEAREST)
                                         for s in (1/3, .5, 2/3, .75, 1., 1.25, 4/3, 1.5, 5/3, 2.)]

    def score(self, frame, already_normalized=False):
        # Keep native pixel sizes: removing the Windows title bar must not
        # rescale glyphs and defeat matching a wide line of controls.
        image = frame
        hsv = cv2.cvtColor(image[int(image.shape[0]*.72):, :round(image.shape[1]*.68)], cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (0, 0, 160), (179, 65, 255))
        score = 0.
        order = list(range(len(self._templates)))
        if self.preferred_template is not None:
            order.remove(self.preferred_template)
            order.insert(0, self.preferred_template)
        for index in order:
            template = self._templates[index]
            h, w = template.shape
            if h > mask.shape[0] or w > mask.shape[1]:
                continue
            current = float(cv2.minMaxLoc(cv2.matchTemplate(mask, template, cv2.TM_CCOEFF_NORMED))[1])
            score = max(score, current)
            if current >= .60:
                self.preferred_template = index
                return current
        return score

    def matches(self, frame, already_normalized=False):
        return self.score(frame, already_normalized) >= .60


def find_cues(frame):
    """Read outer moving ring + nested fixed target, in normalized pixels."""
    h, w = frame.shape[:2]
    x0, y0 = round(w*.22), round(h*.12)
    roi = frame[y0:round(h*.87), x0:round(w*.78)]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    results = []
    for kind, lo, hi in [('insert', (80, 70, 150), (100, 255, 255)),
                         ('remove', (22, 80, 190), (38, 255, 255))]:
        mask = cv2.inRange(hsv, lo, hi)
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:
            continue
        boxes = [cv2.boundingRect(contour) for contour in contours]
        candidates = []
        for index, (x, y, cw, ch) in enumerate(boxes):
            cx, cy = x+x0+cw/2, y+y0+ch/2
            if hierarchy[0, index, 3] != -1:
                continue
            if not (w*.15 < cw < w*.6 and h*.11 < ch < h*.5 and 1.5 < cw/ch < 3.5):
                continue
            if abs(cx-w*.5) > w*.075:
                continue
            if not ((h*.48 < cy < h*.82) if kind == 'insert' else (h*.2 < cy < h*.53)):
                continue
            # Level 0: moving ring. Level 1: its hole. Level 2: fixed target.
            # Ignore narrow ring-hole contours and food/flame components.
            hole = hierarchy[0, index, 2]
            anchor = None
            while hole != -1:
                child = hierarchy[0, hole, 2]
                while child != -1:
                    ax, ay, aw, ah = boxes[child]
                    if (w*.12 < aw < cw*.94 and ah > h*.025
                            and abs(ax+aw/2-(x+cw/2)) < cw*.12):
                        if anchor is None or aw > anchor:
                            anchor = aw
                    child = hierarchy[0, child, 0]
                hole = hierarchy[0, hole, 0]
            candidates.append({'kind': kind, 'width': float(cw), 'anchor': anchor,
                               'box': (x+x0, y+y0, cw, ch)})
        if candidates:
            results.append(max(candidates, key=lambda cue: cue['width']))
    return results


class GrillEngine:
    def __init__(self, calibration=None):
        from feedback import VerdictReader, VerdictCalibration
        self.signature = GrillSignature()
        self.reader = VerdictReader()
        self.calibration = calibration or VerdictCalibration()
        self.active = False
        self.last_signature = self.last_feedback = -100.
        self.cues = {}
        self.next_id = 1
        self.plans = []
        self.feedback_updates = []
        self.sent_inputs = deque(maxlen=12)
        self.period_estimates = deque(maxlen=100)

    def record_input(self, plan, actual):
        phase = 'insert' if plan.get('action') == '넣기' else 'remove'
        eligible = abs(actual-plan.get('deadline', actual)) <= .015
        self.sent_inputs.append({'phase': phase, 'actual': actual, 'id': plan['id'],
                                 'graded': False, 'eligible': eligible})

    def _feedback(self, frame, timestamp):
        if timestamp-self.last_feedback < .035:
            return
        self.last_feedback = timestamp
        verdict = self.reader.read(frame, timestamp)
        if verdict is None:
            return
        matched = next((item for item in reversed(self.sent_inputs)
                        if not item['graded'] and .003 <= timestamp-item['actual'] <= .65), None)
        phase, updated = None, False
        if matched is not None and verdict['score'] >= .90:
            matched['graded'] = True
            phase = matched['phase']
            if matched['eligible']:
                updated = self.calibration.update(phase, verdict['verdict'], matched['actual'])
        self.feedback_updates.append(dict(verdict, phase=phase, updated=updated,
                                         delay_ms=self.calibration.delay.get(phase, 0.)*1000))

    def process(self, frame, timestamp, lead_seconds=0.):
        self.plans = []
        self.feedback_updates = []
        image = normalized(frame)
        if timestamp-self.last_signature >= .2:
            self.active = self.signature.matches(frame)
            self.last_signature = timestamp
        if not self.active:
            self.cues.clear()
            self.period_estimates.clear()
            return [], []
        self._feedback(frame, timestamp)
        candidates = find_cues(image)
        events, seen = [], set()
        for cue in candidates:
            kind = cue['kind']
            seen.add(kind)
            state = self.cues.get(kind)
            alive = state is not None and state['due'] is not None and timestamp <= state['due']+.26
            if state is None or (timestamp-state['seen'] > .65 and not alive):
                state = {'id': self.next_id, 'seen': timestamp, 'samples': deque(maxlen=80),
                         'anchors': deque(maxlen=40), 'estimates': deque(maxlen=60),
                         'fired': False, 'base_due': None, 'due': None, 'committed': False,
                         'last_width': None, 'velocity': 0., 'rms': 0., 'reliable': False}
                self.next_id += 1
                self.cues[kind] = state
            state['seen'] = timestamp
            if cue['anchor'] is not None:
                state['anchors'].append(cue['anchor'])
            # Frozen animation must not become a new zero-speed observation.
            changed = cue['width'] != state['last_width']
            state['last_width'] = cue['width']
            if state['fired'] or not changed or len(state['anchors']) < 2:
                continue
            anchor = float(np.median(state['anchors']))
            ratio = cue['width']/anchor
            state['samples'].append((timestamp, ratio))
            model = fit_motion(state['samples'], window=.65, noise_floor=.002)
            if model is None or model.span < .10 or model.velocity >= -.12:
                continue
            # Arrival means outer cue and fixed target have equal scale.
            # v5's 1.08 multiplier plus fixed 60ms delay depended on tempo.
            predicted = model.crossing(1.)
            uncertainty = model.rms/abs(model.velocity)
            # Both cue types span the same musical interval but have different
            # perspective scales. Learn that interval from clean motion, then
            # use it as a shared rate prior through frame stalls and jumps.
            scale_span = .764 if kind == 'insert' else .93
            period = -scale_span/model.velocity
            if model.span >= .35 and uncertainty < .025 and .55 < period < 3.5:
                self.period_estimates.append(period)
            if len(self.period_estimates) >= 5:
                shared_period = float(np.median(self.period_estimates))
                predicted = timestamp+(ratio-1.)/scale_span*shared_period
                state['reliable'] = True
            if uncertainty > .032 or not -.12 < predicted-timestamp < 1.25:
                continue
            state['velocity'], state['rms'] = model.velocity, model.rms
            state['estimates'].append(predicted)
            median = float(np.median(state['estimates']))
            stable = len(state['estimates']) >= 4 and float(np.std(list(state['estimates'])[-6:])) < .025
            if state['base_due'] is None:
                state['base_due'] = median
            elif not state['committed']:
                state['base_due'] = median
            elif (state['base_due']-timestamp > .10 and abs(median-state['base_due']) < .035):
                candidate = state['base_due']*.85+median*.15
                state['base_due'] = float(np.clip(candidate, state['lock_due']-.025, state['lock_due']+.025))
            if stable and not state['committed'] and median-timestamp <= .30:
                state['committed'] = True
                state['lock_due'] = state['base_due']
            state['due'] = state['base_due']+self.calibration.delay[kind]

        for kind, state in list(self.cues.items()):
            due = state['due']
            if due is not None and timestamp <= due+.26:
                coast = .65 if state['committed'] or state['reliable'] else .20
                self.plans.append({'id': state['id'], 'deadline': due, 'base_deadline': state['base_due'],
                                   'time': timestamp, 'observed': state['seen'], 'validated': timestamp,
                                   'valid_until': due+.26, 'kind': 'grill', 'max_silence': coast,
                                   'committed': state['committed'], 'coasting': kind not in seen,
                                   'velocity': state['velocity'], 'rms': state['rms'],
                                   'action': '넣기' if kind == 'insert' else '꺼내기',
                                   'eta_ms': (due-timestamp)*1000})
                if not state['fired'] and timestamp+lead_seconds >= due:
                    state['fired'] = True
                    events.append(dict(self.plans[-1], time=timestamp))
            expiry = max(state['seen']+.65, due+.26 if due is not None else -100.)
            if timestamp > expiry:
                del self.cues[kind]
        return events, candidates
