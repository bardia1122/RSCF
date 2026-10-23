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

from support import block_mean, fill_span, get_region, polygon_bbox, put_pixel

TOP, BOTTOM, RIGHT, LEFT = 8, 4, 2, 1


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
    tips = 5
    step = 2 * math.pi / tips
    pair = [(r_outer, 0.0), (r_inner, step / 2)]

    points = []
    for i in range(tips):
        for r, offset in pair:
            angle = theta + i * step + offset
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return points


def draw_line_bresenham(img, x0, y0, x1, y1, color):
    """Draw the line from pixel (x0, y0) to pixel (x1, y1), both end pixels included.

    * Works for every direction and slope (all eight octants, horizontal, vertical,
      diagonal and a single point when the two ends are equal).
    * x0, y0, x1, y1 are integers.  Integer arithmetic only: no division and no floating
      point inside the loop.
    * Write pixels with put_pixel(img, x, y, color); it ignores positions outside the image.
    """
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x1 >= x0 else -1
    sy = 1 if y1 >= y0 else -1

    steep = dy > dx
    if steep:
        dx, dy = dy, dx

    p = 2 * dy - dx
    x, y = x0, y0
    for _ in range(dx + 1):
        put_pixel(img, x, y, color)
        if p >= 0:
            if steep:
                x += sx
            else:
                y += sy
            p -= 2 * dx
        p += 2 * dy
        if steep:
            y += sy
        else:
            x += sx


def clip_line_cohen_sutherland(x0, y0, x1, y1, win):
    """Clip the segment (x0, y0)-(x1, y1) against the rectangle win = (xmin, ymin, xmax, ymax).

    * Coordinates are floats, y-up.  A point ON the boundary is inside.
    * Return (cx0, cy0, cx1, cy1) -- floats, the visible part of the segment, with the first
      point still being the one that comes from (x0, y0) -- or None if nothing is visible.
    * Do not round the result; the scene rounds the end points just before drawing.
    * Use the outcode bits TOP, BOTTOM, RIGHT, LEFT defined above, and recompute the outcode
      of an end point after you move it.
    """
    xmin, ymin, xmax, ymax = map(float, win)

    def code(x, y):
        c = 0
        if y > ymax:
            c |= TOP
        elif y < ymin:
            c |= BOTTOM
        if x > xmax:
            c |= RIGHT
        elif x < xmin:
            c |= LEFT
        return c

    x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
    c0 = code(x0, y0)
    c1 = code(x1, y1)

    while True:
        if c0 == 0 and c1 == 0:
            return x0, y0, x1, y1
        if c0 & c1:
            return None

        c = c0 if c0 else c1
        if c & TOP:
            x = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0)
            y = ymax
        elif c & BOTTOM:
            x = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0)
            y = ymin
        elif c & RIGHT:
            y = y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
            x = xmax
        else:
            y = y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
            x = xmin

        if c == c0:
            x0, y0 = x, y
            c0 = code(x0, y0)
        else:
            x1, y1 = x, y
            c1 = code(x1, y1)


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
    xmin, ymin, xmax, ymax = win
    left_limit = math.ceil(xmin)
    right_limit = math.floor(xmax)
    first_row = max(math.ceil(ymin), 0)
    last_row = min(math.floor(ymax), img.shape[0] - 1)
    if left_limit > right_limit or first_row > last_row:
        return

    et = {}
    n = len(polygon)
    for i in range(n):
        xa, ya = polygon[i]
        xb, yb = polygon[(i + 1) % n]
        if ya == yb:
            continue
        if ya > yb:
            xa, ya, xb, yb = xb, yb, xa, ya
        start = math.ceil(ya)
        end = math.ceil(yb) - 1
        if start > end:
            continue
        slope = (xb - xa) / (yb - ya)
        et.setdefault(start, []).append([end, xa + (start - ya) * slope, slope])

    if not et:
        return

    y = max(first_row, min(et))
    top = min(last_row, max(e[0] for edges in et.values() for e in edges))

    aet = []
    for start, edges in et.items():
        if start <= y:
            for end, x, slope in edges:
                if end >= y:
                    aet.append([end, x + (y - start) * slope, slope])

    while y <= top:
        aet = [e for e in aet if e[0] >= y]

        xs = sorted(e[1] for e in aet)
        for i in range(0, len(xs) - 1, 2):
            a = max(math.ceil(xs[i]), left_limit)
            b = min(math.floor(xs[i + 1]), right_limit)
            if a <= b:
                fill_span(img, y, a, b, color)

        y += 1
        for e in aet:
            e[1] += e[2]
        for end, x, slope in et.get(y, []):
            aet.append([end, x, slope])


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
    k = max(1, int(k))
    h, w = img.shape[:2]

    box = polygon_bbox(polygon, w, h)
    if box is None:
        return
    xmin, ymin, xmax, ymax = win
    bx0 = max(box[0], math.floor(xmin + 0.5))
    by0 = max(box[1], math.floor(ymin + 0.5))
    bx1 = min(box[2], math.floor(xmax + 0.5))
    by1 = min(box[3], math.floor(ymax + 0.5))
    if bx0 > bx1 or by0 > by1:
        return

    mask = np.zeros(((by1 - by0 + 1) * k, (bx1 - bx0 + 1) * k), np.uint8)

    def scale(x, y):
        return k * (x - bx0) + (k - 1) / 2, k * (y - by0) + (k - 1) / 2

    big_poly = [scale(x, y) for x, y in polygon]
    wx0, wy0 = scale(xmin, ymin)
    wx1, wy1 = scale(xmax, ymax)
    fill_polygon_scanline(mask, big_poly, 1, (wx0, wy0, wx1, wy1))

    alpha = block_mean(mask, k)
    if img.ndim == 3:
        alpha = alpha[:, :, None]

    region = get_region(img, bx0, by0, bx1, by1)
    out = alpha * np.array(color, dtype=float) + (1 - alpha) * region.astype(float)
    region[:] = np.clip(np.round(out), 0, 255).astype(np.uint8)
