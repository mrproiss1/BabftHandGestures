"""
Roblox Build A Boat Hand Gesture Controller (BABFT - Pure WASD)
==============================================================
A clean, real-time computer vision controller for Roblox Build A Boat.
Tracks hand gestures via webcam using MediaPipe and sends DirectInput
hardware scancodes (W, A, S, D) directly to Roblox.

Controls:
  - Point FORWARD / UP         -> W (Move Forward)
  - Point FORWARD + LEFT (WA)  -> W + A (Diagonal Forward-Left)
  - Point FORWARD + RIGHT (WD) -> W + D (Diagonal Forward-Right)
  - Point LEFT                 -> A (Steer Left)
  - Point RIGHT                -> D (Steer Right)
  - Closed FIST                -> S (Move Backward - no pointing down needed)
  - Neutral / Hand Open        -> Release all keys
"""

import os
import sys
import time
import math
import json
import atexit
import ctypes
import subprocess
from ctypes import wintypes
from typing import Dict, List, Tuple, Optional

# --- DEPENDENCIES CHECK ---
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

# --- DIRECTINPUT HARDWARE SCANCODES (ROBLOX COMPATIBILITY) ---
user32 = ctypes.windll.user32

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
        _fields_ = [("ki", KEYBDINPUT)]
    _anonymous_ = ("i",)
    _fields_ = [("type", wintypes.DWORD), ("i", _I)]

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

# Hardware scancodes for WASD
SCANCODE_MAP = {
    'w': 0x11,
    'a': 0x1E,
    's': 0x1F,
    'd': 0x20,
}

CURRENTLY_HELD = {'w': False, 'a': False, 's': False, 'd': False}

def send_scancode(key_char: str, is_up: bool = False):
    sc = SCANCODE_MAP.get(key_char.lower())
    if sc is None:
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

def press_key(key: str):
    global CURRENTLY_HELD
    key = key.lower()
    if key in CURRENTLY_HELD and not CURRENTLY_HELD[key]:
        if HAS_KEYBOARD:
            try:
                keyboard.press(key)
            except Exception:
                pass
        send_scancode(key, is_up=False)
        CURRENTLY_HELD[key] = True

def release_key(key: str):
    global CURRENTLY_HELD
    key = key.lower()
    if key in CURRENTLY_HELD and CURRENTLY_HELD[key]:
        if HAS_KEYBOARD:
            try:
                keyboard.release(key)
            except Exception:
                pass
        send_scancode(key, is_up=True)
        CURRENTLY_HELD[key] = False

def release_all_keys():
    for k in list(CURRENTLY_HELD.keys()):
        release_key(k)

atexit.register(release_all_keys)


# --- CAMERA ENUMERATION ---
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


# --- CONFIGURATION ---
def get_resource_path(relative_path: str) -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(current_dir, relative_path)
    if os.path.exists(p):
        return p
    p2 = os.path.join(current_dir, "..", "HandGunBabft", relative_path)
    if os.path.exists(p2):
        return os.path.abspath(p2)
    return p

CONFIG_FILE = get_resource_path("config.json")
MODEL_FILE = get_resource_path("hand_landmarker.task")

