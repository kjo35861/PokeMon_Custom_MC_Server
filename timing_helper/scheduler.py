"""A cancellable, deadline-driven input thread; vision never waits for key-up."""
import ctypes
from ctypes import wintypes as wt
import threading
import time


def prediction_rejection(plan, now):
    """A fresh validation is distinct from the last visible contour sample."""
    confirmed = plan.get('validated', plan.get('observed', now))
    silence = min(.65, plan.get('max_silence', .16)) if plan.get('kind') == 'grill' else .16
    if now-confirmed > silence:
        return 'stale prediction'
    if now > plan.get('valid_until', float('inf')):
        return 'prediction window ended'
    if now-plan['deadline'] > .060:
        return 'expired'
    return None


class PreciseWait:
    def __init__(self):
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateWaitableTimerExW.argtypes = [ctypes.c_void_p, wt.LPCWSTR, wt.DWORD, wt.DWORD]
        self.kernel.CreateWaitableTimerExW.restype = wt.HANDLE
        self.kernel.SetWaitableTimer.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_longlong), wt.LONG,
                                                ctypes.c_void_p, ctypes.c_void_p, wt.BOOL]
        self.kernel.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
        self.kernel.CloseHandle.argtypes = [wt.HANDLE]
        self.handle = self.kernel.CreateWaitableTimerExW(None, None, 2, 0x1F0003)

    def sleep(self, seconds):
        if seconds <= 0:
            return
        if self.handle:
            due = ctypes.c_longlong(-max(1, round(seconds*10_000_000)))
            if self.kernel.SetWaitableTimer(self.handle, ctypes.byref(due), 0, None, None, False):
                self.kernel.WaitForSingleObject(self.handle, max(1, round(seconds*1000)+10))
                return
        time.sleep(seconds)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class InputScheduler:
    def __init__(self, stop_event, fire, guard=lambda: True, completed=lambda *args: None):
        self.stop_event, self.fire, self.guard, self.completed = stop_event, fire, guard, completed
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.context = None
        self.generation = 0
        self.pending = {}
        self.done = set()
        self.inflight = set()
        self.rejected = {}
        self.closed = False
        self.thread = None

    def __enter__(self):
        self.thread = threading.Thread(target=self.run, name='timing-input', daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        with self.lock:
            self.closed = True
            self.pending.clear()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=1)

    def set_context(self, context):
        with self.lock:
            if context != self.context:
                self.context = context
                self.generation += 1
                self.pending.clear()
                self.done.clear()
                self.rejected.clear()
                self.wake.set()

    def clear(self):
        self.set_context(object())

    def soon(self, horizon=.25):
        with self.lock:
            return any(plan['deadline']-time.perf_counter() < horizon for plan in self.pending.values())

    def submit(self, plan):
        with self.lock:
            key = plan['id']
            if (key in self.done or (self.generation, key) in self.inflight
                    or self.closed or self.stop_event.is_set()):
                return
            failed = self.rejected.get(key)
            if failed is not None and abs(plan['deadline']-failed['deadline']) < .005:
                confirmed = plan.get('validated', plan.get('observed', 0.))
                if failed['reason'] != 'stale prediction' or confirmed <= failed['confirmed']:
                    return
            item = dict(plan, context=self.context, generation=self.generation)
            old = self.pending.get(key)
            if old and old['deadline']-time.perf_counter() < .018:
                # Do not chase sub-pixel fit noise in the final 18 milliseconds.
                item['deadline'] = old['deadline']
            self.pending[key] = item
        self.wake.set()

    def cancel(self, identities):
        """Cancel ordinary strip fragments when a mash prompt takes priority."""
        with self.lock:
            for key in identities:
                self.pending.pop(key, None)
        self.wake.set()

    def reconcile(self, identities, kind=None):
        """Discard orphaned reservations, optionally for one input kind only."""
        valid = set(identities)
        with self.lock:
            for key in list(self.pending):
                if key not in valid and (kind is None or self.pending[key].get('kind') == kind):
                    del self.pending[key]

    def run(self):
        timer = PreciseWait()
        try:
            while not self.closed and not self.stop_event.is_set():
                with self.lock:
                    candidate = min(self.pending.values(), key=lambda p: p['deadline'], default=None)
                if candidate is None:
                    self.wake.wait(.02)
                    self.wake.clear()
                    continue
                remaining = candidate['deadline']-time.perf_counter()
                if remaining > .020:
                    self.wake.wait(min(.015, remaining-.020))
                    self.wake.clear()
                    continue
                if remaining > .0005:
                    timer.sleep(min(.002, remaining-.00035))
                    continue
                if remaining > 0:
                    continue  # At most 0.5ms of fine waiting; no long busy loop.
                with self.lock:
                    current = self.pending.get(candidate['id'])
                    if current is not candidate:
                        continue
                    del self.pending[candidate['id']]
                    token = (candidate['generation'], candidate['id'])
                    if (candidate['generation'] != self.generation or candidate['id'] in self.done
                            or token in self.inflight or self.closed or self.stop_event.is_set()):
                        continue
                    # Claim atomically with dequeue. Vision keeps running while
                    # guard/fire/key-up execute, and must not queue this ID again.
                    self.inflight.add(token)
                try:
                    if not self.guard():
                        continue
                    rejection = prediction_rejection(candidate, time.perf_counter())
                    if rejection is not None:
                        with self.lock:
                            if candidate['generation'] == self.generation:
                                self.rejected[candidate['id']] = {
                                    'deadline': candidate['deadline'], 'reason': rejection,
                                    'confirmed': candidate.get('validated', candidate.get('observed', 0.))}
                        self.completed(candidate, None, rejection)
                        continue
                    with self.lock:
                        if (candidate['generation'] != self.generation or self.closed
                                or self.stop_event.is_set()):
                            continue
                        # Once a key attempt starts it cannot safely be retried,
                        # even if its callback fails after key-down. Rejected
                        # forecasts above remain eligible for a fresh retry.
                        self.done.add(candidate['id'])
                    actual = self.fire(candidate)
                    self.completed(candidate, actual, 'sent' if actual is not None else 'skipped')
                except Exception as exc:
                    self.completed(candidate, None, f'error: {exc}')
                finally:
                    with self.lock:
                        self.inflight.discard(token)
        finally:
            timer.close()
