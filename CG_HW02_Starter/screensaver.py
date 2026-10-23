"""
screensaver.py -- live viewer, exporter and benchmark.  DO NOT EDIT.

    python screensaver.py                    live window (needs: pip install pygame)
    python screensaver.py --zoom 2           bigger window
    python screensaver.py --aa --k 8         start with anti-aliasing on (bonus; 8 x 8 samples)
    python screensaver.py --t0 8 --paused    start paused at t = 8 s (step with the arrow keys)
    python screensaver.py --export           save frame_noaa.png (and frame_aa.png if the bonus is done)
    python screensaver.py --export --t 7.5 --k 8 --crop 600 120 64 48 --crop-zoom 10
    python screensaver.py --bench            bonus: time per frame and anti-aliasing error for k = 1, 2, 4, 8, 16
    python screensaver.py --gif demo.gif --seconds 6

Keys:  A  anti-aliasing on/off (bonus)    K  change k (2, 3, 4, 6, 8)    W  wireframe
       SPACE  pause      LEFT / RIGHT  step 1/30 s while paused    S  save PNG    ESC  quit
"""
from __future__ import annotations

import argparse
import os
import sys
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

import scene
from support import save_image

KS = [2, 3, 4, 6, 8]


def load_impl():
    import rasterize
    return rasterize


def _implemented(fn, *args):
    """False if the function still raises NotImplementedError (unfinished starter code)."""
    try:
        fn(*args)
        return True
    except NotImplementedError:
        return False
    except Exception:  # noqa: BLE001  (a bug is not the same as 'not written')
        return True


def export(args, impl):
    rep = {}
    t = scene.EXPORT_T if args.t is None else args.t
    a = scene.render_frame(t, aa_k=1, wireframe=True, impl=impl, report=rep)
    save_image(a, "frame_noaa.png")
    print(f"saved frame_noaa.png (k=1, with the star's outline) for t = {t} s")
    rep_aa = {}
    b = scene.render_frame(t, aa_k=args.k, wireframe=False, impl=impl, report=rep_aa)
    bonus = _implemented(impl.fill_polygon_aa, np.zeros((8, 8, 3), np.uint8), [(1.0, 1.0), (5.0, 1.0), (3.0, 5.0)], (255, 0, 0), (0.0, 0.0, 7.0, 7.0), 2)
    if bonus:
        save_image(b, "frame_aa.png")
        print(f"saved frame_aa.png (k={args.k}) for t = {t} s")
    else:
        print("frame_aa.png not written: fill_polygon_aa (bonus) is not implemented yet")
    if args.crop:
        x, y, w, h = args.crop                      # lower-left corner (x, y) in scene coordinates (y up) and the size
        z = args.crop_zoom
        H = scene.H
        plain = scene.render_frame(t, aa_k=1, wireframe=False, impl=impl, report=rep)   # fair comparison: no wireframe
        tiles = []
        for name, im in (("noaa", plain), ("aa", b)):
            if name == "aa" and not bonus:
                continue
            c = np.kron(im[H - (y + h):H - y, x:x + w], np.ones((z, z, 1), np.uint8))
            save_image(c, f"crop_{name}.png")
            tiles.append(c)
        if len(tiles) == 2:
            sep = np.full((tiles[0].shape[0], 8, 3), 255, np.uint8)
            save_image(np.hstack([tiles[0], sep, tiles[1]]), "crop_compare.png")
            print("saved crop_noaa.png, crop_aa.png and crop_compare.png")
        else:
            print("saved crop_noaa.png")
    missing = rep["missing"] | (rep_aa["missing"] - {"fill_polygon_aa"})
    if missing:
        print("not implemented yet:", ", ".join(sorted(missing)))


def bench(args, impl):
    rep = {}
    scene.render_frame(1.0, aa_k=2, wireframe=False, impl=impl, report=rep)
    unfinished = not _implemented(impl.fill_polygon_aa, np.zeros((8, 8, 3), np.uint8), [(1.0, 1.0), (5.0, 1.0), (3.0, 5.0)], (255, 0, 0), (0.0, 0.0, 7.0, 7.0), 2)
    if unfinished or rep["missing"] & {"fill_polygon_scanline", "make_star_vertices"}:
        sys.exit("--bench measures the anti-aliasing bonus: finish make_star_vertices, fill_polygon_scanline and fill_polygon_aa first.")
    times = [2.0 + 0.37 * i for i in range(12)]
    ref = [scene.render_frame(t, aa_k=16, wireframe=False, impl=impl) for t in times]
    print("   k   samples   ms/frame      fps    error vs k=16 (mean |diff| around the star, 0..255)")
    for k in (1, 2, 4, 8, 16):
        t0 = time.perf_counter()
        frames = [scene.render_frame(t, aa_k=k, wireframe=False, impl=impl) for t in times]
        ms = (time.perf_counter() - t0) / len(times) * 1000
        errs = []
        for f, r, t in zip(frames, ref, times):
            cx, cy = scene.motion(t)[:2]
            x0, y0 = max(int(cx - 90), 0), max(int(cy - 90), 0)
            fg, rg = f[::-1], r[::-1]                       # geometric order (y up)
            errs.append(np.abs(fg[y0:y0 + 180, x0:x0 + 180].astype(float) - rg[y0:y0 + 180, x0:x0 + 180].astype(float)).mean())
        print(f"{k:4d}   {k * k:7d}   {ms:8.1f}   {1000 / ms:7.1f}    {np.mean(errs):8.3f}")


