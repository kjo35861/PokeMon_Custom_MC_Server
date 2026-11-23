"""Mash-window regression tests and video replay. Never sends real keys."""
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from burst import BurstReader, BurstController
from scheduler import InputScheduler, prediction_rejection
from vision import Candy, TimingEngine, find_board


def cue(count=0):
    return {'required': 4, 'count': count, 'score': 1.}


def prompt_board(count=0):
    board = np.full((290, 1237, 3), (105, 155, 185), np.uint8)
    templates = BurstReader()._templates
    for name, x, y in [('prompt', 194, 27),
                       (('zero', 'one', 'two', 'three', 'four')[count], 259, 29),
                       ('limit_four', 272, 29)]:
        raw = templates[name]
        h, w = raw.shape[:2]
        board[y:y+h, x:x+w] = raw
    return board


class BurstTests(unittest.TestCase):
    def test_prompt_and_completion_at_multiple_gui_scales(self):
        reader = BurstReader()
        for scale in (.5, 2/3, .75, 1., 1.25, 1.5, 2.):
            for count in range(5):
                with self.subTest(scale=scale, count=count):
                    frame = cv2.resize(prompt_board(count), None, fx=scale, fy=scale,
                                       interpolation=cv2.INTER_NEAREST)
                    result = reader.read(frame)
                    self.assertIsNotNone(result)
                    self.assertEqual(result['count'], count)
                    self.assertEqual(result['required'], 4)

    def test_plain_wood_and_different_required_count_do_not_trigger(self):
        reader = BurstReader()
        self.assertIsNone(reader.read(np.full((290, 1237, 3), 160, np.uint8)))
        frame = prompt_board()
        # Replace the denominator with 0: this is not the supported /4 cue.
        frame[29:49, 280:298] = (105, 155, 185)
        raw = reader._templates['zero']
        frame[29:49, 279:293] = raw
        self.assertIsNone(reader.read(frame))

    def test_continuous_prompt_sends_exactly_four_independent_presses(self):
        reader = Mock(read=Mock(return_value=cue()))
        controller = BurstController(reader)
        fired = []
        def fire(plan):
            fired.append((plan['id'], time.perf_counter()))
            time.sleep(.020)  # Includes the key hold: vision keeps submitting.
            return fired[-1][1]
        with InputScheduler(threading.Event(), fire) as scheduler:
            scheduler.set_context('mash')
            end = time.perf_counter()+.5
            while time.perf_counter() < end:
                controller.update(None, time.perf_counter())
                for plan in controller.plans:
                    scheduler.submit(plan)
                time.sleep(.004)
        self.assertEqual(len(fired), 4)
        self.assertEqual(len({item[0] for item in fired}), 4)
        self.assertTrue(all(b[1]-a[1] >= .060 for a, b in zip(fired, fired[1:])))

    def test_completion_latches_until_next_window(self):
        reader = Mock(read=Mock(return_value=cue()))
        controller = BurstController(reader)
        controller.update(None, 1.)
        old = {p['id'] for p in controller.plans}
        reader.read.return_value = cue(4)
        controller.update(None, 1.10)
        self.assertEqual(controller.plans, [])
        reader.read.return_value = cue()
        controller.update(None, 1.15)
        self.assertEqual(controller.plans, [])
        reader.read.return_value = None
        controller.update(None, 1.40)
        reader.read.return_value = cue()
        controller.update(None, 1.50)
        self.assertTrue(old.isdisjoint(p['id'] for p in controller.plans))
        self.assertEqual(len(controller.plans), 4)

    def test_existing_count_only_requests_remaining_presses(self):
        controller = BurstController(Mock(read=Mock(return_value=cue(2))))
        controller.update(None, 1.)
        self.assertEqual([p['step'] for p in controller.plans], [3, 4])
        self.assertAlmostEqual(controller.plans[0]['deadline'], 1.025)

    def test_delayed_capture_does_not_start_burst_in_the_past(self):
        controller = BurstController(Mock(read=Mock(return_value=cue())))
        controller.update(None, 1., input_time=1.14)
        self.assertAlmostEqual(controller.plans[0]['deadline'], 1.165)
        self.assertGreater(controller.plans[0]['valid_until'], controller.plans[0]['deadline'])

    def test_single_missing_frame_does_not_restart_four_taps(self):
        reader = Mock(read=Mock(return_value=cue()))
        controller = BurstController(reader)
        controller.update(None, 1.)
        identities = {p['id'] for p in controller.plans}
        reader.read.return_value = None
        controller.update(None, 1.033)
        self.assertEqual(controller.plans, [])
        reader.read.return_value = cue()
        controller.update(None, 1.066)
        self.assertEqual(controller.episode, 1)
        self.assertTrue(all(p['id'] in identities for p in controller.plans))

    def test_prompt_end_cancels_burst_but_keeps_next_normal_note(self):
        fired = []
        with InputScheduler(threading.Event(), lambda p: fired.append(p['id'])) as scheduler:
            scheduler.set_context('same-round')
            now = time.perf_counter()
            scheduler.submit({'id': ('burst', 1, 0), 'kind': 'burst', 'deadline': now+.04})
            scheduler.submit({'id': 11, 'deadline': now+.06})
            scheduler.reconcile([], kind='burst')
            time.sleep(.10)
        self.assertEqual(fired, [11])

    def test_strip_fragments_are_muted_and_next_normal_note_survives(self):
        engine = TimingEngine(1237, 290, 1237*.09)
        frame = np.full((290, 1237, 3), (105, 155, 185), np.uint8)
        engine.burst = BurstController(Mock())
        events, burst_ids, cancelled = [], set(), set()
        for i in range(175):
            now = i/100
            engine.burst.reader.read.return_value = cue() if .92 <= now <= 1.20 else None
            notes = [Candy(1237*.09+600*(due-now), 100, 30, 'marker') for due in (1., 1.5)]
            with patch.object(engine.detector, 'detect', return_value=notes):
                hits, _ = engine.process(frame, now)
            events.extend(hits)
            burst_ids.update(p['id'] for p in engine.plans if p.get('kind') == 'burst')
            cancelled.update(engine.cancelled_ids)
        self.assertEqual(len(burst_ids), 4)
        self.assertEqual(len(events), 1)
        self.assertAlmostEqual(events[0]['time'], 1.5, delta=.02)
        self.assertIn(1, cancelled)


