"""
support.py -- helper code supplied with the assignment.  DO NOT EDIT.

Coordinate convention used everywhere in this assignment
--------------------------------------------------------
* Geometry is y-up, as in the lecture slides: x grows to the right, y grows UPWARD,
  and pixel (0, 0) is the bottom-left pixel of the picture.
* Pixel (i, j) is the lattice point (i, j).  A pixel belongs to a shape when this point is
  inside the shape; a Bresenham end point given as integers names a pixel directly, and a
  float end point (for example the output of clipping) is rounded to the nearest integer.
* An image is a NumPy array of shape (H, W, 3), dtype uint8, stored in the usual array order
  (row 0 is the TOP row).  put_pixel and fill_span convert y to the array row (row = H - 1 - y)
  for you, so in your own code never assume that y grows downward in the array.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image  # allowed: load / save only


def put_pixel(img: np.ndarray, x: int, y: int, color) -> None:
    """Write pixel (x, y) (y-up).  Silently ignores positions outside the image."""
    h, w = img.shape[:2]
    if 0 <= x < w and 0 <= y < h:
        img[h - 1 - y, x] = color


def fill_span(img: np.ndarray, y: int, x_first: int, x_last: int, color) -> None:
    """Write the horizontal run of pixels x_first..x_last (both included) on scan line y (y-up).

    The run is clamped to the image, so it is always safe to call.  `img` may be
    an (H, W, 3) image or an (H, W) mask.  Using this helper (instead of one
    put_pixel call per pixel) is what keeps the live program fast.
    """
    h, w = img.shape[:2]
    if y < 0 or y >= h:
        return
    a = max(int(x_first), 0)
    b = min(int(x_last), w - 1)
    if a <= b:
        img[h - 1 - y, a:b + 1] = color


def polygon_bbox(polygon, w: int, h: int):
    """Smallest pixel rectangle (x0, y0, x1, y1), inclusive, y-up, that contains every pixel
    touched by the polygon's bounding box (pixel (i, j) occupies the square of side 1 centred
    on the point (i, j)), clipped to a w x h image.  Returns None if nothing is left."""
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    x0, x1 = max(0, math.floor(min(xs) + 0.5)), min(w - 1, math.floor(max(xs) + 0.5))
    y0, y1 = max(0, math.floor(min(ys) + 0.5)), min(h - 1, math.floor(max(ys) + 0.5))
    if x0 > x1 or y0 > y1:
        return None
    return x0, y0, x1, y1


def get_region(img: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    """A VIEW of the pixels x0..x1, y0..y1 (inclusive, y-up, inside the image) of `img`.

    The rows of the view are in array order, i.e. in the same order as the rows of a mask made
    by fill_span, so  block_mean(mask, k)  and this view have the same shape and line up.
    Writing into the view (region[...] = values) changes img.
    """
    h = img.shape[0]
    return img[h - 1 - y1:h - y0, x0:x1 + 1]


def block_mean(mask_hi: np.ndarray, k: int) -> np.ndarray:
    """Average of every k x k block of a (h*k, w*k) mask: returns an (h, w) float array.

    For an anti-aliasing mask of 0/1 samples this is the coverage of each pixel
    (the fraction of its k*k samples that are inside the shape), a number in [0, 1].
    """
    h, w = mask_hi.shape[0] // k, mask_hi.shape[1] // k
    return mask_hi.reshape(h, k, w, k).mean(axis=(1, 3))


def new_image(w: int, h: int, color=(0, 0, 0)) -> np.ndarray:
    img = np.empty((h, w, 3), np.uint8)
    img[:] = color
    return img


def load_image(path: str) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"), dtype=np.uint8)


def save_image(img: np.ndarray, path: str) -> None:
    Image.fromarray(np.asarray(img, dtype=np.uint8)).save(path)
