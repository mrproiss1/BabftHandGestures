"""
Roblox Build A Boat Hand Gesture Controller (BABFT)
===================================================
A real-time computer vision controller for Roblox: Build A Boat For Treasure (BABFT).
Tracks hand positions and gestures via webcam using MediaPipe and sends DirectInput hardware
scancodes directly to Roblox.

Gesture Mappings:
  - Point FORWARD (Index into camera)   -> Move Forward (W)
  - Point UP      (Index pointing up)   -> Jump / Throttle Up (Space / G)
  - Point RIGHT   (Index pointing right)-> Steer Right (D / L)
  - Point LEFT    (Index pointing left) -> Steer Left (A / K)
  - Point DOWN    (Index pointing down) -> Reverse / Brake (S / T)
  - PINCH / SNAP  (Thumb + Index touch) -> Action / Left Click / Fire Cannon (Z,B,V,C,X,N)
  - Neutral / Hand Open                -> Release movement keys
"""

import os
import sys
import time
import math
import json
import atexit
import ctypes
import threading
import subprocess
from ctypes import wintypes
from typing import Dict, List, Tuple, Optional

# --- REQUIRED PACKAGES AUTO-CHECK ---
REQUIRED_PACKAGES = [
    ('opencv-python', 'cv2'),
    ('mediapipe', 'mediapipe'),
    ('keyboard', 'keyboard'),
    ('pygrabber', 'pygrabber'),
]

def ensure_dependencies():
    missing = []
    for pkg, imp in REQUIRED_PACKAGES:
        try:
            __import__(imp)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installing missing packages: {missing}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--disable-pip-version-check"] + missing)
        except Exception as e:
            print(f"Failed to install packages: {e}")

ensure_dependencies()

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

try:
    from pygrabber.dshow_graph import FilterGraph
    HAS_PYGRABBER = True
except Exception:
    HAS_PYGRABBER = False

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# --- DIRECTINPUT SCANCODES & HARDWARE INPUT (ROBLOX COMPATIBILITY) ---
user32 = ctypes.windll.user32

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]
    _anonymous_ = ("i",)
    _fields_ = [("type", wintypes.DWORD), ("i", _I)]

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

# DirectInput hardware scancodes
SCANCODE_MAP = {
    'w': 0x11,
    'a': 0x1E,
    's': 0x1F,
    'd': 0x20,
    'space': 0x39,
    'f': 0x21,
    'g': 0x22,
    't': 0x14,
    'k': 0x25,
    'l': 0x26,
    'z': 0x2C,
    'b': 0x30,
    'v': 0x2F,
    'c': 0x2E,
    'x': 0x2D,
    'n': 0x31,
}

def send_scancode(key_name: str, is_up: bool = False):
    sc = SCANCODE_MAP.get(key_name.lower())
    if sc is None:
        try:
            vk = user32.VkKeyScanW(ord(key_name[0])) & 0xFF
            sc = user32.MapVirtualKeyW(vk, 0)
        except Exception:
            return

    inp = INPUT()
    inp.type = 1  # INPUT_KEYBOARD
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if is_up else 0)
    inp.ki.wVk = 0
    inp.ki.wScan = int(sc)
    inp.ki.dwFlags = int(flags)
    inp.ki.time = 0
    inp.ki.dwExtraInfo = None
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def send_mouse_click():
    """Sends Left Mouse Down followed by Left Mouse Up in background."""
    def _click():
        inp_down = INPUT()
        inp_down.type = 0  # INPUT_MOUSE
        inp_down.mi.dwFlags = MOUSEEVENTF_LEFTDOWN
        user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))

        time.sleep(0.05)

        inp_up = INPUT()
        inp_up.type = 0
        inp_up.mi.dwFlags = MOUSEEVENTF_LEFTUP
        user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))

    threading.Thread(target=_click, daemon=True).start()

# --- KEY STATE DISPATCHER ---
CURRENTLY_HELD_KEYS: Dict[str, bool] = {}
PENDING_AUTO_RELEASES: List[Tuple[str, float]] = []

def press_key(key: str):
    global CURRENTLY_HELD_KEYS
    key = key.lower()
    if not CURRENTLY_HELD_KEYS.get(key, False):
        if HAS_KEYBOARD:
            try:
                keyboard.press(key)
            except Exception:
                pass
        try:
            send_scancode(key, is_up=False)
        except Exception:
            pass
        CURRENTLY_HELD_KEYS[key] = True

