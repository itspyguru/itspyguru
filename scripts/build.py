#!/usr/bin/env python3
"""Build the itspyguru profile page.

Draws "pyGuru Run": the last year of GitHub contributions as platforms on the
Varanasi ghats, with a pixel runner hopping across them. Also draws one game
cartridge per pinned repo and rewrites the "Now playing" block in README.md.

Standard library only. Text is drawn as pixel rectangles because GitHub serves
README SVGs as images, which cannot load web fonts.

    python3 scripts/build.py                         # live (GITHUB_TOKEN or gh auth token)
    python3 scripts/build.py --offline scripts/fixtures.json
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
USER = "itspyguru"
SHELF = ["Python-Games", "Python-on-WhatsApp", "Python-Projects",
         "Tkinter-Applications", "python-from-scratch", "Decrypto"]
NOW_SKIP = {"itspyguru", "itspyguru.github.io"}

QUERY = """query($login:String!){user(login:$login){
 contributionsCollection{contributionCalendar{totalContributions
   weeks{contributionDays{date contributionCount}}}}
 repositories(first:100, privacy:PUBLIC, ownerAffiliations:OWNER,
   orderBy:{field:PUSHED_AT,direction:DESC}){nodes{name description url
   stargazerCount pushedAt isFork isArchived primaryLanguage{name color}}}}}"""

# --------------------------------------------------------------------------
# data

def token():
    for k in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(k):
            return os.environ[k]
    return subprocess.run(["gh", "auth", "token"], capture_output=True,
                          text=True, check=True).stdout.strip()


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token()}", "Content-Type": "application/json",
        "User-Agent": "pyguru-run"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL errors: {data['errors']}")
    return data


def streak(days):
    counts = [d["contributionCount"] for d in days]
    if counts and counts[-1] == 0:  # today may not have started yet
        counts = counts[:-1]
    n = 0
    for c in reversed(counts):
        if c == 0:
            break
        n += 1
    return n

# --------------------------------------------------------------------------
# pixel font (5x7)

GLYPHS = {
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    "F": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    "G": [" ####", "#    ", "#    ", "#  ##", "#   #", "#   #", " ####"],
    "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "I": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"],
    "J": ["  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "],
    "K": ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    "R": ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", "#   #", " # # ", " # # ", "  #  "],
    "W": ["#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"],
    "X": ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    "Y": ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
    "0": [" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "3": ["#### ", "    #", "    #", " ### ", "    #", "    #", "#### "],
    "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    "6": [" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    "9": [" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "],
    " ": ["     "] * 7,
    "*": ["  #  ", "  #  ", "#####", " ### ", " # # ", "#   #", "     "],
    "-": ["     ", "     ", "     ", "#####", "     ", "     ", "     "],
    ".": ["     ", "     ", "     ", "     ", "     ", "     ", "  #  "],
    ":": ["     ", "  #  ", "     ", "     ", "     ", "  #  ", "     "],
    "/": ["    #", "    #", "   # ", "  #  ", " #   ", "#    ", "#    "],
    "+": ["     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "],
    ">": ["#    ", " #   ", "  #  ", "   # ", "  #  ", " #   ", "#    "],
    "_": ["     ", "     ", "     ", "     ", "     ", "     ", "#####"],
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def text_d(s, x, y, scale):
    """SVG path data drawing `s` in the pixel font, top-left at (x, y)."""
    out = []
    for i, ch in enumerate(s.upper()):
        g = GLYPHS.get(ch, GLYPHS[" "])
        for r, row in enumerate(g):
            c = 0
            while c < 5:  # merge horizontal runs into one rect
                if row[c] == "#":
                    run = 1
                    while c + run < 5 and row[c + run] == "#":
                        run += 1
                    px = x + (i * 6 + c) * scale
                    out.append(f"M{px} {y + r * scale}h{run * scale}v{scale}h-{run * scale}z")
                    c += run
                else:
                    c += 1
    return "".join(out)


def text(s, x, y, scale, fill, shadow=None, cls="", anchor="start"):
    if anchor == "middle":
        x = round(x - text_width(s, scale) / 2)
    parts = []
    if shadow:
        parts.append(f'<path d="{text_d(s, x + scale, y + scale, scale)}" fill="{shadow}"/>')
    parts.append(f'<path d="{text_d(s, x, y, scale)}" fill="{fill}"/>')
    c = f' class="{cls}"' if cls else ""
    return f"<g{c}>{''.join(parts)}</g>"

# --------------------------------------------------------------------------
# header: pyGuru Run

W, H = 960, 300
GROUND = 236
COL_W = 16
MAX_H = 84

THEMES = {
    "dark": dict(
        sky=["#070b1f", "#131640", "#2a1f5c", "#4a2b6b"],
        far="#1a1745", near="#100e2e", window="#ffcf5a", stone="#2d2a55",
        stone2="#3a3670", river=["#1a1c4a", "#0a0b24"], shimmer="#6b74d6",
        stars=1.0, moon=True, hud="#ffffff", hud_shadow="#0a0b24",
        greens=["#123a2a", "#0e6b38", "#26a641", "#39d353"], zero="#2d2a55",
        accent="#ffd43b"),
    "light": dict(
        sky=["#3b2d6b", "#8e4d8f", "#e9787a", "#ffc380"],
        far="#7a3d72", near="#4a2350", window="#ffe08a", stone="#6e3a63",
        stone2="#8a4b78", river=["#c76d7c", "#5c2f61"], shimmer="#ffd3a1",
        stars=0.45, moon=False, hud="#ffffff", hud_shadow="#3b1d44",
        greens=["#1f6b45", "#1e8a48", "#2fb553", "#4be06a"], zero="#6e3a63",
        accent="#ffd43b"),
}

SPRITE_TOP = [
    "...HHHH.",
    "..HHHHHH",
    "YY.YYYYY",
    ".Y.SSESS",
    "...SSSSS",
    "...BBBB.",
    "..BBBBBS",
    "..BBBB..",
]
LEGS_A = [".PP..PP.", "WW....WW"]
LEGS_B = ["...PP...", "...WW..."]
SPRITE_COLORS = {"H": "#1b1b2f", "Y": "#ffd43b", "S": "#f1c27d", "E": "#111111",
                 "B": "#3776ab", "P": "#23253a", "W": "#f4f4f4"}
PX = 3  # sprite pixel size -> 24x30 runner


def sprite_rects(rows, y0=0):
    out = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch in SPRITE_COLORS:
                out.append(f'<rect x="{c * PX}" y="{(y0 + r) * PX}" width="{PX}" '
                           f'height="{PX}" fill="{SPRITE_COLORS[ch]}"/>')
    return "".join(out)


def snap(v, g=4):
    return int(round(v / g) * g)


def skyline(t, rng):
    """Procedural ghat skyline: shikhara temples, havelis, chhatris."""
    far, near = [], []
    # far layer: low haze of buildings
    x = 0
    while x < W:
        w = rng.choice([24, 32, 40, 48])
        h = rng.choice([40, 52, 60, 72])
        far.append(f'<rect x="{x}" y="{GROUND - h}" width="{w}" height="{h}"/>')
        if rng.random() < 0.4:  # small dome
            far.append(f'<rect x="{x + w // 2 - 6}" y="{GROUND - h - 8}" width="12" height="8"/>'
                       f'<rect x="{x + w // 2 - 2}" y="{GROUND - h - 12}" width="4" height="4"/>')
        x += w
    # near layer
    x = -8
    windows, flags = [], []
    while x < W:
        kind = rng.choices(["temple", "haveli", "chhatri"], [3, 4, 2])[0]
        if kind == "temple":
            base_w = rng.choice([40, 48, 56])
            base_h = rng.choice([28, 36])
            y = GROUND - base_h
            near.append(f'<rect x="{x}" y="{y}" width="{base_w}" height="{base_h}"/>')
            # stepped shikhara
            w, cx = base_w - 8, x + base_w // 2
            levels = rng.choice([5, 6, 7])
            for _ in range(levels):
                near.append(f'<rect x="{cx - w // 2}" y="{y - 8}" width="{w}" height="8"/>')
                y -= 8
                w = max(8, w - rng.choice([4, 8]))
            near.append(f'<rect x="{cx - 2}" y="{y - 8}" width="4" height="8"/>')
            near.append(f'<rect x="{cx - 4}" y="{y - 4}" width="8" height="4"/>')
            # saffron flag on the spire
            flags.append(f'<g class="flag" style="transform-origin:{cx + 2}px {y - 20}px">'
                         f'<rect x="{cx}" y="{y - 24}" width="2" height="16" fill="{t["near"]}"/>'
                         f'<path d="M{cx + 2} {y - 24}h12l-4 4 4 4h-12z" fill="#ff8a1f"/></g>')
            x += base_w + rng.choice([0, 4, 8])
        elif kind == "haveli":
            w = rng.choice([40, 48, 56, 64])
            h = rng.choice([56, 64, 72, 80])
            near.append(f'<rect x="{x}" y="{GROUND - h}" width="{w}" height="{h}"/>')
            # parapet teeth
            for px in range(x, x + w, 8):
                near.append(f'<rect x="{px}" y="{GROUND - h - 4}" width="4" height="4"/>')
            for wy in range(GROUND - h + 8, GROUND - 12, 16):
                for wx in range(x + 8, x + w - 8, 12):
                    if rng.random() < 0.35:
                        d = round(rng.uniform(0, 6), 2)
                        windows.append(f'<rect class="win" style="animation-delay:-{d}s" '
                                       f'x="{wx}" y="{wy}" width="4" height="6"/>')
            x += w
        else:
            w = 24
            h = rng.choice([24, 32])
            near.append(f'<rect x="{x + 2}" y="{GROUND - h}" width="4" height="{h}"/>'
                        f'<rect x="{x + w - 6}" y="{GROUND - h}" width="4" height="{h}"/>'
                        f'<rect x="{x}" y="{GROUND - h - 4}" width="{w}" height="4"/>'
                        f'<rect x="{x + 4}" y="{GROUND - h - 12}" width="{w - 8}" height="8"/>'
                        f'<rect x="{x + 8}" y="{GROUND - h - 16}" width="{w - 16}" height="4"/>'
                        f'<rect x="{x + 10}" y="{GROUND - h - 20}" width="4" height="4"/>')
            x += w + 4
    return (f'<g fill="{t["far"]}">{"".join(far)}</g>'
            f'<g fill="{t["near"]}">{"".join(near)}</g>'
            f'<g fill="{t["window"]}">{"".join(windows)}</g>{"".join(flags)}')


def header(theme, cal, today):
    t = THEMES[theme]
    rng = random.Random(f"pyguru-{theme}")
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    total, n = cal["totalContributions"], len(weeks)
    peak = max(weeks) or 1
    nz = sorted(c for c in weeks if c)
    q = [nz[int(len(nz) * f)] for f in (0.25, 0.5, 0.75)] if nz else [1, 2, 3]

    x0 = (W - n * COL_W) // 2
    cols = []
    for i, c in enumerate(weeks):
        h = 4 if c == 0 else 8 + snap(math.sqrt(c / peak) * (MAX_H - 8))
        lvl = 0 if c <= q[0] else 1 if c <= q[1] else 2 if c <= q[2] else 3
        cols.append(dict(x=x0 + i * COL_W, top=GROUND - h, h=h, c=c,
                         fill=t["zero"] if c == 0 else t["greens"][lvl]))

    T = 14.0           # loop length, seconds
    RUN = 0.86         # share of the loop spent running the columns
    css, body = [], []

    # sky
    stops = "".join(f'<stop offset="{i / (len(t["sky"]) - 1):.2f}" stop-color="{c}"/>'
                    for i, c in enumerate(t["sky"]))
    rstops = (f'<stop offset="0" stop-color="{t["river"][0]}"/>'
              f'<stop offset="1" stop-color="{t["river"][1]}"/>')
    defs = (f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>'
            f'<linearGradient id="river" x1="0" y1="0" x2="0" y2="1">{rstops}</linearGradient>'
            f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="16"/></clipPath>')
    body.append(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')

    # stars
    stars = []
    for _ in range(int(90 * t["stars"])):
        sx, sy = snap(rng.uniform(8, W - 8), 2), snap(rng.uniform(6, 150), 2)
        d, dur = round(rng.uniform(0, 4), 2), round(rng.uniform(2.5, 5), 2)
        if rng.random() < 0.15:  # plus-shaped bright star
            stars.append(f'<g class="tw" style="animation-delay:-{d}s;animation-duration:{dur}s">'
                         f'<rect x="{sx - 2}" y="{sy}" width="6" height="2"/>'
                         f'<rect x="{sx}" y="{sy - 2}" width="2" height="6"/></g>')
        else:
            stars.append(f'<rect class="tw" style="animation-delay:-{d}s;animation-duration:{dur}s" '
                         f'x="{sx}" y="{sy}" width="2" height="2"/>')
    body.append(f'<g fill="#ffffff">{"".join(stars)}</g>')
    body.append('<g class="shoot"><rect x="0" y="0" width="4" height="2" fill="#fff"/>'
                '<rect x="-12" y="-2" width="12" height="2" fill="#fff" opacity=".6"/>'
                '<rect x="-28" y="-4" width="16" height="2" fill="#fff" opacity=".3"/></g>')

    # moon (dark) or setting sun (light)
    if t["moon"]:
        mx, my, mr = 800, 84, 18
        moon = []
        for yy in range(-mr, mr + 1, 2):
            half = int(math.sqrt(max(0, mr * mr - yy * yy)))
            moon.append(f'<rect x="{mx - half}" y="{my + yy}" width="{half * 2}" height="2"/>')
        body.append(f'<g fill="#fff4d6">{"".join(moon)}</g>'
                    f'<rect x="{mx - 8}" y="{my - 6}" width="6" height="4" fill="#e8dcb8"/>'
                    f'<rect x="{mx + 4}" y="{my + 6}" width="4" height="4" fill="#e8dcb8"/>')
        reflect_x, reflect_c = mx, "#fff4d6"
    else:
        sx, sy, sr = 660, 190, 40
        sun = []
        for yy in range(-sr, 1, 2):
            half = int(math.sqrt(max(0, sr * sr - yy * yy)))
            sun.append(f'<rect x="{sx - half}" y="{sy + yy}" width="{half * 2}" height="2"/>')
        body.append(f'<g fill="#ffe3a3" opacity=".9">{"".join(sun)}</g>')
        reflect_x, reflect_c = sx, "#ffe3a3"

    # skyline
    body.append(skyline(t, rng))

    # ghat steps
    for k, (y, h) in enumerate([(GROUND, 6), (GROUND + 6, 6), (GROUND + 12, 6)]):
        body.append(f'<rect x="0" y="{y}" width="{W}" height="{h}" '
                    f'fill="{t["stone2"] if k % 2 == 0 else t["stone"]}"/>')
        for px in range(-(k * 6) % 20, W, 20):
            body.append(f'<rect x="{px}" y="{y}" width="2" height="{h}" fill="{t["stone"]}"/>')
    ry = GROUND + 18
    body.append(f'<rect x="0" y="{ry}" width="{W}" height="{H - ry}" fill="url(#river)"/>')

    # river shimmer + reflection
    sh = []
    for _ in range(26):
        sx, sy = snap(rng.uniform(0, W)), snap(rng.uniform(ry + 6, H - 6), 2)
        d = round(rng.uniform(0, 3), 2)
        sh.append(f'<rect class="shim" style="animation-delay:-{d}s" x="{sx}" y="{sy}" '
                  f'width="{rng.choice([8, 12, 16])}" height="2"/>')
    body.append(f'<g fill="{t["shimmer"]}">{"".join(sh)}</g>')
    refl = "".join(f'<rect class="shim" style="animation-delay:-{i * 0.3:.1f}s" '
                   f'x="{reflect_x - 14 + (i % 2) * 6}" y="{ry + 4 + i * 6}" width="{28 - i * 3}" height="2"/>'
                   for i in range(7))
    body.append(f'<g fill="{reflect_c}" opacity=".7">{refl}</g>')

    # floating diyas
    diyas = []
    for i in range(7):
        dy = snap(rng.uniform(ry + 10, H - 12), 2)
        d = round(i * 40 / 7 + rng.uniform(0, 3), 2)
        diyas.append(f'<g class="drift" style="animation-delay:-{d}s">'
                     f'<rect x="0" y="{dy}" width="10" height="4" fill="#8a4b2a"/>'
                     f'<rect x="2" y="{dy + 4}" width="6" height="2" fill="#5e2f18"/>'
                     f'<rect class="flame" style="animation-delay:-{i * 0.13:.2f}s" x="4" y="{dy - 4}" '
                     f'width="2" height="4" fill="#ffd43b"/>'
                     f'<rect x="3" y="{dy - 2}" width="4" height="2" fill="#ff8a1f"/></g>')
    body.append("".join(diyas))

    # level: contribution columns
    colg = []
    for c in cols:
        colg.append(f'<rect x="{c["x"] + 1}" y="{c["top"]}" width="{COL_W - 2}" height="{c["h"]}" fill="{c["fill"]}"/>')
        if c["c"]:
            colg.append(f'<rect x="{c["x"] + 1}" y="{c["top"]}" width="{COL_W - 2}" height="4" fill="#ffffff" opacity=".28"/>'
                        f'<rect x="{c["x"] + COL_W - 5}" y="{c["top"] + 4}" width="4" height="{c["h"] - 4}" fill="#000" opacity=".22"/>')
            for by in range(c["top"] + 12, GROUND - 2, 12):
                colg.append(f'<rect x="{c["x"] + 1}" y="{by}" width="{COL_W - 6}" height="2" fill="#000" opacity=".14"/>')
    body.append("".join(colg))

    # goal flag after the last column
    gx = x0 + n * COL_W + 14
    body.append(f'<rect x="{gx}" y="{GROUND - 64}" width="4" height="64" fill="#e6e6e6"/>'
                f'<rect x="{gx - 2}" y="{GROUND - 68}" width="8" height="6" fill="{t["accent"]}"/>'
                f'<path class="goal" style="transform-origin:{gx + 4}px {GROUND - 52}px" '
                f'd="M{gx + 4} {GROUND - 60}h22l-6 8 6 8h-22z" fill="#39d353"/>')

    # runner path: hop from column to column, then to the goal flag
    pts = []  # (fraction, x, y)
    sh_ = 10 * PX  # sprite height in px
    ox = (COL_W - 8 * PX) // 2
    for i, c in enumerate(cols):
        f = RUN * i / (n - 1)
        pts.append((f, c["x"] + ox, c["top"] - sh_))
        if i < n - 1:
            nxt = cols[i + 1]
            apex = min(c["top"], nxt["top"]) - sh_ - 10
            pts.append((RUN * (i + 0.5) / (n - 1), c["x"] + COL_W / 2 + ox, apex))
    end_x, end_y = gx - 8 * PX - 2, GROUND - sh_
    pts.append(((RUN + 1) / 2 - 0.04, (cols[-1]["x"] + end_x) / 2, cols[-1]["top"] - sh_ - 24))
    pts.append((0.95, end_x, end_y))
    pts.append((0.995, end_x, end_y))
    pts.append((1.0, cols[0]["x"] + ox, cols[0]["top"] - sh_))
    frames = "".join(f"{p * 100:.3f}%{{transform:translate({x:.0f}px,{y:.0f}px)}}" for p, x, y in pts)
    css.append(f"@keyframes run{{{frames}}}")
    css.append(f".runner{{animation:run {T}s linear infinite}}")
    body.append(f'<g class="runner"><g>{sprite_rects(SPRITE_TOP)}</g>'
                f'<g class="la">{sprite_rects(LEGS_A, 8)}</g>'
                f'<g class="lb">{sprite_rects(LEGS_B, 8)}</g></g>')

    # coins on the five biggest weeks: spin, then pop with "+N" when collected
    top5 = sorted(range(n), key=lambda i: weeks[i], reverse=True)[:5]
    for k, i in enumerate(sorted(top5)):
        c = cols[i]
        f = RUN * i / (n - 1) * 100
        cx, cy = c["x"] + COL_W // 2, c["top"] - 30
        css.append(f"@keyframes pop{k}{{0%,{f - 0.4:.2f}%{{opacity:1;transform:translateY(0)}}"
                   f"{f + 2.5:.2f}%{{opacity:0;transform:translateY(-14px)}}"
                   f"99.6%{{opacity:0;transform:translateY(0)}}100%{{opacity:1}}}}"
                   f"@keyframes plus{k}{{0%,{f:.2f}%{{opacity:0;transform:translateY(0)}}"
                   f"{f + 0.6:.2f}%{{opacity:1}}{f + 7:.2f}%{{opacity:0;transform:translateY(-22px)}}"
                   f"100%{{opacity:0}}}}")
        body.append(f'<g style="animation:pop{k} {T}s linear infinite">'
                    f'<g class="spin" style="transform-origin:{cx}px {cy + 5}px">'
                    f'<rect x="{cx - 4}" y="{cy}" width="8" height="10" fill="#ffd43b"/>'
                    f'<rect x="{cx - 2}" y="{cy - 2}" width="4" height="14" fill="#ffd43b"/>'
                    f'<rect x="{cx - 1}" y="{cy + 2}" width="2" height="6" fill="#c9971c"/></g></g>')
        body.append(f'<g style="animation:plus{k} {T}s linear infinite;opacity:0">'
                    f'{text("+" + str(weeks[i]), cx, cy - 14, 2, "#ffd43b", t["hud_shadow"], anchor="middle")}</g>')

    # level clear banner
    css.append(f"@keyframes clear{{0%,{RUN * 100 + 4:.1f}%{{opacity:0}}{RUN * 100 + 5:.1f}%,99.4%{{opacity:1}}100%{{opacity:0}}}}")
    body.append(f'<g style="animation:clear {T}s steps(1) infinite;opacity:0">'
                f'{text("LEVEL CLEAR", W / 2, 120, 3, t["accent"], t["hud_shadow"], anchor="middle")}</g>')

    # HUD
    year = today.year
    body.append(text("1UP PYGURU", 24, 18, 2, t["hud"], t["hud_shadow"]))
    body.append(text(f"SCORE {total:06d}", W / 2, 18, 2, t["hud"], t["hud_shadow"], anchor="middle"))
    s = streak(days)
    right = f"STREAK {s}D  LVL {year}"
    body.append(text(right, W - 24 - text_width(right, 2), 18, 2, t["hud"], t["hud_shadow"]))
    body.append(text("PYGURU RUN", W / 2, 50, 5, "#ffffff", t["hud_shadow"], anchor="middle"))
    body.append(text("PRESS * TO PLAY", W / 2, 98, 2, t["accent"], t["hud_shadow"], cls="blink", anchor="middle"))

    css.append("""
