"""Timing regression/stress tests. All input callbacks are mocked; no keys sent."""
import argparse
from collections import deque
import importlib.util
import json
from pathlib import Path
import random
import sys
import threading
import time
import unittest

import numpy as np

from motion import fit_motion, add_sample
from scheduler import InputScheduler
from vision import NoteTracker, Candy
from screen_capture import ScreenCapture
from types import SimpleNamespace


def tracking_stress(tracker_class=NoteTracker, candy_class=Candy, modern=True):
    all_errors, missed, extras = [], 0, 0
    for seed in range(12):
        rng = random.Random(seed)
        arrivals = [.85+i*.060 for i in range(20)]
        tracker = tracker_class(1000, 240, 90)
        produced, pending, done = [], {}, set()
        source, processing, blocked = 0., 0., -1.
        last_source = -1.
        previous = None
        while source < 2.6:
            source += rng.uniform(.010, .023)
            positions = [90+600*(arrival-source) for arrival in arrivals]
            notes = [candy_class(x+rng.gauss(0, .6), 80, 22)
                     for x in positions if -10 < x < 1000]
            delivered = max(processing+.001, source+rng.uniform(.003, .022))
            processing = delivered+rng.uniform(.001, .010)
            if not modern and processing < blocked:
                continue
            if rng.random() < .16 and previous is not None:
                sample_time, notes = previous  # cached desktop frame
            else:
                sample_time = source
                previous = (sample_time, notes)
            if modern:
                # Already queued inputs fire while vision processes the next frame.
                for ident, due in list(pending.items()):
                    if due <= processing:
                        produced.append(due)
                        done.add(ident)
                        del pending[ident]
                if sample_time != last_source:
                    tracker.update(notes, sample_time, 0.)
                    last_source = sample_time
                    for plan in tracker.plans:
                        if plan['id'] not in done:
                            pending[plan['id']] = max(plan['deadline'], processing)
            else:
                events = tracker.update(notes, processing, .006)
                for _ in events:
                    produced.append(processing)
                    blocked = processing+.025
        if modern:
            produced.extend(pending.values())
        unmatched = list(arrivals)
        for actual in sorted(produced):
            if not unmatched:
                extras += 1
                continue
            expected = min(unmatched, key=lambda at: abs(actual-at))
            if abs(actual-expected) < .10:
                all_errors.append((actual-expected)*1000)
                unmatched.remove(expected)
            else:
                extras += 1
        missed += len(unmatched)
    values = np.asarray(all_errors)
    return {'expected_notes': 240, 'missed': missed, 'extra': extras,
            'mean_error_ms': round(float(values.mean()), 3),
            'stddev_ms': round(float(values.std()), 3),
            'p95_absolute_error_ms': round(float(np.percentile(np.abs(values), 95)), 3)}


def scheduler_benchmark(count=45):
    stop = threading.Event()
    actual = []
    event = threading.Event()
    def fire(plan):
        stamp = time.perf_counter()
        time.sleep(.010)  # Simulate key-down/up without sending an actual key.
        return stamp
    def completed(plan, stamp, status):
        actual.append((plan, stamp, status))
        if len(actual) == count:
            event.set()
    with InputScheduler(stop, fire, completed=completed) as scheduler:
        scheduler.set_context('test')
        start = time.perf_counter()+.10
        for i in range(count):
            scheduler.submit({'id': i, 'deadline': start+i*.025})
        if not event.wait(5):
            raise AssertionError(f'Only {len(actual)}/{count} mocked inputs executed')
    errors = [(stamp-plan['deadline'])*1000 for plan, stamp, status in actual if stamp is not None]
    assert len(errors) == count, actual
    return {'mock_inputs': count, 'mean_error_ms': round(float(np.mean(errors)), 3),
            'p95_absolute_error_ms': round(float(np.percentile(np.abs(errors), 95)), 3),
            'max_absolute_error_ms': round(float(np.max(np.abs(errors))), 3)}


