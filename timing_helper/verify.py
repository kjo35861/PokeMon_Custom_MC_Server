"""Replay supplied footage and synthetic ingredients. Never inject real keys."""
import argparse
import ctypes
import json
import unittest
import queue
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

import cv2
import numpy as np

from vision import TimingEngine, NoteTracker, Candy, find_board
import win_input as win
from screen_capture import ScreenCapture, relative_region
from session import GameSession
from grill import GrillEngine, GrillSignature


class DetectorTests(unittest.TestCase):
    @staticmethod
    def simulate(color, shape, marker, scale=1., speed=400., fps=60):
        w, h = round(1000*scale), round(240*scale)
        target = w*.09
        engine = TimingEngine(w, h, target)
        # Fixed textured wood, moving beat lines, and arbitrary ingredient art.
        rng = np.random.default_rng(4)
        base = np.empty((h, w, 3), np.uint8)
        base[:] = (105, 155, 185)
        noise = rng.integers(-5, 6, (h, w, 1), dtype=np.int16)
        base = np.clip(base.astype(np.int16)+noise, 0, 255).astype(np.uint8)
        hits = []
        velocity = speed*scale
        end = 1+w/velocity+.5
        for i in range(round(end*fps)):
            now = i/fps
            frame = base.copy()
            for k in range(5):
                gx = round((k*w/4-velocity*now) % w)
                cv2.line(frame, (gx, int(h*.07)), (gx, int(h*.92)), (65, 100, 125), max(1, round(scale)))
            if now >= 1:
                cx = round(w*.88-velocity*(now-1))
                cy = round(h*.32)
                r = round(h*.1)
                if shape == 'circle':
                    cv2.circle(frame, (cx, cy), r, color, -1)
                elif shape == 'triangle':
                    poly = np.array([(cx-r, cy+r), (cx+r, cy+r), (cx, cy-r)])
                    cv2.fillPoly(frame, [poly], color)
                else:
                    cv2.rectangle(frame, (cx-r, cy-r), (cx+r, cy+r), color, -1)
                if marker:
                    cv2.line(frame, (cx-r, round(h*.54)), (cx+r, round(h*.49)),
                             (105, 115, 238), max(2, round(h*.022)))
            events, _ = engine.process(frame, now, .5/fps)
            hits.extend(events)
        return hits, 1+(w*.88-target)/velocity

    def test_any_color_with_and_without_shared_marker(self):
        colors = [(230, 80, 20), (15, 25, 220), (20, 220, 40),
                  (235, 235, 235), (15, 15, 15), (40, 220, 230),
                  (80, 110, 145), (160, 160, 160)]
        for marker in (True, False):
            for i, color in enumerate(colors):
                with self.subTest(color=color, marker=marker):
                    hits, crossing = self.simulate(color, ('circle', 'triangle', 'square')[i % 3], marker)
                    self.assertEqual(len(hits), 1, hits)
                    self.assertLess(abs(hits[0]['time']-crossing), .045)

    def test_different_scale_and_speed(self):
        for scale, speed, fps in [(.65, 220, 30), (1.4, 700, 60)]:
            with self.subTest(scale=scale, speed=speed):
                hits, crossing = self.simulate((40, 210, 210), 'triangle', False, scale, speed, fps)
                self.assertEqual(len(hits), 1, hits)
                self.assertLess(abs(hits[0]['time']-crossing), .06)

    def test_stationary_object_and_reverse_motion_do_not_fire(self):
        for reverse in (False, True):
            tracker = NoteTracker(1000, 240, 90)
            hits = []
            for i in range(120):
                x = 100+i*2 if reverse else 100
                hits.extend(tracker.update([Candy(x, 80, 40)], i/60, 1/120))
            self.assertEqual(hits, [])

    def test_offscreen_or_dimmed_board_does_not_fire(self):
        engine = TimingEngine(1000, 240, 90)
        for value in (0, 50, 255):
            frame = np.full((240, 1000, 3), value, np.uint8)
            hits, notes = engine.process(frame, value)
            self.assertFalse(engine.active)
            self.assertEqual(hits+notes, [])


