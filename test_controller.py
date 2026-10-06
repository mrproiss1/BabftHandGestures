"""
Unit and integration tests for BABFT WASD Hand Gesture Controller
"""

import os
import sys
import glob
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from BabftHandGestures import (
    BabftWASDController,
    SCANCODE_MAP,
    dist2d
)

def test_config():
    print("Testing config and initialization...")
    controller = BabftWASDController()
    assert controller.active_cam_idx is not None
    assert len(controller.camera_list) > 0
    print(" Config OK!")

def test_scancodes():
    print("Testing WASD scancodes...")
    required = ['w', 'a', 's', 'd']
    for k in required:
        assert k in SCANCODE_MAP, f"Missing scancode for {k}"
    print(" WASD Scancodes OK!")

def test_wasd_on_user_photos():
    print("Testing WASD classifier on user photos...")
    controller = BabftWASDController()

    user_img_dir = r"C:\Users\mrproiss1\.gemini\antigravity-ide\brain\a000ab24-f9c5-45a3-b7ea-173158d26c76\.user_uploaded"
    if not os.path.exists(user_img_dir):
        print("User images directory not found, skipping image test.")
        return

    images = sorted(glob.glob(os.path.join(user_img_dir, "*.jpg")))
    assert len(images) == 5, f"Expected 5 images, found {len(images)}"

    model_path = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
    detector = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.IMAGE,
        num_hands=1
    ))

    # User images:
    # 1: Pointing UP -> ['w']
    # 2: Pointing FORWARD -> ['w']
    # 4: Pointing FORWARD + RIGHT together -> ['w', 'd']
    # 5: Pointing RIGHT -> ['d']
    expected_keys = {
        0: ['w'],       # Image 1 (Up) -> W
        1: ['w'],       # Image 2 (Forward) -> W
        3: ['w', 'd'],  # Image 4 (Forward + Right together) -> W + D
        4: ['d'],       # Image 5 (Pure Right) -> D
    }

    for idx, exp_k in expected_keys.items():
        img = cv2.imread(images[idx])
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        assert res.hand_landmarks, f"No landmarks in image {idx+1}"
        keys, label = controller.classify_wasd(res.hand_landmarks[0])
        print(f"  Photo {idx+1}: Got keys={keys}, label='{label}' (Expected {exp_k})")
        assert keys == exp_k, f"Photo {idx+1} mismatch: got {keys}, expected {exp_k}"

    print(" User gesture images classified into correct WASD keys and combos accurately!")

if __name__ == "__main__":
    test_config()
    test_scancodes()
    test_wasd_on_user_photos()
    print("\n ALL WASD TESTS PASSED SUCCESSFULLY!")