def release_key(key: str):
    global CURRENTLY_HELD_KEYS
    key = key.lower()
    if CURRENTLY_HELD_KEYS.get(key, False):
        if HAS_KEYBOARD:
            try:
                keyboard.release(key)
            except Exception:
                pass
        try:
            send_scancode(key, is_up=True)
        except Exception:
            pass
        CURRENTLY_HELD_KEYS[key] = False

def tap_key(key: str, hold_duration: float = 0.08):
    global PENDING_AUTO_RELEASES
    press_key(key)
    PENDING_AUTO_RELEASES.append((key, time.time() + hold_duration))

def release_all_keys():
    global CURRENTLY_HELD_KEYS, PENDING_AUTO_RELEASES
    for k in list(CURRENTLY_HELD_KEYS.keys()):
        if CURRENTLY_HELD_KEYS[k]:
            release_key(k)
    for k, _ in PENDING_AUTO_RELEASES:
        release_key(k)
    PENDING_AUTO_RELEASES.clear()

atexit.register(release_all_keys)

def process_pending_releases():
    global PENDING_AUTO_RELEASES
    now = time.time()
    remaining = []
    for k, expire in PENDING_AUTO_RELEASES:
        if now >= expire:
            release_key(k)
        else:
            remaining.append((k, expire))
    PENDING_AUTO_RELEASES = remaining


# --- CAMERA DISCOVERY ---
def get_available_cameras() -> List[Tuple[int, str]]:
    cameras = []
    if HAS_PYGRABBER:
        try:
            graph = FilterGraph()
            devices = graph.get_input_devices()
            for idx, name in enumerate(devices):
                clean = "".join(c for c in name if 32 <= ord(c) < 127).strip()
                cameras.append((idx, clean or f"Camera {idx}"))
            if cameras:
                return cameras
        except Exception:
            pass

    backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
    for idx in range(4):
        cap = cv2.VideoCapture(idx, backend)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            if ret:
                cameras.append((idx, f"Camera {idx}"))
    if not cameras:
        cameras.append((0, "Default Camera"))
    return cameras


# --- CANNON MANAGER (GUNNER MODE) ---
CANNON_KEYS = ['z', 'b', 'v', 'c', 'x', 'n']
CANNON_COOLDOWN = 10.0

class CannonManager:
    def __init__(self):
        self.keys = CANNON_KEYS
        self.cooldown = CANNON_COOLDOWN
        self.last_fired: Dict[str, float] = {k: -CANNON_COOLDOWN for k in CANNON_KEYS}

    def get_cooldown_left(self, key: str, now: float) -> float:
        return max(0.0, self.cooldown - (now - self.last_fired[key]))

    def fire_next_ready(self, now: float) -> Optional[str]:
        for k in self.keys:
            if self.get_cooldown_left(k, now) <= 0.0:
                self.last_fired[k] = now
                tap_key(k, hold_duration=0.08)
                if HAS_WINSOUND:
                    threading.Thread(target=lambda: winsound.Beep(920, 50), daemon=True).start()
                return k
        return None

    def reset(self):
        for k in self.keys:
            self.last_fired[k] = -self.cooldown


# --- PATH RESOLUTION & CONFIG ---
def get_resource_path(relative_path: str) -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(current_dir, relative_path)
    if os.path.exists(p):
        return p
    # Fallback search parent folders
    p2 = os.path.join(current_dir, "..", "HandGunBabft", relative_path)
    if os.path.exists(p2):
        return os.path.abspath(p2)
    return p

CONFIG_FILE = get_resource_path("config.json")
MODEL_FILE = get_resource_path("hand_landmarker.task")

DEFAULT_CONFIG = {
    "mode": "boat",                       # "boat" (WASD + Space) or "gunner" (F, G, T, K, L + Cannons)
    "selected_camera_name": "USB2.0 PC CAMERA",
    "selected_camera_index": 1,
    "tracked_hand": "both",               # "both", "right", "left"
    "sensitivity_x": 0.12,
    "sensitivity_y": 0.12,
    "sensitivity_z": 0.08,
    "pinch_threshold": 0.45,
    "always_on_top": True,
    "show_gesture_guide": True,
    "click_hold_seconds": 0.06
}

def load_config() -> dict:
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            print(f"Config load error: {e}")
    return cfg

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Config save error: {e}")