DEFAULT_CONFIG = {
    "selected_camera_name": "USB2.0 PC CAMERA",
    "selected_camera_index": 1,
    "tracked_hand": "both",
    "sensitivity_x": 0.08,
    "sensitivity_y": 0.10,
    "sensitivity_z": 0.08,
    "always_on_top": True,
    "show_gesture_guide": True
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


def dist2d(p1, p2) -> float:
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


# --- MAIN WASD CONTROLLER ---
class BabftWASDController:
    def __init__(self):
        self.config = load_config()
        self.tracked_hand = self.config.get("tracked_hand", "both")
        self.always_on_top = bool(self.config.get("always_on_top", True))
        self.show_gesture_guide = bool(self.config.get("show_gesture_guide", True))
        self.sensitivity_x = float(self.config.get("sensitivity_x", 0.08))
        self.sensitivity_y = float(self.config.get("sensitivity_y", 0.10))
        self.sensitivity_z = float(self.config.get("sensitivity_z", 0.08))

        self.camera_list = get_available_cameras()
        self.active_cam_idx = self._select_initial_camera()
        self.cap = None

        self.current_keys: List[str] = []
        self.active_direction_label = "NEUTRAL"
        self.window_name = "BABFT Hand WASD Controller"

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

    def classify_wasd(self, lm) -> Tuple[List[str], str]:
        """
        Classifies hand gestures with single or simultaneous keys:
          - Point FORWARD / UP         -> ['w']
          - Point FORWARD + LEFT (WA)  -> ['w', 'a']
          - Point FORWARD + RIGHT (WD) -> ['w', 'd']
          - Point LEFT                 -> ['a']
          - Point RIGHT                -> ['d']
          - Closed FIST (or down)      -> ['s']
          - None                       -> [] (Neutral)
        """
        wrist = lm[0]
        idx_mcp = lm[5]
        idx_tip = lm[8]
        middle_mcp = lm[9]

        palm_size = max(dist2d(wrist, middle_mcp), 0.001)

        idx_dx = idx_tip.x - idx_mcp.x
        idx_dy = idx_tip.y - idx_mcp.y
        idx_dz = idx_tip.z - idx_mcp.z
        idx_2d_len = math.hypot(idx_dx, idx_dy) / palm_size

        # 1. Closed FIST detection for Backward (S) - no pointing down needed!
        if idx_dz > -0.07 and idx_2d_len < 0.35:
            idx_curl = dist2d(idx_tip, wrist) / palm_size
            mid_curl = dist2d(lm[12], wrist) / palm_size
            ring_curl = dist2d(lm[16], wrist) / palm_size
            pinky_curl = dist2d(lm[20], wrist) / palm_size
            idx_to_mcp = dist2d(idx_tip, idx_mcp) / palm_size

            if idx_to_mcp < 0.45 or idx_curl < 1.05:
                other_curled = sum([
                    mid_curl < 1.05,
                    ring_curl < 1.05,
                    pinky_curl < 1.05
                ])
                if other_curled >= 2:
                    return ['s'], "CLOSED FIST (S - BACK)"

        # 2. Pointing Forward into camera lens (along -Z)
        if idx_dz < -self.sensitivity_z and idx_2d_len < 0.45:
            if idx_dx < -self.sensitivity_x:
                return ['w', 'a'], "FORWARD + LEFT (W + A)"
            elif idx_dx > self.sensitivity_x:
                return ['w', 'd'], "FORWARD + RIGHT (W + D)"
            else:
                return ['w'], "POINT FORWARD (W)"

        # 3. 2D Angle-based directional pointing (Supports diagonal combinations)
        if idx_2d_len >= 0.28 or abs(idx_dy) > 0.08 or abs(idx_dx) > 0.08:
            angle_deg = math.degrees(math.atan2(idx_dy, idx_dx))  # 0=Right, -90=Up, 180/-180=Left, 90=Down

            # Forward-Left diagonal (-150 to -110 deg)
            if -150 <= angle_deg < -110:
                return ['w', 'a'], "FORWARD + LEFT (W + A)"
            # Pure Forward Up (-110 to -70 deg)
            elif -110 <= angle_deg <= -70:
                return ['w'], "POINT UP (W)"
            # Forward-Right diagonal (-70 to -30 deg)
            elif -70 < angle_deg < -30:
                return ['w', 'd'], "FORWARD + RIGHT (W + D)"
            # Pure Right (-30 to +40 deg)
            elif -30 <= angle_deg <= 40:
                return ['d'], "POINT RIGHT (D)"
            # Down / Backward (+40 to +140 deg)
            elif 40 < angle_deg <= 140:
                return ['s'], "POINT DOWN (S)"
            # Pure Left
            else:
                return ['a'], "POINT LEFT (A)"

        return [], "NEUTRAL"

    def apply_wasd_input(self, target_keys: List[str]):
        """Ensures all target WASD keys are pressed, cleanly releasing others."""
        for k in ['w', 'a', 's', 'd']:
            if k in target_keys:
                press_key(k)
            else:
                release_key(k)
        self.current_keys = target_keys

    def draw_hud(self, frame: np.ndarray, landmarks, handedness: str, fps: float):
        h, w, _ = frame.shape

        # Clean top bar without visual button clutter
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 42), (18, 18, 18), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # Simple title and FPS counter
        cv2.putText(frame, "BUILD A BOAT WASD", (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 220, 100), 2)
        cv2.putText(frame, f"{int(fps)} FPS", (w - 75, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (150, 150, 150), 1)

        # Skeleton Tracking Lines
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
                if idx == 8:  # Index Tip
                    cv2.circle(frame, pt, 8, (0, 255, 255), -1)
                else:
                    cv2.circle(frame, pt, 4, (0, 140, 255), -1)

            # Draw Index Aim Vector if pointing
            if any(k in self.current_keys for k in ['w', 'a', 'd']):
                idx_base = (int(landmarks[5].x * w), int(landmarks[5].y * h))
                idx_tip = (int(landmarks[8].x * w), int(landmarks[8].y * h))
                cv2.arrowedLine(frame, idx_base, idx_tip, (0, 255, 255), 2, tipLength=0.25)

        # Minimal Gesture Guide Card (Right Side)
        if self.show_gesture_guide:
            guide_items = [
                ("W",       "Point FORWARD / UP", "Forward"),
                ("W + A",   "Point FWD + LEFT",   "Forward-Left"),
                ("W + D",   "Point FWD + RIGHT",  "Forward-Right"),
                ("A",       "Point LEFT",         "Steer Left"),
                ("D",       "Point RIGHT",        "Steer Right"),
                ("S",       "Closed FIST",        "Backward"),
            ]
            gw = 185
            gh = len(guide_items) * 24 + 32
            gx = w - gw - 12
            gy = 50

            card_bg = frame.copy()
            cv2.rectangle(card_bg, (gx, gy), (gx + gw, gy + gh), (15, 15, 15), -1)
            cv2.addWeighted(card_bg, 0.80, frame, 0.20, 0, frame)
            cv2.rectangle(frame, (gx, gy), (gx + gw, gy + gh), (70, 70, 70), 1)
            cv2.putText(frame, "WASD CONTROLS", (gx + 12, gy + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 240, 180), 1)

            for i, (k_tag, pose_desc, act_desc) in enumerate(guide_items):
                iy = gy + 38 + i * 24
                # Check if this guide row matches active keys
                target_match = False
                if k_tag == "W" and self.current_keys == ['w']:
                    target_match = True
                elif k_tag == "W + A" and set(self.current_keys) == {'w', 'a'}:
                    target_match = True
                elif k_tag == "W + D" and set(self.current_keys) == {'w', 'd'}:
                    target_match = True
                elif k_tag == "A" and self.current_keys == ['a']:
                    target_match = True
                elif k_tag == "D" and self.current_keys == ['d']:
                    target_match = True
                elif k_tag == "S" and self.current_keys == ['s']:
                    target_match = True

                if target_match:
                    cv2.rectangle(frame, (gx + 4, iy - 13), (gx + gw - 4, iy + 7), (0, 180, 80), -1)
                    col = (0, 0, 0)
                else:
                    col = (220, 220, 220)

                cv2.putText(frame, f"[{k_tag}] {pose_desc}", (gx + 8, iy), cv2.FONT_HERSHEY_SIMPLEX, 0.36, col, 1)

        # Bottom Bar: Active Gesture and WASD Virtual Keys
        bot_overlay = frame.copy()
        cv2.rectangle(bot_overlay, (0, h - 55), (w, h), (15, 15, 15), -1)
        cv2.addWeighted(bot_overlay, 0.85, frame, 0.15, 0, frame)

        # Status text
        cv2.putText(frame, f"ACTION: {self.active_direction_label}", (15, h - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)

        # WASD Key Badges (Lights up multiple keys when active together)
        wasd_keys = ['W', 'A', 'S', 'D']
        bx = w - 20
        for k in reversed(wasd_keys):
            is_active = (k.lower() in self.current_keys)
            bg_col = (0, 220, 80) if is_active else (40, 40, 40)
            txt_col = (0, 0, 0) if is_active else (160, 160, 160)
            bx -= 45
            cv2.rectangle(frame, (bx, h - 45), (bx + 36, h - 12), bg_col, -1)
            cv2.rectangle(frame, (bx, h - 45), (bx + 36, h - 12), (180, 180, 180), 1)
            cv2.putText(frame, k, (bx + 11, h - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, txt_col, 2)

    def run(self):
        cv2.namedWindow(self.window_name)
        self.apply_always_on_top()

        if not self.start_camera(self.active_cam_idx):
            print("Failed to start camera. Trying default index 0...")
            if not self.start_camera(0):
                print("No webcam found. Exiting.")
                return

        fps = 0.0
        frame_count = 0
        fps_timer = time.time()
        last_ms = 0

        print("\n========================================================")
        print("  BABFT WASD Hand Controller Started Successfully!")
        print("========================================================")
        print("Controls:")
        print("  Point FORWARD / UP         -> W (Move Forward)")
        print("  Point FORWARD + LEFT (WA)  -> W + A (Diagonal Forward-Left)")
        print("  Point FORWARD + RIGHT (WD) -> W + D (Diagonal Forward-Right)")
        print("  Point LEFT                 -> A (Steer Left)")
        print("  Closed FIST                -> S (Move Backward - no pointing down)")
        print("  Point RIGHT                -> D (Steer Right)")
        print("  Rest / Open Hand           -> Neutral (Release all keys)")
        print("\nHotkeys:")
        print("  [H]     - Switch Tracked Hand (Both / Right / Left)")
        print("  [T]     - Toggle Always-On-Top Window")
        print("  [G]     - Toggle Gesture Guide HUD")
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

                frame = cv2.flip(frame, 1)

                cur_ms = int(now * 1000)
                if cur_ms <= last_ms:
                    cur_ms = last_ms + 1
                last_ms = cur_ms

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                det_res = self.detector.detect_for_video(mp_img, cur_ms)

                landmarks, handedness = self.get_tracked_hand_landmarks(det_res)

                if landmarks:
                    target_keys, label = self.classify_wasd(landmarks)
                    self.active_direction_label = label
                    self.apply_wasd_input(target_keys)
                else:
                    self.active_direction_label = "NO HAND DETECTED"
                    self.apply_wasd_input([])

                self.draw_hud(frame, landmarks, handedness, fps)

                cv2.imshow(self.window_name, frame)
                key = cv2.waitKey(1) & 0xFF

                if key in [ord('q'), 27]:
                    break
                elif key == ord('h'):
                    order = ["both", "right", "left"]
                    next_idx = (order.index(self.tracked_hand) + 1) % len(order)
                    self.tracked_hand = order[next_idx]
                    self.config["tracked_hand"] = self.tracked_hand
                    save_config(self.config)
                elif key == ord('t'):
                    self.always_on_top = not self.always_on_top
                    self.config["always_on_top"] = self.always_on_top
                    save_config(self.config)
                    self.apply_always_on_top()
                elif key == ord('g'):
                    self.show_gesture_guide = not self.show_gesture_guide
                    self.config["show_gesture_guide"] = self.show_gesture_guide
                    save_config(self.config)

        finally:
            release_all_keys()
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()
            print("BABFT Controller safely closed.")


if __name__ == "__main__":
    app = BabftWASDController()
    app.run()
