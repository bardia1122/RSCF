"""
rasterize.py -- THIS IS YOUR FILE.

Fill in the functions below.  Do not rename them and do not change their signatures:
the viewer (screensaver.py), the self-check (selfcheck.py) and the grader import them by name.
The algorithms themselves are in the slides (Lecture 3: Bresenham, Lecture 4: scan-line,
Lecture 5: Cohen-Sutherland); this file only fixes what each function receives and returns.

Allowed
    * the math module; NumPy for the image arrays;
      the helpers in support.py (put_pixel, fill_span, polygon_bbox, get_region, block_mean).
    * Whole-array NumPy operations ONLY inside fill_polygon_aa (bonus).
Not allowed
    * Any ready-made drawing, clipping or polygon-filling function (Pillow ImageDraw, OpenCV,
      matplotlib, scikit-image, pygame.draw, ...), or hard-coding the ten star vertices.
Conventions: see the top of support.py.  Geometry is y-up (x to the right, y upward); pixel (i, j)
is the lattice point (i, j).  The image array is (H, W, 3) uint8 and put_pixel / fill_span convert y to
the array row for you.
"""
from __future__ import annotations

import math

import numpy as np

from support import block_mean, fill_span, get_region, polygon_bbox, put_pixel  # noqa: F401  (you will need them)

# Outcode bits for Cohen-Sutherland: [T B R L] as in Lecture 5 (y-up: TOP means y > ymax)
TOP, BOTTOM, RIGHT, LEFT = 8, 4, 2, 1


# ----------------------------------------------------------------------------
# Part 1 -- the star, built with five-fold rotational symmetry
# ----------------------------------------------------------------------------
def make_star_vertices(cx, cy, r_outer, r_inner, theta):
    """Return the 10 vertices of a five-pointed star as a list of (x, y) floats, in order around the star:
    outer, inner, outer, inner, ...

    * The star is centred at (cx, cy).  Vertex 0 is an OUTER vertex at distance r_outer from the centre
      in the direction theta (radians, counter-clockwise from the +x axis, as in y-up geometry).
    * Vertex 1 is the INNER vertex of the same sector: distance r_inner, direction theta + 36 degrees.
    * The other four outer/inner pairs are the same pair turned by 72, 144, 216 and 288 degrees about
      the centre.  Build the pair once and repeat it; do not type ten vertices by hand.
    * The coordinates stay floats: do not round them here.
    """
    raise NotImplementedError("TODO: star vertices")


# ----------------------------------------------------------------------------
# Part 2 -- Bresenham line
# ----------------------------------------------------------------------------
def draw_line_bresenham(img, x0, y0, x1, y1, color):
    """Draw the line from pixel (x0, y0) to pixel (x1, y1), both end pixels included.

    * Works for every direction and slope (all eight octants, horizontal, vertical,
      diagonal and a single point when the two ends are equal).
    * x0, y0, x1, y1 are integers.  Integer arithmetic only: no division and no floating
      point inside the loop.
    * Write pixels with put_pixel(img, x, y, color); it ignores positions outside the image.
    """
    raise NotImplementedError("TODO: Bresenham")


# ----------------------------------------------------------------------------
# Part 3 -- Cohen-Sutherland line clipping
# ----------------------------------------------------------------------------
def clip_line_cohen_sutherland(x0, y0, x1, y1, win):
    """Clip the segment (x0, y0)-(x1, y1) against the rectangle win = (xmin, ymin, xmax, ymax).

    * Coordinates are floats, y-up.  A point ON the boundary is inside.
    * Return (cx0, cy0, cx1, cy1) -- floats, the visible part of the segment, with the first
      point still being the one that comes from (x0, y0) -- or None if nothing is visible.
    * Do not round the result; the scene rounds the end points just before drawing.
    * Use the outcode bits TOP, BOTTOM, RIGHT, LEFT defined above, and recompute the outcode
      of an end point after you move it.
    """
    raise NotImplementedError("TODO: Cohen-Sutherland")


# ----------------------------------------------------------------------------
# Part 4 -- scan-line polygon fill, limited to the clipping window
# ----------------------------------------------------------------------------
def fill_polygon_scanline(img, polygon, color, win):
    """Fill the interior of `polygon` (list of (x, y) floats, any number of vertices >= 3,
    convex or concave, clockwise or counter-clockwise), but ONLY the part inside the window
    win = (xmin, ymin, xmax, ymax).

    * Pixel (i, j) is filled when the point (i, j) is inside the polygon (even-odd rule) AND
      xmin <= i <= xmax and ymin <= j <= ymax (the window includes its boundary).
      Pixels whose point lies exactly on an edge of the polygon are not checked by the tests;
      follow the vertex rule of Lecture 4 so that a vertex is never counted twice.
    * Use an edge table + active edge table.  Do not build a new, clipped polygon:
      process only the scan lines inside the window, and cut every span to [xmin, xmax].
    * Write each run of pixels with fill_span(img, y, x_first, x_last, color).
    * `img` can be an (H, W, 3) image or an (H, W) mask (the bonus uses a mask).
    * Polygons and windows may extend beyond the image; nothing must crash or wrap around.
    """
    raise NotImplementedError("TODO: scan-line fill")


# ----------------------------------------------------------------------------
# Bonus -- anti-aliasing by supersampling   (coverage = alpha, as in HW01)
# ----------------------------------------------------------------------------
def fill_polygon_aa(img, polygon, color, win, k=4):
    """Fill the part of `polygon` that lies inside `win` with anti-aliased edges, using k x k
    supersampling.   BONUS: the scene still works if this function is not written.

    Steps (see the assignment text):
      1. box = polygon_bbox(polygon, w, h), reduced to the pixels the window can touch --
         the only part of the image that can change
      2. mask = zeros of shape (box_h * k, box_w * k)
      3. move the polygon AND the window into the box and scale them by k, with the same map
             (x, y) -> (k*(x - bx0) + (k-1)/2,  k*(y - by0) + (k-1)/2)
         (the (k-1)/2 puts the k x k samples around the centre of their pixel)
      4. fill_polygon_scanline(mask, scaled_polygon, 1, scaled_window)      -- YOUR function
      5. coverage = block_mean(mask, k)                                      -- alpha of every pixel, 0..1
      6. blend over region = get_region(img, bx0, by0, bx1, by1):
             C_out = alpha*C_shape + (1 - alpha)*C_old
         and write the result back into the region (convert to uint8; rounding or truncation
         are both accepted)
    Pixels outside the box must not change.
    """
    raise NotImplementedError("TODO: anti-aliased fill (bonus)")