# --- GEOMETRY HELPERS ---
def dist2d(p1, p2) -> float:
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def dist3d(p1, p2) -> float:
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)


# --- MAIN CONTROLLER APPLICATION ---
class BabftHandController:
    def __init__(self):
        self.config = load_config()
        self.mode = self.config.get("mode", "boat")
        self.tracked_hand = self.config.get("tracked_hand", "both")
        self.always_on_top = bool(self.config.get("always_on_top", True))
        self.show_gesture_guide = bool(self.config.get("show_gesture_guide", True))

        self.sensitivity_x = float(self.config.get("sensitivity_x", 0.12))
        self.sensitivity_y = float(self.config.get("sensitivity_y", 0.12))
        self.sensitivity_z = float(self.config.get("sensitivity_z", 0.08))
        self.pinch_threshold = float(self.config.get("pinch_threshold", 0.45))

        # Camera setup
        self.camera_list = get_available_cameras()
        self.active_cam_idx = self._select_initial_camera()
        self.cap = None

        # Cannons manager
        self.cannons = CannonManager()

        # State tracking
        self.current_gesture = "NEUTRAL"
        self.active_keys: List[str] = []
        self.last_action_time = 0.0
        self.action_debounce = 0.35
        self.last_status_msg = "Ready. Show hand in view."
        self.status_msg_time = 0.0

        # UI state
        self.show_cam_dropdown = False
        self.cam_dropdown_rects: List[Tuple[int, Tuple[int, int, int, int]]] = []
        self.ui_buttons: Dict[str, Tuple[int, int, int, int]] = {}
        self.window_name = "BABFT Hand Gesture Controller"

        # MediaPipe Detector
        if not os.path.exists(MODEL_FILE):
            print(f"Error: Model file {MODEL_FILE} not found!")
            sys.exit(1)

        base_opts = python.BaseOptions(model_asset_path=MODEL_FILE)
        opts = vision.HandLandmarkerOptions(
            base_options=base_opts,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.55,
            min_hand_presence_confidence=0.55,
            min_tracking_confidence=0.55
        )
        self.detector = vision.HandLandmarker.create_from_options(opts)

    def _select_initial_camera(self) -> int:
        saved_name = self.config.get("selected_camera_name", "")
        saved_idx = self.config.get("selected_camera_index", 1)

        for idx, name in self.camera_list:
            if saved_name and (saved_name.lower() in name.lower() or name.lower() in saved_name.lower()):
                return idx
        for idx, _ in self.camera_list:
            if idx == saved_idx:
                return idx
        for idx, name in self.camera_list:
            if "usb" in name.lower() or "hd" in name.lower():
                return idx
        return self.camera_list[0][0] if self.camera_list else 0

    def start_camera(self, index: int) -> bool:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        print(f"Opening camera [{index}]...")
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(index)

        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.active_cam_idx = index
            name = dict(self.camera_list).get(index, f"Camera {index}")
            self.config["selected_camera_index"] = index
            self.config["selected_camera_name"] = name
            save_config(self.config)
            print(f"Connected to camera: [{index}] {name}")
            return True
        print(f"Could not open camera [{index}]")
        return False

    def apply_always_on_top(self):
        try:
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1 if self.always_on_top else 0)
            hwnd = user32.FindWindowW(None, self.window_name)
            if hwnd:
                HWND_TOPMOST = -1 if self.always_on_top else -2
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
        except Exception as e:
            print(f"Always-on-top error: {e}")

    def on_mouse(self, event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        # Handle camera dropdown selection
        if self.show_cam_dropdown:
            for cam_idx, (rx, ry, rw, rh) in self.cam_dropdown_rects:
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    self.start_camera(cam_idx)
                    self.show_cam_dropdown = False
                    return
            self.show_cam_dropdown = False
            return

        # Check button clicks
        for btn_id, (bx, by, bw, bh) in self.ui_buttons.items():
            if bx <= x <= bx + bw and by <= y <= by + bh:
                if btn_id == "mode":
                    self.mode = "gunner" if self.mode == "boat" else "boat"
                    self.config["mode"] = self.mode
                    save_config(self.config)
                    release_all_keys()
                    self.set_status(f"Mode switched to: {self.mode.upper()}")
                elif btn_id == "cam":
                    self.camera_list = get_available_cameras()
                    self.show_cam_dropdown = not self.show_cam_dropdown
                elif btn_id == "guide":
                    self.show_gesture_guide = not self.show_gesture_guide
                    self.config["show_gesture_guide"] = self.show_gesture_guide
                    save_config(self.config)
                elif btn_id == "topmost":
                    self.always_on_top = not self.always_on_top
                    self.config["always_on_top"] = self.always_on_top
                    save_config(self.config)
                    self.apply_always_on_top()
                    self.set_status(f"Pin On Top: {'ON' if self.always_on_top else 'OFF'}")
                elif btn_id == "hand":
                    order = ["both", "right", "left"]
                    next_idx = (order.index(self.tracked_hand) + 1) % len(order)
                    self.tracked_hand = order[next_idx]
                    self.config["tracked_hand"] = self.tracked_hand
                    save_config(self.config)
                    self.set_status(f"Tracked Hand: {self.tracked_hand.upper()}")
                break

    def set_status(self, msg: str):
        self.last_status_msg = msg
        self.status_msg_time = time.time()

    def get_tracked_hand_landmarks(self, detection_res):
        if not detection_res.hand_landmarks:
            return None, ""
        if self.tracked_hand == "both":
            handedness = detection_res.handedness[0][0].category_name.lower() if detection_res.handedness else ""
            return detection_res.hand_landmarks[0], handedness

        for idx, landmarks in enumerate(detection_res.hand_landmarks):
            handedness = detection_res.handedness[idx][0].category_name.lower() if detection_res.handedness else ""
            if handedness == self.tracked_hand:
                return landmarks, handedness
        return None, ""

    # --- CORE GESTURE CLASSIFIER ---
    def classify_gesture(self, lm, now: float) -> Tuple[str, dict]:
        """
        Classifies the hand pose into one of the 6 core BABFT gestures:
          - PINCH_ACTION: Thumb and index/middle touch (Action/Click/Cannon)
          - POINT_FORWARD: Index finger pointed directly at camera (W / Drive)
          - POINT_UP: Index finger pointing UP (Space / Jump / Pitch Up)
          - POINT_RIGHT: Index finger pointing RIGHT (D / Steer Right)
          - POINT_LEFT: Index finger pointing LEFT (A / Steer Left)
          - POINT_DOWN: Index finger pointing DOWN (S / Reverse / Pitch Down)
          - NEUTRAL: Hand open or resting
        """
        wrist = lm[0]
        thumb_tip = lm[4]
        idx_mcp = lm[5]
        idx_pip = lm[6]
        idx_dip = lm[7]
        idx_tip = lm[8]
        middle_mcp = lm[9]
        middle_tip = lm[12]

        palm_size = max(dist2d(wrist, middle_mcp), 0.001)

        # Index vector (MCP to TIP)
        idx_dx = idx_tip.x - idx_mcp.x
        idx_dy = idx_tip.y - idx_mcp.y
        idx_dz = idx_tip.z - idx_mcp.z
        idx_2d_len = math.hypot(idx_dx, idx_dy) / palm_size

        # DIP to TIP vector for curl detection
        dip_dy = idx_tip.y - idx_dip.y

        # Distances to thumb
        d_ti = dist3d(thumb_tip, idx_tip) / palm_size
        d_ti_pip = dist3d(thumb_tip, idx_pip) / palm_size
        d_tm = dist3d(thumb_tip, middle_tip) / palm_size
        min_pinch_dist = min(d_ti, d_ti_pip, d_tm)

        # 1. POINTING FORWARD INTO CAMERA (User Image 2)
        # Pointing along -Z towards camera lens with foreshortened 2D projection
        if idx_dz < -self.sensitivity_z and idx_2d_len < 0.35:
            return "POINT_FORWARD", {"dz": idx_dz, "len2d": idx_2d_len}

        # 2. PINCH / SNAP GESTURE (User Image 3)
        # Thumb touching index tip or PIP, or middle tip
        if min_pinch_dist < 0.52 and idx_2d_len < 0.50:
            return "PINCH_ACTION", {"pinch_dist": min_pinch_dist, "d_ti": d_ti}

        # 3. DIRECTIONAL POINTING (User Images 1, 4, 5 & Left/Down)
        if idx_2d_len >= 0.30 or abs(idx_dy) > 0.10 or abs(idx_dx) > 0.10:
            angle_deg = math.degrees(math.atan2(idx_dy, idx_dx))  # 0=Right, -90=Up, 180=Left, 90=Down

            if -140 <= angle_deg <= -45:
                return "POINT_UP", {"angle": angle_deg, "dy": idx_dy}
            elif -45 < angle_deg <= 45:
                return "POINT_RIGHT", {"angle": angle_deg, "dx": idx_dx}
            elif 45 < angle_deg <= 135:
                return "POINT_DOWN", {"angle": angle_deg, "dy": idx_dy}
            else:
                return "POINT_LEFT", {"angle": angle_deg, "dx": idx_dx}

        return "NEUTRAL", {}

    def execute_gesture_actions(self, gesture: str, now: float):
        """Dispatches keypresses and actions based on active mode."""
        self.current_gesture = gesture
        active = []

        if self.mode == "boat":
            # --- BOAT DRIVER MODE (WASD + SPACE + CLICK) ---
            # Forward
            if gesture == "POINT_FORWARD":
                press_key('w')
                active.append('W')
            else:
                release_key('w')

            # Jump / Space
            if gesture == "POINT_UP":
                press_key('space')
                active.append('SPACE')
            else:
                release_key('space')

            # Steer Left
            if gesture == "POINT_LEFT":
                press_key('a')
                active.append('A')
            else:
                release_key('a')

            # Steer Right
            if gesture == "POINT_RIGHT":
                press_key('d')
                active.append('D')
            else:
                release_key('d')

            # Reverse / Brake
            if gesture == "POINT_DOWN":
                press_key('s')
                active.append('S')
            else:
                release_key('s')

            # Action / Left Mouse Click on Pinch
            if gesture == "PINCH_ACTION":
                if now - self.last_action_time >= self.action_debounce:
                    send_mouse_click()
                    tap_key('f', hold_duration=0.06)
                    self.last_action_time = now
                    self.set_status("PINCH CLICK! (Left Click + F)")
                    if HAS_WINSOUND:
                        threading.Thread(target=lambda: winsound.Beep(1100, 40), daemon=True).start()
                active.append('CLICK')

        elif self.mode == "gunner":
            # --- CANNON & TURRET GUNNER MODE ---
            # Continuous F hold while aiming
            press_key('f')
            active.append('F')

            # Pitch Up
            if gesture == "POINT_UP":
                press_key('g')
                active.append('G')
            else:
                release_key('g')

            # Pitch Down
            if gesture == "POINT_DOWN":
                press_key('t')
                active.append('T')
            else:
                release_key('t')

            # Aim Left
            if gesture == "POINT_LEFT":
                press_key('k')
                active.append('K')
            else:
                release_key('k')

            # Aim Right
            if gesture == "POINT_RIGHT":
                press_key('l')
                active.append('L')
            else:
                release_key('l')

            # Cannon Fire on Pinch
            if gesture == "PINCH_ACTION":
                if now - self.last_action_time >= self.action_debounce:
                    fired = self.cannons.fire_next_ready(now)
                    self.last_action_time = now
                    if fired:
                        self.set_status(f"FIRED CANNON [{fired.upper()}]!")
                    else:
                        self.set_status("ALL CANNONS ON COOLDOWN (10s)!")
                active.append('CANNON')

        self.active_keys = active

    # --- UI DRAWING & HUD ---
    def draw_hud(self, frame: np.ndarray, landmarks, handedness: str, fps: float, now: float):
        h, w, _ = frame.shape

        # Semi-transparent top bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 55), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # 1. Mode Badge
        mode_str = f"MODE: {self.mode.upper()} [M]"
        mode_col = (0, 220, 100) if self.mode == "boat" else (0, 160, 255)
        cv2.putText(frame, mode_str, (15, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.65, mode_col, 2)
        (mw, _), _ = cv2.getTextSize(mode_str, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        self.ui_buttons["mode"] = (10, 10, mw + 10, 35)

        # 2. Camera Button
        cam_name = dict(self.camera_list).get(self.active_cam_idx, f"Cam {self.active_cam_idx}")
        if len(cam_name) > 14:
            cam_name = cam_name[:12] + ".."
        cam_btn_text = f"Cam: {cam_name}"
        (cw, _), _ = cv2.getTextSize(cam_btn_text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
        cx1 = mw + 30
        cv2.rectangle(frame, (cx1, 12), (cx1 + cw + 14, 42), (50, 50, 50), -1)
        cv2.rectangle(frame, (cx1, 12), (cx1 + cw + 14, 42), (180, 180, 180), 1)
        cv2.putText(frame, cam_btn_text, (cx1 + 7, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)
        self.ui_buttons["cam"] = (cx1, 12, cw + 14, 30)

        # 3. Tracked Hand Button
        hand_text = f"Hand: {self.tracked_hand.title()} [H]"
        (hw, _), _ = cv2.getTextSize(hand_text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
        hx1 = cx1 + cw + 22
        cv2.rectangle(frame, (hx1, 12), (hx1 + hw + 14, 42), (50, 50, 50), -1)
        cv2.rectangle(frame, (hx1, 12), (hx1 + hw + 14, 42), (180, 180, 180), 1)
        cv2.putText(frame, hand_text, (hx1 + 7, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 220, 220), 1)
        self.ui_buttons["hand"] = (hx1, 12, hw + 14, 30)

        # 4. Pin Topmost Button
        pin_text = f"Pin: {'ON' if self.always_on_top else 'OFF'} [T]"
        (pw, _), _ = cv2.getTextSize(pin_text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
        px1 = hx1 + hw + 22
        cv2.rectangle(frame, (px1, 12), (px1 + pw + 14, 42), (50, 50, 50), -1)
        cv2.rectangle(frame, (px1, 12), (px1 + pw + 14, 42), (180, 180, 180), 1)
        cv2.putText(frame, pin_text, (px1 + 7, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 100), 1)
        self.ui_buttons["topmost"] = (px1, 12, pw + 14, 30)

        # 5. Guide Toggle Button
        guide_text = "Guide [G]"
        (gw, _), _ = cv2.getTextSize(guide_text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
        gx1 = px1 + pw + 22
        cv2.rectangle(frame, (gx1, 12), (gx1 + gw + 14, 42), (50, 50, 50), -1)
        cv2.rectangle(frame, (gx1, 12), (gx1 + gw + 14, 42), (180, 180, 180), 1)
        cv2.putText(frame, guide_text, (gx1 + 7, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 255), 1)
        self.ui_buttons["guide"] = (gx1, 12, gw + 14, 30)

        # FPS counter (right-aligned)
        fps_text = f"{int(fps)} FPS"
        cv2.putText(frame, fps_text, (w - 75, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1)

        # --- SKELETON RENDERING ---
        if landmarks:
            HAND_BONES = [
                (0, 1), (1, 2), (2, 3), (3, 4),
                (0, 5), (5, 6), (6, 7), (7, 8),
                (5, 9), (9, 10), (10, 11), (11, 12),
                (9, 13), (13, 14), (14, 15), (15, 16),
                (13, 17), (17, 18), (18, 19), (19, 20),
                (0, 17)
            ]
            for p1, p2 in HAND_BONES:
                pt1 = (int(landmarks[p1].x * w), int(landmarks[p1].y * h))
                pt2 = (int(landmarks[p2].x * w), int(landmarks[p2].y * h))
                cv2.line(frame, pt1, pt2, (40, 220, 80), 2)

            for idx, p in enumerate(landmarks):
                pt = (int(p.x * w), int(p.y * h))
                if idx == 8:  # Index tip
                    cv2.circle(frame, pt, 7, (0, 255, 255), -1)
                elif idx == 4: # Thumb tip
                    cv2.circle(frame, pt, 6, (255, 180, 0), -1)
                else:
                    cv2.circle(frame, pt, 4, (0, 120, 255), -1)

            # Draw Index Aim Vector line
            idx_base = (int(landmarks[5].x * w), int(landmarks[5].y * h))
            idx_tip = (int(landmarks[8].x * w), int(landmarks[8].y * h))
            cv2.arrowedLine(frame, idx_base, idx_tip, (0, 255, 255), 2, tipLength=0.25)

        # --- ON-SCREEN GESTURE GUIDE ("make it i show the hands position") ---
        if self.show_gesture_guide:
            guide_items = [
                ("FORWARD", "Index In", "W (Drive)" if self.mode == "boat" else "Aim Lock"),
                ("UP",      "Index Up", "Space (Jump)" if self.mode == "boat" else "G (Pitch Up)"),
                ("LEFT",    "Index Left", "A (Turn L)" if self.mode == "boat" else "K (Aim Left)"),
                ("RIGHT",   "Index Right","D (Turn R)" if self.mode == "boat" else "L (Aim Right)"),
                ("DOWN",    "Index Down", "S (Reverse)" if self.mode == "boat" else "T (Pitch Down)"),
                ("PINCH",   "Thumb+Idx",  "Click / F" if self.mode == "boat" else "Cannon Shot"),
            ]

            card_w = 175
            card_h = len(guide_items) * 26 + 32
            gx = w - card_w - 12
            gy = 65

            # Guide background box
            guide_overlay = frame.copy()
            cv2.rectangle(guide_overlay, (gx, gy), (gx + card_w, gy + card_h), (15, 15, 15), -1)
            cv2.addWeighted(guide_overlay, 0.78, frame, 0.22, 0, frame)
            cv2.rectangle(frame, (gx, gy), (gx + card_w, gy + card_h), (70, 70, 70), 1)

            cv2.putText(frame, "HAND GESTURE GUIDE", (gx + 12, gy + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 240, 180), 1)

            for i, (g_key, pose_desc, key_action) in enumerate(guide_items):
                iy = gy + 38 + i * 26
                is_active = (g_key in self.current_gesture)

                # Highlight row if active
                if is_active:
                    cv2.rectangle(frame, (gx + 4, iy - 14), (gx + card_w - 4, iy + 8), (0, 180, 80), -1)
                    col = (0, 0, 0)
                else:
                    col = (220, 220, 220)

                text = f"{pose_desc:<10} -> {key_action}"
                cv2.putText(frame, text, (gx + 8, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1)

        # --- BOTTOM STATUS & ACTIVE KEY BADGES ---
        bot_overlay = frame.copy()
        cv2.rectangle(bot_overlay, (0, h - 55), (w, h), (15, 15, 15), -1)
        cv2.addWeighted(bot_overlay, 0.85, frame, 0.15, 0, frame)

        # Gesture Announcement
        g_name = self.current_gesture.replace("_", " ")
        cv2.putText(frame, f"GESTURE: {g_name}", (15, h - 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        # Status text
        status_disp = self.last_status_msg
        cv2.putText(frame, status_disp, (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1)

        # Active Keys visual badges (right side of bottom bar)
        badges = ['W', 'A', 'S', 'D', 'SPACE', 'CLICK'] if self.mode == "boat" else ['F', 'G', 'T', 'K', 'L', 'CANNON']
        bx = w - 15
        for badge in reversed(badges):
            (bw, _), _ = cv2.getTextSize(badge, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            bx -= (bw + 16)
            is_lit = (badge in self.active_keys)
            bg_col = (0, 220, 80) if is_lit else (40, 40, 40)
            txt_col = (0, 0, 0) if is_lit else (140, 140, 140)
            cv2.rectangle(frame, (bx, h - 42), (bx + bw + 10, h - 14), bg_col, -1)
            cv2.putText(frame, badge, (bx + 5, h - 23), cv2.FONT_HERSHEY_SIMPLEX, 0.42, txt_col, 1)

        # In Gunner Mode: Render Cannon Cooldowns Bar
        if self.mode == "gunner":
            cw_overlay = frame.copy()
            cv2.rectangle(cw_overlay, (0, h - 90), (w, h - 55), (20, 20, 20), -1)
            cv2.addWeighted(cw_overlay, 0.85, frame, 0.15, 0, frame)
            cv2.putText(frame, "CANNONS:", (15, h - 68), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

            cx = 105
            for k in CANNON_KEYS:
                cd = self.cannons.get_cooldown_left(k, now)
                ready = (cd <= 0.0)
                box_col = (0, 200, 80) if ready else (30, 30, 160)
                cv2.rectangle(frame, (cx, h - 85), (cx + 55, h - 62), box_col, -1)
                cv2.rectangle(frame, (cx, h - 85), (cx + 55, h - 62), (180, 180, 180), 1)
                lbl = f"[{k.upper()}] OK" if ready else f"[{k.upper()}] {cd:.1f}s"
                cv2.putText(frame, lbl, (cx + 4, h - 69), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1)
                cx += 65

        # Camera Dropdown Menu
        if self.show_cam_dropdown:
            self.cam_dropdown_rects.clear()
            dw = 220
            dh = len(self.camera_list) * 28 + 10
            dx = self.ui_buttons.get("cam", (100, 12, 100, 30))[0]
            dy = 46
            cv2.rectangle(frame, (dx, dy), (dx + dw, dy + dh), (30, 30, 30), -1)
            cv2.rectangle(frame, (dx, dy), (dx + dw, dy + dh), (200, 200, 200), 1)

            for idx, (c_idx, c_name) in enumerate(self.camera_list):
                iy = dy + 6 + idx * 28
                rect = (dx + 4, iy, dw - 8, 24)
                self.cam_dropdown_rects.append((c_idx, rect))
                is_sel = (c_idx == self.active_cam_idx)
                if is_sel:
                    cv2.rectangle(frame, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (0, 160, 60), -1)
                disp = f"[{c_idx}] {c_name[:18]}"
                cv2.putText(frame, disp, (dx + 8, iy + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1)

    # --- MAIN LOOP ---
    def run(self):
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.on_mouse)
        self.apply_always_on_top()

        if not self.start_camera(self.active_cam_idx):
            print("Failed to start initial camera. Trying camera index 0...")
            if not self.start_camera(0):
                print("No working webcam found. Exiting.")
                return

        fps = 0.0
        frame_count = 0
        fps_timer = time.time()
        last_ms = 0

        print("\n========================================================")
        print("  BABFT Hand Gesture Controller Started Successfully!")
        print("========================================================")
        print("Hotkeys:")
        print("  [M]     - Toggle Mode: Boat WASD <-> Cannon Gunner")
        print("  [H]     - Switch Tracked Hand (Both / Right / Left)")
        print("  [T]     - Toggle Always-On-Top Window")
        print("  [G]     - Toggle Gesture Guide HUD")
        print("  [C]     - Recenter / Reset Action Timers")
        print("  [Q/ESC] - Quit safely and release all keys\n")

        try:
            while self.cap.isOpened():
                success, frame = self.cap.read()
                if not success:
                    time.sleep(0.01)
                    continue

                now = time.time()
                frame_count += 1
                if now - fps_timer >= 1.0:
                    fps = frame_count / (now - fps_timer)
                    frame_count = 0
                    fps_timer = now

                # Mirror frame for intuitive selfie interaction
                frame = cv2.flip(frame, 1)

                # Process pending auto-releases (taps)
                process_pending_releases()

                # Strictly increasing millisecond timestamps for MediaPipe VIDEO mode
                cur_ms = int(now * 1000)
                if cur_ms <= last_ms:
                    cur_ms = last_ms + 1
                last_ms = cur_ms

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                det_res = self.detector.detect_for_video(mp_img, cur_ms)

                landmarks, handedness = self.get_tracked_hand_landmarks(det_res)

                if landmarks:
                    gesture, _ = self.classify_gesture(landmarks, now)
                    self.execute_gesture_actions(gesture, now)
                else:
                    self.execute_gesture_actions("NEUTRAL", now)

                # Render HUD
                self.draw_hud(frame, landmarks, handedness, fps, now)

                cv2.imshow(self.window_name, frame)
                key = cv2.waitKey(1) & 0xFF

                if key in [ord('q'), 27]: # Q or ESC
                    break
                elif key == ord('m'):
                    self.mode = "gunner" if self.mode == "boat" else "boat"
                    self.config["mode"] = self.mode
                    save_config(self.config)
                    release_all_keys()
                    self.set_status(f"Mode switched to: {self.mode.upper()}")
                elif key == ord('h'):
                    order = ["both", "right", "left"]
                    next_idx = (order.index(self.tracked_hand) + 1) % len(order)
                    self.tracked_hand = order[next_idx]
                    self.config["tracked_hand"] = self.tracked_hand
                    save_config(self.config)
                    self.set_status(f"Tracked Hand: {self.tracked_hand.upper()}")
                elif key == ord('t'):
                    self.always_on_top = not self.always_on_top
                    self.config["always_on_top"] = self.always_on_top
                    save_config(self.config)
                    self.apply_always_on_top()
                    self.set_status(f"Pin On Top: {'ON' if self.always_on_top else 'OFF'}")
                elif key == ord('g'):
                    self.show_gesture_guide = not self.show_gesture_guide
                    self.config["show_gesture_guide"] = self.show_gesture_guide
                    save_config(self.config)
                elif key == ord('c'):
                    self.cannons.reset()
                    self.set_status("Reset cooldowns and recentered.")

        finally:
            release_all_keys()
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()
            print("BABFT Hand Controller cleanly shut down.")


if __name__ == "__main__":
    app = BabftHandController()
    app.run()
