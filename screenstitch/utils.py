"""I/O helpers — image loading, saving, path handling."""

from pathlib import Path

import cv2
import numpy as np

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


def load_image(path: str | Path, *, color: bool = True) -> np.ndarray:
    """Load an image from disk. Returns BGR numpy array (or grayscale if color=False)."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")
    flag = cv2.IMREAD_COLOR if color else cv2.IMREAD_GRAYSCALE
    img = cv2.imread(str(path), flag)
    if img is None:
        raise ValueError(f"Failed to decode image: {path}")
    return img


def load_images(folder: str | Path, *, color: bool = True) -> list[tuple[str, np.ndarray]]:
    """Load all supported images from a folder. Returns list of (filename, image) pairs."""
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder}")
    pairs = []
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() in SUPPORTED_EXTENSIONS:
            pairs.append((p.name, load_image(p, color=color)))
    if not pairs:
        raise FileNotFoundError(f"No supported images in {folder}")
    return pairs


def save_image(path: str | Path, image: np.ndarray) -> Path:
    """Save an image to disk. Creates parent dirs if needed. Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(path), image)
    if not ok:
        raise IOError(f"Failed to write image: {path}")
    return path


def to_gray(image: np.ndarray) -> np.ndarray:
    """Convert BGR image to grayscale. No-op if already single-channel."""
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
