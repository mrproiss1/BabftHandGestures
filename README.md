# Roblox Build A Boat Hand Gesture Controller (WASD Only)

A streamlined, real-time computer-vision hand tracker for Roblox: Build A Boat For Treasure (BABFT) that translates your hand gestures directly into W, A, S, D movement keys.

---

## Hand Gestures & WASD Mapping

| Hand Gesture | Key Pressed | Roblox Action | Notes |
| :--- | :---: | :--- | :--- |
| **Point FORWARD / UP** | **`W`** | Move Forward / Throttle | Point index into camera or upward |
| **Point LEFT** | **`A`** | Steer Left | Point index finger to the left |
| **Point RIGHT** | **`D`** | Steer Right | Point index finger to the right |
| **Closed FIST** | **`S`** | Move Backward / Reverse | Curl fingers into a fist (no wrist bending down) |
| **Open / Resting Hand** | *None* | Release all keys | Neutral relaxed position |

---

## Clean On-Screen HUD

- **Minimal Header**: Clean title and FPS counter without button boxes or camera name clutter.
- **Visual Action Status**: Displays active direction and glowing virtual `[W]`, `[A]`, `[S]`, `[D]` badges at the bottom.
- **Hand Skeleton**: Real-time colored bone tracking and pointing aim vector.
- **Controls Reference Card**: Compact overlay on the right showing the 4 WASD actions (toggle with `[G]`).

---

## Hotkeys

| Hotkey | Action |
| :---: | :--- |
| **`[H]`** | Switch tracked hand (`Both` -> `Right` -> `Left`) |
| **`[T]`** | Toggle Always-On-Top window pinning |
| **`[G]`** | Toggle Gesture Guide card on/off |
| **`[Q]` / `[ESC]`** | Safely exit and release all pressed keys |

---

## How to Run

### Method 1: Double-Click
Double-click `run.bat` in this folder.

### Method 2: Command Line
```bash
cd c:\Users\mrproiss1\Desktop\Coding\Python\BabftHandGestures
python BabftHandGestures.py
```

---

## Technical Details
- **DirectInput Hardware Scancodes**: Utilizes Windows Win32 `user32.SendInput` with `KEYEVENTF_SCANCODE` (`0x11` for W, `0x1E` for A, `0x1F` for S, `0x20` for D) for 100% reliable input capture in Roblox without being blocked by anti-cheat.
- **Automatic Key Release**: All keys are safely released when your hand leaves the camera frame or when the program closes.
