# Roblox Build A Boat Hand Gesture Controller ⛵🖐️

A real-time computer-vision hand tracker for **Roblox: Build A Boat For Treasure (BABFT)** that translates your real hand gestures into game movement, vehicle steering, and cannon combat directly through your webcam.

---

## 🎮 Hand Gestures & Control Mapping

The controller supports two distinct gameplay modes: **Boat Driving Mode (WASD)** and **Cannon Gunner Mode**.

| Hand Gesture | Visual Reference | Boat Mode (WASD) | Gunner Mode | Description |
| :--- | :---: | :---: | :---: | :--- |
| **Point FORWARD** | `⊙` (Index into camera) | **`W`** | **Lock / Hold `F`** | Drive boat forward / throttle into the camera plane |
| **Point UP** | `↑` (Index up) | **`Space`** | **`G` (Pitch Up)** | Jump, jetpack throttle, or aim gun upward |
| **Point RIGHT** | `→` (Index right) | **`D`** | **`L` (Aim Right)** | Steer right / rotate vehicle right |
| **Point LEFT** | `←` (Index left) | **`A`** | **`K` (Aim Left)** | Steer left / rotate vehicle left |
| **Point DOWN** | `↓` (Index down) | **`S`** | **`T` (Pitch Down)** | Reverse, brake, or tilt gun downward |
| **Pinch / Finger Snap** | `🤌` (Thumb + Index touch) | **Left Click + `F`** | **Fire Cannon** | Click blocks / trigger tools / fire 6-cannon battery |
| **Hand Open / Rest** | ✋ | **Release All** | **Neutral** | Safe automatic key release |

---

## 🕹️ Two Control Modes

Toggle anytime using **`[M]`** or by clicking the **`MODE`** button on the top HUD bar:

### 1. 🚤 Boat Driver Mode (Default)
- **Forward (`W`)**: Point your index finger directly forward toward your screen/webcam.
- **Steer Left (`A`) / Steer Right (`D`)**: Point your index finger left or right.
- **Jump / Flight (`Space`)**: Point your index finger straight up.
- **Reverse / Slow Down (`S`)**: Point your index finger down.
- **Interact / Click (`Left Mouse Click` + `F`)**: Tap or pinch your thumb and index finger together.

### 2. 💥 Cannon & Turret Gunner Mode
- **Active Hold (`F`)**: Automatically holds `F` continuously while your hand is visible.
- **Pitch Up (`G`) / Pitch Down (`T`)**: Point up or down to aim your cannon or hinge servos.
- **Aim Left (`K`) / Aim Right (`L`)**: Point left or right to traverse your turret.
- **Fire Cannons (`Z`, `B`, `V`, `C`, `X`, `N`)**: Pinch or snap your fingers to shoot through a 6-cannon cycle with individual 10-second cooldown trackers.

---

## 🖥️ Live On-Screen HUD & Visual Guide

The application window is designed to float directly over Roblox:
- **Hand Gesture Guide**: Live card displaying the detected gesture and reference poses.
- **Active Key Badges**: Visual indicators for `[W]`, `[A]`, `[S]`, `[D]`, `[SPACE]`, `[CLICK]`, etc. that light up green when pressed.
- **Full Hand Skeleton**: Real-time colored bone tracking and index aim direction vector.
- **Camera Switcher**: Quick dropdown menu to select between multiple webcams with memory.
- **Always-on-Top Toggle**: Pin the tracker window above the Roblox game client.

---

## ⌨️ Hotkeys

| Hotkey | Action |
| :---: | :--- |
| **`[M]`** | Toggle between **Boat Driver** and **Cannon Gunner** modes |
| **`[H]`** | Switch tracked hand (`Both` ➔ `Right` ➔ `Left`) |
| **`[T]`** | Toggle Always-On-Top window pinning |
| **`[G]`** | Toggle On-Screen Hand Gesture Guide card |
| **`[C]`** | Recenter / reset cannon cooldown timers |
| **`[Q]` / `[ESC]`** | Safely exit and release all pressed keys |

---

## 🚀 How to Run

### Method 1: Double-Click (Recommended)
Double-click `run.bat` in this folder.

### Method 2: Terminal / Command Prompt
```bash
cd c:\Users\mrproiss1\Desktop\Coding\Python\BabftHandGestures
python BabftHandGestures.py
```

---

## ⚙️ Configuration (`config.json`)

Customize thresholds and preferences:
```json
{
  "mode": "boat",
  "selected_camera_name": "USB2.0 PC CAMERA",
  "selected_camera_index": 1,
  "tracked_hand": "both",
  "sensitivity_x": 0.12,
  "sensitivity_y": 0.12,
  "sensitivity_z": 0.08,
  "pinch_threshold": 0.45,
  "always_on_top": true,
  "show_gesture_guide": true,
  "click_hold_seconds": 0.06
}
```

---

## 🛡️ Technical Details
- **DirectInput Hardware Scancodes**: Utilizes Windows Win32 `user32.SendInput` with `KEYEVENTF_SCANCODE` for 100% reliable input capture inside Roblox (bypasses Hyperion virtual key blocking).
- **Dual Dispatch**: Combines SendInput with Python `keyboard` library as a fallback.
- **Automatic Key Release**: All keys are safely released upon hand leaving frame or on application exit (`atexit`).
