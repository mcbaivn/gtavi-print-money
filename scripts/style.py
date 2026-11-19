"""GTA look for every short: animated neon gradient border + GTA-style text fonts.

border_graph(src, out, theme)  ffmpeg filter graph that frames [src] with a glowing neon border -> [out]
font_for(*texts)               "Pricedown" family when installed and the text has no Vietnamese, else "Bangers"
FONTS_DIR                      bundled fonts (Bangers, SIL OFL), passed to the subtitles filter as fontsdir

Pricedown (Typodermic) is the classic GTA typeface. Its free desktop licence allows use in rendered video but
not redistribution, so it is not bundled: install it yourself and it is picked up automatically.
Pricedown has no Vietnamese glyphs, so Vietnamese text always uses Bangers.
"""
import os, re
from pathlib import Path

W, H = 1080, 1920
FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"

# 5-stop gradients that slowly rotate around the frame. "vice" = GTA VI sunset palette.
THEMES = {
    "vice": ["0xFF2BD6", "0xFF7A00", "0xFFE53D", "0x00E5FF", "0x9B30FF"],
    "neon": ["0x00F0FF", "0xFF00E1", "0x39FF14", "0x2D5BFF", "0xFF2E63"],
    "gold": ["0xFFE53D", "0xFFB300", "0xFF7A00", "0xFFF4B0", "0xFFB300"],
}
BORDER = 20   # px of solid neon at the edge
RADIUS = 44   # inner corner radius
GLOW = 34     # blur radius of the glow spilling into the picture

_VI = re.compile(r"[\u0102\u0103\u0110\u0111\u01a0\u01a1\u01af\u01b0\u1ea0-\u1ef9]")
_PRICEDOWN = None


def _find_pricedown():
    """Family name of an installed Pricedown font, or ''."""
    global _PRICEDOWN
    if _PRICEDOWN is not None:
        return _PRICEDOWN
    _PRICEDOWN = ""
    dirs = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
            Path.home() / "Library/Fonts", Path("/Library/Fonts"),
            Path.home() / ".local/share/fonts", Path.home() / ".fonts", Path("/usr/share/fonts")]
    for d in dirs:
        try:
            hits = [p for p in d.rglob("*") if p.suffix.lower() in (".ttf", ".otf") and "pricedown" in p.name.lower()]
        except OSError:
            continue
        for p in hits:
            try:
                from fontTools.ttLib import TTFont
                _PRICEDOWN = TTFont(str(p), lazy=True)["name"].getDebugName(1) or ""
            except Exception:
                _PRICEDOWN = "Pricedown Bl"
            if _PRICEDOWN:
                return _PRICEDOWN
    return _PRICEDOWN


def has_vietnamese(*texts):
    return any(_VI.search(t or "") for t in texts)


_HANGUL = re.compile(r"[ᄀ-ᇿ㄰-㆏가-힯]")
_JA = re.compile(r"[぀-ヿ㐀-䶿一-鿿ｦ-ﾟ]")


def font_for(*texts, font="auto"):
    """font: auto | bangers | pricedown. Korean -> Black Han Sans, Japanese -> Dela Gothic One (both bundled)."""
    if any(_HANGUL.search(t or "") for t in texts):
        return "Black Han Sans"
    if any(_JA.search(t or "") for t in texts):
        return "Dela Gothic One"
    if font == "bangers" or has_vietnamese(*texts):
        return "Bangers"
    if font in ("auto", "pricedown"):
        pd = _find_pricedown()
        if pd:
            return pd
    return "Bangers"


# per-font sizes, measured in libass: band = capital/glyph band (top, bottom) around the \an5 anchor as a
# fraction of the font size (used to place the hook's gradient stripes); join = word separator in captions.
PROFILES = {
    "Bangers": dict(file="Bangers-Regular.ttf", cap=160, hook=176, hook_lh=140, title_box=100, box_lh=0.78,
                    bubble=66, band=(-0.147, 0.293), group=3, join=" ", spacing=2),
    "Black Han Sans": dict(file="BlackHanSans-Regular.ttf", cap=120, hook=112, hook_lh=148, title_box=86, box_lh=1.15,
                           bubble=60, band=(-0.45, 0.28), group=3, join=" ", spacing=1),
    "Dela Gothic One": dict(file="DelaGothicOne-Regular.ttf", cap=132, hook=132, hook_lh=150, title_box=82, box_lh=1.2,
                            bubble=58, band=(-0.31, 0.30), group=4, join="", spacing=0),
}
PROFILE_DEFAULT = dict(file=None, cap=150, hook=160, hook_lh=150, title_box=96, box_lh=0.95, bubble=66,
                       band=(-0.30, 0.34), group=3, join=" ", spacing=2)


def profile(font):
    return PROFILES.get(font, PROFILE_DEFAULT)


_FULLWIDTH = str.maketrans({"！": "!", "？": "?", "，": ",", "：": ":", "；": ";", "（": "(", "）": ")"})


def norm_text(s, font):
    """Black Han Sans has no full-width punctuation: use the ASCII forms for Korean."""
    return s.translate(_FULLWIDTH) if font == "Black Han Sans" else s


_ADV = {}


