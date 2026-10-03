"""
Unit and integration tests for BABFT Hand Gesture Controller
"""

import os
import sys
import glob
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Import module
from BabftHandGestures import (
    BabftHandController,
    SCANCODE_MAP,
    CANNON_KEYS,
    dist2d,
    dist3d
)

def test_config():
    print("Testing config and initialization...")
    controller = BabftHandController()
    assert controller.mode in ["boat", "gunner"]
    assert controller.active_cam_idx is not None
    assert len(controller.camera_list) > 0
    print(" Config OK!")

def test_scancodes():
    print("Testing scancodes...")
    required = ['w', 'a', 's', 'd', 'space', 'f', 'g', 't', 'k', 'l', 'z', 'b', 'v', 'c', 'x', 'n']
    for k in required:
        assert k in SCANCODE_MAP, f"Missing scancode for {k}"
    print(" Scancodes OK!")

def test_gestures_on_user_photos():
    print("Testing classifier on user photos...")
    controller = BabftHandController()

    user_img_dir = r"C:\Users\mrproiss1\.gemini\antigravity-ide\brain\a000ab24-f9c5-45a3-b7ea-173158d26c76\.user_uploaded"
    if not os.path.exists(user_img_dir):
        print("User images directory not found, skipping image test.")
        return

    images = sorted(glob.glob(os.path.join(user_img_dir, "*.jpg")))
    assert len(images) == 5, f"Expected 5 images, found {len(images)}"

    # We need IMAGE running mode detector for static images
    model_path = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
    detector = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.IMAGE,
        num_hands=1
    ))

    expected_gestures = [
        "POINT_UP",       # Image 1: Index pointing up
        "POINT_FORWARD",  # Image 2: Index pointing into camera
        "PINCH_ACTION",   # Image 3: Thumb & Index pinch
        "POINT_UP",       # Image 4: Hand angled pointing up-right
        "POINT_RIGHT",    # Image 5: Hand pointing right
    ]

    for idx, (img_path, exp) in enumerate(zip(images, expected_gestures)):
        img = cv2.imread(img_path)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        assert res.hand_landmarks, f"No landmarks in image {idx+1}"
        gesture, details = controller.classify_gesture(res.hand_landmarks[0], now=0.0)
        print(f"  Photo {idx+1}: Got {gesture} (Expected {exp})")
        assert gesture == exp, f"Photo {idx+1} mismatch: got {gesture}, expected {exp}"

    print(" All user gesture images classified accurately!")

if __name__ == "__main__":
    test_config()
    test_scancodes()
    test_gestures_on_user_photos()
    print("\n ALL TESTS PASSED SUCCESSFULLY!")
