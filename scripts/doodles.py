#!/usr/bin/env python3
"""Hand-drawn profile widgets for github.com/BunnyLucy, redrawn daily by an Action.

Writes doodles/{contrib,stats,langs}.svg. Standard library only.
Light/dark colours live in a <style> block, so one file works in both themes.
"""
import datetime as dt, json, math, os, random, urllib.request, zlib

LOGIN = os.environ.get("GH_LOGIN", "BunnyLucy")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("DOODLE_OUT", "doodles")
MOCK = os.environ.get("DOODLE_MOCK")

TYPE = "'Special Elite','Courier Prime','Courier New',Courier,monospace"
HAND = "'Caveat','Bradley Hand','Segoe Print','Chalkboard SE','Comic Sans MS',cursive"

STYLE = f"""<style>
.ink{{fill:#1f1b17}} .inks{{stroke:#1f1b17;fill:none}} .soft{{fill:#5f574e}} .faint{{fill:#b9b0a2}} .faints{{stroke:#b9b0a2;fill:none}}
.paper{{fill:#fffdf7}} .tape{{fill:#ebe4d6;opacity:.9}} .shadow{{fill:#1f1b17;opacity:.07}}
.l1{{stroke:#d89aa5}} .l2{{stroke:#c27a86}} .l3{{stroke:#ab5e67}} .l4{{stroke:#853f46}} .hl{{stroke:#ab5e67;fill:none}}
.c0{{stroke:#ab5e67}} .c1{{stroke:#957b94}} .c2{{stroke:#63607d}} .c3{{stroke:#d89aa5}} .c4{{stroke:#853f46}} .c5{{stroke:#3c405e}}
.type{{font-family:{TYPE}}} .hand{{font-family:{HAND}}}
.w{{opacity:0;animation:pop .5s ease-out forwards}}
@keyframes pop{{from{{opacity:0;transform:translateY(-4px)}}to{{opacity:1;transform:none}}}}
@media (prefers-reduced-motion:reduce){{.w{{animation:none;opacity:1}}}}
@media (prefers-color-scheme:dark){{
 .ink{{fill:#ece4d6}} .inks{{stroke:#ece4d6}} .soft{{fill:#b3a99b}} .faint{{fill:#5d564e}} .faints{{stroke:#5d564e}}
 .paper{{fill:#22201d}} .tape{{fill:#4a443d}} .shadow{{fill:#000;opacity:.25}}
 .l1{{stroke:#8d5a66}} .l2{{stroke:#b9737f}} .l3{{stroke:#d89aa5}} .l4{{stroke:#f0c4cb}} .hl{{stroke:#d89aa5}}
 .c0{{stroke:#d89aa5}} .c1{{stroke:#b9a0b8}} .c2{{stroke:#9a96b8}} .c3{{stroke:#f0c4cb}} .c4{{stroke:#c27a86}} .c5{{stroke:#7d82a8}}
}}
</style>"""


# ---------------------------------------------------------------- data
QUERY = """query($login:String!){user(login:$login){
 followers{totalCount} pullRequests{totalCount} issues{totalCount}
 contributionsCollection{totalCommitContributions
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}
 repositories(first:100,ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC){totalCount
  nodes{stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}"""


def fetch():
    if MOCK:
        return json.load(open(MOCK))["data"]["user"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "doodles"})
    res = json.load(urllib.request.urlopen(req, timeout=30))
    if "errors" in res:
        raise SystemExit(f"GraphQL error: {res['errors']}")
    return res["data"]["user"]


