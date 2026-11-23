"""Recognize the four-tap chopping prompt. This module never sends keys."""
from pathlib import Path
import sys

import cv2
import numpy as np


class BurstReader:
    """Read the shared prompt, rather than treating its food strip as notes."""
    _templates = None

    def __init__(self):
        if self._templates is None:
            base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))/'assets'
            self.__class__._templates = {
                name: cv2.imdecode(np.frombuffer((base/f'burst_{name}.png').read_bytes(), np.uint8), 1)
                for name in ('prompt', 'zero', 'one', 'two', 'three', 'four', 'limit_four')}
        self.scaled = {}

    def read(self, board):
        h, w = board.shape[:2]
        scale = h/290
        # Scale templates to the native board, avoiding resampling small text up.
        roi = board[round(h*.04):round(h*.24), round(w*.10):round(w*.55)]
        mask = cv2.inRange(roi, (0, 0, 0), (95, 95, 95))
        if np.count_nonzero(mask) < max(20, 70*scale*scale):
            return None
        if h not in self.scaled:
            # Rasterization phase matters for small pixel-font strokes. Include
            # alternate pixel origins, rather than lowering recognition scores.
            phases = range(4 if scale < 1 else 2)
            self.scaled[h] = {name: [] for name in self._templates}
            seen = {name: set() for name in self._templates}
            for method in (cv2.INTER_NEAREST, cv2.INTER_AREA):
                for dy in phases:
                    for dx in phases:
                        for name, raw in self._templates.items():
                            padded = cv2.copyMakeBorder(raw, dy, len(phases)-1-dy, dx, len(phases)-1-dx,
                                                        cv2.BORDER_CONSTANT, value=(130, 160, 190))
                            resized = cv2.resize(padded, None, fx=scale, fy=scale, interpolation=method)
                            binary = cv2.inRange(resized, (0, 0, 0), (95, 95, 95))
                            bx, by, bw, bh = cv2.boundingRect(binary)
                            if bw == 0 or bh == 0:
                                continue
                            cropped = binary[by:by+bh, bx:bx+bw]
                            key = (cropped.shape, cropped.tobytes())
                            if key not in seen[name]:
                                seen[name].add(key)
                                self.scaled[h][name].append((cropped, bx-dx*scale, by-dy*scale))
        best = None
        for template, ox, oy in self.scaled[h]['prompt']:
            if mask.shape[0] < template.shape[0] or mask.shape[1] < template.shape[1]:
                continue
            _, score, _, (x, y) = cv2.minMaxLoc(cv2.matchTemplate(mask, template, cv2.TM_CCOEFF_NORMED))
            if best is None or score > best[0]:
                best = (score, round(x-ox), round(y-oy))
        if best is None or best[0] < .78:
            return None
        score, x, y = best
        # Confirm /4 as well: a different required count must not receive four taps.
        suffix = mask[max(0, y-round(2*scale)):y+round(26*scale),
                      x+round(73*scale):x+round(105*scale)]
        def best_score(region, name):
            return max((cv2.minMaxLoc(cv2.matchTemplate(region, t, cv2.TM_CCOEFF_NORMED))[1]
                        for t, _, _ in self.scaled[h][name] if region.shape[0] >= t.shape[0]
                        and region.shape[1] >= t.shape[1]), default=0.)
        limit_score = best_score(suffix, 'limit_four')
        if limit_score < .72:
            return None
        numerator = mask[max(0, y-round(2*scale)):y+round(26*scale),
                         x+round(62*scale):x+round(81*scale)]
        scores = {}
        for number, name in enumerate(('zero', 'one', 'two', 'three', 'four')):
            scores[number] = best_score(numerator, name)
        count = max(scores, key=scores.get)
        if scores[count] < .78:
            count = None  # Intermediate counts are not guessed from food sprites.
        return {'required': 4, 'count': count, 'score': float(score)}


class BurstController:
    """At most four distinct key presses per continuous prompt appearance."""
    def __init__(self, reader=None):
        self.reader = reader or BurstReader()
        self.episode = 0
        self.start = None
        self.last_seen = -100.
        self.finished = False
        self.count = 0
        self.initial_count = 0
        self.visible = False
        self.plans = []

    def update(self, board, now, input_time=None):
        dispatch_time = max(now, input_time if input_time is not None else now)
        cue = self.reader.read(board)
        self.visible = cue is not None
        self.plans = []
        if cue is None:
            if now-self.last_seen > .20:
                self.start = None
            return
        if self.start is None:
            self.episode += 1
            self.start = dispatch_time+.025
            self.finished = False
            self.count = 0
            self.initial_count = cue['count'] or 0
        self.last_seen = now
        if cue['count'] is not None:
            self.count = max(self.count, cue['count'])
        if cue['count'] == cue['required']:
            self.finished = True
        if self.finished:
            return
        for index in range(cue['required']):
            if index < self.count:
                continue
            due = self.start+(index-self.initial_count)*.080
            if due < now-.060:
                continue
            self.plans.append({'id': ('burst', self.episode, index), 'kind': 'burst',
                               'deadline': due, 'observed': now, 'valid_until': dispatch_time+.100,
                               'step': index+1, 'required': cue['required']})
