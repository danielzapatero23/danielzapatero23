#!/usr/bin/env python3
"""Genera terminal.svg para el perfil de GitHub de danielzapatero23.

Lo ejecuta la GitHub Action una vez al día: consulta las últimas versiones
del stack y la actividad pública del usuario, y redibuja el SVG.
Para cambiar textos, toca solo la sección CONFIG.
"""
import json
import os
import random
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

# ───────────────────────────── CONFIG ─────────────────────────────
USER = "danielzapatero23"
TITLE = "ZAPATERO"  # dibujado con la tipografía Monoton (scripts/title_path.txt)
PROMPT = "daniel@burgos"
WHOAMI = ("Daniel", "erp & automation dev", "Burgos, ES")
STACK = ["python", "odoo", "n8n", "docker", "fastapi", "kotlin", "c#"]
STATUS = "currently: building invoiceflow · automating odoo with n8n"
PROJECTS = [
    ("taller_management/", "Odoo 17 workshop management module (TFG)"),
    ("invoiceflow/", "AI-powered invoice management portal"),
    ("assistant/", "personal assistant web app (FastAPI)"),
    ("trading-bot/", "XAUUSD / NQ bot using SMC"),
    ("froggy-roads/", "2D Crossy Road-style game (Unity)"),
]
CONTAINERS = [("postgres", True), ("odoo-17", True), ("n8n", True)]
WORKFLOW = [  # (nodo, detalle, color)
    ("Webhook", "new invoice received", "#f0883e"),
    ("AI · Python", "extract fields", "#a371f7"),
    ("Odoo", "create account.move", "#875a7b"),
    ("Notify", "send to Telegram", "#3fb950"),
]
# Repos cuyas releases salen en el feed (owner/repo, nombre a mostrar)
STACK_REPOS = [
    ("n8n-io/n8n", "n8n"),
    ("fastapi/fastapi", "fastapi"),
    ("docker/compose", "docker compose"),
    ("pydantic/pydantic", "pydantic"),
]
FALLBACK_FEED = "now building :: invoiceflow  ///  automating with n8n  ///  odoo + python + docker"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "terminal.svg")
# ──────────────────────────────────────────────────────────────────