# ---------------------------------------------------------------- pencil
class Pencil:
    """Seeded wobble so the same day is drawn the same way every run."""

    def __init__(self, seed):
        self.r = random.Random(zlib.crc32(str(seed).encode()))

    def j(self, a):
        return self.r.uniform(-a, a)

    def line(self, x1, y1, x2, y2, wob=1.0):
        mx, my = (x1 + x2) / 2 + self.j(wob), (y1 + y2) / 2 + self.j(wob)
        return (f"M{x1 + self.j(wob / 2):.1f} {y1 + self.j(wob / 2):.1f}"
                f"Q{mx:.1f} {my:.1f} {x2 + self.j(wob / 2):.1f} {y2 + self.j(wob / 2):.1f}")

    def rect(self, x, y, w, h, wob=1.6, twice=True):
        d = "".join(self.line(*s, wob) for s in
                    [(x, y, x + w, y), (x + w, y, x + w, y + h), (x + w, y + h, x, y + h), (x, y + h, x, y)])
        if twice:
            d += "".join(self.line(*s, wob * 1.4) for s in
                         [(x, y, x + w, y), (x + w, y, x + w, y + h), (x + w, y + h, x, y + h), (x, y + h, x, y)])
        return d

    def circle(self, cx, cy, rad, wob=0.5, n=9):
        a0 = self.r.uniform(0, 2 * math.pi)
        span = 2 * math.pi + self.r.uniform(0.25, 0.6)  # overshoot, like a pen loop
        pts = []
        for i in range(n + 1):
            a = a0 + span * i / n
            rr = rad + self.j(wob)
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
        for i in range(1, len(pts) - 1):
            mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
            d += f"Q{pts[i][0]:.1f} {pts[i][1]:.1f} {mx:.1f} {my:.1f}"
        return d

    def scribble(self, x, y, w, h, strokes):
        """Zig-zag crayon fill inside a box."""
        d = f"M{x + self.j(1):.1f} {y + h + self.j(1):.1f}"
        for i in range(1, strokes + 1):
            t = i / strokes
            px = x + w * t + self.j(0.8)
            py = (y if i % 2 else y + h) + self.j(1.0)
            d += f"L{px:.1f} {py:.1f}"
        return d


def path(d, cls, width, extra=""):
    return f'<path d="{d}" class="{cls}" stroke-width="{width}" fill="none" stroke-linecap="round" stroke-linejoin="round" {extra}/>'


def svg(w, h, title, body):
    t = title.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{t}"><title>{t}</title>{STYLE}\n{body}\n</svg>\n')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def arrowhead(p, x, y, ang, cls="inks", size=7):
    a1, a2 = ang + 2.6, ang - 2.6
    d = (f"M{x + size * math.cos(a1):.1f} {y + size * math.sin(a1):.1f}L{x:.1f} {y:.1f}"
         f"L{x + size * math.cos(a2):.1f} {y + size * math.sin(a2):.1f}")
    return path(d, cls, 1.6)


