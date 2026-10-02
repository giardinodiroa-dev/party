"""The story actors as hand-authored SVG drawings in a soft anime style: rounded shapes,
pastel watercolour fills, warm outlines, big glossy eyes, blush, sparkles.

Each drawing is written to assets/sprites/<actor>.svg the first time, and HIS copy wins
from then on: edit the file and the story shows your version. Nothing here is fetched.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

SPRITES_DIR = Path(__file__).resolve().parents[2] / "assets" / "sprites"
OUT = "#4a3a35"
CREAM, SKY, DEEP, SAGE, BLUSH, STRAW, LILAC, NIGHT = "#fff4dc", "#9ed0e6", "#6fa8c9", "#a9c9a4", "#f6b8b8", "#f1d58a", "#c9b6e4", "#3a3f5c"
WHITE, PEACH, SOOT, GOLD, CORAL, LEAF, ROSE, MINT = "#ffffff", "#fbd4a8", "#2b2b2b", "#f4c95d", "#f08a7a", "#7fb069", "#e8a0bf", "#bfe8d8"

DEFS = f"""<defs>
<radialGradient id="hl" cx="35%" cy="30%" r="70%"><stop offset="0" stop-color="{WHITE}" stop-opacity=".55"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></radialGradient>
<radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="{WHITE}" stop-opacity=".9"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></radialGradient>
<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.5"/></filter>
</defs>"""
STROKE = f'stroke="{OUT}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"'


def svg(body: str) -> str:
    import re
    # a per-element stroke-width after the shared STROKE wins: drop the earlier one inside the same tag
    body = re.sub(r'(stroke-width|stroke-linecap|stroke-linejoin)="[^"]*"(?=[^<>]*\1=")', "", body)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">{DEFS}{body}</svg>'


def eyes(x1: float, x2: float, y: float, r: float = 11) -> str:
    out = ""
    for x in (x1, x2):
        out += (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{OUT}"/>'
                f'<circle cx="{x - r * .32}" cy="{y - r * .35}" r="{r * .36}" fill="{WHITE}"/>'
                f'<circle cx="{x + r * .3}" cy="{y + r * .3}" r="{r * .16}" fill="{WHITE}" opacity=".8"/>')
    return out


def blush(x1: float, x2: float, y: float, r: float = 9) -> str:
    return "".join(f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r * .6}" fill="{BLUSH}" opacity=".75"/>' for x in (x1, x2))


def smile(x: float, y: float, w: float = 14) -> str:
    return f'<path d="M{x - w} {y} Q{x} {y + w * .9} {x + w} {y}" fill="none" {STROKE} stroke-width="3"/>'


def sparkle(x: float, y: float, s: float = 8, color: str = WHITE) -> str:
    return f'<path d="M{x} {y - s} Q{x} {y} {x + s} {y} Q{x} {y} {x} {y + s} Q{x} {y} {x - s} {y} Q{x} {y} {x} {y - s}Z" fill="{color}" opacity=".9"/>'


def sparkles(pts) -> str:
    return "".join(sparkle(x, y, s) for x, y, s in pts)


def hl(x: float, y: float, rx: float, ry: float) -> str:
    return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="url(#hl)"/>'


def soot(x: float, y: float, r: float = 10) -> str:
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{SOOT}" filter="url(#soft)"/>'
            f'<circle cx="{x}" cy="{y}" r="{r * .9}" fill="{SOOT}"/>' + eyes(x - r * .4, x + r * .4, y - r * .1, r * .3))


ACTORS: dict[str, str] = {
    "ufo": svg(
        f'<ellipse cx="128" cy="150" rx="104" ry="30" fill="{LILAC}" {STROKE}/>'
        f'<path d="M72 138 Q128 60 184 138Z" fill="{SKY}" {STROKE}/>' + hl(110, 110, 30, 18)
        + eyes(112, 144, 118, 10) + blush(96, 160, 126) + smile(128, 128, 9)
        + "".join(f'<circle cx="{x}" cy="156" r="6" fill="{GOLD}" {STROKE} stroke-width="2"/>' for x in (70, 100, 128, 156, 186))
        + sparkles([(40, 70, 7), (216, 60, 9), (210, 200, 6)])),
    "rocket": svg(
        f'<path d="M128 24 C170 70 166 140 156 184 L100 184 C90 140 86 70 128 24Z" fill="{CREAM}" {STROKE}/>'
        f'<path d="M100 150 L68 196 L104 184Z M156 150 L188 196 L152 184Z" fill="{CORAL}" {STROKE}/>'
        f'<circle cx="128" cy="104" r="20" fill="{SKY}" {STROKE}/>' + hl(120, 96, 10, 7)
        + f'<path d="M108 184 Q128 240 148 184Z" fill="{GOLD}" {STROKE} stroke-width="3"/>'
        f'<path d="M116 184 Q128 220 140 184Z" fill="{WHITE}" opacity=".8"/>'
        + eyes(120, 136, 100, 5) + sparkles([(50, 60, 8), (210, 90, 6), (60, 220, 7)])),
    "alien": svg(
        f'<path d="M64 120 C64 50 192 50 192 120 C192 170 160 200 128 200 C96 200 64 170 64 120Z" fill="{SAGE}" {STROKE}/>'
        + hl(104, 96, 36, 22)
        + f'<path d="M96 48 L84 18 M160 48 L172 18" fill="none" {STROKE}/><circle cx="84" cy="16" r="7" fill="{GOLD}" {STROKE} stroke-width="3"/><circle cx="172" cy="16" r="7" fill="{GOLD}" {STROKE} stroke-width="3"/>'
        + eyes(100, 156, 118, 18) + blush(84, 172, 150, 11) + smile(128, 164, 12)
        + f'<path d="M110 200 L106 236 M146 200 L150 236" fill="none" {STROKE}/>' + sparkles([(40, 60, 8), (220, 200, 7)])),
    "angel": svg(
        f'<path d="M128 70 C70 20 20 120 110 150 C128 160 128 160 146 150 C236 120 186 20 128 70Z" fill="{WHITE}" opacity=".92" {STROKE}/>'
        f'<ellipse cx="128" cy="30" rx="30" ry="9" fill="none" stroke="{GOLD}" stroke-width="5"/>'
        f'<circle cx="128" cy="78" r="30" fill="{PEACH}" {STROKE}/>'
        f'<path d="M98 70 Q128 30 158 70 Q150 56 128 54 Q106 56 98 70Z" fill="{STRAW}" {STROKE} stroke-width="3"/>'
        + eyes(116, 140, 82, 8) + blush(104, 152, 94) + smile(128, 94, 7)
        + f'<path d="M100 108 L84 220 L172 220 L156 108Z" fill="{CREAM}" {STROKE}/>' + sparkles([(50, 200, 9), (206, 190, 8), (128, 236, 6)])),
    "jesus": svg(
        f'<circle cx="128" cy="76" r="44" fill="url(#glow)"/><circle cx="128" cy="76" r="36" fill="none" stroke="{GOLD}" stroke-width="5"/>'
        f'<circle cx="128" cy="80" r="26" fill="{PEACH}" {STROKE}/>'
        f'<path d="M102 76 Q128 36 154 76 L154 100 Q128 96 102 100Z" fill="{OUT}" opacity=".85"/>'
        f'<path d="M110 100 Q128 122 146 100 Q128 108 110 100Z" fill="{OUT}" opacity=".85"/>'
        + eyes(118, 138, 82, 6) + blush(108, 148, 92, 7)
        + f'<path d="M104 108 L80 230 L176 230 L152 108Z" fill="{WHITE}" {STROKE}/>'
        f'<path d="M104 130 L30 160 M152 130 L226 160" fill="none" {STROKE} stroke-width="8" stroke-linecap="round"/>'
        f'<path d="M104 130 L30 160 M152 130 L226 160" fill="none" stroke="{WHITE}" stroke-width="4"/>'
        + sparkles([(36, 90, 9), (220, 70, 8), (128, 244, 5)])),
    "comet": svg(
        f'<path d="M180 84 L20 150 L180 120Z M180 60 L40 60 L176 92Z M184 110 L60 210 L186 128Z" fill="{SKY}" opacity=".7"/>'
        f'<circle cx="186" cy="96" r="36" fill="{GOLD}" {STROKE}/>' + hl(176, 84, 14, 10)
        + eyes(176, 200, 94, 8) + blush(168, 208, 108, 7) + smile(188, 108, 7) + sparkles([(60, 90, 8), (100, 180, 7), (220, 40, 6)])),
    "planet": svg(
        f'<circle cx="128" cy="128" r="64" fill="{CORAL}" {STROKE}/>' + hl(108, 104, 28, 18)
        + f'<path d="M64 100 Q128 80 192 100" fill="none" stroke="{STRAW}" stroke-width="10" opacity=".8"/>'
        f'<ellipse cx="128" cy="134" rx="118" ry="26" fill="none" {STROKE} stroke-width="8"/><ellipse cx="128" cy="134" rx="118" ry="26" fill="none" stroke="{STRAW}" stroke-width="4"/>'
        + eyes(112, 144, 124, 8) + blush(98, 158, 138) + smile(128, 140, 8) + sparkles([(30, 60, 8), (226, 196, 7)])),
    "moon": svg(
        f'<path d="M150 40 A80 80 0 1 0 150 216 A62 62 0 1 1 150 40Z" fill="{STRAW}" {STROKE}/>' + hl(96, 100, 24, 30)
        + eyes(96, 120, 120, 8) + blush(84, 132, 136, 7) + f'<path d="M100 146 Q110 156 120 146" fill="none" {STROKE} stroke-width="3"/>'
        + f'<path d="M190 70 L196 90 L216 96 L196 102 L190 122 L184 102 L164 96 L184 90Z" fill="{WHITE}"/>' + sparkles([(210, 170, 7), (200, 30, 5)])),
    "gaspump": svg(
        f'<rect x="78" y="52" width="88" height="160" rx="16" fill="{CORAL}" {STROKE}/>' + hl(100, 80, 20, 14)
        + f'<rect x="92" y="66" width="60" height="40" rx="8" fill="{SKY}" {STROKE} stroke-width="3"/>'
        f'<text x="122" y="94" font-family="DejaVu Sans" font-weight="bold" font-size="20" text-anchor="middle" fill="{OUT}">GAS</text>'
        f'<path d="M166 90 Q210 90 210 140 L210 180" fill="none" {STROKE} stroke-width="6"/><rect x="200" y="176" width="22" height="26" rx="5" fill="{NIGHT}" {STROKE} stroke-width="3"/>'
        + eyes(108, 136, 130, 7) + blush(96, 148, 142, 6) + smile(122, 146, 8)
        + f'<rect x="66" y="208" width="112" height="14" rx="6" fill="{SAGE}" {STROKE} stroke-width="3"/>' + sparkles([(40, 60, 8)])),
    "cat": svg(
        f'<path d="M60 96 L54 40 L100 70 L156 70 L202 40 L196 96 Q200 150 128 160 Q56 150 60 96Z" fill="{STRAW}" {STROKE}/>'
        f'<path d="M64 66 L74 52 L94 74Z M192 66 L182 52 L162 74Z" fill="{BLUSH}"/>' + hl(100, 92, 30, 20)
        + eyes(100, 156, 108, 14) + blush(78, 178, 128, 10)
        + f'<path d="M122 124 L134 124 L128 132Z" fill="{BLUSH}" {STROKE} stroke-width="2"/><path d="M118 138 Q128 146 138 138" fill="none" {STROKE} stroke-width="3"/>'
        f'<path d="M40 118 L84 124 M40 136 L84 132 M216 118 L172 124 M216 136 L172 132" fill="none" {STROKE} stroke-width="3"/>'
        f'<ellipse cx="128" cy="196" rx="64" ry="36" fill="{STRAW}" {STROKE}/><path d="M188 190 Q236 160 220 110" fill="none" {STROKE} stroke-width="10"/><path d="M188 190 Q236 160 220 110" fill="none" stroke="{STRAW}" stroke-width="4"/>'
        + sparkles([(30, 40, 7), (226, 230, 6)])),
    "whale": svg(
        f'<path d="M20 128 C20 70 120 60 170 90 C200 110 200 150 170 166 C120 196 20 186 20 128Z" fill="{DEEP}" {STROKE}/>'
        f'<path d="M30 150 C70 180 150 180 176 160 L176 166 C120 196 20 186 20 128Z" fill="{MINT}" opacity=".7"/>' + hl(80, 100, 40, 20)
        + f'<path d="M172 126 L234 94 L224 128 L234 164Z" fill="{DEEP}" {STROKE}/>'
        + eyes(58, 58, 116, 10) + blush(44, 76, 136, 7) + f'<path d="M40 150 Q70 166 100 152" fill="none" {STROKE} stroke-width="3"/>'
        f'<path d="M100 74 Q96 40 76 36 M100 74 Q110 40 126 46" fill="none" stroke="{SKY}" stroke-width="6" stroke-linecap="round"/>'
        + sparkles([(200, 50, 8), (40, 60, 6), (220, 210, 7)])),
    "dove": svg(
        f'<path d="M30 140 C70 100 130 96 176 116 Q210 128 230 120 L210 150 Q150 184 80 170 Q40 162 30 140Z" fill="{WHITE}" {STROKE}/>'
        f'<path d="M110 118 C110 60 160 40 196 60 C170 70 150 100 150 122Z" fill="{CREAM}" {STROKE}/>' + hl(120, 130, 30, 14)
        + f'<path d="M218 128 L238 132 L220 140Z" fill="{GOLD}" {STROKE} stroke-width="2"/>'
        + eyes(204, 204, 126, 6) + blush(196, 196, 138, 5)
        + f'<path d="M60 176 L36 228 M74 180 L62 232" fill="none" stroke="{LEAF}" stroke-width="5" stroke-linecap="round"/><circle cx="40" cy="214" r="7" fill="{LEAF}"/><circle cx="56" cy="226" r="7" fill="{LEAF}"/>'
        + sparkles([(40, 60, 8), (210, 200, 6)])),
    "star": svg(
        f'<path d="M128 22 L156 96 L234 100 L172 150 L192 226 L128 184 L64 226 L84 150 L22 100 L100 96Z" fill="{GOLD}" {STROKE}/>' + hl(108, 100, 30, 24)
        + eyes(110, 146, 122, 10) + blush(94, 162, 140, 8) + smile(128, 142, 9) + sparkles([(30, 40, 9), (226, 50, 7), (220, 220, 8)])),
    "eye": svg(
        f'<path d="M16 128 C70 40 186 40 240 128 C186 216 70 216 16 128Z" fill="{WHITE}" {STROKE}/>'
        f'<circle cx="128" cy="128" r="46" fill="{LILAC}" {STROKE}/><circle cx="128" cy="128" r="38" fill="{NIGHT}"/>'
        f'<circle cx="128" cy="128" r="20" fill="{OUT}"/><circle cx="112" cy="112" r="12" fill="{WHITE}"/><circle cx="142" cy="142" r="6" fill="{WHITE}" opacity=".8"/>'
        + "".join(f'<circle cx="{x}" cy="{y}" r="2.5" fill="{WHITE}"/>' for x, y in ((100, 140), (150, 110), (130, 158), (118, 96)))
        + f'<path d="M40 110 Q128 30 216 110" fill="none" {STROKE} stroke-width="6"/>' + sparkles([(30, 60, 7), (226, 200, 7)])),
    "heart": svg(
        f'<path d="M128 220 C40 160 30 70 86 60 C110 56 124 76 128 90 C132 76 146 56 170 60 C226 70 216 160 128 220Z" fill="{ROSE}" {STROKE}/>' + hl(96, 96, 26, 22)
        + eyes(108, 148, 116, 9) + blush(90, 166, 134, 8) + smile(128, 136, 8)
        + f'<path d="M30 110 Q0 90 20 60 M226 110 Q256 90 236 60" fill="none" stroke="{WHITE}" stroke-width="6" stroke-linecap="round" opacity=".8"/>'
        + sparkles([(40, 40, 8), (216, 40, 8)])),
    "satellite": svg(
        f'<rect x="12" y="104" width="76" height="48" rx="6" fill="{SKY}" {STROKE}/><rect x="168" y="104" width="76" height="48" rx="6" fill="{SKY}" {STROKE}/>'
        f'<path d="M30 104 L30 152 M50 104 L50 152 M70 104 L70 152 M186 104 L186 152 M206 104 L206 152 M226 104 L226 152" stroke="{DEEP}" stroke-width="2"/>'
        f'<rect x="88" y="90" width="80" height="76" rx="12" fill="{CREAM}" {STROKE}/>' + hl(112, 112, 20, 14)
        + eyes(114, 142, 120, 8) + blush(102, 154, 136, 6) + smile(128, 140, 7)
        + f'<path d="M128 90 L128 54" fill="none" {STROKE}/><path d="M96 54 A32 20 0 0 1 160 54" fill="{STRAW}" {STROKE} stroke-width="3"/>'
        + sparkles([(40, 50, 7), (220, 210, 7)])),
    "astronaut": svg(
        f'<circle cx="128" cy="80" r="46" fill="{WHITE}" {STROKE}/><path d="M92 76 A36 30 0 0 1 164 76 A36 36 0 0 1 92 76Z" fill="{NIGHT}" {STROKE} stroke-width="3"/>'
        + f'<ellipse cx="112" cy="66" rx="12" ry="7" fill="{WHITE}" opacity=".6"/>' + eyes(116, 140, 84, 7) + blush(104, 152, 96, 6) + smile(128, 98, 6)
        + f'<rect x="92" y="122" width="72" height="80" rx="20" fill="{CREAM}" {STROKE}/><rect x="112" y="140" width="32" height="18" rx="4" fill="{SKY}" {STROKE} stroke-width="2"/>'
        f'<path d="M92 140 L40 112 M164 140 L216 112" fill="none" {STROKE} stroke-width="14"/><path d="M92 140 L40 112 M164 140 L216 112" fill="none" stroke="{CREAM}" stroke-width="7"/>'
        f'<path d="M106 202 L96 238 M150 202 L160 238" fill="none" {STROKE} stroke-width="14"/><path d="M106 202 L96 238 M150 202 L160 238" fill="none" stroke="{CREAM}" stroke-width="7"/>'
        + sparkles([(40, 60, 8), (216, 220, 6)])),
    "dragon": svg(
        f'<path d="M20 180 C50 100 110 220 150 130 C170 90 200 100 230 90" fill="none" {STROKE} stroke-width="30"/>'
        f'<path d="M20 180 C50 100 110 220 150 130 C170 90 200 100 230 90" fill="none" stroke="{SAGE}" stroke-width="20"/>'
        f'<path d="M20 180 C50 100 110 220 150 130 C170 90 200 100 230 90" fill="none" stroke="{MINT}" stroke-width="6" stroke-dasharray="2 10"/>'
        f'<ellipse cx="216" cy="88" rx="32" ry="24" fill="{SAGE}" {STROKE}/>' + eyes(210, 230, 82, 7) + blush(204, 236, 96, 5)
        + f'<path d="M190 60 L200 36 L212 60 M216 56 L228 34 L236 58" fill="{CORAL}" {STROKE} stroke-width="3"/>'
        f'<path d="M110 150 L90 90 L140 128Z" fill="{LILAC}" {STROKE}/>' + sparkles([(40, 60, 8), (230, 200, 7), (100, 230, 6)])),
    "unicorn": svg(
        f'<ellipse cx="118" cy="150" rx="70" ry="44" fill="{WHITE}" {STROKE}/>'
        f'<path d="M90 190 L84 232 M110 192 L108 234 M136 192 L138 234 M160 186 L166 230" fill="none" {STROKE} stroke-width="12"/><path d="M90 190 L84 232 M110 192 L108 234 M136 192 L138 234 M160 186 L166 230" fill="none" stroke="{WHITE}" stroke-width="6"/>'
        f'<path d="M160 120 C176 70 196 70 214 84 C236 100 230 130 206 138 Q180 142 160 120Z" fill="{WHITE}" {STROKE}/>'
        f'<path d="M196 72 L212 24 L222 78Z" fill="{GOLD}" {STROKE} stroke-width="3"/>'
        f'<path d="M168 110 C150 90 150 120 134 112 C120 130 150 140 150 150" fill="none" stroke="{ROSE}" stroke-width="9" stroke-linecap="round"/><path d="M168 110 C150 90 150 120 134 112" fill="none" stroke="{LILAC}" stroke-width="5" stroke-linecap="round"/>'
        + eyes(200, 200, 100, 8) + blush(190, 190, 114, 6)
        + f'<path d="M52 150 C20 150 20 200 50 200" fill="none" stroke="{ROSE}" stroke-width="10" stroke-linecap="round"/><path d="M52 150 C20 150 20 200 50 200" fill="none" stroke="{SKY}" stroke-width="4" stroke-linecap="round"/>'
        + sparkles([(40, 60, 9), (226, 190, 7), (120, 40, 6)])),
    "fish": svg(
        f'<path d="M30 128 C60 60 160 60 190 128 C160 196 60 196 30 128Z" fill="{GOLD}" {STROKE}/>' + hl(90, 100, 30, 18)
        + f'<path d="M186 128 L240 86 L234 128 L240 170Z" fill="{CORAL}" {STROKE}/>'
        f'<path d="M100 60 L90 30 L130 56Z" fill="{CORAL}" {STROKE} stroke-width="3"/>'
        + eyes(72, 72, 120, 11) + blush(58, 90, 138, 6) + f'<path d="M48 148 Q60 158 72 148" fill="none" {STROKE} stroke-width="3"/>'
        f'<path d="M120 100 Q150 128 120 156" fill="none" {STROKE} stroke-width="3"/>'
        f'<path d="M60 24 L72 44 L96 44 L84 58 L90 80 L72 68 L54 80 L60 58 L48 44 L72 44Z" fill="{GOLD}" {STROKE} stroke-width="2" transform="translate(-10 -6)"/>'
        + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="{SKY}" stroke-width="3"/>' for x, y, r in ((30, 70, 6), (44, 46, 4), (24, 36, 3)))),
    "sun": svg(
        "".join(f'<path d="M128 128 L{128 + 118 * __import__("math").cos(a)} {128 + 118 * __import__("math").sin(a)}" stroke="{GOLD}" stroke-width="{14 if i % 2 else 8}" stroke-linecap="round" opacity=".9"/>' for i, a in enumerate(__import__("math").radians(k * 22.5) for k in range(16)))
        + f'<circle cx="128" cy="128" r="70" fill="{GOLD}" {STROKE}/><circle cx="128" cy="128" r="58" fill="{STRAW}"/>' + hl(104, 100, 28, 22)
        + eyes(108, 148, 122, 10) + blush(90, 166, 142, 9) + smile(128, 144, 10)),
    "earth": svg(
        f'<circle cx="128" cy="128" r="90" fill="{SKY}" {STROKE}/>'
        f'<path d="M70 80 C100 60 140 70 130 100 C120 130 90 128 76 116 C64 104 60 90 70 80Z M150 150 C180 140 206 160 196 186 C186 206 156 206 148 186 C142 170 140 156 150 150Z M60 150 C80 146 92 160 84 176 C76 190 60 184 56 170Z" fill="{LEAF}" {STROKE} stroke-width="3"/>'
        + hl(96, 92, 40, 28) + f'<ellipse cx="170" cy="86" rx="30" ry="12" fill="{WHITE}" opacity=".7"/><ellipse cx="92" cy="200" rx="24" ry="10" fill="{WHITE}" opacity=".6"/>'
        + eyes(108, 148, 130, 9) + blush(92, 164, 148, 8) + smile(128, 150, 8) + sparkles([(30, 40, 8), (226, 220, 7)])),
    "galaxy": svg(
        f'<ellipse cx="128" cy="128" rx="110" ry="60" fill="{LILAC}" opacity=".35" filter="url(#soft)"/>'
        f'<path d="M128 128 C160 100 220 110 230 150 C200 140 170 150 160 160 M128 128 C96 156 36 146 26 106 C56 116 86 106 96 96" fill="none" stroke="{WHITE}" stroke-width="14" stroke-linecap="round" opacity=".85"/>'
        f'<path d="M128 128 C160 100 220 110 230 150 C200 140 170 150 160 160 M128 128 C96 156 36 146 26 106 C56 116 86 106 96 96" fill="none" stroke="{SKY}" stroke-width="6" stroke-linecap="round"/>'
        f'<circle cx="128" cy="128" r="30" fill="{WHITE}" {STROKE}/>' + eyes(118, 138, 126, 7) + blush(108, 148, 138, 5) + smile(128, 140, 5)
        + sparkles([(50, 60, 8), (210, 70, 7), (200, 200, 9), (60, 200, 6)])),
    "meteor": svg(
        f'<path d="M160 100 L20 60 L150 130 M166 120 L40 170 L170 150 M156 86 L60 20 L166 100" fill="{CORAL}" opacity=".8"/>'
        f'<path d="M170 84 C210 70 230 110 214 150 C196 180 150 170 148 136 C146 110 150 92 170 84Z" fill="{STRAW}" {STROKE}/>' + hl(176, 108, 16, 12)
        + f'<circle cx="196" cy="140" r="7" fill="{PEACH}" {STROKE} stroke-width="2"/><circle cx="166" cy="120" r="5" fill="{PEACH}" {STROKE} stroke-width="2"/>'
        + eyes(176, 198, 112, 7) + blush(168, 208, 124, 5) + smile(188, 126, 6) + sparkles([(40, 210, 8), (230, 40, 7)])),
    "phoenix": svg(
        f'<path d="M128 60 C70 20 20 90 60 150 C80 120 100 120 110 140 Q128 100 146 140 C156 120 176 120 196 150 C236 90 186 20 128 60Z" fill="{CORAL}" {STROKE}/>'
        f'<path d="M128 60 C90 40 60 90 80 130 Q110 100 128 120 Q146 100 176 130 C196 90 166 40 128 60Z" fill="{GOLD}" opacity=".9"/>'
        f'<path d="M110 130 C100 170 110 210 128 230 C146 210 156 170 146 130Z" fill="{CORAL}" {STROKE}/>'
        f'<circle cx="128" cy="98" r="24" fill="{GOLD}" {STROKE}/><path d="M112 80 L120 56 L128 78 L136 56 L144 80Z" fill="{CORAL}" {STROKE} stroke-width="2"/>'
        + eyes(120, 136, 100, 6) + blush(110, 146, 110, 5) + f'<path d="M124 114 L132 114 L128 122Z" fill="{GOLD}" {STROKE} stroke-width="2"/>'
        f'<path d="M128 230 C110 236 100 250 96 250 M128 230 C146 236 156 250 160 250" fill="none" stroke="{GOLD}" stroke-width="5" stroke-linecap="round"/>'
        + sparkles([(40, 180, 9), (216, 180, 9), (128, 20, 6)])),
    "owl": svg(
        f'<path d="M64 110 C64 40 192 40 192 110 L192 180 C192 220 64 220 64 180Z" fill="{PEACH}" {STROKE}/>'
        f'<path d="M72 70 L60 30 L104 56 M184 70 L196 30 L152 56" fill="{PEACH}" {STROKE}/>'
        f'<path d="M88 130 C88 200 168 200 168 130 C168 110 88 110 88 130Z" fill="{CREAM}" {STROKE} stroke-width="3"/>'
        f'<circle cx="102" cy="104" r="24" fill="{WHITE}" {STROKE}/><circle cx="154" cy="104" r="24" fill="{WHITE}" {STROKE}/>'
        + eyes(104, 152, 106, 12) + f'<path d="M120 118 L136 118 L128 134Z" fill="{GOLD}" {STROKE} stroke-width="2"/>'
        + "".join(f'<path d="M{x} {y} q6 -8 12 0 q6 -8 12 0" fill="none" {STROKE} stroke-width="2"/>' for x, y in ((104, 160), (120, 176), (104, 192)))
        + blush(84, 172, 128, 7) + f'<path d="M100 220 L94 238 M110 220 L110 238 M146 220 L146 238 M156 220 L162 238" fill="none" {STROKE} stroke-width="4"/>'
        + sparkles([(30, 200, 7), (226, 60, 7)])),
    "butterfly": svg(
        f'<path d="M128 120 C60 40 10 90 60 140 C20 170 60 230 128 160Z" fill="{LILAC}" {STROKE}/>'
        f'<path d="M128 120 C196 40 246 90 196 140 C236 170 196 230 128 160Z" fill="{LILAC}" {STROKE}/>'
        f'<circle cx="78" cy="110" r="16" fill="{ROSE}"/><circle cx="178" cy="110" r="16" fill="{ROSE}"/><circle cx="84" cy="176" r="10" fill="{SKY}"/><circle cx="172" cy="176" r="10" fill="{SKY}"/>'
        f'<ellipse cx="128" cy="140" rx="12" ry="40" fill="{NIGHT}" {STROKE}/>'
        f'<path d="M122 104 Q110 70 96 66 M134 104 Q146 70 160 66" fill="none" {STROKE} stroke-width="3"/><circle cx="96" cy="64" r="4" fill="{OUT}"/><circle cx="160" cy="64" r="4" fill="{OUT}"/>'
        + eyes(123, 133, 118, 4) + sparkles([(40, 40, 8), (216, 40, 8), (128, 230, 6)])),
    "lighthouse": svg(
        f'<path d="M96 230 L108 90 L148 90 L160 230Z" fill="{WHITE}" {STROKE}/>'
        f'<path d="M104 130 L152 130 L155 152 L101 152Z M99 180 L157 180 L160 204 L96 204Z" fill="{CORAL}"/>'
        f'<rect x="100" y="60" width="56" height="32" rx="6" fill="{GOLD}" {STROKE}/><path d="M156 76 L240 44 L240 108Z" fill="{GOLD}" opacity=".45"/>'
        f'<path d="M100 60 L128 36 L156 60Z" fill="{CORAL}" {STROKE}/>'
        + eyes(118, 138, 112, 6) + blush(108, 148, 122, 5) + smile(128, 122, 6)
        + f'<path d="M60 236 Q90 220 128 236 Q166 220 200 236" fill="none" stroke="{SKY}" stroke-width="8" stroke-linecap="round"/>' + sparkles([(40, 60, 8), (210, 200, 7)])),
    "crown": svg(
        f'<path d="M46 196 L36 86 L88 132 L128 56 L168 132 L220 86 L210 196Z" fill="{GOLD}" {STROKE}/>' + hl(100, 120, 30, 22)
        + f'<rect x="46" y="186" width="164" height="28" rx="6" fill="{CORAL}" {STROKE}/>'
        + "".join(f'<circle cx="{x}" cy="{y}" r="9" fill="{c}" {STROKE} stroke-width="3"/>' for x, y, c in ((36, 84, ROSE), (128, 52, SKY), (220, 84, ROSE), (88, 200, SKY), (168, 200, SKY)))
        + eyes(110, 146, 158, 7) + blush(94, 162, 170, 6) + smile(128, 172, 7) + sparkles([(20, 40, 8), (236, 40, 8), (128, 236, 6)])),
    "tree": svg(
        f'<path d="M116 236 L116 150 Q128 140 140 150 L140 236Z" fill="{PEACH}" {STROKE}/>'
        f'<path d="M116 170 Q80 160 70 130 M140 160 Q180 150 190 120" fill="none" {STROKE} stroke-width="8"/>'
        f'<circle cx="128" cy="96" r="70" fill="{SAGE}" {STROKE}/><circle cx="80" cy="120" r="40" fill="{SAGE}" {STROKE}/><circle cx="176" cy="116" r="42" fill="{SAGE}" {STROKE}/>'
        f'<circle cx="128" cy="96" r="66" fill="{LEAF}" opacity=".5"/>' + hl(104, 70, 30, 22)
        + "".join(f'<circle cx="{x}" cy="{y}" r="6" fill="{ROSE}"/>' for x, y in ((96, 80), (150, 70), (120, 120), (170, 134), (74, 130)))
        + eyes(114, 142, 100, 7) + blush(102, 154, 112, 6) + smile(128, 116, 6) + f'<path d="M116 236 Q90 250 60 246 M140 236 Q166 250 196 246" fill="none" {STROKE} stroke-width="4"/>'
        + sparkles([(30, 40, 8), (226, 200, 7)])),
}


def ensure_files(root: Path = SPRITES_DIR) -> None:
    """Write our drawings once; a file that exists is his and is never overwritten."""
    root.mkdir(parents=True, exist_ok=True)
    for kind, text in ACTORS.items():
        f = root / f"{kind}.svg"
        if not f.exists():
            f.write_text(text)


def render(kind: str, size: int = 256, root: Path = SPRITES_DIR) -> QImage | None:
    """His SVG (assets/sprites/<kind>.svg) if present, else ours; None if the actor has neither."""
    f = root / f"{kind}.svg"
    r = QSvgRenderer(str(f)) if f.exists() else (QSvgRenderer(ACTORS[kind].encode()) if kind in ACTORS else None)
    if r is None or not r.isValid():
        return None
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p, QRectF(0, 0, size, size))
    p.end()
    return img
