"""DXGI-first desktop capture with GDI fallback and display-switch recovery."""
import ctypes
import re
import time

import mss
import numpy as np


class CaptureUnavailable(RuntimeError):
    pass


def relative_region(rect, output_rect):
    """Convert desktop coordinates, including negative monitor origins."""
    x, y, w, h = rect
    left, top, right, bottom = output_rect
    if w <= 0 or h <= 0 or x < left or y < top or x+w > right or y+h > bottom:
        return None
    return (x-left, y-top, x+w-left, y+h-top)


class ScreenCapture:
    def __init__(self):
        self.gdi = None
        self.camera = None
        self.output_rect = None
        self.retry_at = 0.
        self.name = '화면 준비 중'
        self.com_initialized = False
        self.last_dxgi = None
        self.frame_time = 0.
        self.frame_token = None

    def __enter__(self):
        # COM must be initialized on the actual capture thread as well as Tk's.
        try:
            # comtypes (used by DXcam) initializes STA when first imported.
            result = ctypes.OleDLL('ole32').CoInitializeEx(None, 2)
            self.com_initialized = result in (0, 1)
        except OSError as exc:
            # Tk or another library may already have initialized an STA here.
            if getattr(exc, 'hresult', None) != -2147417850:  # RPC_E_CHANGED_MODE
                raise
        self.gdi = mss.mss()
        return self

    def reset(self):
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception:
                pass
        self.camera = None
        self.output_rect = None
        self.retry_at = 0.
        self.last_dxgi = None
        self.frame_time = 0.
        self.frame_token = None

    def _timestamp_dxgi(self, captured_at):
        duplicator = getattr(self.camera, '_duplicator', None)
        source_time = float(getattr(duplicator, 'latest_frame_time', 0.))
        if source_time > 0 and -.01 < captured_at-source_time < 5:
            # DXcam 0.3.0 reports the DXGI LastPresentTime in QPC seconds,
            # the same clock used by Python perf_counter on Windows.
            self.frame_time = source_time
            self.frame_token = ('dxgi', source_time)
        else:
            self.frame_time = captured_at
            self.frame_token = ('capture', captured_at)

    def __exit__(self, *_):
        self.reset()
        if self.gdi is not None:
            self.gdi.close()
        if self.com_initialized:
            ctypes.OleDLL('ole32').CoUninitialize()

    def _open_dxgi(self, rect):
        import dxcam
        outputs = re.findall(r'Device\[(\d+)\] Output\[(\d+)\]', dxcam.output_info())
        for device_idx, output_idx in outputs:
            camera = None
            try:
                camera = dxcam.create(device_idx=int(device_idx), output_idx=int(output_idx),
                                      output_color='BGR', backend='dxgi')
                # DXcam 0.3.0 exposes DesktopCoordinates on its DXGI descriptor.
                # Keep this version-pinned adapter isolated from timing logic.
                coords = camera._output.desc.DesktopCoordinates
                bounds = (coords.left, coords.top, coords.right, coords.bottom)
                if relative_region(rect, bounds) is not None:
                    self.camera, self.output_rect = camera, bounds
                    return
            except Exception:
                continue
            finally:
                if camera is not None and camera is not self.camera:
                    camera.release()
        raise CaptureUnavailable('게임 화면이 하나의 모니터 안에 있어야 합니다.')

    def grab(self, rect):
        now = time.perf_counter()
        if self.camera is not None and relative_region(rect, self.output_rect) is None:
            self.reset()
        if self.camera is None and now >= self.retry_at:
            try:
                self._open_dxgi(rect)
            except Exception:
                self.retry_at = now+1.
        if self.camera is not None:
            try:
                region = relative_region(rect, self.output_rect)
                frame = self.camera.grab(region=region, new_frame_only=False)
                if frame is not None and frame.size and int(frame.max()) > 3:
                    self.name = 'DXGI 전체화면'
                    self._timestamp_dxgi(time.perf_counter())
                    self.last_dxgi = (rect, frame, now, self.frame_time, self.frame_token)
                    return frame
                # A full-frame relocation grab can consume the newest DXGI
                # frame immediately before a board crop. Reuse only that fresh
                # owned frame, avoiding a black GDI fallback in exclusive mode.
                if self.last_dxgi is not None:
                    old_rect, old_pixels, captured_at, source_time, token = self.last_dxgi
                    x, y, w, h = old_rect
                    crop = relative_region(rect, (x, y, x+w, y+h))
                    if crop is not None and now-captured_at < .06:
                        left, top, right, bottom = crop
                        self.name = 'DXGI 전체화면'
                        self.frame_time, self.frame_token = source_time, token
                        return old_pixels[top:bottom, left:right].copy()
            except Exception:
                self.reset()
                self.retry_at = now+.3
        try:
            x, y, w, h = rect
            frame = np.array(self.gdi.grab({'left': x, 'top': y, 'width': w, 'height': h}))[:, :, :3].copy()
            if frame.size and int(frame.max()) > 3:
                self.name = 'GDI 호환 캡처'
                self.frame_time = (now+time.perf_counter())/2
                self.frame_token = ('gdi', self.frame_time)
                return frame
        except Exception as exc:
            raise CaptureUnavailable(str(exc)) from exc
        raise CaptureUnavailable('전체화면 전환 중입니다. 새 화면을 기다립니다.')


def capture_self_test(destination):
    """Verify the packaged GPU backend on a worker; save metadata, not images."""
    import json
    import threading
    from pathlib import Path
    report = {'frames': [], 'error': None}
    def run():
        try:
            with ScreenCapture() as screen:
                for _ in range(4):
                    pixels = screen.grab((0, 0, 64, 64))
                    report['frames'].append({'backend': screen.name, 'shape': list(pixels.shape)})
                    time.sleep(.05)
        except Exception as exc:
            report['error'] = repr(exc)
    worker = threading.Thread(target=run)
    worker.start()
    worker.join(timeout=15)
    if worker.is_alive():
        report['error'] = 'capture timed out'
    report['dxgi_ok'] = any('DXGI' in frame['backend'] for frame in report['frames'])
    Path(destination).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['dxgi_ok'] and report['error'] is None else 2
