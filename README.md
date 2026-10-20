# Roblox Build A Boat Hand Gesture Controller (BABFT - Pure WASD)

A streamlined, real-time computer vision hand tracker for **Roblox: Build A Boat For Treasure (BABFT)** that translates your hand gestures directly into **`W`**, **`A`**, **`S`**, **`D`** movement keys.

Built with OpenCV, Google MediaPipe, and DirectInput hardware scancodes for 100% reliable capture in the Roblox desktop client.

---

# 📜 LICENSE & ATTRIBUTION REQUIREMENTS

> [!IMPORTANT]
> ### **mrproiss1 Attribution License**
> This project is licensed under the custom **mrproiss1 Attribution License**. You are free to use, modify, and share this tool for both personal and public use under the mandatory attribution terms below.

```text
==================================================================================
                          mrproiss1 Attribution License
                           Copyright (c) 2026 mrproiss1
==================================================================================

Permission is granted to use, copy, modify, and share this project for
personal or public use, subject to the conditions below.

If you post a video, stream, tutorial, showcase, review, or other public
media featuring this project, you must clearly credit:

    Created by mrproiss1
    GitHub: https://github.com/mrproiss1

1. The credit must be VISIBLE in the video itself (on screen).
2. Clearly place the credit and GitHub link in the video description.
3. You may NOT claim this project as your own original work.

This project is provided "as is", without warranty of any kind, express or
implied. The author is not liable for any damages or issues caused by use of
this project.
==================================================================================
```

### 🎬 Mandatory Content Creator Checklist (YouTube, TikTok, Twitch, Kick)
If you feature this software in any video, stream, tutorial, or showcase:
- [x] **On-Screen Display**: Display **"Created by mrproiss1"** visibly in your video.
- [x] **Video Description**: Include **`Created by mrproiss1 | GitHub: https://github.com/mrproiss1`** in the top section of your video description.
- [x] **Originality**: Do not claim ownership, originality, or creation of this tracking tool.

---

## Hand Gestures & WASD Mapping

| Hand Gesture | Key Sent to Roblox | Roblox Action | Description |
| :--- | :---: | :--- | :--- |
| **Point FORWARD / UP** | **`W`** | Move Forward | Point index into camera or straight up |
| **Point FWD + LEFT** | **`W + A`** | Forward + Steer Left | Point diagonally forward and to the left |
| **Point FWD + RIGHT** | **`W + D`** | Forward + Steer Right | Point diagonally forward and to the right |
| **Point LEFT** | **`A`** | Steer Left | Point index finger horizontally left |
| **Point RIGHT** | **`D`** | Steer Right | Point index finger horizontally right |
| **Closed FIST** | **`S`** | Move Backward / Reverse | Curl fingers into a fist (no wrist bending down) |
| **Open / Resting Hand** | *None* | Release all keys | Neutral relaxed position |

---

## Clean On-Screen HUD

- **Minimal Header**: Clean title and FPS counter without button boxes or clutter.
- **Visual Action Status**: Displays active direction and glowing virtual `[W]`, `[A]`, `[S]`, `[D]` badges at the bottom (supports multiple keys active simultaneously).
- **Hand Skeleton**: Real-time colored bone tracking and pointing aim vector.
- **Controls Reference Card**: Compact overlay on the right showing the WASD single and combo actions (toggle on/off with `[G]`).

---

## In-App Hotkeys

| Hotkey | Action |
| :---: | :--- |
| **`[H]`** | Switch tracked hand (`Both` -> `Right` -> `Left`) |
| **`[T]`** | Toggle Always-On-Top window pinning |
| **`[G]`** | Toggle Gesture Guide card on/off |
| **`[Q]` / `[ESC]`** | Safely exit and release all pressed keys |

---

## How to Run

### Method 1: Standalone Windows Executable (Recommended - No Python Needed)
1. Download **`BabftHandGestures.exe`** from [**Releases**](https://github.com/mrproiss1/BabftHandGestures/releases/latest).
2. Double-click `BabftHandGestures.exe` to run. Everything is pre-bundled (AI model, OpenCV, DirectInput)!

### Method 2: Double-Click Script Launcher
Double-click `run.bat` (Windows) or execute `bash run.sh` (Linux/macOS).

### Method 3: Command Line
```bash
# Clone the repository
git clone https://github.com/mrproiss1/BabftHandGestures.git
cd BabftHandGestures

# Install dependencies
pip install -r requirements.txt

# Run the controller
python BabftHandGestures.py
```

### Command Line Options
```bash
# Launch with specific camera and tracked hand:
python BabftHandGestures.py --camera 0 --hand right

# Run headless (no window, minimal CPU/GPU overhead):
python BabftHandGestures.py --headless

# Adjust gesture sensitivities:
python BabftHandGestures.py --sensitivity-x 0.08 --sensitivity-y 0.10 --sensitivity-z 0.08
```

---

## Configuration (`config.json`)

Settings are saved automatically in `config.json`:

```json
{
  "selected_camera_name": "Default Camera",
  "selected_camera_index": 0,
  "tracked_hand": "both",
  "sensitivity_x": 0.08,
  "sensitivity_y": 0.10,
  "sensitivity_z": 0.08,
  "always_on_top": true,
  "show_gesture_guide": true
}
```

---

## Technical Details

- **DirectInput Hardware Scancodes**: Utilizes Windows Win32 `user32.SendInput` with `KEYEVENTF_SCANCODE` (`0x11` for W, `0x1E` for A, `0x1F` for S, `0x20` for D) for 100% reliable input capture in Roblox without being blocked by anti-cheat.
- **Simultaneous Key Dispatch**: Supports dual-key combinations (`W + A` and `W + D`) held down concurrently when steering while moving forward.
- **Automatic Key Release**: All keys are safely released when your hand leaves the camera frame or when the program closes.
- **Automatic AI Model Download**: Auto-fetches `hand_landmarker.task` from Google MediaPipe CDN if missing.
