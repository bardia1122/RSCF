"""
selfcheck.py -- run it to test your rasterize.py.  DO NOT EDIT.

    python selfcheck.py                  every required group (star, bresenham, clip, fill, frames)
    python selfcheck.py clip fill        only some:  star | bresenham | clip | fill | frames
    python selfcheck.py aa               the anti-aliasing bonus
    python selfcheck.py -v               show more details for failures

The grader uses the same kinds of tests with many more (and different) inputs, so passing
everything here is a good sign but not a promise.  Pictures that show where your output
differs are written to the folder selfcheck_out/ (they are drawn upright, y up).
"""
from __future__ import annotations

import base64
import contextlib
import json
import math
import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image

import scene
from support import save_image

HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = os.path.join(HERE, "golden")
OUT = "selfcheck_out"
VERBOSE = "-v" in sys.argv


# ----------------------------------------------------------------------------
class Timeout(Exception):
    pass


@contextlib.contextmanager
def time_limit(seconds):
    if hasattr(signal, "SIGALRM"):
        def handler(*_):
            raise Timeout()
        old = signal.signal(signal.SIGALRM, handler)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        try:
            yield
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
    else:
        yield


STATE = {"timeouts": 0}


def run(fn, *args, limit=3.0):
    if STATE["timeouts"] >= 3:
        return False, "skipped: earlier checks of this group already timed out (infinite loop?)"
    try:
        with time_limit(limit):
            return True, fn(*args)
    except Timeout:
        STATE["timeouts"] += 1
        return False, "took too long (infinite loop?)"
    except NotImplementedError as e:
        return False, f"not implemented yet ({e})"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


class Report:
    def __init__(self, title):
        self.title, self.rows, self.order = title, {}, []
        STATE["timeouts"] = 0

    def add(self, cat, ok, msg=""):
        if cat not in self.rows:
            self.rows[cat] = [0, 0, []]
            self.order.append(cat)
        r = self.rows[cat]
        r[1] += 1
        r[0] += 1 if ok else 0
        if not ok and msg and len(r[2]) < (4 if VERBOSE else 1):
            r[2].append(msg)

    def show(self):
        print(f"\n== {self.title} " + "=" * max(3, 66 - len(self.title)))
        good = tot = 0
        for cat in self.order:
            p, n, msgs = self.rows[cat]
            good, tot = good + p, tot + n
            print(f"  [{'PASS' if p == n else 'FAIL'}] {cat:<52s} {p}/{n}")
            for m in msgs:
                print(f"         e.g. {m}")
        print(f"  -> {good}/{tot} checks passed")
        return good, tot


def load(name):
    with open(os.path.join(GOLD, name)) as f:
        return json.load(f)


def unpack(b64, shape):
    bits = np.unpackbits(np.frombuffer(base64.b64decode(b64), np.uint8))
    return bits[:shape[0] * shape[1]].reshape(shape).astype(bool)


def geo(a):
    """Array order (row 0 = top) -> geometric order (index [y, x], y up)."""
    return a[::-1]


COLOR = (200, 100, 50)