# ---------- feed ----------
def gh_get(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def fetch_feed():
    items = []  # (fecha, texto)
    try:
        for ev in gh_get(f"/users/{USER}/events/public?per_page=30"):
            if ev.get("type") != "PushEvent":
                continue
            commits = ev.get("payload", {}).get("commits") or []
            if not commits:
                continue
            repo = ev["repo"]["name"].split("/")[-1]
            if repo == USER:  # no mostrar los commits del propio bot del perfil
                continue
            msg = commits[-1]["message"].splitlines()[0][:60]
            items.append((ev["created_at"][:10], f"push -> {repo}: {msg}"))
            if len(items) >= 3:
                break
    except Exception as e:  # sin red o sin eventos: seguimos
        print("events:", e)
    for full, name in STACK_REPOS:
        try:
            rel = gh_get(f"/repos/{full}/releases/latest")
            items.append((rel["published_at"][:10], f"{name} {rel['tag_name'].split('@')[-1]} released"))
        except Exception as e:
            print(full, e)
    items.sort(key=lambda x: x[0], reverse=True)
    if not items:
        return FALLBACK_FEED
    return "  ///  ".join(f"{txt} :: {d}" for d, txt in items)


# ---------- svg ----------
W, H = 900, 660
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
CW = 8.45  # ancho aprox. de carácter a 14px
C = {
    "bg": "#0d1117", "term": "#0a0e13", "bar": "#161b22", "border": "#30363d",
    "prompt": "#f85149", "path": "#58a6ff", "text": "#e6edf3", "dim": "#8b949e",
    "green": "#3fb950", "orange": "#f0883e", "cyan": "#39c5cf",
}


def appear(t, fade=0.25):
    return f'<animate attributeName="opacity" from="0" to="1" begin="{t}s" dur="{fade}s" fill="freeze"/>'


class Doc:
    def __init__(self):
        self.parts, self.clip_id = [], 0

    def add(self, s):
        self.parts.append(s)

    def prompt_line(self, y, cmd, t_show, t_type):
        """Prompt que aparece en t_show y comando que se teclea durante t_type s."""
        self.clip_id += 1
        cid = f"type{self.clip_id}"
        px = 32 + (len(PROMPT) + 4) * CW
        w = len(cmd) * CW + 6
        self.add(
            f'<clipPath id="{cid}"><rect x="{px:.1f}" y="{y-16}" width="0" height="22">'
            f'<animate attributeName="width" from="0" to="{w:.1f}" begin="{t_show+0.15}s" dur="{t_type}s" '
            f'calcMode="discrete" values="{";".join(f"{w*k/len(cmd):.1f}" for k in range(len(cmd)+1))}" fill="freeze"/>'
            f'</rect></clipPath>'
        )
        self.add(
            f'<g opacity="0">{appear(t_show, 0.01)}'
            f'<text x="32" y="{y}" class="t"><tspan fill="{C["prompt"]}">{PROMPT}</tspan>'
            f'<tspan fill="{C["text"]}">:</tspan><tspan fill="{C["path"]}">~</tspan>'
            f'<tspan fill="{C["text"]}">$ </tspan></text>'
            f'<text x="{px:.1f}" y="{y}" class="t" fill="{C["text"]}" clip-path="url(#{cid})">{escape(cmd)}</text></g>'
        )
        return t_show + 0.15 + t_type


def build(feed):
    d = Doc()
    synced = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    random.seed(23)

    # marco y ventana
    d.add(f'<rect width="{W}" height="{H}" rx="10" fill="{C["term"]}" stroke="{C["border"]}"/>')
    d.add(f'<path d="M0 10 a10 10 0 0 1 10 -10 h{W-20} a10 10 0 0 1 10 10 v26 h-{W} z" fill="{C["bar"]}"/>')
    for i, col in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        d.add(f'<circle cx="{20+i*20}" cy="18" r="6" fill="{col}"/>')
    d.add(f'<text x="{W/2}" y="23" text-anchor="middle" class="s" fill="{C["dim"]}">'
          f'{PROMPT}: ~/dev   ::   feed synced {synced}</text>')

    # workflow estilo n8n (columna derecha)
    nx, nw, nh = 700, 168, 34
    ny0, gap = 300, 64
    d.add(f'<text x="{nx}" y="{ny0-16}" class="s" fill="{C["dim"]}">workflow.json</text>')
    for i in range(len(WORKFLOW) - 1):
        y1 = ny0 + i * gap + nh
        y2 = ny0 + (i + 1) * gap
        cxn = nx + nw / 2
        d.add(f'<line x1="{cxn}" y1="{y1}" x2="{cxn}" y2="{y2}" stroke="{C["border"]}" stroke-width="2"/>')
        T = len(WORKFLOW) * 0.9
        k1, k2 = i * 0.9 / T, (i + 1) * 0.9 / T
        d.add(f'<circle cx="{cxn}" cy="{y1}" r="3.5" fill="{WORKFLOW[i][2]}" opacity="0">'
              f'<animate attributeName="cy" values="{y1};{y1};{y2};{y2}" keyTimes="0;{k1:.3f};{k2:.3f};1" dur="{T}s" repeatCount="indefinite"/>'
              f'<animate attributeName="opacity" values="0;1;0" keyTimes="0;{k1:.3f};{k2:.3f}" calcMode="discrete" dur="{T}s" repeatCount="indefinite"/></circle>')
    for i, (title, sub, col) in enumerate(WORKFLOW):
        y = ny0 + i * gap
        d.add(f'<rect x="{nx}" y="{y}" width="{nw}" height="{nh}" rx="6" fill="{C["bar"]}" stroke="{C["border"]}"/>'
              f'<rect x="{nx}" y="{y}" width="5" height="{nh}" rx="2" fill="{col}"/>'
              f'<text x="{nx+14}" y="{y+15}" class="s" fill="{C["text"]}" font-weight="700">{escape(title)}</text>'
              f'<text x="{nx+14}" y="{y+28}" class="xs" fill="{C["dim"]}">{escape(sub)}</text>')
        # destello cuando el paquete llega al nodo
        T = len(WORKFLOW) * 0.9
        k = max(i * 0.9 / T, 0.001)
        d.add(f'<rect x="{nx}" y="{y}" width="{nw}" height="{nh}" rx="6" fill="none" stroke="{col}" stroke-width="1.5" opacity="0">'
              f'<animate attributeName="opacity" values="0;0;1;0;0" keyTimes="0;{k:.3f};{k+0.04:.3f};{k+0.2:.3f};1" dur="{T}s" repeatCount="indefinite"/></rect>')

    # 1. docker compose up
    t = d.prompt_line(66, "docker compose up -d", 0.3, 0.9)
    for i, (name, ok) in enumerate(CONTAINERS):
        y = 90 + i * 20
        tt = t + 0.2 + i * 0.35
        d.add(f'<g opacity="0">{appear(tt, 0.01)}<text x="32" y="{y}" class="s" xml:space="preserve">'
              f'<tspan fill="{C["green"]}">✔</tspan><tspan fill="{C["dim"]}"> Container </tspan>'
              f'<tspan fill="{C["text"]}">{escape(name.ljust(14))}</tspan>'
              f'<tspan fill="{C["green"]}">Started</tspan></text></g>')
    t += 0.2 + len(CONTAINERS) * 0.35 + 0.1

    # 2. título (Monoton, neón)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "title_path.txt")) as f:
        tpath = f.read().strip()
    x0, tw = 34, 599
    d.add(f'<g opacity="0"><animate attributeName="opacity" values="0;1;0.15;0.9;0.3;1;0.6;1" '
          f'keyTimes="0;0.12;0.22;0.36;0.46;0.62;0.75;1" begin="{t}s" dur="1.1s" fill="freeze"/>'
          f'<g><animate attributeName="opacity" values="1;1;0.55;1;0.8;1;1" keyTimes="0;0.9;0.915;0.93;0.95;0.965;1" '
          f'dur="7s" begin="{t+2}s" repeatCount="indefinite"/>'
          f'<path d="{tpath}" fill="url(#grad)" filter="url(#glow)"/></g></g>')
    t += 1.2

    # 3. whoami
    t = d.prompt_line(268, "whoami", t, 0.4)
    name, role, place = WHOAMI
    d.add(f'<g opacity="0">{appear(t+0.15)}<text x="32" y="292" class="t" fill="{C["text"]}">{name} '
          f'(<tspan fill="{C["path"]}">@{USER}</tspan>) <tspan fill="{C["dim"]}">//</tspan> '
          f'<tspan fill="{C["green"]}">{escape(role)}</tspan> <tspan fill="{C["dim"]}">//</tspan> {place}</text></g>')
    t += 0.4

    # 4. stack
    t = d.prompt_line(324, "cat stack.txt", t, 0.5)
    tags = " ".join(f"[{s}]" for s in STACK)
    d.add(f'<g opacity="0">{appear(t+0.15)}<text x="32" y="348" class="t" fill="{C["orange"]}">{tags}</text></g>')
    t += 0.4

    # 4b. estado
    t = d.prompt_line(380, "cat status.txt", t, 0.5)
    d.add(f'<g opacity="0">{appear(t+0.15)}<text x="32" y="404" class="t" fill="{C["green"]}">{escape(STATUS)}</text></g>')
    t += 0.4

    # 5. proyectos
    t = d.prompt_line(436, "ls ~/projects", t, 0.5)
    for i, (name, desc) in enumerate(PROJECTS):
        y = 460 + i * 22
        d.add(f'<g opacity="0">{appear(t+0.15+i*0.15)}<text x="32" y="{y}" class="t" xml:space="preserve">'
              f'<tspan fill="{C["cyan"]}">{escape(name.ljust(20))}</tspan>'
              f'<tspan fill="{C["dim"]}">-&gt; {escape(desc)}</tspan></text></g>')
    t += 0.3 + len(PROJECTS) * 0.15

    # 6. prompt final con cursor
    y = 460 + len(PROJECTS) * 22 + 14
    cx = 32 + (len(PROMPT) + 4) * CW
    d.add(f'<g opacity="0">{appear(t, 0.01)}<text x="32" y="{y}" class="t"><tspan fill="{C["prompt"]}">{PROMPT}</tspan>'
          f'<tspan fill="{C["text"]}">:</tspan><tspan fill="{C["path"]}">~</tspan><tspan fill="{C["text"]}">$</tspan></text>'
          f'<rect x="{cx:.1f}" y="{y-13}" width="9" height="16" fill="{C["text"]}">'
          f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" repeatCount="indefinite"/></rect></g>')

    # 7. feed en vivo
    fy = H - 40
    d.add(f'<line x1="20" y1="{fy-12}" x2="{W-20}" y2="{fy-12}" stroke="{C["border"]}"/>')
    label_w = 112
    feed_txt = escape(feed)
    feed_w = len(feed) * 7.3
    dur = max(18, feed_w / 55)
    d.add(f'<g clip-path="url(#ticker)"><text y="{fy+13}" class="s" fill="#7ee787" xml:space="preserve">{feed_txt}'
          f'<animate attributeName="x" from="{W-20}" to="{20+label_w-feed_w:.0f}" dur="{dur:.0f}s" repeatCount="indefinite"/></text></g>')
    d.add(f'<rect x="20" y="{fy}" width="{label_w}" height="20" rx="3" fill="#238636"/>'
          f'<circle cx="32" cy="{fy+10}" r="3.5" fill="#fff"><animate attributeName="opacity" values="1;0.2;1" dur="1.4s" repeatCount="indefinite"/></circle>'
          f'<text x="42" y="{fy+14}" class="s" fill="#fff" font-weight="700">LIVE FEED</text>')

    defs = (
        f'<defs>'
        f'<linearGradient id="grad" gradientUnits="userSpaceOnUse" x1="{x0}" y1="0" x2="{x0+tw}" y2="0">'
        f'<stop offset="0" stop-color="#3b82f6"/><stop offset=".5" stop-color="#22d3ee"/><stop offset="1" stop-color="#22c55e"/></linearGradient>'
        f'<filter id="glow" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="3.5" result="b"/>'
        f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        f'<clipPath id="bodyunused"><rect x="0" y="36" width="{W}" height="{H-90}"/></clipPath>'
        f'<clipPath id="ticker"><rect x="{20+label_w+8}" y="{fy-2}" width="{W-40-label_w-8}" height="24"/></clipPath>'
        f'</defs>'
    )
    style = (f'<style>.t{{font:14px {MONO};}} .s{{font:12px {MONO};}} .xs{{font:10.5px {MONO};}}</style>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'role="img" aria-label="{USER} terminal">{style}{defs}{"".join(d.parts)}</svg>')


if __name__ == "__main__":
    feed = os.environ.get("FEED_OVERRIDE") or fetch_feed()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(feed))
    print("feed:", feed)
    print("ok ->", OUT)