class TimingTests(unittest.TestCase):
    def test_cached_frame_preserves_original_presentation_time(self):
        screen = ScreenCapture()
        timestamp = time.perf_counter()-.018
        camera = SimpleNamespace(grab=lambda **kw: np.full((40, 100, 3), 150, np.uint8),
                                 _duplicator=SimpleNamespace(latest_frame_time=timestamp))
        screen.camera, screen.output_rect = camera, (0, 0, 1920, 1080)
        screen.grab((0, 0, 100, 40))
        first = screen.frame_token
        time.sleep(.002)
        screen.grab((0, 0, 100, 40))
        self.assertEqual(first, screen.frame_token)
        self.assertEqual(timestamp, screen.frame_time)

    def test_motion_ignores_duplicate_frame_times(self):
        samples = deque(maxlen=48)
        for i in range(12):
            add_sample(samples, i/60, 300-i*10)
            add_sample(samples, i/60, 999)
        model = fit_motion(samples)
        self.assertAlmostEqual(model.velocity, -600, places=4)

    def test_single_contour_outlier_does_not_shift_deadline(self):
        samples = [(i/60, 300-600*i/60+(14 if i == 6 else 0)) for i in range(12)]
        model = fit_motion(samples)
        self.assertLess(abs(model.crossing(90)-.35), .004)

    def test_close_notes_are_not_blocked_by_85ms_cooldown(self):
        result = tracking_stress()
        self.assertEqual(result['missed'], 0, result)
        self.assertEqual(result['extra'], 0, result)
        self.assertLess(result['p95_absolute_error_ms'], 8, result)

    def test_scheduler_cancels_on_focus_guard_failure(self):
        fired = []
        with InputScheduler(threading.Event(), lambda p: fired.append(p), guard=lambda: False) as scheduler:
            scheduler.set_context('old')
            scheduler.submit({'id': 1, 'deadline': time.perf_counter()+.02})
            time.sleep(.05)
        self.assertEqual(fired, [])

    def test_scheduler_cancels_previous_round(self):
        fired = []
        with InputScheduler(threading.Event(), lambda p: fired.append(p)) as scheduler:
            scheduler.set_context('old')
            scheduler.submit({'id': 1, 'deadline': time.perf_counter()+.025})
            scheduler.set_context('new')
            time.sleep(.05)
        self.assertEqual(fired, [])

    def test_scheduler_rejects_stale_predictions(self):
        fired = []
        with InputScheduler(threading.Event(), lambda p: fired.append(p)) as scheduler:
            scheduler.set_context('test')
            scheduler.submit({'id': 1, 'deadline': time.perf_counter()+.015,
                              'observed': time.perf_counter()-.3})
            time.sleep(.04)
        self.assertEqual(fired, [])

    def test_scheduler_deduplicates_repeated_updates(self):
        fired = []
        def fire(plan):
            fired.append(plan)
            return time.perf_counter()
        with InputScheduler(threading.Event(), fire) as scheduler:
            scheduler.set_context('test')
            deadline = time.perf_counter()+.025
            for _ in range(10):
                scheduler.submit({'id': 1, 'deadline': deadline})
            time.sleep(.055)
            scheduler.submit({'id': 1, 'deadline': time.perf_counter()})
            time.sleep(.02)
        self.assertEqual(len(fired), 1)

    def test_scheduler_deduplicates_updates_during_key_hold(self):
        for kind in ('chop', 'grill'):
            with self.subTest(kind=kind):
                fired = []
                entered, release, finished = (threading.Event() for _ in range(3))
                def fire(plan):
                    fired.append(plan['id'])
                    entered.set()
                    release.wait(.5)  # vision submits while the key is still down
                    return time.perf_counter()
                with InputScheduler(threading.Event(), fire,
                                    completed=lambda *args: finished.set()) as scheduler:
                    scheduler.set_context(kind)
                    plan = {'id': 1, 'kind': kind, 'deadline': time.perf_counter()+.02}
                    try:
                        scheduler.submit(plan)
                        self.assertTrue(entered.wait(1))
                        for _ in range(10):
                            scheduler.submit(plan)
                        release.set()
                        self.assertTrue(finished.wait(1))
                        time.sleep(.04)
                    finally:
                        release.set()
                self.assertEqual(fired, [1])

    def test_inflight_old_round_does_not_complete_new_round_identity(self):
        fired = []
        entered, release, second = (threading.Event() for _ in range(3))
        def fire(plan):
            fired.append(plan['context'])
            if len(fired) == 1:
                entered.set()
                release.wait(.5)
            else:
                second.set()
            return time.perf_counter()
        with InputScheduler(threading.Event(), fire) as scheduler:
            try:
                scheduler.set_context('old')
                scheduler.submit({'id': 1, 'deadline': time.perf_counter()+.01})
                self.assertTrue(entered.wait(1))
                scheduler.set_context('new')
                scheduler.submit({'id': 1, 'deadline': time.perf_counter()+.02})
                release.set()
                self.assertTrue(second.wait(1))
                scheduler.submit({'id': 1, 'deadline': time.perf_counter()})
                time.sleep(.04)
            finally:
                release.set()
        self.assertEqual(fired, ['old', 'new'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TimingTests))
    report = {'v4_tracking_stress': tracking_stress(), 'mock_scheduler': scheduler_benchmark(),
              'note': 'Synthetic/offline measurements; not Minecraft judgement accuracy.'}
    if args.baseline:
        spec = importlib.util.spec_from_file_location('vision_v3', args.baseline)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        report['v3_tracking_stress'] = tracking_stress(module.NoteTracker, module.Candy, False)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