# ----------------------------------------------------------------------------
# 1. The star: public examples (expected values from the formula in the assignment)
# ----------------------------------------------------------------------------
def check_star(impl):
    rep = Report("Star vertices (five-fold symmetry)")
    for case in load("star_cases.json"):
        cx, cy, ro, ri, th = case["args"]
        exp = [tuple(p) for p in case["expected"]]
        label = f"make_star_vertices({cx}, {cy}, {ro}, {ri}, {th:.4f})"
        ok, v = run(impl.make_star_vertices, cx, cy, ro, ri, th, limit=1.0)
        if not ok:
            rep.add("returns 10 vertices", False, f"{label}: {v}")
            rep.add("distance from the centre", False)
            rep.add("repeats every 72 degrees", False)
            rep.add("order and starting vertex", False)
            continue
        try:
            pts = [(float(p[0]), float(p[1])) for p in v]
        except Exception:  # noqa: BLE001
            rep.add("returns 10 vertices", False, f"{label}: must return a list of (x, y) pairs, got {v!r}")
            rep.add("distance from the centre", False)
            rep.add("repeats every 72 degrees", False)
            rep.add("order and starting vertex", False)
            continue
        tol = 1e-8 * (1.0 + ro + abs(cx) + abs(cy))
        rep.add("returns 10 vertices", len(pts) == 10, f"{label}: returned {len(pts)} vertices")
        if len(pts) != 10:
            rep.add("distance from the centre", False)
            rep.add("repeats every 72 degrees", False)
            rep.add("order and starting vertex", False)
            continue
        rep.add("distance from the centre",
                all(abs(math.hypot(p[0] - cx, p[1] - cy) - (ro if i % 2 == 0 else ri)) <= tol for i, p in enumerate(pts)),
                f"{label}: even-numbered vertices must be at distance r_outer and odd-numbered ones at r_inner")
        sym = False
        for sgn in (1, -1):
            c, s = math.cos(sgn * 2 * math.pi / 5), math.sin(sgn * 2 * math.pi / 5)
            good = True
            for i in range(10):
                px, py = pts[i][0] - cx, pts[i][1] - cy
                nx, ny = pts[(i + 2) % 10]
                if abs(c * px - s * py + cx - nx) > tol or abs(s * px + c * py + cy - ny) > tol:
                    good = False
                    break
            sym |= good
        rep.add("repeats every 72 degrees", sym, f"{label}: vertex i+2 must be vertex i turned by 72 degrees about the centre")
        dev = max(max(abs(p[0] - q[0]), abs(p[1] - q[1])) for p, q in zip(pts, exp))
        hint = "vertex 0 must be the outer vertex in direction theta; the others follow counter-clockwise, 36 degrees apart"
        if dev > tol:
            alt = pts[1:] + pts[:1]
            if max(max(abs(p[0] - q[0]), abs(p[1] - q[1])) for p, q in zip(alt, exp)) <= tol:
                hint = "the list starts with the inner vertex; it must start with the outer one"
            elif max(max(abs(p[0] - q[0]), abs(p[1] - q[1])) for p, q in zip([pts[0]] + pts[:0:-1], exp)) <= tol:
                hint = "the vertices go clockwise; they must go counter-clockwise (y up)"
        rep.add("order and starting vertex", dev <= tol,
                f"{label}: vertex 0 expected ({exp[0][0]:.3f}, {exp[0][1]:.3f}), got ({pts[0][0]:.3f}, {pts[0][1]:.3f}); {hint}")
    return rep.show()


# ----------------------------------------------------------------------------
# 2. Bresenham: a property test (any correct implementation passes)
# ----------------------------------------------------------------------------
def line_defect(pix, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    steep = abs(dy) > abs(dx)
    mj0, mj1, mn0, dmj, dmn = (y0, y1, x0, dy, dx) if steep else (x0, x1, y0, dx, dy)
    lo, hi = min(mj0, mj1), max(mj0, mj1)
    if len(pix) != hi - lo + 1:
        return f"expected {hi - lo + 1} pixels, got {len(pix)}"
    by_major = {}
    for (x, y) in pix:
        a, b = (y, x) if steep else (x, y)
        by_major.setdefault(a, []).append(b)
    for a in range(lo, hi + 1):
        bs = by_major.get(a, [])
        if len(bs) != 1:
            return f"step {a} of the major axis has {len(bs)} pixels (expected exactly 1)"
        b = bs[0]
        ok = (b == mn0) if dmj == 0 else abs(2 * dmj * (b - mn0) - 2 * (a - mj0) * dmn) <= abs(dmj)
        if not ok:
            return f"pixel ({b if steep else a}, {a if steep else b}) is more than half a pixel away from the ideal line"
    return None


def draw_set(impl, x0, y0, x1, y1):
    ox, oy = min(x0, x1) - 2, min(y0, y1) - 2
    w, h = abs(x1 - x0) + 5, abs(y1 - y0) + 5
    img = np.zeros((h, w, 3), np.uint8)
    impl.draw_line_bresenham(img, x0 - ox, y0 - oy, x1 - ox, y1 - oy, COLOR)
    rows, xs = np.nonzero(img.any(axis=2))
    ys = h - 1 - rows                                       # array row -> y (y up)
    bad = bool((img[rows, xs] != np.array(COLOR)).any()) if len(xs) else False
    return set(zip((xs + ox).tolist(), (ys + oy).tolist())), bad


def check_bresenham(impl):
    rep = Report("Bresenham line")
    rng = np.random.default_rng(7)

    def test(cat, x0, y0, x1, y1):
        ok, v = run(draw_set, impl, x0, y0, x1, y1)
        if not ok:
            rep.add(cat, False, f"line ({x0},{y0})->({x1},{y1}): {v}")
            return
        pix, bad = v
        msg = line_defect(pix, x0, y0, x1, y1) or ("wrong colour" if bad else None)
        rep.add(cat, msg is None, f"line ({x0},{y0})->({x1},{y1}): {msg}")

    for (ux, uy) in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]:
        for ln in (1, 2, 17):
            test("horizontal, vertical, diagonal", 30, 30, 30 + ux * ln, 30 + uy * ln)
    test("single point", 7, 9, 7, 9)
    for r in (23, 61):
        for deg in range(0, 360, 10):
            a = math.radians(deg)
            test("fan of lines (every octant)", 70, 70, 70 + round(r * math.cos(a)), 70 + round(r * math.sin(a)))
    for _ in range(40):
        x0, y0, x1, y1 = (int(v) for v in rng.integers(0, 90, 4))
        test("random lines, both directions", x0, y0, x1, y1)
        test("random lines, both directions", x1, y1, x0, y0)
    for _ in range(10):
        x0, y0 = (int(v) for v in rng.integers(0, 50, 2))
        test("long lines", x0, y0, x0 + int(rng.integers(300, 900)), y0 + int(rng.integers(-900, 900)))
    img = np.zeros((40, 40, 3), np.uint8)
    ok, v = run(lambda: impl.draw_line_bresenham(img, -100, -20, 150, 70, COLOR))
    rep.add("line that leaves the image (must not crash)", ok, v if not ok else "")
    return rep.show()


