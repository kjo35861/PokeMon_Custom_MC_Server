"""Persistent session state across rounds, focus changes and F11 resizing."""
from vision import find_board, board_visible, TimingEngine
from grill import GrillSignature, GrillEngine
from feedback import VerdictCalibration


class GameSession:
    def __init__(self, size, board=None, target_ratio=.09, auto_tune=True):
        self.size = size
        self.board = board
        self.target_ratio = target_ratio
        self.engine = None
        self.kind = 'chop' if board is not None else None
        self.grill_signature = GrillSignature()
        self.calibration = VerdictCalibration(enabled=auto_tune)
        self.reset_tracking()

    @property
    def active(self):
        return self.engine is not None and self.engine.active

    @property
    def plans(self):
        return self.engine.plans if self.engine is not None else []

    @property
    def feedback_updates(self):
        return getattr(self.engine, 'feedback_updates', [])

    def reset_tracking(self):
        if self.board is None:
            self.engine = None
        elif self.kind == 'grill':
            self.engine = GrillEngine(self.calibration)
        else:
            _, _, w, h = self.board
            self.engine = TimingEngine(w, h, w*self.target_ratio)

    def update_size(self, size):
        if size == self.size:
            return False
        self.size = size
        # GUI scale is not necessarily proportional to resolution. Locate the
        # actual board again rather than scaling stale windowed coordinates.
        self.board = None
        self.engine = None
        self.kind = None
        return True

    def relocate(self, frame):
        if self.grill_signature.matches(frame):
            height, width = frame.shape[:2]
            rect = (0, 0, width, height)
            if self.kind != 'grill' or self.board != rect or self.engine is None:
                self.board, self.kind = rect, 'grill'
                self.reset_tracking()
            return True
        if self.active:
            return False
        rect = find_board(frame)
        if rect is None:
            return False
        x, y, w, h = rect
        if not board_visible(frame[y:y+h, x:x+w]):
            return False
        if self.kind != 'chop' or self.board != rect or self.engine is None:
            self.board, self.kind = rect, 'chop'
            self.reset_tracking()
        return True

    def process(self, board_pixels, timestamp, lead_seconds=0., input_time=None):
        if self.engine is None:
            return [], []
        if self.kind == 'chop':
            return self.engine.process(board_pixels, timestamp, lead_seconds, input_time=input_time)
        return self.engine.process(board_pixels, timestamp, lead_seconds)
