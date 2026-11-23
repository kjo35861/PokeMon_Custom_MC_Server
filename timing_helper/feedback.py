"""Read the game's displayed judgement, independently from input timer error."""
from pathlib import Path
import sys
import cv2
import numpy as np


class VerdictReader:
    _templates = None

    def __init__(self):
        if self._templates is None:
            base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))/'assets'
            self.__class__._templates = {}
            for name in ('perfect', 'early', 'late', 'miss'):
                raw = cv2.imdecode(np.frombuffer((base/f'grill_{name}.png').read_bytes(), np.uint8), 0)
                self._templates[name] = [cv2.resize(raw, None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
                                         for s in (1., 2/3, 4/3, .75, 1.5)]
        self.preferred = {name: 0 for name in self._templates}
        self.last_visible = -100.
        self.last_emitted = None

    def read(self, frame, now):
        h, w = frame.shape[:2]
        roi = frame[round(h*.12):round(h*.34), round(w*.40):round(w*.60)]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        white = cv2.inRange(hsv, (0, 0, 150), (179, 15, 255))
        green = cv2.inRange(hsv, (40, 55, 80), (90, 255, 255))
        red = cv2.inRange(hsv, (0, 65, 100), (12, 255, 255))|cv2.inRange(hsv, (165, 65, 100), (179, 255, 255))
        masks = {'perfect': green, 'early': white, 'late': white, 'miss': red}
        best = (0., None)
        for name, templates in self._templates.items():
            mask = masks[name]
            if np.count_nonzero(mask) < 40:
                continue
            order = [self.preferred[name]]+[i for i in range(len(templates)) if i != self.preferred[name]]
            for index in order:
                template = templates[index]
                if template.shape[0] > mask.shape[0] or template.shape[1] > mask.shape[1]:
                    continue
                score = float(cv2.minMaxLoc(cv2.matchTemplate(mask, template, cv2.TM_CCOEFF_NORMED))[1])
                if score > best[0]:
                    best = (score, name)
                if score > .82:
                    self.preferred[name] = index
                    break
        if best[0] < .72:
            if now-self.last_visible > .18:
                self.last_emitted = None
            return None
        self.last_visible = now
        if self.last_emitted == best[1]:
            return None
        self.last_emitted = best[1]
        return {'verdict': best[1], 'score': best[0], 'time': now}


class VerdictCalibration:
    """Bounded per-action feedback tuning; only actual sent inputs can teach it."""
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.delay = {'insert': 0., 'remove': 0.}
        self.step = {'insert': .012, 'remove': .012}
        self.direction = {'insert': 0, 'remove': 0}
        self.learned = set()

    def update(self, phase, verdict, identity):
        if not self.enabled or identity in self.learned or verdict not in ('perfect', 'early', 'late'):
            return False
        self.learned.add(identity)
        direction = 1 if verdict == 'early' else -1 if verdict == 'late' else 0
        if direction:
            if self.direction[phase] and direction != self.direction[phase]:
                self.step[phase] = max(.003, self.step[phase]*.5)
            self.delay[phase] = float(np.clip(self.delay[phase]+direction*self.step[phase], -.08, .08))
            self.direction[phase] = direction
        else:
            self.step[phase] = min(self.step[phase], .006)
        return True