class InputTests(unittest.TestCase):
    def test_correct_windows_input_structure_size(self):
        self.assertEqual(ctypes.sizeof(win.INPUT), 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)

    def test_no_input_without_game_focus_or_while_space_held(self):
        with patch.object(win.user32, 'SendInput') as send:
            with patch.object(win, 'foreground_is', return_value=False):
                self.assertFalse(win.tap_space(123))
            with patch.object(win, 'foreground_is', return_value=True), patch.object(win, 'key_down', return_value=True):
                self.assertFalse(win.tap_space(123))
            send.assert_not_called()

    def test_mock_input_always_releases_key(self):
        flags = []
        def send(n, pointer, size):
            flags.append(ctypes.cast(pointer, ctypes.POINTER(win.INPUT)).contents.ki.dwFlags)
            return 1
        with patch.object(win.user32, 'SendInput', side_effect=send), \
             patch.object(win, 'foreground_is', return_value=True), \
             patch.object(win, 'key_down', return_value=False), \
             patch.object(win.time, 'sleep', side_effect=RuntimeError('interrupted')):
            with self.assertRaises(RuntimeError):
                win.tap_space(123)
        self.assertEqual(flags, [0x0008, 0x0008 | 0x0002])

    def test_recreated_window_must_belong_to_same_game(self):
        with patch.object(win.user32, 'GetForegroundWindow', return_value=321), \
             patch.object(win, 'foreground_is', return_value=True), \
             patch.object(win, 'process_id', return_value=99):
            self.assertEqual(win.focused_game(123, 99), 321)
            self.assertIsNone(win.focused_game(123, 100))


class SessionTests(unittest.TestCase):
    def test_fullscreen_region_handles_secondary_monitor_origins(self):
        self.assertEqual(relative_region((-1920, 0, 1920, 1080), (-1920, 0, 0, 1080)), (0, 0, 1920, 1080))
        self.assertEqual(relative_region((100, 200, 1200, 280), (0, 0, 2560, 1440)), (100, 200, 1300, 480))
        self.assertIsNone(relative_region((-50, 0, 1920, 1080), (0, 0, 1920, 1080)))

    def test_dxgi_capture_uses_output_relative_coordinates(self):
        screen = ScreenCapture()
        pixels = np.full((280, 1200, 3), 150, np.uint8)
        camera = SimpleNamespace(grab=lambda **kw: pixels, release=lambda: None)
        screen.camera = camera
        screen.output_rect = (-1920, 0, 0, 1080)
        self.assertIs(screen.grab((-1820, 200, 1200, 280)), pixels)
        self.assertIn('DXGI', screen.name)

    def test_dxgi_failure_falls_back_without_ending_session(self):
        screen = ScreenCapture()
        def fail(**kw):
            raise OSError('DXGI display mode changed')
        camera = SimpleNamespace(grab=fail, release=lambda: None)
        screen.camera = camera
        screen.output_rect = (0, 0, 1920, 1080)
        screen.gdi = SimpleNamespace(grab=lambda rect: np.full((280, 1200, 4), 160, np.uint8))
        result = screen.grab((100, 200, 1200, 280))
        self.assertEqual(result.shape, (280, 1200, 3))
        self.assertIn('GDI', screen.name)
        self.assertIsNone(screen.camera)

    def test_immediate_board_crop_reuses_fresh_dxgi_full_frame(self):
        screen = ScreenCapture()
        full = np.full((1080, 1920, 3), 150, np.uint8)
        camera = SimpleNamespace(release=lambda: None)
        frames = iter([full, None])
        camera.grab = lambda **kw: next(frames)
        screen.camera = camera
        screen.output_rect = (0, 0, 1920, 1080)
        screen.gdi = SimpleNamespace(grab=lambda _: (_ for _ in ()).throw(AssertionError('GDI must not be used')))
        screen.grab((0, 0, 1920, 1080))
        board = screen.grab((100, 200, 1200, 280))
        self.assertEqual(board.shape, (280, 1200, 3))
        self.assertTrue((board == 150).all())

    def test_resize_relocates_instead_of_scaling_old_coordinates(self):
        session = GameSession((1920, 1080), (100, 200, 1200, 280), .12)
        self.assertTrue(session.update_size((2560, 1440)))
        self.assertIsNone(session.board)
        frame = np.zeros((1440, 2560, 3), np.uint8)
        frame[500:800, 600:1900] = (105, 155, 185)
        self.assertTrue(session.relocate(frame))
        self.assertEqual(session.board, (600, 500, 1300, 300))
        self.assertAlmostEqual(session.engine.tracker.target_x, 1300*.12)

    def test_worker_survives_escape_resize_and_capture_interruption(self):
        from app import App
        checks, resets, grabs = [0], [0], [0]
        stop = SimpleNamespace(stopped=False)
        stop.is_set = lambda: stop.stopped
        stop.set = lambda: setattr(stop, 'stopped', True)
        stop.wait = lambda _: None
        def keys(vk):
            if vk == 0x78:
                checks[0] += 1
                return checks[0] >= 20
            return vk == 0x1B  # Esc held through every frame: must NOT stop.
        def geometry(_):
            return (0, 0, 1920, 1080) if checks[0] <= 10 else (0, 0, 2560, 1440)
        def grab(rect):
            grabs[0] += 1
            if grabs[0] == 3:
                raise OSError('temporary display transition')
            x, y, w, h = rect
            if w > 1500:
                pixels = np.zeros((h, w, 3), np.uint8)
                pixels[300:580, 200:1400] = (105, 155, 185)
                return pixels
            return np.full((h, w, 3), (105, 155, 185), np.uint8)
        class FakeCapture:
            name = 'mock DXGI'
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def reset(self): resets[0] += 1
            def grab(self, rect): return grab(rect)
        app = SimpleNamespace(events=queue.Queue())
        with patch('app.ScreenCapture', FakeCapture), \
             patch.object(win, 'key_down', side_effect=keys), \
             patch.object(win, 'process_id', return_value=99), \
             patch.object(win, 'focused_game', return_value=123), \
             patch.object(win, 'client_rect', side_effect=geometry):
            App.run_loop(app, 123, (1920, 1080), (200, 300, 1200, 280), .09, True, 0, stop)
        messages = list(app.events.queue)
        self.assertEqual(checks[0], 20, messages)
        self.assertTrue(any(kind == 'hit' and '2560×1440' in message for kind, message in messages))
        self.assertFalse(any(kind == 'error' for kind, _ in messages), messages)
        self.assertGreaterEqual(resets[0], 2)


