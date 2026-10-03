# Roblox Build A Boat Hand Gesture Controller (WASD Only) ⛵🖐️

A streamlined, real-time computer-vision hand tracker for **Roblox: Build A Boat For Treasure (BABFT)** that translates your hand pointing gestures directly into **W, A, S, D** movement keys.

---

## 🎮 Hand Gestures & WASD Mapping

| Hand Gesture | Visual Reference | Key Pressed | Roblox Action |
| :--- | :---: | :---: | :--- |
| **Point FORWARD / UP** | `⊙` / `↑` | **`W`** | Move Forward / Throttle Forward |
| **Point LEFT** | `←` | **`A`** | Steer Left |
| **Point DOWN** | `↓` | **`S`** | Move Backward / Reverse |
| **Point RIGHT** | `→` | **`D`** | Steer Right |
| **Rest / Open Hand** | ✋ | *None* | Release all keys cleanly |

---

## 🖥️ Live On-Screen HUD

- **WASD Status**: Shows the currently detected gesture and active key.
- **Glowing Virtual Keys**: Virtual `[W]`, `[A]`, `[S]`, `[D]` badges light up bright green when active.
- **Full Hand Skeleton**: Real-time colored bone tracking and aim vector arrow.
- **Controls Reference Card**: Live side card displaying the gesture mapping.
- **Camera Selector**: Dropdown to switch between webcams with settings memory.
- **Always-on-Top Toggle**: Pin the floating HUD over your Roblox game window.

---

## ⌨️ Hotkeys

| Hotkey | Action |
| :---: | :--- |
| **`[H]`** | Switch tracked hand (`Both` ➔ `Right` ➔ `Left`) |
| **`[T]`** | Toggle Always-On-Top window pinning |
| **`[G]`** | Toggle Gesture Guide card on/off |
| **`[Q]` / `[ESC]`** | Safely exit and release all pressed keys |

---

## 🚀 How to Run

### Method 1: Double-Click
Double-click `run.bat` in this folder.

### Method 2: Command Line
```bash
cd c:\Users\mrproiss1\Desktop\Coding\Python\BabftHandGestures
python BabftHandGestures.py
```

---

## 🛡️ Technical Details
- **DirectInput Hardware Scancodes**: Utilizes Windows Win32 `user32.SendInput` with `KEYEVENTF_SCANCODE` (`0x11` for W, `0x1E` for A, `0x1F` for S, `0x20` for D) for 100% reliable input capture in Roblox without being blocked by anti-cheat.
- **Automatic Key Release**: All keys are safely released when your hand leaves the camera frame or when the program closes.
