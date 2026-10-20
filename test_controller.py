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
    print("[OK] Config OK!")


def test_scancodes():
    print("Testing WASD scancodes...")
    required = ['w', 'a', 's', 'd']
    for k in required:
        assert k in SCANCODE_MAP, f"Missing scancode for {k}"
    print("[OK] WASD Scancodes OK!")


def test_wasd_mock_landmarks():
    print("Testing WASD classifier with synthetic landmark structures...")
    controller = BabftWASDController()

    class MockLandmark:
        def __init__(self, x=0.5, y=0.5, z=0.0):
            self.x = x
            self.y = y
            self.z = z

    # 1. Test Pointing UP -> ['w']
    lm_up = [MockLandmark() for _ in range(21)]
    lm_up[0] = MockLandmark(0.5, 0.8, 0.0)    # Wrist
    lm_up[5] = MockLandmark(0.5, 0.6, 0.0)    # Index MCP
    lm_up[8] = MockLandmark(0.5, 0.2, 0.0)    # Index Tip (pointing up: dy < 0)
    lm_up[9] = MockLandmark(0.5, 0.5, 0.0)    # Middle MCP
    keys_up, label_up = controller.classify_wasd(lm_up)
    assert 'w' in keys_up, f"Expected 'w' in keys for pointing up, got {keys_up}"
    print(f"[OK] Point Up classified as: {keys_up} ({label_up})")

    # 2. Test Pointing RIGHT -> ['d']
    lm_right = [MockLandmark() for _ in range(21)]
    lm_right[0] = MockLandmark(0.3, 0.5, 0.0)
    lm_right[5] = MockLandmark(0.4, 0.5, 0.0)
    lm_right[8] = MockLandmark(0.8, 0.5, 0.0) # Index Tip (pointing right: dx > 0)
    lm_right[9] = MockLandmark(0.4, 0.45, 0.0)
    keys_right, label_right = controller.classify_wasd(lm_right)
    assert 'd' in keys_right, f"Expected 'd' in keys for pointing right, got {keys_right}"
    print(f"[OK] Point Right classified as: {keys_right} ({label_right})")

    # 3. Test Pointing LEFT -> ['a']
    lm_left = [MockLandmark() for _ in range(21)]
    lm_left[0] = MockLandmark(0.7, 0.5, 0.0)
    lm_left[5] = MockLandmark(0.6, 0.5, 0.0)
    lm_left[8] = MockLandmark(0.2, 0.5, 0.0) # Index Tip (pointing left: dx < 0)
    lm_left[9] = MockLandmark(0.6, 0.45, 0.0)
    keys_left, label_left = controller.classify_wasd(lm_left)
    assert 'a' in keys_left, f"Expected 'a' in keys for pointing left, got {keys_left}"
    print(f"[OK] Point Left classified as: {keys_left} ({label_left})")


def test_wasd_on_local_test_images():
    print("Testing WASD classifier on local test images (if present)...")
    test_img_dir = os.path.join(os.path.dirname(__file__), "tests", "test_images")
    if not os.path.exists(test_img_dir):
        print("Optional test_images directory not present, skipping image file test.")
        return

    images = sorted(glob.glob(os.path.join(test_img_dir, "*.jpg")))
    if not images:
        return

    controller = BabftWASDController()
    model_path = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
    detector = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.IMAGE,
        num_hands=1
    ))

    for idx, img_path in enumerate(images):
        img = cv2.imread(img_path)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if res.hand_landmarks:
            keys, label = controller.classify_wasd(res.hand_landmarks[0])
            print(f"  Image {os.path.basename(img_path)}: Keys={keys}, Label='{label}'")


if __name__ == "__main__":
    test_config()
    test_scancodes()
    test_wasd_mock_landmarks()
    test_wasd_on_local_test_images()
    print("\n[OK] ALL WASD TESTS PASSED SUCCESSFULLY!")