def _advances(font):
    if font in _ADV:
        return _ADV[font]
    fn = profile(font)["file"] or "Bangers-Regular.ttf"
    try:
        from fontTools.ttLib import TTFont
        tt = TTFont(str(FONTS_DIR / fn), lazy=True)
        # libass (like VSFilter) scales a font so that usWinAscent + usWinDescent = the ASS font size
        os2 = tt["OS/2"]
        cmap, hmtx, scale = tt.getBestCmap(), tt["hmtx"], (os2.usWinAscent + os2.usWinDescent) or tt["head"].unitsPerEm
        _ADV[font] = (cmap, hmtx, scale)
    except Exception:
        _ADV[font] = None
    return _ADV[font]


def text_px(s, font, size):
    """Rendered width of s in px (advance widths from the font file; 0.6 em per glyph if unknown)."""
    adv = _advances(font)
    sp = profile(font)["spacing"]
    total = 0.0
    for ch in s:
        if adv and ord(ch) in adv[0]:
            total += adv[1][adv[0][ord(ch)]][0] / adv[2] * size
        else:
            total += (1.0 if _JA.search(ch) or _HANGUL.search(ch) else 0.6) * size
        total += sp
    return total


def _tokens(text, font):
    """Breakable units: words, or for Japanese short phrase chunks (break after kana runs and punctuation)."""
    if profile(font)["join"]:
        return text.split()
    out, cur = [], ""
    hira = lambda c: "぀" <= c <= "ゟ"
    for i, ch in enumerate(text.replace(" ", "")):
        cur += ch
        nxt = text.replace(" ", "")[i + 1] if i + 1 < len(text.replace(" ", "")) else ""
        if ch in "、。！？!?…" or (hira(ch) and nxt and not hira(nxt) and nxt not in "、。！？!?…ー"):
            out.append(cur); cur = ""
    return out + ([cur] if cur else [])


def wrap_px(text, font, size, max_px, max_lines=3):
    """Greedy wrap by real width, then rebalance so lines have similar width (no lone last word)."""
    toks, j = _tokens(text, font), profile(font)["join"]
    if not toks:
        return []

    def greedy(limit):
        lines, cur = [], []
        for t in toks:
            if cur and text_px(j.join(cur + [t]), font, size) > limit:
                lines.append(cur); cur = [t]
            else:
                cur.append(t)
        return lines + ([cur] if cur else [])

    base = greedy(max_px)
    n = len(base)
    if n > 1:
        total = text_px(j.join(toks), font, size)
        lim = total / n
        while lim < max_px:
            alt = greedy(lim)
            if len(alt) == n:
                base = alt
                break
            lim += 10
    return [j.join(l) for l in base[:max_lines]]


def fontsdir_opt():
    p = str(FONTS_DIR).replace("\\", "/").replace(":", "\\:")
    return f":fontsdir='{p}'"


def border_graph(src, out, theme="vice", w=W, h=H):
    """Filter graph: [src] (w x h) -> [out] with an animated neon gradient border and inner glow.

    Masks are drawn once (geq on a single frame, then looped), so the per-frame cost is the gradient,
    two alpha merges and two overlays.
    """
    if theme in (None, "", "none"):
        return f"[{src}]null[{out}]"
    cols = THEMES.get(theme, THEMES["vice"])
    t, r = BORDER, RADIUS
    # distance from the inner rounded rectangle (inset t, corner radius r); > r means "in the border"
    dist = (f"hypot(max(abs(X-{w / 2})-({w / 2 - t - r}),0),max(abs(Y-{h / 2})-({h / 2 - t - r}),0))")
    ring = f"255*clip({dist}-{r}+0.5,0,1)"
    core = f"255*clip(1.6-abs({dist}-{r}-1.5),0,1)"  # thin bright line on the inner edge: the "neon tube"
    stops = ":".join(f"c{i}={c}" for i, c in enumerate(cols))
    one = f"color=c=black:s={w}x{h}:r=30:d=0.04,format=gray"
    return (
        f"gradients=s={w}x{h}:r=30:{stops}:n={len(cols)}:speed=0.012:x0=0:y0=0:x1={w}:y1={h},format=rgba,split=2[nb_g1][nb_g2];"
        f"{one},geq=lum='{ring}',loop=loop=-1:size=1,split=2[nb_ring][nb_r2];"
        f"[nb_r2]boxblur=lr={GLOW}:lp=2,lutyuv=y='min(255,val*1.6)'[nb_glow];"
        f"{one},geq=lum='{core}',loop=loop=-1:size=1[nb_core];"
        f"[nb_g1][nb_ring]alphamerge[nb_ringc];"
        f"[nb_g2][nb_glow]alphamerge,colorchannelmixer=aa=0.85[nb_glowc];"
        f"color=c=white:s={w}x{h}:r=30,format=rgba[nb_white];[nb_white][nb_core]alphamerge,colorchannelmixer=aa=0.8[nb_corec];"
        f"[{src}]format=yuv420p[nb_in];[nb_in][nb_glowc]overlay=shortest=1:format=auto[nb_t1];"
        f"[nb_t1][nb_ringc]overlay=shortest=1:format=auto[nb_t2];[nb_t2][nb_corec]overlay=shortest=1:format=auto[{out}]"
    )