# ----------------------------------------------------------------------------
# 3. Cohen-Sutherland: public examples (expected values from an independent algorithm)
# ----------------------------------------------------------------------------
def check_clip(impl):
    rep = Report("Cohen-Sutherland clipping")
    for case in load("clip_cases.json"):
        win, seg, exp, touch, cat = tuple(case["win"]), case["seg"], case["expected"], case["touch"], case["cat"]
        ok, res = run(impl.clip_line_cohen_sutherland, *seg, win, limit=1.0)
        label = f"segment {tuple(round(v, 2) for v in seg)}, window {tuple(round(v, 2) for v in win)}"
        if not ok:
            rep.add(cat, False, f"{label}: {res}")
            continue
        scale = 1.0 + max(abs(v) for v in seg)
        if exp is None:
            rep.add(cat, res is None, f"{label}: should be rejected (None), got {res}")
            continue
        degenerate = math.hypot(exp[2] - exp[0], exp[3] - exp[1]) < 1e-7 * scale
        if res is None:
            rep.add(cat, touch or degenerate, f"{label}: expected {tuple(round(v, 3) for v in exp)}, got None")
            continue
        try:
            res = tuple(float(v) for v in res)
            good = len(res) == 4 and all(abs(a - b) <= 1e-6 * scale for a, b in zip(res, exp))
        except Exception:  # noqa: BLE001
            rep.add(cat, False, f"{label}: result must be a tuple of 4 numbers or None, got {res!r}")
            continue
        msg = f"{label}: expected {tuple(round(v, 4) for v in exp)}, got {tuple(round(v, 4) for v in res)}"
        if not good and all(abs(a - b) <= 1e-6 * scale for a, b in zip(res, (exp[2], exp[3], exp[0], exp[1]))):
            msg += "  (the end points are swapped: keep the order of the input)"
        rep.add(cat, good, msg)
    return rep.show()


# ----------------------------------------------------------------------------
# 4. Scan-line fill: public examples, compared pixel by pixel
# ----------------------------------------------------------------------------
def on_boundary(mask):
    p = np.pad(mask, 1, mode="edge")
    b = np.zeros_like(mask)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            b |= p[1 + dy:1 + dy + mask.shape[0], 1 + dx:1 + dx + mask.shape[1]] != mask
    return b