def make_gif(args, impl):
    from PIL import Image
    n = int(args.seconds * args.fps)
    frames = []
    for i in range(n):
        im = scene.render_frame(args.t0 + i / args.fps, aa_k=args.k if args.aa else 1, wireframe=not args.aa, impl=impl)
        frames.append(Image.fromarray(im).quantize(colors=96, dither=Image.Dither.NONE))
    frames[0].save(args.gif, save_all=True, append_images=frames[1:], duration=int(1000 / args.fps), loop=0, optimize=True)
    print(f"saved {args.gif}: {n} frames")


def live(args, impl):
    try:
        import pygame
    except ImportError:
        sys.exit("pygame is not installed.  Run:  pip install pygame     (or use --export / --gif)")
    pygame.init()
    z = args.zoom
    screen = pygame.display.set_mode((scene.W * z, scene.H * z))
    pygame.display.set_caption("Screensaver - Computer Graphics HW02")
    font = pygame.font.SysFont("consolas,menlo,dejavusansmono,couriernew,monospace", 14)
    clock = pygame.time.Clock()
    aa, ki, wire = args.aa, KS.index(args.k) if args.k in KS else 2, not args.aa
    t, paused, running, frames_seen = args.t0, args.paused, True, 0
    started = time.perf_counter()
    fps_hist = []
    while running:
        dt = clock.tick(60) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_a:
                    aa = not aa
                    wire = wire and not aa                      # wireframe hides the smooth edge
                elif e.key == pygame.K_k:
                    ki = (ki + 1) % len(KS)
                elif e.key == pygame.K_w:
                    wire = not wire
                elif e.key == pygame.K_SPACE:
                    paused = not paused
                elif e.key == pygame.K_LEFT and paused:
                    t = max(0.0, t - 1 / 30)
                elif e.key == pygame.K_RIGHT and paused:
                    t += 1 / 30
                elif e.key == pygame.K_s:
                    name = f"screenshot_t{t:.2f}.png"
                    save_image(scene.render_frame(t, aa_k=KS[ki] if aa else 1, wireframe=wire, impl=impl), name)
                    print("saved", name)
        if not paused:
            t += min(dt, 0.1)               # same idea as the dt clamp of the SceneLab Application
        k = KS[ki] if aa else 1
        rep = {}
        frame = scene.render_frame(t, aa_k=k, wireframe=wire, impl=impl, report=rep)
        surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        if z > 1:
            surf = pygame.transform.scale(surf, (scene.W * z, scene.H * z))
        screen.blit(surf, (0, 0))
        fps = clock.get_fps()
        fps_hist.append(fps)
        hud = f"t = {t:6.2f} s   fps {fps:4.0f}   AA: {'%dx%d' % (k, k) if k > 1 else 'off'}   wireframe: {'on' if wire else 'off'}"
        screen.blit(font.render(hud, True, (200, 210, 225)), (12 * z, 12 * z))
        keys = "A anti-aliasing (bonus)   K samples   W wireframe   SPACE pause   <- -> step   S save   ESC quit"
        screen.blit(font.render(keys, True, (110, 122, 143)), (12 * z, (scene.H - 26) * z))
        if rep["missing"]:
            msg = "not implemented yet: " + ", ".join(sorted(rep["missing"]))
            surf2 = font.render(msg, True, (255, 140, 120))
            screen.blit(surf2, ((scene.W * z - surf2.get_width()) // 2, (scene.H // 2) * z))
        pygame.display.flip()
        frames_seen += 1
        if args.duration and time.perf_counter() - started > args.duration:
            if args.screenshot:
                pygame.image.save(screen, args.screenshot)
            ok = [f for f in fps_hist[10:] if f > 0]
            print(f"ran {frames_seen} frames, average fps {np.mean(ok) if ok else 0:.1f}")
            running = False
    pygame.quit()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zoom", type=int, default=1)
    ap.add_argument("--k", type=int, default=4, help="samples per pixel side for anti-aliasing (bonus)")
    ap.add_argument("--aa", action="store_true", help="start with anti-aliasing on (bonus)")
    ap.add_argument("--t0", type=float, default=0.0, help="start time in seconds")
    ap.add_argument("--paused", action="store_true", help="start paused")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--t", type=float, default=None, help="time of the exported frame (default: a moment where the star is cut by the window)")
    ap.add_argument("--crop", type=int, nargs=4, metavar=("X", "Y", "W", "H"),
                    help="with --export: magnify the piece with lower-left corner (X, Y) (scene coordinates, y up) and size W x H")
    ap.add_argument("--crop-zoom", type=int, default=8)
    ap.add_argument("--bench", action="store_true")
    ap.add_argument("--gif")
    ap.add_argument("--seconds", type=float, default=6.0)
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--duration", type=float, default=0.0, help="quit automatically after this many seconds")
    ap.add_argument("--screenshot", help="with --duration: save the window to this PNG before quitting")
    args = ap.parse_args()
    impl = load_impl()
    if args.export:
        export(args, impl)
    elif args.bench:
        bench(args, impl)
    elif args.gif:
        make_gif(args, impl)
    else:
        live(args, impl)


if __name__ == "__main__":
    main()