# ---------------------------------------------------------------- contribution wall
def contrib(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    W, left, top = 900, 52, 44
    pitch = min(15.5, (W - left - 30) / len(weeks))
    body = []

    for i, lab in ((1, "mon"), (3, "wed"), (5, "fri")):
        body.append(f'<text x="14" y="{top + i * pitch + 3.5:.1f}" class="type faint" font-size="9.5">{lab}</text>')

    days, last_month = [], None
    for wi, wk in enumerate(weeks):
        cx = left + wi * pitch + pitch / 2
        first = dt.date.fromisoformat(wk["contributionDays"][0]["date"])
        if first.month != last_month and wi < len(weeks) - 2:
            if last_month is not None or first.day <= 7:
                body.append(f'<text x="{cx - 4:.1f}" y="{top - 14}" class="hand soft" font-size="15">'
                            f'{first.strftime("%b").lower()}</text>')
            last_month = first.month
        cells = []
        for d in wk["contributionDays"]:
            date = dt.date.fromisoformat(d["date"])
            row = (date.weekday() + 1) % 7  # sunday first, like GitHub
            cy = top + row * pitch
            days.append((date, d["contributionCount"], cx, cy))
            cells.append(cell(Pencil(d["date"]), d["contributionLevel"], cx, cy, pitch))
        body.append(f'<g class="w" style="animation-delay:{wi * 0.025:.3f}s">{"".join(cells)}</g>')

    bottom = top + 6 * pitch + pitch / 2
    p = Pencil("notes")
    busiest = max(days, key=lambda t: t[1])
    if busiest[1] > 0:
        _, n, bx, by = busiest
        nx = min(max(bx - 60, left), W - 160)
        ny = bottom + 44
        body.append(f'<text x="{nx:.1f}" y="{ny:.1f}" class="hand ink" font-size="19">'
                    'busiest day</text>')
        sx, sy = min(max(bx - 30, nx + 20), nx + 80), ny - 22  # start just above the note
        c1x, c1y = (sx + bx) / 2 + (28 if bx >= sx else -28), (sy + by) / 2 + 4
        body.append(path(f"M{sx:.1f} {sy:.1f}Q{c1x:.1f} {c1y:.1f} {bx - 3:.1f} {by + 9:.1f}", "inks", 1.5))
        ang = math.atan2((by + 9) - c1y, (bx - 3) - c1x)
        body.append(arrowhead(p, bx - 3, by + 9, ang))
        body.append(path(p.circle(bx, by, pitch * 0.62, 0.8), "hl", 1.4))
    else:
        body.append(f'<text x="{left}" y="{bottom + 44:.1f}" class="hand soft" font-size="19">'
                    'a quiet year</text>')

    lx, ly = W - 210, bottom + 76
    body.append(f'<text x="{lx}" y="{ly + 4}" class="type faint" font-size="10">less</text>')
    for i, lv in enumerate(["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]):
        body.append(cell(Pencil(f"legend{i}"), lv, lx + 44 + i * 18, ly, 15.5))
    body.append(f'<text x="{lx + 44 + 5 * 18 + 4}" y="{ly + 4}" class="type faint" font-size="10">more</text>')

    H = int(ly + 22)
    return svg(W, H, f"{LOGIN}'s contributions, hand-drawn: {cal['totalContributions']} in the last year",
               "\n".join(body))


def cell(p, level, cx, cy, pitch):
    s = pitch * 0.78
    if level == "NONE":
        return f'<circle cx="{cx + p.j(.6):.1f}" cy="{cy + p.j(.6):.1f}" r="1.2" class="faint"/>'
    if level == "FIRST_QUARTILE":
        return path(p.circle(cx, cy, s * 0.36, 0.5), "l1", 1.5)
    if level == "SECOND_QUARTILE":
        return (path(p.circle(cx, cy, s * 0.42, 0.6), "l2", 1.5)
                + path(p.scribble(cx - s * .22, cy - s * .2, s * .44, s * .4, 3), "l2", 1.2))
    if level == "THIRD_QUARTILE":
        return (path(p.scribble(cx - s * .4, cy - s * .38, s * .8, s * .76, 6), "l3", 1.7)
                + path(p.circle(cx, cy, s * 0.5, 0.7), "l3", 1.2))
    return (path(p.scribble(cx - s * .46, cy - s * .44, s * .92, s * .88, 9), "l4", 2.1)
            + path(p.circle(cx, cy, s * 0.56, 0.8), "inks", 1.0))


# ---------------------------------------------------------------- sticky-note cards
def card_frame(p, w, h, title, rot):
    return [f'<g transform="rotate({rot} {w / 2} {h / 2})">',
            f'<rect x="20" y="24" width="{w - 36}" height="{h - 42}" class="shadow"/>',
            f'<rect x="16" y="18" width="{w - 36}" height="{h - 42}" class="paper"/>',
            path(p.rect(16, 18, w - 36, h - 42, 1.4), "inks", 1.2),
            f'<rect x="{w / 2 - 34}" y="8" width="68" height="20" class="tape" transform="rotate(-4 {w / 2} 18)"/>',
            f'<text x="38" y="58" class="type ink" font-size="14" letter-spacing="3">{esc(title)}</text>',
            path(p.line(38, 66, 38 + len(title) * 11.5, 63, 2), "hl", 1.8)]


def stats(user):
    W, H = 440, 250
    p = Pencil("stats")
    repos = user["repositories"]
    stars = sum(n["stargazerCount"] for n in repos["nodes"])
    rows = [("stars collected", stars), ("commits this year", user["contributionsCollection"]["totalCommitContributions"]),
            ("pull requests", user["pullRequests"]["totalCount"]), ("issues opened", user["issues"]["totalCount"]),
            ("public repos", repos["totalCount"]), ("followers", user["followers"]["totalCount"])]
    body = card_frame(p, W, H, "FIELD NOTES", -1.2)
    for i, (label, val) in enumerate(rows):
        y = 94 + i * 24
        body.append(f'<text x="40" y="{y}" class="type soft" font-size="12.5">{label}</text>')
        body.append(path(p.line(40 + len(label) * 7.6 + 8, y - 3, W - 92, y - 4, 0.8), "faints", 1, 'stroke-dasharray="1 4"'))
        body.append(f'<text x="{W - 46}" y="{y + 2}" text-anchor="end" class="hand ink" font-size="23">{val}</text>')
    # a little doodled star in the corner
    cx, cy, pts = W - 62, 54, []
    for k in range(11):
        a = -math.pi / 2 + k * math.pi / 5
        r = 11 if k % 2 == 0 else 4.6
        pts.append(f"{cx + r * math.cos(a) + p.j(.6):.1f} {cy + r * math.sin(a) + p.j(.6):.1f}")
    body.append(path("M" + "L".join(pts), "l1", 1.6))
    body.append("</g>")
    return svg(W, H, "Field notes: " + ", ".join(f"{v} {k}" for k, v in rows), "\n".join(body))


def langs(user):
    W, H = 440, 250
    p = Pencil("langs")
    sizes = {}
    for n in user["repositories"]["nodes"]:
        for e in n["languages"]["edges"]:
            k = e["node"]["name"]
            sizes.setdefault(k, [0, e["node"]["color"] or "#b9b0a2"])
            sizes[k][0] += e["size"]
    total = sum(v[0] for v in sizes.values()) or 1
    top = [kv for kv in sorted(sizes.items(), key=lambda kv: -kv[1][0]) if kv[1][0] / total >= 0.01][:6]
    body = card_frame(p, W, H, "INK & LANGUAGES", 1.1)
    x0, maxw = 150, W - 150 - 112
    for i, (name, (size, color)) in enumerate(top):
        y = 94 + i * 24
        pct = size / total
        bw = max(6, maxw * pct / (top[0][1][0] / total))
        body.append(f'<text x="40" y="{y}" class="type soft" font-size="12.5">{esc(name)}</text>')
        body.append(path(p.scribble(x0, y - 11, bw, 9, max(3, int(bw / 4))), f"c{i}", 2))
        body.append(path(p.line(x0 - 2, y + 1, x0 + bw + 2, y, 0.8), "inks", 0.9))
        body.append(f'<text x="{W - 46}" y="{y + 1}" text-anchor="end" class="hand ink" font-size="20">'
                    f'{pct * 100:.0f}%</text>')
    if not top:
        body.append('<text x="40" y="110" class="hand soft" font-size="20">nothing here yet</text>')
    body.append("</g>")
    return svg(W, H, "Languages: " + ", ".join(f"{k} {v[0] * 100 / total:.0f}%" for k, v in top), "\n".join(body))


# ---------------------------------------------------------------- link doodles
ICONS = {
    # tiny house with a heart window
    "home": "M4 15L13 6L22 15M7 13V23H19V13M13 21C10 18.6 9.6 17 10.8 16.2C11.7 15.6 12.6 16.1 13 16.8C13.4 16.1 14.3 15.6 15.2 16.2C16.4 17 16 18.6 13 21Z",
    # open book
    "blog": "M3 9Q8 6.5 13 9.5Q18 6.5 23 9V21Q18 18.5 13 21.5Q8 18.5 3 21ZM13 9.5V21.5",
    # island with a little hill and a wave
    "island": "M3 19Q8 12 13 13Q18 12 23 19ZM9 13.4Q11 8 14.5 9.5M14.5 9.5Q16.5 6.5 19 8M2 23Q5 21 8 23T14 23T20 23T25 22",
    # speech bubble
    "hi": "M4 8Q4 5 7 5H19Q22 5 22 8V15Q22 18 19 18H11L6.5 22L7.5 18Q4 18 4 15ZM9.5 11.5H9.6M13 11.5H13.1M16.5 11.5H16.6",
}


def link(key, label):
    p = Pencil("link-" + key)
    w = int(52 + len(label) * 11.5)
    body = [path(ICONS[key], "inks", 1.6, 'transform="translate(2 6)"'),
            f'<text x="38" y="27" class="hand ink" font-size="22">{esc(label)}</text>',
            path(p.line(38, 34, w - 6, 32.5, 1.8), "hl", 1.8)]
    return svg(w, 42, label, "\n".join(body))


LINKS = [("home", "yishu.asia"), ("blog", "the blog"), ("island", "the 3D island"), ("hi", "say hi")]


if __name__ == "__main__":
    user = fetch()
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("contrib", contrib), ("stats", stats), ("langs", langs)):
        with open(f"{OUT}/{name}.svg", "w", encoding="utf-8") as f:
            f.write(fn(user))
        print("drew", name)
    for key, label in LINKS:
        with open(f"{OUT}/link-{key}.svg", "w", encoding="utf-8") as f:
            f.write(link(key, label))
    print("drew links")