class GrillTests(unittest.TestCase):
    def test_shrinking_cue_fires_once_for_different_food_colors(self):
        for color in [(10, 30, 210), (230, 230, 230), (25, 180, 40)]:
            engine = GrillEngine()
            hits = []
            for i in range(100):
                now = i/60
                image = np.zeros((540, 960, 3), np.uint8)
                # Simulate the shared HUD independently from real food art.
                raw = GrillSignature._templates[1]
                for channel in range(3):
                    image[479:479+raw.shape[0],145:145+raw.shape[1],channel] = raw
                cv2.rectangle(image, (390, 300), (570, 390), (230, 230, 100), 5)
                cv2.ellipse(image, (480, 340), (60, 22), 0, 0, 360, color, -1)
                if now < 1.4:
                    width = round(310-90*now)
                    cv2.rectangle(image, (480-width//2, 345-round(width/4)),
                                  (480+width//2, 345+round(width/4)), (230, 230, 100), 4)
                events, _ = engine.process(image, now, 1/120)
                hits.extend(events)
            self.assertEqual(len(hits), 1, (color, hits))
            self.assertEqual(hits[0]['action'], '넣기')

    def test_colored_frames_without_minigame_hud_do_not_fire(self):
        engine = GrillEngine()
        for i in range(60):
            image = np.zeros((540, 960, 3), np.uint8)
            cv2.rectangle(image, (300+i, 270), (660-i, 410), (230, 230, 100), 5)
            events, _ = engine.process(image, i/60, 1/120)
            self.assertEqual(events, [])
            self.assertFalse(engine.active)


def replay_video(path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f'Cannot open {path}')
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_MSEC, 6000)
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError('Cannot read calibration frame')
    rect = find_board(frame)
    if not rect:
        raise RuntimeError('Cannot find board')
    x, y, w, h = rect
    engine = TimingEngine(w, h, w*.09)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    events, judgements = [], []
    was_green = False
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        now = i/fps
        hits, _ = engine.process(frame[y:y+h, x:x+w], now, .5/fps)
        events.extend(hits)
        # Independently identify the green "accurate" feedback in the footage.
        patch_image = frame[max(0,y-round(h*.4)):y, x:x+round(w*.2)]
        hsv = cv2.cvtColor(patch_image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (40, 85, 70), (90, 255, 255))
        green = engine.active and np.count_nonzero(mask) > 40
        if green and not was_green:
            judgements.append(now)
        was_green = green
        i += 1
    cap.release()
    assert len(events) == 4, f'Expected 4 notes, got {events}'
    assert len(judgements) == 4, f'Expected 4 successful judgements, got {judgements}'
    errors = [(event['time']-judge)*1000 for event, judge in zip(events, judgements)]
    assert all(abs(e) <= 100+1e-6 for e in errors), errors
    assert all(event['time'] < 12 for event in events), 'Unexpected hit after song ended'
    return {'frames': i, 'fps': fps, 'board': rect,
            'trigger_times': [e['time'] for e in events],
            'recorded_judgement_times': judgements,
            'difference_from_recorded_feedback_ms': errors,
            'note': 'Offline visual replay; no actual keyboard input was sent.'}


def replay_two_rounds(path):
    session = None
    hits = []
    offset = 0.
    for scale in (1., .75):
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        i = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if scale != 1:
                frame = cv2.resize(frame, None, fx=scale, fy=scale)
            h, w = frame.shape[:2]
            if session is None:
                session = GameSession((w, h))
            session.update_size((w, h))
            if not session.active and i % 5 == 0:
                session.relocate(frame)
            if session.board is not None:
                x, y, bw, bh = session.board
                events, _ = session.process(frame[y:y+bh, x:x+bw], offset+i/fps, .5/fps)
                hits.extend(events)
            i += 1
        cap.release()
        offset += i/fps+1
    assert len(hits) == 8, f'Two rounds and resolution switch should detect 8 notes: {hits}'
    return {'rounds': 2, 'resolution_scales': [1, .75], 'detected_notes': len(hits)}


def replay_grill(path):
    report = []
    for scale, crop_top in [(1., 0), (.75, 0), (1., 24)]:
        engine = GrillEngine()
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        i, hits = 0, []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if crop_top:
                frame = frame[crop_top:]
            if scale != 1:
                frame = cv2.resize(frame, None, fx=scale, fy=scale)
            events, _ = engine.process(frame, i/fps, .5/fps)
            hits.extend(events)
            i += 1
        cap.release()
        assert [e['action'] for e in hits] == ['넣기', '꺼내기', '넣기', '꺼내기'], hits
        # Approximate observed key/animation times; feedback is shown later.
        reference = [2.8, 6.4, 7.6, 11.2]
        differences = [round((e['time']-t)*1000, 2) for e, t in zip(hits, reference)]
        assert all(abs(d) < 110 for d in differences), differences
        report.append({'scale': scale, 'titlebar_removed': bool(crop_top), 'actions': [e['action'] for e in hits],
                       'times': [e['time'] for e in hits], 'difference_from_observed_ms': differences})
    return report


def replay_mixed_rounds(chop_path, grill_path):
    session = None
    total = []
    offset = 0.
    modes = []
    for path, scale in [(chop_path, 1.), (grill_path, .75), (chop_path, .75)]:
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        i, hits = 0, []
        last_search = -100.
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = frame[24:]  # Match the actual native client capture path.
            if scale != 1:
                frame = cv2.resize(frame, None, fx=scale, fy=scale)
            h, w = frame.shape[:2]
            if session is None:
                session = GameSession((w, h))
            if session.update_size((w, h)):
                last_search = -100.
            now = offset+i/fps
            if now-last_search > (.8 if session.active else .3):
                session.relocate(frame)
                last_search = now
            if session.board is not None:
                x, y, bw, bh = session.board
                events, _ = session.process(frame[y:y+bh, x:x+bw], now, .5/fps)
                hits.extend(events)
                if events and (not modes or modes[-1] != session.kind):
                    modes.append(session.kind)
            i += 1
        cap.release()
        assert len(hits) == 4, (path, hits)
        total.extend(hits)
        offset += i/fps+1
    assert modes == ['chop', 'grill', 'chop'], modes
    return {'rounds': 3, 'modes': modes, 'total_actions': len(total)}


def replay_deadlines(path, drop_every=0):
    """Exercise the v4 live prediction path with 12ms delivery latency."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    session, context = None, None
    pending, done, actual = {}, set(), []
    i, last_search = 0, -100.
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        timestamp = i/fps
        i += 1
        if drop_every and i % drop_every == 0:
            continue
        delivered = timestamp+.012
        for ident, plan in list(pending.items()):
            if plan['deadline'] <= delivered:
                actual.append(plan)
                done.add(ident)
                del pending[ident]
        frame = frame[24:]
        h, w = frame.shape[:2]
        if session is None:
            session = GameSession((w, h))
        if timestamp-last_search > (.8 if session.active else .3):
            session.relocate(frame)
            last_search = timestamp
        if session.board is None:
            continue
        x, y, bw, bh = session.board
        session.process(frame[y:y+bh, x:x+bw], timestamp, 0.)
        next_context = session.engine if session.active else None
        if next_context is not context:
            pending.clear()
            done.clear()
            context = next_context
        for plan in session.plans:
            if plan['id'] not in done:
                pending[plan['id']] = dict(plan, deadline=max(plan['deadline'], delivered))
    cap.release()
    assert len(actual) == 4, actual
    return {'drop_every': drop_every, 'actions': [p.get('action', '썰기') for p in actual],
            'scheduled_times': [p['deadline'] for p in actual]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--grill-video', type=Path)
    args = parser.parse_args()
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(DetectorTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(InputTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(SessionTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(GrillTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.video:
        report = replay_video(args.video)
        report['consecutive_rounds'] = replay_two_rounds(args.video)
        if args.grill_video:
            report['grill'] = replay_grill(args.grill_video)
            report['mixed_rounds'] = replay_mixed_rounds(args.video, args.grill_video)
        print(json.dumps(report, indent=2))
        if args.report:
            args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
