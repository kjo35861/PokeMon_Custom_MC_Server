"""Local screen-based helper for the cooking minigame; F8 start/stop, F9 stop."""
import os
import sys
import time
import queue
import threading
import traceback
from pathlib import Path
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox

import cv2
from PIL import Image, ImageTk

import win_input as win
from vision import find_board
from screen_capture import ScreenCapture, CaptureUnavailable
from session import GameSession
from grill import GrillSignature
from scheduler import InputScheduler


class App:
    def __init__(self, root):
        self.root = root
        root.title('요리 타이밍 도우미 v8 · 다다닥 연타 지원')
        root.geometry('1040x820')
        root.minsize(860, 700)
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.hwnd = None
        self.capture_size = None
        self.frame = None
        self.board = None
        self.detected_kind = None
        self.target_ratio = .09
        self.scale = 1.
        self.image_origin = (0, 0)
        self.mode = 'none'
        self.drag = None
        self.preview_photo = None
        self.key_states = {}
        self.dry = tk.BooleanVar(value=True)
        self.bias = tk.StringVar(value='0')
        self.phase_bias = {name: tk.StringVar(value='0') for name in ('chop', 'insert', 'remove')}
        self.auto_tune = tk.BooleanVar(value=True)
        self.verdict_stats = tk.StringVar(value='실제 게임 판정: 대기 중')
        self.verdict_counts = dict.fromkeys(('perfect', 'early', 'late', 'miss'), 0)
        self.state = tk.StringVar(value='요리 화면을 열고 화면을 잡아주세요. 기본은 감지만 하는 모드입니다.')
        self.stats = tk.StringVar(value='대기 중')

        top = ttk.Frame(root, padding=12)
        top.pack(fill='x')
        ttk.Label(top, text='요리 타이밍 도우미', font=('맑은 고딕', 18, 'bold')).pack(anchor='w')
        ttk.Label(top, text='썰기는 재료 이동, 굽기는 넣기·꺼내기 테두리를 자동 감지합니다.  F8 시작/정지 · F9 즉시 정지').pack(anchor='w', pady=(3, 8))
        row = ttk.Frame(top)
        row.pack(fill='x')
        self.capture_button = ttk.Button(row, text='① 화면 잡기 (3초 후)', command=self.prepare_capture)
        self.capture_button.pack(side='left')
        ttk.Button(row, text='② 도마 직접 지정', command=lambda: self.set_mode('board')).pack(side='left', padx=6)
        ttk.Button(row, text='③ 판정선 지정', command=lambda: self.set_mode('target')).pack(side='left')
        ttk.Button(row, text='판정선 기본값', command=self.default_target).pack(side='left', padx=6)
        options = ttk.Frame(top)
        options.pack(fill='x', pady=10)
        ttk.Checkbutton(options, text='감지만 하기 (Space 입력 없음)', variable=self.dry).pack(side='left')
        ttk.Label(options, text='타이밍 보정 ms (+는 일찍 / −는 늦게)').pack(side='left', padx=(22, 6))
        ttk.Spinbox(options, textvariable=self.bias, from_=-100, to=100, width=7, increment=5).pack(side='left')
        ttk.Button(options, text='시작 / 정지 (F8)', command=self.toggle).pack(side='right')
        phase_row = ttk.Frame(top)
        phase_row.pack(fill='x', pady=(0, 5))
        ttk.Label(phase_row, text='개별 보정 ms (+는 일찍):').pack(side='left', padx=(0, 8))
        for name, label in [('chop', '썰기'), ('insert', '굽기 넣기'), ('remove', '굽기 꺼내기')]:
            ttk.Label(phase_row, text=label).pack(side='left', padx=(8, 3))
            ttk.Spinbox(phase_row, textvariable=self.phase_bias[name], from_=-100, to=100,
                        width=5, increment=5).pack(side='left')
        ttk.Checkbutton(phase_row, text='게임 판정으로 자동 보정', variable=self.auto_tune).pack(side='left', padx=12)
        ttk.Label(top, textvariable=self.state, wraplength=990, foreground='#175f44').pack(anchor='w', pady=4)
        ttk.Label(top, textvariable=self.stats).pack(anchor='w')
        ttk.Label(top, textvariable=self.verdict_stats, foreground='#175f44').pack(anchor='w')

        self.canvas = tk.Canvas(root, background='#20252b', highlightthickness=0, height=340)
        self.canvas.pack(fill='both', expand=True, padx=12)
        self.canvas.bind('<Configure>', lambda _: self.render())
        self.canvas.bind('<ButtonPress-1>', self.mouse_down)
        self.canvas.bind('<B1-Motion>', self.mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.mouse_up)
        self.log = tk.Text(root, height=5, state='disabled', font=('맑은 고딕', 9))
        self.log.pack(fill='x', padx=12, pady=8)
        ttk.Label(root, text='썰기·굽기를 자동 구분합니다. F11 전환과 미니게임 종료 후에도 대기하며 다음 판에서 이어집니다. F9 또는 F8로 정지하세요.',
                  wraplength=800).pack(anchor='w', padx=12, pady=(0, 10))
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(30, self.pump)

    def add_log(self, message):
        self.log.configure(state='normal')
        self.log.insert('end', time.strftime('%H:%M:%S')+'  '+message+'\n')
        if int(self.log.index('end-1c').split('.')[0]) > 150:
            self.log.delete('1.0', '30.0')
        self.log.see('end')
        self.log.configure(state='disabled')

    def running(self):
        return self.worker is not None and self.worker.is_alive()

    def stop(self):
        self.stop_event.set()
        self.state.set('정지됨 · F8로 다시 시작할 수 있습니다.')

    def prepare_capture(self):
        self.stop()
        self.capture_button.configure(state='disabled')
        self.state.set('3초 안에 마인크래프트의 썰기 또는 굽기 화면을 클릭하세요.')
        self.root.after(3000, self.capture)

    def capture(self):
        self.capture_button.configure(state='normal')
        hwnd = win.user32.GetForegroundWindow()
        if not win.foreground_is(hwnd):
            self.state.set('캡처 취소: 마인크래프트 창이 활성 상태여야 합니다. 화면 잡기를 다시 누르세요.')
            return
        try:
            x, y, w, h = win.client_rect(hwnd)
            with ScreenCapture() as screen:
                for attempt in range(10):
                    try:
                        self.frame = screen.grab((x, y, w, h))
                        break
                    except CaptureUnavailable:
                        if attempt == 9:
                            raise
                        time.sleep(.05)
            self.hwnd, self.capture_size = hwnd, (w, h)
            is_grill = GrillSignature().matches(self.frame)
            self.board = (0, 0, w, h) if is_grill else find_board(self.frame)
            self.detected_kind = 'grill' if is_grill else ('chop' if self.board else None)
            self.target_ratio = .09
            self.mode = 'none'
            if is_grill:
                self.state.set('굽기 미니게임을 찾았습니다. 판정선 지정 없이 넣기·꺼내기 테두리를 자동 추적합니다.')
                self.add_log('굽기 화면 감지 · F8로 시작할 수 있습니다.')
            elif self.board:
                self.state.set('도마를 찾았습니다. 빨간 판정선을 칼이 내려오는 위치에 맞추고, 감지 모드로 확인하세요.')
                self.add_log(f'도마 자동 감지: {self.board}. 필요하면 직접 지정할 수 있습니다.')
            else:
                self.state.set('도마 자동 감지 실패. ② 도마 직접 지정을 눌러 도마 사각형만 드래그하세요.')
            self.render()
        except Exception as exc:
            self.state.set(f'화면 잡기 실패: {exc}')

    def set_mode(self, mode):
        self.stop()
        if self.frame is None:
            self.state.set('먼저 ① 화면 잡기를 사용하세요.')
            return
        if self.detected_kind == 'grill':
            self.state.set('굽기는 도마나 판정선을 지정하지 않습니다. 넣기·꺼내기 테두리를 자동 감지합니다.')
            return
        if mode == 'target' and not self.board:
            self.state.set('먼저 도마 영역을 지정하세요.')
            return
        self.mode = mode
        self.state.set('미리보기에서 도마의 왼쪽 위부터 오른쪽 아래까지 드래그하세요.' if mode == 'board'
                       else '미리보기에서 칼이 내려오는 고정 위치를 클릭하세요. 재료가 아닌 칼 위치입니다.')

    def default_target(self):
        self.stop()
        self.target_ratio = .09
        self.render()

    def to_frame(self, event):
        ox, oy = self.image_origin
        x = (event.x-ox)/self.scale
        y = (event.y-oy)/self.scale
        return (min(max(0, x), self.frame.shape[1]-1),
                min(max(0, y), self.frame.shape[0]-1))

    def mouse_down(self, event):
        if self.frame is None:
            return
        if self.mode == 'board':
            self.drag = self.to_frame(event)
        elif self.mode == 'target' and self.board:
            x, _ = self.to_frame(event)
            bx, by, bw, bh = self.board
            if not bx <= x <= bx+bw:
                return
            self.target_ratio = (x-bx)/bw
            self.mode = 'none'
            self.state.set('판정선 지정 완료. F8로 감지를 시작하고 게임 창을 클릭하세요.')
            self.render()

    def mouse_drag(self, event):
        if self.drag is not None:
            self.render()
            x0, y0 = self.drag
            x1, y1 = self.to_frame(event)
            ox, oy = self.image_origin
            self.canvas.create_rectangle(ox+x0*self.scale, oy+y0*self.scale,
                                         ox+x1*self.scale, oy+y1*self.scale,
                                         outline='#44e7c0', width=2)

    def mouse_up(self, event):
        if self.drag is None:
            return
        x0, y0 = self.drag
        x1, y1 = self.to_frame(event)
        self.drag = None
        if abs(x1-x0) >= 100 and abs(y1-y0) >= 40:
            self.board = (round(min(x0, x1)), round(min(y0, y1)),
                          round(abs(x1-x0)), round(abs(y1-y0)))
            self.detected_kind = 'chop'
            self.mode = 'none'
            self.state.set('도마 지정 완료. ③ 판정선 지정을 눌러 칼 위치를 맞추세요.')
        self.render()

    def render(self):
        self.canvas.delete('all')
        cw, ch = max(self.canvas.winfo_width(), 1), max(self.canvas.winfo_height(), 1)
        if self.frame is None:
            self.canvas.create_text(cw/2, ch/2, text='화면을 잡으면 이곳에 도마와 판정선이 표시됩니다.',
                                    fill='#dce4ec', font=('맑은 고딕', 13))
            return
        h, w = self.frame.shape[:2]
        self.scale = min(cw/w, ch/h)
        dw, dh = max(1, round(w*self.scale)), max(1, round(h*self.scale))
        self.image_origin = ((cw-dw)/2, (ch-dh)/2)
        rgb = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        self.preview_photo = ImageTk.PhotoImage(Image.fromarray(rgb).resize((dw, dh)))
        ox, oy = self.image_origin
        self.canvas.create_image(ox, oy, anchor='nw', image=self.preview_photo)
        if self.board:
            x, y, bw, bh = self.board
            self.canvas.create_rectangle(ox+x*self.scale, oy+y*self.scale,
                                         ox+(x+bw)*self.scale, oy+(y+bh)*self.scale,
                                         outline='#44e7c0', width=2)
            if self.detected_kind != 'grill':
                tx = ox+(x+bw*self.target_ratio)*self.scale
                self.canvas.create_line(tx, oy+y*self.scale, tx, oy+(y+bh)*self.scale,
                                        fill='#ff5252', width=2)
                self.canvas.create_text(tx+4, oy+y*self.scale-10, anchor='w', text='판정선',
                                        fill='#ff5252', font=('맑은 고딕', 10, 'bold'))

    def toggle(self):
        if self.running():
            self.stop()
            return
        if not self.hwnd or not win.user32.IsWindow(self.hwnd):
            current = win.user32.GetForegroundWindow()
            candidates = win.minecraft_windows()
            self.hwnd = current if win.foreground_is(current) else (candidates[0][0] if len(candidates) == 1 else None)
            if not self.hwnd:
                self.state.set('마인크래프트를 켜고 게임 화면에서 F8을 누르세요. 또는 화면 잡기를 사용하세요.')
                return
            _, _, w, h = win.client_rect(self.hwnd)
            self.capture_size = (w, h)
            self.board = None
            self.detected_kind = None
        try:
            bias = float(self.bias.get())
            offsets = {name: float(value.get())/1000 for name, value in self.phase_bias.items()}
            if not -100 <= bias <= 100 or any(not -.1 <= value <= .1 for value in offsets.values()):
                raise ValueError
        except ValueError:
            self.state.set('타이밍 보정은 -100~100ms 숫자로 입력하세요.')
            return
        self.stop_event = threading.Event()
        # A full-frame oven capture is not a cutting-board calibration.
        calibrated_board = self.board if self.detected_kind == 'chop' else None
        args = (self.hwnd, self.capture_size, calibrated_board, self.target_ratio,
                self.dry.get(), bias/1000, self.stop_event, offsets, self.auto_tune.get())
        self.worker = threading.Thread(target=self.run_loop, args=args, daemon=True)
        self.worker.start()
        self.add_log('시작: '+('감지만 하기' if self.dry.get() else 'Space 자동 입력')+f' / 보정 {bias:+g}ms')
        self.state.set('연속 대기 켜짐 · 미니게임을 열면 작동하고 끝나면 다음 판을 기다립니다. F9로 정지합니다.')

    def run_loop(self, hwnd, size, board, target_ratio, dry, bias, stop_event, offsets=None, auto_tune=True):
        session = GameSession(size, board, target_ratio, auto_tune=auto_tune)
        bound_pid = win.process_id(hwnd)
        count = 0
        last_stats = last_frame = time.perf_counter()
        interval = 1/120
        frames = 0
        was_focused = False
        last_search = last_problem = -100.
        was_active = False
        last_token = None
        last_good_frame = [time.perf_counter()]
        input_errors = deque(maxlen=120)
        frame_ages = deque(maxlen=120)
        offsets = offsets or {}
        sent_outcomes = queue.Queue()

        def guard():
            if win.key_down(0x78):
                stop_event.set()
                return False
            return not stop_event.is_set() and win.foreground_is(hwnd)

        def fire(plan):
            if dry:
                return time.perf_counter()
            stamp = []
            sent = win.tap_space(hwnd, duration=.020 if plan.get('kind') == 'burst' else .010,
                                 on_down=stamp.append)
            return stamp[0] if sent and stamp else None

        def completed(plan, actual, status):
            nonlocal count
            if actual is None:
                now = time.perf_counter()
                age = (now-plan.get('observed', now))*1000
                validation_age = (now-plan.get('validated', plan.get('observed', now)))*1000
                label = (f'다다닥 {plan["step"]}/{plan["required"]}' if plan.get('kind') == 'burst'
                         else f'굽기 {plan["action"]}' if 'action' in plan else '썰기')
                self.events.put(('hit', f'입력 생략 · {status} · {label} · '
                                       f'테두리/재료 {age:.0f}ms · 확인 {validation_age:.0f}ms'))
                return
            count += 1
            if not dry:
                sent_outcomes.put((plan.get('context'), dict(plan), actual))
            error = (actual-plan['deadline'])*1000
            input_errors.append(abs(error))
            detail = (f'다다닥 {plan["step"]}/{plan["required"]}' if plan.get('kind') == 'burst'
                      else f'굽기 {plan["action"]}' if 'action' in plan else '썰기')
            recovery = ' · 테두리 소실 보완' if plan.get('coasting') else ''
            self.events.put(('hit', f'{"감지" if dry else "Space"} #{count} · {detail} · 예약 오차 {error:+.2f}ms{recovery}'))
        try:
            with ScreenCapture() as screen, InputScheduler(stop_event, fire, guard, completed) as scheduler:
                while not stop_event.is_set():
                    loop_start = time.perf_counter()
                    # This worker-level check remains responsive while Tk is busy.
                    if win.key_down(0x78):  # F9 only; Esc belongs to Minecraft.
                        stop_event.set()
                        break
                    focused = win.focused_game(hwnd, bound_pid)
                    if not focused:
                        scheduler.set_context(None)
                        if was_focused:
                            session.reset_tracking()
                            screen.reset()
                        was_focused = False
                        self.events.put(('stats', f'게임 창 활성화 대기 · 누적 감지 {count}회'))
                        stop_event.wait(.08)
                        continue
                    if focused != hwnd:
                        scheduler.set_context(None)
                        hwnd = focused
                        screen.reset()
                        session.reset_tracking()
                        last_search = -100.
                    was_focused = True
                    try:
                        wx, wy, ww, wh = win.client_rect(hwnd)
                        if ww < 100 or wh < 100:
                            raise CaptureUnavailable('게임 화면 전환 대기')
                        if session.update_size((ww, wh)):
                            scheduler.set_context(None)
                            screen.reset()
                            last_search = -100.
                            self.events.put(('hit', f'화면 크기 변경 {ww}×{wh} · 미니게임 자동 탐색'))
                        search_interval = .8 if session.active else .3
                        if loop_start-last_search >= search_interval and not scheduler.soon(.25):
                            full = screen.grab((wx, wy, ww, wh))
                            old_engine = session.engine
                            if session.relocate(full):
                                if session.engine is not old_engine:
                                    self.events.put(('preview', (full.copy(), session.board, (ww, wh), hwnd, session.kind)))
                            last_search = loop_start
                        if session.board is None:
                            self.events.put(('stats', f'연속 대기 · 썰기/굽기 화면 탐색 중 · 누적 {count}회'))
                            stop_event.wait(.04)
                            continue
                        bx, by, bw, bh = session.board
                        before = time.perf_counter()
                        pixels = screen.grab((wx+bx, wy+by, bw, bh))
                    except (CaptureUnavailable, OSError, ValueError) as exc:
                        scheduler.set_context(None)
                        session.reset_tracking()
                        screen.reset()
                        if loop_start-last_problem > 2:
                            self.events.put(('stats', f'연속 대기 · 화면 복구 중: {exc}'))
                            last_problem = loop_start
                        stop_event.wait(.2)
                        continue
                    after = time.perf_counter()
                    timestamp = getattr(screen, 'frame_time', 0.) or (before+after)/2
                    token = (session.engine, getattr(screen, 'frame_token', None) or timestamp)
                    if token == last_token:
                        stop_event.wait(.001)
                        continue
                    last_token = token
                    age = after-timestamp
                    if age > .15 or age < -.01:
                        # Stable grill forecasts can bridge a bounded render
                        # freeze. The scheduler still checks focus, stop, the
                        # forecast's confidence window and its expiry.
                        if session.kind != 'grill' or not session.active or age > .65 or age < -.01:
                            scheduler.set_context(None)
                        stop_event.wait(.002)
                        continue
                    last_good_frame[0] = after
                    frame_ages.append(max(0., age*1000))
                    interval = interval*.8 + min(.1, timestamp-last_frame)*.2
                    last_frame = timestamp
                    # Estimate processing/capture delay and half a polling interval.
                    while True:
                        try:
                            owner, sent_plan, sent_at = sent_outcomes.get_nowait()
                        except queue.Empty:
                            break
                        if owner is session.engine and hasattr(owner, 'record_input'):
                            owner.record_input(sent_plan, sent_at)
                    events, ingredients = session.process(pixels, timestamp, 0., input_time=time.perf_counter())
                    scheduler.set_context(session.engine if session.active else None)
                    if session.kind == 'chop':
                        scheduler.cancel(session.engine.cancelled_ids)
                        scheduler.reconcile((p['id'] for p in session.plans if p.get('kind') == 'burst'),
                                            kind='burst')
                    for verdict in session.feedback_updates:
                        self.events.put(('verdict', verdict))
                    if was_active and not session.active:
                        self.events.put(('hit', '미니게임 종료/화면 전환 · 다음 판 자동 대기'))
                    if session.active and not was_active:
                        name = '굽기' if session.kind == 'grill' else '썰기'
                        self.events.put(('hit', f'{name} 미니게임 감지 · 자동 재개'))
                    was_active = session.active
                    for plan in session.plans:
                        phase = ('insert' if plan.get('action') == '넣기' else 'remove') if 'action' in plan else 'chop'
                        # Mash timing starts at the visible window, not at a
                        # moving note's target. Normal timing offsets do not apply.
                        adjusted = (plan if plan.get('kind') == 'burst' else
                                    dict(plan, deadline=plan['deadline']-bias-offsets.get(phase, 0.)))
                        scheduler.submit(adjusted)
                    if session.kind == 'grill':
                        scheduler.reconcile(plan['id'] for plan in session.plans)
                    frames += 1
                    now = time.perf_counter()
                    if now-last_stats > .35:
                        name = '굽기' if session.kind == 'grill' else '썰기'
                        state = f'{name} 작동 중' if session.active else '다음 미니게임 대기'
                        error_ms = sorted(input_errors)[round((len(input_errors)-1)*.95)] if input_errors else 0.
                        capture_ms = sum(frame_ages)/len(frame_ages) if frame_ages else 0.
                        self.events.put(('stats', f'{"감지 전용" if dry else "자동 입력"} · {state} · '
                                                 f'{frames/(now-last_stats):.0f}fps · '
                                                 f'누적 {count}회 · 화면 지연 {capture_ms:.1f}ms · 예약 오차95% {error_ms:.2f}ms'))
                        frames, last_stats = 0, now
                    stop_event.wait(max(0, 1/120-(time.perf_counter()-loop_start)))
        except Exception as exc:
            self.events.put(('error', f'중지: {exc}'))
        finally:
            stop_event.set()
            self.events.put(('stopped', None))

    def pump(self):
        for vk in (0x77, 0x78):  # F8 / F9
            pressed = win.key_down(vk)
            if pressed and not self.key_states.get(vk, False):
                self.toggle() if vk == 0x77 else self.stop()
            self.key_states[vk] = pressed
        for _ in range(80):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'stats':
                self.stats.set(value)
            elif kind == 'hit':
                self.add_log(value)
            elif kind == 'preview':
                self.frame, self.board, self.capture_size, self.hwnd, self.detected_kind = value
                self.render()
            elif kind == 'verdict':
                names = {'perfect': '정확', 'early': '빠름', 'late': '느림', 'miss': '놓침'}
                verdict = value['verdict']
                self.verdict_counts[verdict] += 1
                self.verdict_stats.set('실제 게임 판정: '+ ' · '.join(
                    f'{names[name]} {count}' for name, count in self.verdict_counts.items()))
                detail = ''
                if value.get('updated'):
                    phase = '넣기' if value['phase'] == 'insert' else '꺼내기'
                    detail = f' · {phase} 자동 지연 {value["delay_ms"]:+.0f}ms'
                self.add_log(f'게임 판정 {names[verdict]}{detail}')
            elif kind == 'error':
                self.state.set(value)
                self.add_log(value)
            elif kind == 'stopped':
                self.add_log('작동 종료')
        self.root.after(30, self.pump)

    def close(self):
        self.stop_event.set()
        if self.worker:
            self.worker.join(timeout=.7)
        self.root.destroy()


