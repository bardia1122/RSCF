"""
scene.py -- the screensaver scene.  DO NOT EDIT.

A five-pointed star drifts and spins inside a frame.  The frame is a big outer rectangle
and, inside it, a smaller rectangle: the clipping window.  The star moves anywhere inside the
outer rectangle and may slide under the frame, but only the part of the star that lies inside
the clipping window must be visible.

Everything is a pure function of the time t (in seconds), so the picture for a given t is
always the same, no matter how fast or slow your computer is.  The same code is used by the
live viewer (screensaver.py), by the exporter and by the grader.

Geometry is y-up (see support.py).  What your rasterize.py does, every frame:

    make_star_vertices           the 10 vertices of the star, from its centre, radii and angle
    fill_polygon_scanline        the star, filled; every span is limited to the window (k = 1)
    fill_polygon_aa              the same with anti-aliasing (bonus, k > 1)
    clip_line_cohen_sutherland   each of the 10 edges of the star is clipped to the window ...
    draw_line_bresenham          ... and the visible piece (rounded to pixels) is drawn;
                                 the frame, the window and the grid are drawn with it too
"""
from __future__ import annotations

import math

import numpy as np

# ----------------------------------------------------------------------------
# geometry and colours   (rectangles are (xmin, ymin, xmax, ymax), inclusive pixel bounds, y-up)
# ----------------------------------------------------------------------------
W, H = 800, 520                                   # canvas size in pixels
OUTER = (40, 40, 759, 479)                        # the outer rectangle: the star never leaves it
WINDOW = (120, 120, 679, 399)                     # the clipping window (the opening of the frame)
GRID_STEP = 40

R_OUT, R_IN, N_TIPS = 84.0, 38.0, 5               # star: tip radius, notch radius, number of tips
# The centre of the star moves inside ARENA = OUTER shrunk by the star's radius,
# so the whole star always stays inside the outer rectangle.
ARENA = (OUTER[0] + R_OUT + 2, OUTER[1] + R_OUT + 2, OUTER[2] - R_OUT - 2, OUTER[3] - R_OUT - 2)

P0 = (300.0, 210.0)                               # centre at t = 0   (px)
V = (173.0, 119.0)                                # velocity          (px / s)
OMEGA = math.radians(22.0)                        # spin, counter-clockwise (rad / s)
THETA0 = math.pi / 2                              # a tip points up at t = 0
EXPORT_T = 8.2                                    # the time used by `screensaver.py --export`

BG = (18, 21, 28)
FRAME_FILL = (52, 60, 78)                         # the frame: the band between the two rectangles
WINDOW_FILL = (25, 29, 38)
GRID = (37, 43, 56)
OUTER_LINE = (126, 139, 160)
WINDOW_LINE = (96, 165, 250)
SHAPE = (255, 176, 46)
WIRE = (255, 236, 190)


# ----------------------------------------------------------------------------
# motion: closed form, so it does not depend on the frame rate
# ----------------------------------------------------------------------------
def _fold(p0: float, v: float, lo: float, hi: float, t: float):
    """Position of a point that starts at p0 with velocity v and bounces between lo and hi."""
    length = hi - lo
    m = (p0 - lo + v * t) % (2.0 * length)
    return lo + m if m <= length else lo + 2.0 * length - m


def motion(t: float):
    """State at time t: (cx, cy, theta)  -- star centre and the angle of its first tip."""
    return (_fold(P0[0], V[0], ARENA[0], ARENA[2], t),
            _fold(P0[1], V[1], ARENA[1], ARENA[3], t),
            THETA0 + OMEGA * t)


# ----------------------------------------------------------------------------
# drawing
# ----------------------------------------------------------------------------
def _snap(v: float) -> int:
    """Round to the nearest integer (halves go up)."""
    return math.floor(v + 0.5)


def _call(rep, name, fn, *args):
    try:
        return fn(*args)
    except NotImplementedError:
        rep["missing"].add(name)
        return None


def _line(img, impl, rep, p, q, color):
    _call(rep, "draw_line_bresenham", impl.draw_line_bresenham, img,
          _snap(p[0]), _snap(p[1]), _snap(q[0]), _snap(q[1]), color)


def _rect_fill(img, rect, color):
    x0, y0, x1, y1 = rect
    img[H - 1 - y1:H - y0, x0:x1 + 1] = color           # y-up -> array rows


def _rect_outline(img, impl, rep, rect, color):
    x0, y0, x1, y1 = rect
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        _line(img, impl, rep, a, b, color)


_BG_CACHE: dict = {}


def static_background(impl, rep=None):
    """Canvas, frame, window and grid -- drawn once per implementation and cached."""
    key = id(impl)
    if key in _BG_CACHE:
        return _BG_CACHE[key]
    rep = rep if rep is not None else {"missing": set()}
    img = np.empty((H, W, 3), np.uint8)
    img[:] = BG
    _rect_fill(img, OUTER, FRAME_FILL)
    _rect_fill(img, WINDOW, WINDOW_FILL)
    x0, y0, x1, y1 = WINDOW
    for gx in range(x0 + GRID_STEP, x1, GRID_STEP):
        _line(img, impl, rep, (gx, y0 + 1), (gx, y1 - 1), GRID)
    for gy in range(y0 + GRID_STEP, y1, GRID_STEP):
        _line(img, impl, rep, (x0 + 1, gy), (x1 - 1, gy), GRID)
    if not rep["missing"]:
        _BG_CACHE[key] = img
    return img


def star_outline(img, verts, impl, rep):
    """The wireframe: every edge of the star is clipped to the window by YOUR Cohen-Sutherland
    function, rounded to integers and drawn by YOUR Bresenham function."""
    n = len(verts)
    for i in range(n):
        (xa, ya), (xb, yb) = verts[i], verts[(i + 1) % n]
        seg = _call(rep, "clip_line_cohen_sutherland", impl.clip_line_cohen_sutherland, xa, ya, xb, yb, WINDOW)
        if seg is not None:
            _line(img, impl, rep, (seg[0], seg[1]), (seg[2], seg[3]), WIRE)


def render_frame(t: float, aa_k: int = 1, wireframe: bool = True, impl=None,
                 report: dict | None = None) -> np.ndarray:
    """Render the picture for time t.  Returns an (H, W, 3) uint8 array.

    aa_k       1 = no anti-aliasing; k > 1 = supersampling with k x k samples per pixel (bonus)
    wireframe  also draw the star's outline (Cohen-Sutherland + Bresenham)
    impl       module providing the functions (default: rasterize)
    report     optional dict; report["missing"] receives the names of unfinished functions
    """
    if impl is None:
        import rasterize as impl
    rep = report if report is not None else {}
    rep.setdefault("missing", set())
    img = static_background(impl, rep).copy()
    cx, cy, theta = motion(t)

    verts = _call(rep, "make_star_vertices", impl.make_star_vertices, cx, cy, R_OUT, R_IN, theta)
    if verts is not None:
        if aa_k <= 1:
            _call(rep, "fill_polygon_scanline", impl.fill_polygon_scanline, img, verts, SHAPE, WINDOW)
        else:
            _call(rep, "fill_polygon_aa", impl.fill_polygon_aa, img, verts, SHAPE, WINDOW, aa_k)
        if wireframe:
            star_outline(img, verts, impl, rep)
    # the two rectangles are drawn last, so the edge of the window stays crisp
    _rect_outline(img, impl, rep, OUTER, OUTER_LINE)
    _rect_outline(img, impl, rep, WINDOW, WINDOW_LINE)
    return img
