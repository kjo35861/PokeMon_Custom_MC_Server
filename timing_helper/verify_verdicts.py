"""Verify real judgement captions and feedback calibration without any keys."""
from collections import Counter
from pathlib import Path
import json
import threading
import time
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from feedback import VerdictReader, VerdictCalibration
from grill import GrillEngine
from scheduler import InputScheduler, prediction_rejection


class VerdictTests(unittest.TestCase):
    def test_early_late_adjust_separately_and_exact_stops_drift(self):
        calibration = VerdictCalibration()
        calibration.update('insert', 'early', 1)
        self.assertEqual(calibration.delay['insert'], .012)
        self.assertEqual(calibration.delay['remove'], 0.)
        calibration.update('remove', 'late', 2)
        self.assertEqual(calibration.delay['remove'], -.012)
        previous = calibration.delay['insert']
        calibration.update('insert', 'perfect', 3)
        self.assertEqual(calibration.delay['insert'], previous)
        calibration.update('insert', 'early', 1)
        self.assertEqual(calibration.delay['insert'], previous)  # same input cannot teach twice

    def test_feedback_tuning_converges_in_simulation(self):
        calibration = VerdictCalibration()
        verdict = None
        for i in range(15):
            error = calibration.delay['insert']+.023
            verdict = 'perfect' if abs(error) <= .006 else ('early' if error < 0 else 'late')
            calibration.update('insert', verdict, i)
        self.assertEqual(verdict, 'perfect')
        for i in range(30):
            calibration.update('remove', 'early', 100+i)
        self.assertLessEqual(calibration.delay['remove'], .08)

    def test_missed_or_unmatched_input_never_teaches(self):
        calibration = VerdictCalibration()
        self.assertFalse(calibration.update('insert', 'miss', 1))
        engine = GrillEngine(calibration)
        with patch.object(engine.reader, 'read', return_value={'verdict': 'early', 'score': .99, 'time': 5.}):
            engine._feedback(np.zeros((540, 960, 3), np.uint8), 5.)
        self.assertEqual(calibration.delay['insert'], 0.)

    def test_actual_sent_input_is_matched_to_its_phase(self):
        engine = GrillEngine()
        engine.record_input({'id': 1, 'action': '꺼내기'}, 5.)
        with patch.object(engine.reader, 'read', return_value={'verdict': 'late', 'score': .99, 'time': 5.05}):
            engine._feedback(np.zeros((540, 960, 3), np.uint8), 5.05)
        self.assertEqual(engine.calibration.delay['insert'], 0.)
        self.assertEqual(engine.calibration.delay['remove'], -.012)

    def test_late_dispatch_does_not_teach_wrong_target_offset(self):
        engine = GrillEngine()
        engine.record_input({'id': 1, 'action': '꺼내기', 'deadline': 4.95}, 5.)
        with patch.object(engine.reader, 'read', return_value={'verdict': 'late', 'score': .99, 'time': 5.05}):
            engine._feedback(np.zeros((540, 960, 3), np.uint8), 5.05)
        self.assertEqual(engine.calibration.delay['remove'], 0.)

    def test_good_forecast_can_bridge_a_render_stall(self):
        plan = {'kind': 'grill', 'committed': True, 'max_silence': .65,
                'observed': 1., 'validated': 1., 'deadline': 1.4, 'valid_until': 1.66}
        self.assertIsNone(prediction_rejection(plan, 1.4))
        self.assertEqual(prediction_rejection(plan, 1.7), 'stale prediction')
        self.assertEqual(prediction_rejection(dict(plan, kind='chop'), 1.4), 'stale prediction')

    def test_target_is_equal_scale_and_freeze_does_not_move_it(self):
        engine = GrillEngine()
        current = [0.]
        def cues(_):
            # 250ms render plateau shortly before the actual target.
            sample_time = 1.02 if 1.02 < current[0] < 1.4 else current[0]
            return [{'kind': 'insert', 'width': 200-80*sample_time,
                     'anchor': 100, 'box': (350, 250, 200, 100)}]
        frame = np.zeros((540, 960, 3), np.uint8)
        with patch.object(engine.signature, 'matches', return_value=True), patch('grill.find_cues', side_effect=cues):
            for i in range(81):
                current[0] = i/60
                engine.process(frame, current[0])
                if 1.15 <= current[0] <= 1.3:
                    self.assertTrue(engine.plans)
                    plan = engine.plans[0]
                    self.assertTrue(plan['committed'])
                    self.assertLess(abs(plan['base_deadline']-1.25), .003)
        self.assertIsNone(prediction_rejection(dict(plan, validated=1.02), 1.25))

    def test_scheduler_can_accept_corrected_plan_after_rejection(self):
        reports, sent = [], []
        rejected = threading.Event()
        def completed(plan, actual, status):
            reports.append(status)
            if actual is None:
                rejected.set()
        def fire(plan):
            sent.append(plan)
            return time.perf_counter()
        with InputScheduler(threading.Event(), fire, completed=completed) as scheduler:
            scheduler.set_context('test')
            now = time.perf_counter()
            scheduler.submit({'id': 1, 'deadline': now+.015, 'observed': now-.4})
            self.assertTrue(rejected.wait(.5))
            now = time.perf_counter()
            scheduler.submit({'id': 1, 'deadline': now+.025, 'observed': now})
            time.sleep(.06)
        self.assertEqual(len(sent), 1, reports)


def read_video_verdicts(path):
    reader = VerdictReader()
    capture = cv2.VideoCapture(str(path))
    fps = capture.get(cv2.CAP_PROP_FPS)
    found, index = [], 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        verdict = reader.read(frame, index/fps)
        if verdict:
            found.append(verdict)
        index += 1
    capture.release()
    return {'counts': dict(Counter(item['verdict'] for item in found)), 'events': found}


def self_test_report():
    calibration = VerdictCalibration()
    for phase, verdict, ident in [('insert', 'early', 1), ('remove', 'late', 2), ('insert', 'perfect', 3)]:
        calibration.update(phase, verdict, ident)
    VerdictReader()  # Verify all four packaged judgement assets are readable.
    return {'insert_delay_ms': calibration.delay['insert']*1000,
            'remove_delay_ms': calibration.delay['remove']*1000, 'real_keys_sent': False}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--recording', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(VerdictTests))
    report = {'calibration': self_test_report()}
    if args.reference:
        report['reference'] = read_video_verdicts(args.reference)
        assert report['reference']['counts'] == {'perfect': 3, 'early': 1}, report['reference']['counts']
    if args.recording:
        report['recording'] = read_video_verdicts(args.recording)
        assert report['recording']['counts'] == {'early': 9, 'late': 1, 'miss': 5}, report['recording']['counts']
    if args.report:
        args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if tests.wasSuccessful() else 1)