def diff_picture(path, got, exp, bad, win=None):
    """All arrays are in geometric order; the picture is saved upright."""
    img = np.zeros(got.shape + (3,), np.uint8)
    img[exp] = (70, 70, 70)
    img[got & exp] = (150, 150, 150)
    img[bad & got & ~exp] = (255, 60, 60)        # you filled, the oracle did not
    img[bad & ~got & exp] = (60, 140, 255)       # the oracle filled, you did not
    if win is not None:
        x0, y0, x1, y1 = (int(round(v)) for v in win)
        h, w = got.shape
        for x in range(max(x0, 0), min(x1, w - 1) + 1):
            for y in (y0, y1):
                if 0 <= y < h and not img[y, x].any():
                    img[y, x] = (40, 90, 40)
        for y in range(max(y0, 0), min(y1, h - 1) + 1):
            for x in (x0, x1):
                if 0 <= x < w and not img[y, x].any():
                    img[y, x] = (40, 90, 40)
    os.makedirs(OUT, exist_ok=True)
    save_image(img[::-1], path)


def check_fill(impl):
    rep = Report("Scan-line polygon fill (limited to the window)")
    for i, case in enumerate(load("fill_cases.json")):
        w, h = case["size"]
        poly = [tuple(p) for p in case["polygon"]]
        win = tuple(case["win"])
        exp, amb = unpack(case["inside"], (h, w)), unpack(case["ambiguous"], (h, w))
        img = np.zeros((h, w, 3), np.uint8)
        ok, v = run(impl.fill_polygon_scanline, img, poly, COLOR, win, limit=5.0)
        cat = case["name"]
        if not ok:
            rep.add(cat, False, v)
            continue
        got = geo(img.any(axis=2))
        bad = (got != exp) & ~amb
        n = int(bad.sum())
        if n == 0:
            rep.add(cat, True)
            continue
        interior = int((bad & ~on_boundary(exp)).sum())
        ys, xs = np.nonzero(bad)
        outside = int((got & ~exp & bad).sum())
        kind = "only along the edges (check the vertex rule and the span ends)" if interior == 0 else f"{interior} of them away from the edges"
        if case["name"].startswith("window") or case["name"].startswith("scene"):
            kind += f"; {outside} pixels were drawn but are outside the polygon or the window"
        path = f"{OUT}/fill_{i}.png"
        diff_picture(path, got, exp, bad, win)
        rep.add(cat, False, f"{n} wrong pixels, {kind}; first at x={xs[0]}, y={ys[0]}  (picture: {path}; red = extra, blue = missing, green = window)")
    m = np.zeros((200, 200), np.uint8)
    ok, v = run(impl.fill_polygon_scanline, m, [(30.3, 20.7), (170.2, 60.9), (80.6, 170.1)], 1, (0.0, 0.0, 199.0, 199.0), limit=5.0)
    rep.add("also works on an (H, W) mask", ok and m.any(), v if not ok else "nothing was drawn")
    return rep.show()


# ----------------------------------------------------------------------------
# 5. The live scene
# ----------------------------------------------------------------------------
def check_frames(impl):
    rep = Report("The live scene (frames at fixed times)")
    tot = scene.W * scene.H
    x0, y0, x1, y1 = scene.WINDOW
    outside = np.ones((scene.H, scene.W), bool)
    outside[scene.H - 1 - y1:scene.H - y0, x0:x1 + 1] = False            # everything except the window
    for c in load("frames.json"):
        gold = np.array(Image.open(os.path.join(GOLD, c["file"])).convert("RGB"), np.uint8)
        rp = {}
        ok, fr = run(scene.render_frame, c["t"], c["k"], c["wireframe"], impl, rp, limit=10.0)
        label = f"t = {c['t']:5.2f} s"
        if not ok:
            rep.add("frames match the examples", False, f"{label}: {fr}")
            rep.add("nothing is drawn on the frame", False)
            continue
        d = np.abs(fr.astype(int) - gold.astype(int)).max(axis=2)
        n = int((d > 8).sum())
        good = n <= 0.0015 * tot
        path = f"{OUT}/frame_t{c['t']:05.2f}_diff.png"
        if not good:
            os.makedirs(OUT, exist_ok=True)
            save_image(np.clip(np.stack([d * 6] * 3, -1), 0, 255).astype(np.uint8), path)
        rep.add("frames match the examples", good, f"{label}: {n} pixels differ  (picture: {path})")
        leak = int((d[outside] > 8).sum())
        rep.add("nothing is drawn on the frame", leak == 0, f"{label}: {leak} pixels outside the window differ from the example")
    return rep.show()