def self_test_report():
    result = unittest.TextTestRunner(stream=io.StringIO()).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(BurstTests))
    return {'passed': result.wasSuccessful(), 'tests': result.testsRun, 'real_keys_sent': False,
            'failures': [trace for _, trace in result.failures+result.errors]}


def replay_video(path, expected_windows=5):
    cv2.setNumThreads(1)
    capture = cv2.VideoCapture(str(path))
    fps = capture.get(cv2.CAP_PROP_FPS)
    capture.set(cv2.CAP_PROP_POS_MSEC, 8000)
    ok, frame = capture.read()
    assert ok, path
    x, y, w, h = find_board(frame[24:])
    engine = TimingEngine(w, h, w*.09)
    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
    pending, done, actions, rejected = {}, set(), [], []
    index, windows, last_visible = 0, [], False
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        now = index/fps
        index += 1
        engine.process(frame[24:][y:y+h, x:x+w], now)
        if not engine.active:
            pending.clear()
            done.clear()
        visible = engine.burst.visible
        if visible != last_visible:
            windows.append({'time': now, 'visible': visible})
            last_visible = visible
        valid_bursts = {p['id'] for p in engine.plans if p.get('kind') == 'burst'}
        for key in list(pending):
            if key in engine.cancelled_ids or (pending[key].get('kind') == 'burst' and key not in valid_bursts):
                del pending[key]
        for plan in engine.plans:
            if plan['id'] not in done:
                pending[plan['id']] = plan
        for key, plan in list(pending.items()):
            if plan['deadline'] <= now+.010:
                rejection = prediction_rejection(plan, max(now, plan['deadline']))
                if rejection:
                    rejected.append(dict(plan, reason=rejection))
                else:
                    actions.append(plan)
                    done.add(key)
                del pending[key]
    capture.release()
    burst = [p for p in actions if p.get('kind') == 'burst']
    counts = dict(Counter(p['id'][1] for p in burst))
    assert list(counts.values()) == [4]*expected_windows, (counts, windows)
    return {'burst_taps_by_window': counts, 'windows': windows, 'burst_actions': burst,
            'normal_actions': len(actions)-len(burst), 'rejected': rejected,
            'real_keys_sent': False, 'note': 'Video replay is not live game judgement accuracy.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--expected-windows', type=int, default=5)
    args = parser.parse_args()
    report = {'tests': self_test_report()}
    if args.video:
        report['video'] = replay_video(args.video, args.expected_windows)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['tests']['passed'] else 1)
