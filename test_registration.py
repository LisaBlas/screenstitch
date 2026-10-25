"""Quick visual test for the registration module.

Run:  python test_registration.py
Output lands in ./debug/registration/
"""

import cv2
import numpy as np
from pathlib import Path
from screenstitch.pipeline.register import register

OUT = Path("debug/registration")
OUT.mkdir(parents=True, exist_ok=True)


def make_test_scene():
    """Create a 600×400 scene with distinct features, then crop two overlapping views."""
    np.random.seed(7)
    scene = np.random.randint(40, 180, (400, 600, 3), dtype=np.uint8)

    # Scatter shapes for texture
    cv2.circle(scene, (80, 80), 35, (255, 80, 80), -1)
    cv2.circle(scene, (300, 300), 50, (80, 80, 255), -1)
    cv2.rectangle(scene, (400, 50), (550, 180), (80, 220, 80), -1)
    cv2.rectangle(scene, (150, 200), (250, 350), (200, 200, 50), -1)
    cv2.putText(scene, "HELLO", (60, 370), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    cv2.putText(scene, "WORLD", (350, 370), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 0), 3)

    # Two crops with ~150px overlap in the middle
    left = scene[:, :350].copy()
    right = scene[:, 200:].copy()

    cv2.imwrite(str(OUT / "scene_full.png"), scene)
    cv2.imwrite(str(OUT / "input_left.png"), left)
    cv2.imwrite(str(OUT / "input_right.png"), right)
    print(f"Scene: {scene.shape[1]}x{scene.shape[0]}")
    print(f"Left:  {left.shape[1]}x{left.shape[0]}")
    print(f"Right: {right.shape[1]}x{right.shape[0]}")
    return left, right


def main():
    left, right = make_test_scene()

    result = register([left, right], ["left.png", "right.png"])

    print(f"\nCanvas size: {result.canvas_size[0]}x{result.canvas_size[1]}")
    print(f"Good matches: {result.match_counts}")

    # Save warped images
    for i, (name, warped, mask) in enumerate(
        zip(result.names, result.warped_images, result.warped_masks)
    ):
        cv2.imwrite(str(OUT / f"warped_{i}_{name}"), warped)
        cv2.imwrite(str(OUT / f"mask_{i}_{name}"), mask)

    # Naive blend: average where both contribute, else take whichever exists
    m0 = result.warped_masks[0].astype(bool)
    m1 = result.warped_masks[1].astype(bool)
    canvas = np.zeros_like(result.warped_images[0], dtype=np.float64)
    count = np.zeros(canvas.shape[:2], dtype=np.float64)

    for warped, mask in zip(result.warped_images, result.warped_masks):
        valid = mask.astype(bool)
        canvas[valid] += warped[valid].astype(np.float64)
        count[valid] += 1

    count[count == 0] = 1
    canvas = (canvas / count[..., None]).astype(np.uint8)
    cv2.imwrite(str(OUT / "merged_naive.png"), canvas)

    print(f"\nOutputs saved to {OUT.resolve()}")
    print("Open merged_naive.png — it should look like scene_full.png")


if __name__ == "__main__":
    main()
