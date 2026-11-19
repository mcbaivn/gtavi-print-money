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


def font_for(*texts, font="auto"):
    """font: auto | bangers | pricedown."""
    if font == "bangers" or has_vietnamese(*texts):
        return "Bangers"
    if font in ("auto", "pricedown"):
        pd = _find_pricedown()
        if pd:
            return pd
    return "Bangers"


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