def main():
    if '--burst-self-test' in sys.argv:
        import json
        from verify_burst import self_test_report
        report = self_test_report()
        Path(sys.argv[sys.argv.index('--burst-self-test')+1]).write_text(
            json.dumps(report, indent=2), encoding='utf-8')
        return 0 if report['passed'] else 2
    if '--judgement-self-test' in sys.argv:
        import json
        from verify_verdicts import self_test_report
        report = self_test_report()
        Path(sys.argv[sys.argv.index('--judgement-self-test')+1]).write_text(json.dumps(report, indent=2), encoding='utf-8')
        return 0 if report['insert_delay_ms'] == 12 and report['remove_delay_ms'] == -12 else 2
    if '--grill-recovery-self-test' in sys.argv:
        import json
        from verify_grill_recovery import recovery_summary
        report = recovery_summary()
        Path(sys.argv[sys.argv.index('--grill-recovery-self-test')+1]).write_text(
            json.dumps(report, indent=2), encoding='utf-8')
        return 0 if all(case['v5_rejection'] is None for case in report['cases']) else 2
    if '--timing-self-test' in sys.argv:
        import json
        import io
        import unittest
        from verify_timing import scheduler_benchmark, tracking_stress, TimingTests
        regressions = unittest.TestSuite(TimingTests(name) for name in (
            'test_scheduler_deduplicates_updates_during_key_hold',
            'test_inflight_old_round_does_not_complete_new_round_identity'))
        result = unittest.TextTestRunner(stream=io.StringIO()).run(regressions)
        report = {'tracking': tracking_stress(), 'mock_scheduler': scheduler_benchmark(),
                  'scheduler_regressions': {'passed': result.wasSuccessful(),
                                            'tests': result.testsRun},
                  'note': 'No real key events sent. Not game judgement accuracy.'}
        Path(sys.argv[sys.argv.index('--timing-self-test')+1]).write_text(
            json.dumps(report, indent=2), encoding='utf-8')
        return 0 if report['tracking']['missed'] == 0 and result.wasSuccessful() else 2
    if '--capture-self-test' in sys.argv:
        from screen_capture import capture_self_test
        return capture_self_test(sys.argv[sys.argv.index('--capture-self-test')+1])
    root = tk.Tk()
    cv2.setNumThreads(1)
    ttk.Style(root).theme_use('vista')
    app = App(root)
    if '--smoke-test' in sys.argv:
        GrillSignature()  # Also verify the bundled oven-recognition asset.
        root.after(350, app.close)
    root.mainloop()


if __name__ == '__main__':
    try:
        raise SystemExit(main() or 0)
    except Exception:
        error = traceback.format_exc()
        location = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'CookingTimingHelper'
        location.mkdir(exist_ok=True)
        (location/'error.log').write_text(error, encoding='utf-8')
        messagebox.showerror('실행 오류', f'오류 기록: {location / "error.log"}\n\n{error[-1200:]}')
        raise