# ----------------------------------------------------------------------------
# Bonus: anti-aliasing
# ----------------------------------------------------------------------------
def check_aa(impl):
    rep = Report("Anti-aliasing bonus (supersampling -> coverage -> alpha blend)")
    aa = load("aa_cases.json")
    for c in aa["blend"]:                      # the worked example in the bonus section of the assignment
        img = np.zeros((6, 6, 3), np.uint8)
        img[:] = c["bg"]
        poly = [tuple(p) for p in c["polygon"]]
        ok, v = run(impl.fill_polygon_aa, img, poly, tuple(c["fg"]), tuple(c["win"]), c["k"])
        px, py = c["pixel"]
        g = geo(img)
        good = ok and (np.abs(g[py, px].astype(int) - np.array(c["expected"])) <= 1).all()
        rest = g.copy()
        rest[py, px] = c["bg"]
        good = good and (rest == np.array(c["bg"])).all()
        rep.add("blend: C = a*C_shape + (1-a)*C_old", good, v if not ok else
                f"alpha={c['alpha']}, k={c['k']}: pixel ({px}, {py}) should be {tuple(c['expected'])}, got {tuple(g[py, px].tolist())} (or other pixels changed)")
    for c in aa["fill"]:
        poly = [tuple(p) for p in c["polygon"]]
        win = tuple(c["win"])
        img = np.zeros((100, 100, 3), np.uint8)
        img[:] = scene.BG
        ok, v = run(impl.fill_polygon_aa, img, poly, scene.SHAPE, win, c["k"], limit=10.0)
        exp = np.array(Image.open(os.path.join(GOLD, c["expected"])).convert("RGB"), np.uint8)
        name = f"fill_polygon_aa: {c['name']}, k={c['k']}"
        if not ok:
            rep.add(name, False, v)
            continue
        d = np.abs(img.astype(int) - exp.astype(int)).max(axis=2)
        n = int((d > 3).sum())
        if n:
            ys, xs = np.nonzero(d > 3)
            path = f"{OUT}/aa_{c['name'].replace(' ', '_')}.png"
            os.makedirs(OUT, exist_ok=True)
            save_image(np.hstack([img, exp, np.clip(np.stack([d * 8] * 3, -1), 0, 255).astype(np.uint8)]), path)
            rep.add(name, False, f"{n} pixels differ; first at column {xs[0]}, row {ys[0]} of the picture: yours {img[ys[0], xs[0]].tolist()}, expected {exp[ys[0], xs[0]].tolist()}  (picture: {path}: yours | expected | difference x8)")
        else:
            part = int(((img != np.array(scene.BG)).any(axis=2) & (img != np.array(scene.SHAPE)).any(axis=2)).sum())
            rep.add(name, part > 0, "no partially covered pixels: is the result still binary?")
    tot = scene.W * scene.H
    for c in load("frames_aa.json"):
        gold = np.array(Image.open(os.path.join(GOLD, c["file"])).convert("RGB"), np.uint8)
        ok, fr = run(scene.render_frame, c["t"], c["k"], False, impl, {}, limit=10.0)
        if not ok:
            rep.add("anti-aliased frames match the examples", False, f"t = {c['t']}: {fr}")
            continue
        n = int((np.abs(fr.astype(int) - gold.astype(int)).max(axis=2) > 8).sum())
        rep.add("anti-aliased frames match the examples", n <= 0.0003 * tot, f"t = {c['t']:5.2f} s, k = {c['k']}: {n} pixels differ from the example frame")
    return rep.show()


REQUIRED = {"star": check_star, "bresenham": check_bresenham, "clip": check_clip, "fill": check_fill, "frames": check_frames}
GROUPS = dict(REQUIRED, aa=check_aa)


def main():
    names = [a for a in sys.argv[1:] if a in GROUPS] or list(REQUIRED)
    import rasterize as impl
    if not hasattr(signal, "SIGALRM"):
        print("note: on this system an infinite loop cannot be interrupted automatically; press Ctrl+C if a check hangs.")
    total = [0, 0]
    for n in names:
        g, t = GROUPS[n](impl)
        total[0] += g
        total[1] += t
    print(f"\nAll groups: {total[0]}/{total[1]} checks passed")


if __name__ == "__main__":
    main()
