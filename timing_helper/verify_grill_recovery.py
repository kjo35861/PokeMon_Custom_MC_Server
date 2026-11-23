"""Reproduce v4 stale cancellations; no capture or keyboard injection occurs."""
import json
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np

from grill import GrillEngine
from scheduler import InputScheduler, prediction_rejection


def recovery_scenario(kind, hidden_after, late_correction):
    engine = GrillEngine()
    frame = np.zeros((540, 960, 3), np.uint8)
    current = [0.]
    def detect(_):
        if current[0] >= hidden_after:
            return []
        return [{'kind': kind, 'width': 200-80*current[0], 'anchor': 100,
                 'box': (350, 200, 200, 100)}]
    plan = None
    with patch.object(engine.signature, 'matches', return_value=True), patch('grill.find_cues', side_effect=detect):
        for i in range(100):
            current[0] = i/60
            engine.process(frame, current[0])
            if engine.plans:
                plan = dict(engine.plans[0])
            if plan and current[0] >= plan['deadline']+late_correction:
                plan['deadline'] += late_correction
                return plan, current[0], engine
    raise AssertionError('Reservation disappeared before its adjusted deadline')


class RecoveryTests(unittest.TestCase):
    def test_hidden_border_survives_supported_late_corrections(self):
        for kind in ('insert', 'remove'):
            for offset in (0., .10, .20):
                with self.subTest(kind=kind, correction=offset):
                    plan, now, engine = recovery_scenario(kind, 1.05, offset)
                    self.assertIsNone(prediction_rejection(plan, now), plan)
                    self.assertLess(now-plan['validated'], .02)
                    self.assertEqual(plan['id'], 1)
                    if offset >= .10:
                        self.assertGreater(now-plan['observed'], .16)  # v4 rejected this.

    def test_unadjusted_replay_firing_does_not_expire_delayed_live_input(self):
        plan, now, engine = recovery_scenario('remove', 2., .20)
        self.assertTrue(engine.cues['remove']['fired'])
        self.assertIsNone(prediction_rejection(plan, now))

    def test_minigame_exit_clears_held_reservation(self):
        plan, now, engine = recovery_scenario('insert', 1.05, .10)
        with patch.object(engine.signature, 'matches', return_value=False):
            engine.last_signature = -100.
            engine.process(np.zeros((540, 960, 3), np.uint8), now+.01)
        self.assertFalse(engine.active)
        self.assertEqual(engine.plans, [])
        self.assertEqual(engine.cues, {})

    def test_held_plan_has_bounded_lifetime(self):
        plan, now, engine = recovery_scenario('insert', 1.05, .10)
        with patch.object(engine.signature, 'matches', return_value=True), patch('grill.find_cues', return_value=[]):
            engine.process(np.zeros((540, 960, 3), np.uint8), plan['valid_until']+.05)
        self.assertEqual(engine.plans, [])
        self.assertIn(prediction_rejection(plan, plan['valid_until']+.001),
                      ('prediction window ended', 'stale prediction'))

    def test_stop_still_cancels_a_recovered_reservation(self):
        stop = threading.Event()
        fired = []
        with InputScheduler(stop, lambda plan: fired.append(plan)) as scheduler:
            scheduler.set_context('grill')
            now = time.perf_counter()
            scheduler.submit({'id': 1, 'deadline': now+.025, 'observed': now-.25,
                              'validated': now, 'valid_until': now+.1})
            stop.set()
            time.sleep(.05)
        self.assertEqual(fired, [])

    def test_scheduler_sends_revalidated_plan_with_old_contour(self):
        fired = []
        completed = threading.Event()
        def fire(plan):
            fired.append(plan)
            return time.perf_counter()
        with InputScheduler(threading.Event(), fire, completed=lambda *args: completed.set()) as scheduler:
            scheduler.set_context('grill')
            now = time.perf_counter()
            scheduler.submit({'id': 1, 'deadline': now+.02, 'observed': now-.25,
                              'validated': now, 'valid_until': now+.1})
            self.assertTrue(completed.wait(.5))
        self.assertEqual(len(fired), 1)


def recovery_summary():
    cases = []
    for kind in ('insert', 'remove'):
        for offset in (0., .10, .20):
            plan, now, _ = recovery_scenario(kind, 1.05, offset)
            cases.append({'kind': kind, 'late_correction_ms': offset*1000,
                          'last_contour_age_ms': round((now-plan['observed'])*1000, 2),
                          'v4_would_reject': now-plan['observed'] > .16,
                          'v5_rejection': prediction_rejection(plan, now)})
    return {'cases': cases, 'real_keys_sent': False}


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RecoveryTests))
    report = recovery_summary()
    Path(__file__).with_name('grill-recovery-verification.json').write_text(
        json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