.tw{animation:tw 3s ease-in-out infinite}
@keyframes tw{0%,100%{opacity:1}50%{opacity:.2}}
.shoot{animation:shoot 9s linear infinite;opacity:0}
@keyframes shoot{0%,78%{opacity:0;transform:translate(120px,20px)}
 79%{opacity:1;transform:translate(120px,20px)}88%{opacity:1;transform:translate(420px,110px)}
 89%,100%{opacity:0;transform:translate(420px,110px)}}
.win{animation:win 6s steps(1) infinite}
@keyframes win{0%,100%{opacity:1}43%{opacity:.35}47%{opacity:1}80%{opacity:.75}}
.flag,.goal{animation:wave .8s steps(2) infinite}
@keyframes wave{0%{transform:skewY(0)}100%{transform:skewY(-12deg)}}
.shim{animation:shim 3s ease-in-out infinite}
@keyframes shim{0%,100%{opacity:.2;transform:translateX(0)}50%{opacity:.9;transform:translateX(6px)}}
.drift{animation:drift 40s linear infinite}
@keyframes drift{0%{transform:translateX(-20px)}100%{transform:translateX(980px)}}
.flame{animation:flame .5s steps(2) infinite}
@keyframes flame{0%{opacity:1}100%{opacity:.4}}
.la{animation:la .24s steps(1) infinite}.lb{animation:lb .24s steps(1) infinite}
@keyframes la{0%{opacity:1}50%{opacity:0}}@keyframes lb{0%{opacity:0}50%{opacity:1}}
.spin{animation:spin 1s steps(4) infinite}
@keyframes spin{0%{transform:scaleX(1)}50%{transform:scaleX(.25)}100%{transform:scaleX(1)}}
.blink{animation:blink 1.2s steps(1) infinite}
@keyframes blink{0%{opacity:1}60%{opacity:0}}
g,rect,path{transform-box:view-box}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}""")

    title = (f"pyGuru Run: {total} contributions in the last year drawn as platforms "
             f"on the Varanasi ghats, with a pixel runner hopping across them")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'shape-rendering="crispEdges" role="img" aria-label="{title}"><title>{title}</title>'
           f'<defs>{defs}</defs><style>{"".join(css)}</style>'
           f'<g clip-path="url(#frame)">{"".join(body)}</g></svg>')
    return svg, n

# --------------------------------------------------------------------------
# cartridges

def wrap(name, max_chars):
    words = re.split(r"(?<=[-_])", name)
    lines, cur = [], ""
    for w in words:
        if len(cur + w) > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur += w
    lines.append(cur)
    return lines


ICON_COLORS = {"B": "#3776ab", "Y": "#ffd43b", "w": "#ffffff", "k": "#141228",
               "G": "#25d366", "T": "#4a7bd0", "r": "#ff5f56", "y": "#ffbd2e",
               "g": "#27c93f", "S": "#9aa4b8", "P": "#b388ff"}
ICONS = {  # 12-wide pixel icons, one per shelf repo: (rows, hills colour)
    "Python-Games": ([
        "..P......P..", "...P....P...", "..PPPPPPPP..", ".PP.PPPP.PP.",
        "PPPPPPPPPPPP", "P.PPPPPPPP.P", "P.P......P.P", "...PP..PP..."], "#7c4dff"),
    "Python-on-WhatsApp": ([
        "...GGGGGG...", ".GGGGGGGGGG.", "GGGGGGGGGGGG", "GGwwGwwGwwGG",
        "GGwwGwwGwwGG", "GGGGGGGGGGGG", ".GGGGGGGGGG.", "..GGGGGGG...",
        ".GGG........", "GG.........."], "#128c7e"),
    "Python-Projects": ([
        "....BBBB....", "...BwBBBB...", "...BBBBBB...", "......BBB...",
        "..BBBBBBB.YY", ".BBBBBBBYYYY", "BBB.YYYYYYY.", "BBB.YYY.....",
        "....YYYYYY..", "....YYYYwY..", "....YYYYYY.."], "#3776ab"),
    "Tkinter-Applications": ([
        "TTTTTTTTTTTT", "TTTTTTTrTyTg", "wwwwwwwwwwww", "wkkkkkkkkkkw",
        "wkTTTTkkkkkw", "wkkkkkkkkkkw", "wkTTTkkggggw", "wkkkkkkggggw",
        "wwwwwwwwwwww"], "#4a7bd0"),
    "python-from-scratch": ([
        "SSSSSSSSSSSS", "SgSySSSSkkkS", "SSSSSSSSSSSS", "............",
        "SSSSSSSSSSSS", "SgSgSSSSkkkS", "SSSSSSSSSSSS", "............",
        "SSSSSSSSSSSS", "SrSySSSSkkkS", "SSSSSSSSSSSS"], "#2fb553"),
    "Decrypto": ([
        "...SSSSSS...", "..SS....SS..", "..S......S..", "..S......S..",
        "YYYYYYYYYYYY", "YYYYYkkYYYYY", "YYYYkkkkYYYY", "YYYYYkkYYYYY",
        "YYYYYkkYYYYY", "YYYYYYYYYYYY"], "#c9971c"),
}


def icon(rows, x, y, s):
    out = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch in ICON_COLORS:
                out.append(f'<rect x="{x + c * s}" y="{y + r * s}" width="{s}" height="{s}" fill="{ICON_COLORS[ch]}"/>')
    return "".join(out)


def cartridge(repo):
    lang = (repo.get("primaryLanguage") or {}).get("name") or "Code"
    color = (repo.get("primaryLanguage") or {}).get("color") or "#8b949e"
    seed = int(hashlib.md5(repo["name"].encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    CW, CH = 260, 300
    body = "#b9b6c2"
    p = []
    # shell with the corner notch
    p.append(f'<path d="M8 4h208l36 36v252h-244z" fill="#6f6b7d"/>')
    p.append(f'<path d="M4 0h208l36 36v252h-244z" fill="{body}"/>')
    p.append(f'<path d="M4 0h208l36 36v4l-36-36h-208z" fill="#d9d6e0"/>')
    for y in range(12, 40, 6):
        p.append(f'<rect x="24" y="{y}" width="168" height="2" fill="#8f8b9c"/>')
    # label
    lx, ly, lw, lh = 22, 50, 204, 168
    p.append(f'<rect x="{lx - 4}" y="{ly - 4}" width="{lw + 8}" height="{lh + 8}" fill="#8f8b9c"/>')
    p.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" fill="#141228"/>')
    # label art: pixel landscape tinted by the language colour
    for _ in range(18):
        sx, sy = lx + snap(rng.uniform(4, lw - 6), 2), ly + snap(rng.uniform(4, 60), 2)
        d = round(rng.uniform(0, 3), 2)
        p.append(f'<rect class="tw" style="animation-delay:-{d}s" x="{sx}" y="{sy}" width="2" height="2" fill="#fff"/>')
    art = ICONS.get(repo["name"])
    if art:
        color = art[1]
    else:
        p.append(f'<rect x="{lx + lw - 44}" y="{ly + 16}" width="16" height="16" fill="{color}"/>')
    for layer, (base, op) in enumerate([(ly + 92, 0.45), (ly + 108, 0.75)]):
        x, y = lx, base
        while x < lx + lw:
            w = rng.choice([8, 12, 16])
            y = max(ly + 70, min(ly + 116, y + rng.choice([-8, -4, 0, 4, 8])))
            p.append(f'<rect x="{x}" y="{y}" width="{min(w, lx + lw - x)}" height="{ly + lh - y}" '
                     f'fill="{color}" opacity="{op}"/>')
            x += w
    if art:
        s_ = 6
        p.append(f'<g class="bob">{icon(art[0], lx + (lw - 12 * s_) // 2, ly + 14, s_)}</g>')
    # title band
    lines = wrap(repo["name"], 15)[:2]
    band_h = 16 + 18 * len(lines)
    by = ly + lh - band_h
    p.append(f'<rect x="{lx}" y="{by}" width="{lw}" height="{band_h}" fill="#0b0a18" opacity=".88"/>')
    for k, line in enumerate(lines):
        p.append(text(line, lx + lw // 2, by + 9 + k * 18, 2, "#ffffff", anchor="middle"))
    # embossed footer: stars + language
    stars = f"* {repo['stargazerCount']}"
    p.append(text(stars, 24, 238, 3, "#ffd43b", "#6f6b7d"))
    p.append(text(lang.upper()[:12], 226 - text_width(lang.upper()[:12], 2), 244, 2, "#4e4a5c"))
    p.append('<path d="M112 268h24l-12 12z" fill="#8f8b9c"/>')
    title = f"{repo['name']}: {repo['stargazerCount']} stars, {lang}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" width="{CW}" height="{CH}" '
            f'shape-rendering="crispEdges" role="img" aria-label="{title}"><title>{title}</title>'
            f'<style>.tw{{animation:tw 3s ease-in-out infinite}}@keyframes tw{{0%,100%{{opacity:1}}50%{{opacity:.15}}}}'
            f'.bob{{animation:bob 1.6s steps(2) infinite}}@keyframes bob{{0%{{transform:translateY(0)}}100%{{transform:translateY(-8px)}}}}'
            f'@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>'
            f'{"".join(p)}</svg>')

# --------------------------------------------------------------------------
# README "Now playing"

def ago(iso, now):
    d = (now - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    return "today" if d < 1 else "yesterday" if d < 2 else f"{d} days ago"


def now_playing(repos, now):
    rows = []
    for r in repos:
        if r["name"] in NOW_SKIP or r["isFork"] or r["isArchived"]:
            continue
        desc = (r.get("description") or "").strip().rstrip(".")
        desc = f" · {desc}" if desc else ""
        rows.append(f"- ▸ **[{r['name']}]({r['url']})**{desc} · <sub>saved {ago(r['pushedAt'], now)}</sub>")
        if len(rows) == 3:
            break
    return rows

# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", help="read the GraphQL response from this JSON file")
    a = ap.parse_args()
    data = json.loads(Path(a.offline).read_text()) if a.offline else fetch()
    user = data["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    repos = user["repositories"]["nodes"]
    now = dt.datetime.now(dt.timezone.utc)
    ASSETS.mkdir(exist_ok=True)

    weeks_drawn = 0
    for theme in THEMES:
        svg, weeks_drawn = header(theme, cal, now.date())
        (ASSETS / f"run-{theme}.svg").write_text(svg)

    by_name = {r["name"]: r for r in repos}
    carts = 0
    for name in SHELF:
        if name in by_name:
            (ASSETS / f"cart-{name.lower()}.svg").write_text(cartridge(by_name[name]))
            carts += 1

    rows = now_playing(repos, now)
    readme = ROOT / "README.md"
    txt = readme.read_text()
    new = re.sub(r"(<!-- NOW:START -->).*?(<!-- NOW:END -->)",
                 lambda m: m.group(1) + "\n" + "\n".join(rows) + "\n" + m.group(2),
                 txt, flags=re.S)
    readme.write_text(new)

    print(f"weeks drawn: {weeks_drawn}  contributions: {cal['totalContributions']}  "
          f"cartridges: {carts}/{len(SHELF)}  now-playing rows: {len(rows)}")
    if not weeks_drawn or not carts or not rows:
        sys.exit("nothing drawn: refusing to report success")


if __name__ == "__main__":
    main()
