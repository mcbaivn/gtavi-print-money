"""Cut one candidate into a finished vertical clip.

1080x1920, 30 fps, word-by-word burned captions (slurs and swears masked), hook box in the first seconds,
loudness normalised to -14 LUFS, animated neon gradient border and GTA-style text (see style.py). Writes jobs/<id>/edits/clip_<n>.mp4 + .json (metadata for check.py).

usage: python cut.py jobs/<id> --pick 1 [--layout fill|blur|facecam|react] [--hook "TEXT"]
                     [--cam auto|x:y:w:h] [--title "TEXT" --title-style box|outline --title-secs 0] [--captions word|bubble|none]
                     [--border vice|neon|gold|none] [--font auto|bangers|pricedown]
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import load_json, run, save_json, tool
from style import border_graph, font_for, fontsdir_opt, norm_text, profile, text_px, wrap_px

W, H = 1080, 1920


def ts(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


import re as _re
_SLURS = _re.compile(r"\b(nigg\w*|n[i1]gg?a\w*|f[a@]gg?\w*|retard\w*|tranny\w*|chink\w*|spic\w*|kike\w*)\b", _re.I)


_SWEARS = _re.compile(r"\b(fuck\w*|motherfuck\w*|shit\w*|bitch\w*|cunt\w*|dick\w*|pussy\w*|asshole\w*|bastard\w*|whore\w*|slut\w*)\b", _re.I)


def _mask(m):
    w = m.group(0)
    return w[0] + '*' * (len(w) - 1)


def clean(s, profanity=False):
    """Slurs are always masked (n-word -> n****); hard swears too unless profanity=True."""
    s = _SLURS.sub(_mask, s)
    return s if profanity else _SWEARS.sub(_mask, s)


def esc(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def wrap(text, width):
    lines, cur = [], ''
    for wd in text.split():
        if cur and len(cur) + 1 + len(wd) > width:
            lines.append(cur); cur = wd
        else:
            cur = (cur + ' ' + wd).strip()
    return lines + ([cur] if cur else [])


def balanced_wrap(text, width):
    """Same line count as wrap(), but lines of similar length (no lone last word)."""
    lines = wrap(text, width)
    n = len(lines)
    if n > 1:
        for w in range(max(1, -(-len(text) // n)), width + 1):
            alt = wrap(text, w)
            if len(alt) == n:
                return alt
    return lines


# GTA look: Pricedown when installed (Latin text only), else the bundled Bangers; Black Han Sans for Korean,
# Dela Gothic One for Japanese. White letters, thick black outline, purple drop shadow, active word in GTA VI pink;
# the hook gets a sunset gradient (yellow > orange > pink). Sizes and line breaks come from style.profile().
PINK, ORANGE, YELLOW, PURPLE_SH = "&H00A43FFF", "&H002E9AFF", "&H006AF0FF", "&H00501A3A"
HOOK_TOP = 250
TEXT_MAX_PX = 900   # widest line inside the neon border


def gta_hook(hook, start, end, font="Bangers", y0=HOOK_TOP, style="Hook", fade=True):
    """Hook lines with a 3-band sunset gradient: one outlined base layer + two clipped fill layers per line."""
    p = profile(font)
    ev = []
    lines = wrap_px(norm_text(esc(hook), font).upper(), font, p["hook"], TEXT_MAX_PX)
    pop = "\\fscx92\\fscy92\\t(0,120,\\fscx100\\fscy100)" if fade else ""
    top, bot = p["band"]
    top, bot = top * p["hook"], bot * p["hook"]
    third = (bot - top) / 3
    fad = "\\fad(120,180)" if fade else ""
    for i, ln in enumerate(lines):
        y = y0 + i * p["hook_lh"]
        pos = f"\\an5\\pos({W // 2},{y}){fad}{pop}"
        ev.append(f"Dialogue: 1,{ts(start)},{ts(end)},{style},,0,0,0,,{{{pos}\\1c{PINK}}}{ln}")
        b1, b2 = int(y + top + third), int(y + top + 2 * third)
        for (y1, y2, col) in ((y - p["hook"], b1, YELLOW), (b1, b2, ORANGE)):
            ev.append(f"Dialogue: 2,{ts(start)},{ts(end)},{style},,0,0,0,,"
                      f"{{{pos}\\bord0\\shad0\\1c{col}\\clip(0,{y1},{W},{y2})}}{ln}")
    return ev


def title_lines(text, font, style):
    p = profile(font)
    size = p["title_box"] if style == "box" else p["hook"]
    return wrap_px(norm_text(esc(text), font).upper(), font, size, TEXT_MAX_PX)


def build_ass(words, s0, e0, hook, cap_y, title=None, caps='word', profanity=False, font='auto',
              hook_secs=2.6, outro=None, outro_secs=2.6, outro_y=None):
    f = font_for(hook, title[1] if title else "", outro or "", " ".join(w.get("w", "") for w in words), font=font)
    p = profile(f)
    join = p["join"]
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{f},{p['cap']},&H00FFFFFF,&H00FFFFFF,&H00000000,{PURPLE_SH},0,0,0,0,100,100,{p['spacing']},0,1,10,6,5,60,60,0,1
Style: Hook,{f},{p['hook']},&H00FFFFFF,&H00FFFFFF,&H00000000,{PURPLE_SH},0,0,0,0,100,100,{p['spacing']},0,1,12,7,5,60,60,0,1
Style: TitleBox,{f},{p['title_box']},&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,1,0,1,0,0,5,40,40,0,1
Style: Bubble,{f},{p['bubble']},&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,1,0,3,16,0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    ws = [dict(w, w=norm_text(clean(w["w"], profanity), f)) for w in words if s0 <= w["s"] < e0 and w["w"]]
    # caption groups: up to 3 words (more short CJK chunks) that fit one line; break on punctuation or pauses
    groups, cur = [], []
    for w in ws:
        if cur:
            cand = join.join(x["w"] for x in cur + [w]).upper()
            if (len(cur) == p["group"] or w["s"] - cur[-1]["e"] > 0.6 or cur[-1]["w"][-1:] in ".?!,。！？、"
                    or text_px(cand, f, p["cap"] * 1.08) > TEXT_MAX_PX):
                groups.append(cur); cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    hook_end = hook_secs if hook else 0
    for gi, g in enumerate(groups):
        g_end = groups[gi + 1][0]["s"] if gi + 1 < len(groups) else g[-1]["e"] + 0.4
        g_end = min(g_end, g[-1]["e"] + 0.8)
        for k, w in enumerate(g):
            a = w["s"] - s0; b = (g[k + 1]["s"] - s0) if k + 1 < len(g) else g_end - s0
            if b <= a:
                continue
            parts = []
            for j, x in enumerate(g):
                t = esc(x["w"].upper())
                parts.append("{\\c" + PINK + "\\fscx108\\fscy108}" + t + "{\\c&H00FFFFFF&\\fscx100\\fscy100}" if j == k else t)
            pop = "{\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)}" if k == 0 else ""
            if caps == 'bubble':
                if k == 0:
                    txt = esc(join.join(x['w'] for x in g)).strip()
                    txt = txt[:1].upper() + txt[1:]
                    ev.append(f"Dialogue: 0,{ts(a)},{ts(g_end - s0)},Bubble,,0,0,0,,{{\\pos({W // 2},{cap_y})}}{pop}{txt}")
                continue
            ev.append(f"Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{{\\pos({W // 2},{cap_y})}}{pop}{join.join(parts)}")
    if title:  # reaction title: (style, text, y, seconds)
        st, text, ty, secs = title
        end = (e0 - s0) if secs <= 0 else secs
        if st == 'box':
            body = '\\N'.join(title_lines(text, f, 'box'))
            ev.append(f"Dialogue: 2,{ts(0)},{ts(end)},TitleBox,,0,0,0,,{{\\pos({W // 2},{ty})}}{body}")
        else:  # outline: the same sunset-gradient lettering as the hook, centred on the seam
            n = len(title_lines(text, f, 'outline'))
            ev += gta_hook(text, 0, end, f, y0=int(ty - (n - 1) * p["hook_lh"] / 2), fade=False)
        hook = ''
    if hook:
        ev += gta_hook(hook, 0, hook_end, f)
    if outro:
        dur = e0 - s0
        oy = HOOK_TOP if outro_y is None else outro_y
        ev += gta_hook(outro, max(0, dur - outro_secs), dur, f, y0=oy)
    return hdr + "\n".join(ev) + "\n"


CAP_Y = {"fill": 1380, "blur": 1460, "facecam": 1120, "react": 1560}
TOP = 730  # react layout: face panel height = seam y (even)
GAME_H = H - TOP  # 1190


def even(n):
    return int(n) // 2 * 2


def video_filter(layout, cam, ass, band=None, cam_side='right', src=None, game_x=None, face_expr=None, border='vice'):
    """Layout + burned-caption filter graph ending in [vo]. Reused by translate.py."""
    if layout == "fill":
        v = f"[0:v]scale=-2:{H},crop={W}:{H}[v]"
    elif layout == "blur":
        v = (f"[0:v]split[a][b];[a]scale=-2:{H},crop={W}:{H},boxblur=24:2,eq=brightness=-0.08[bg];"
             f"[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2-80[v]")
    elif layout == 'react':
        sw, sh = src
        if face_expr:  # tracked face crop (no cam frame)
            cw, chh, ex, ey = face_expr
            top = f"crop={cw}:{chh}:{ex}:{ey}"
        else:
            x, y, w, h = map(float, cam.split(':'))
            cw, chh = even(sw * w), even(sh * h)
            top = f"crop={cw}:{chh}:{even(sw * x)}:{even(sh * y)}"
        gw = even(sw * GAME_H / sh) if sw * GAME_H / sh >= W else W
        gx = game_x if game_x is not None else ((gw - W) if cam_side == 'left' else 0)
        v = (f"[0:v]split[a][b];[a]{top},scale={W}:{TOP}:force_original_aspect_ratio=increase,crop={W}:{TOP},setsar=1[cam];"
             f"[b]scale={gw}:{GAME_H},crop={W}:{GAME_H}:{even(gx)}:0,setsar=1[game];[cam][game]vstack[v]")
        if band:
            y0, bh, secs = band
            en = f":enable='lte(t,{secs})'" if secs > 0 else ''
            v = v[:-3] + f"[v0];[v0]drawbox=x=0:y={y0}:w=iw:h={bh}:color=white@1:t=fill{en}[v]"
    else:
        x, y, w, h = map(float, cam.split(":"))
        v = (f"[0:v]split[a][b];[a]crop=iw*{w}:ih*{h}:iw*{x}:ih*{y},scale={W}:{int(H * 0.38)}:force_original_aspect_ratio=increase,"
             f"crop={W}:{int(H * 0.38)}[cam];[b]scale=-2:{H - int(H * 0.38)},crop={W}:{H - int(H * 0.38)}[game];[cam][game]vstack[v]")
    sub = str(ass).replace("\\", "/").replace(":", "\\:")
    return v + ";[v]fps=30[vf];" + border_graph("vf", "vb", border) + f";[vb]subtitles='{sub}'{fontsdir_opt()}[vo]"


def game_offset(video, s0, e0, src, cam_box):
    """Pick the x offset of the 1080-wide game crop that avoids static overlays (viewer counters,
    alerts, chat boxes) and the webcam. Static = pixels that barely change across sampled frames
    but carry edges (text/graphics)."""
    try:
        import cv2, numpy as np
    except ImportError:
        return None
    sw, sh = src
    gw = even(sw * GAME_H / sh)
    if gw <= W:
        return 0
    cap = cv2.VideoCapture(str(video)); frames = []
    for k in range(12):
        cap.set(cv2.CAP_PROP_POS_MSEC, (s0 + (e0 - s0) * (k + 0.5) / 12) * 1000)
        ok, f = cap.read()
        if ok:
            frames.append(cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (gw, GAME_H)).astype(np.float32))
    cap.release()
    if len(frames) < 4:
        return None
    st = np.stack(frames)
    std = st.std(0); med = np.median(st, 0)
    edges = cv2.Canny(med.astype(np.uint8), 60, 160) > 0
    bad = (std < 6) & cv2.dilate(edges.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    x, y, w, h = cam_box  # the cam itself also counts as overlay
    bad[int(y * GAME_H):int((y + h) * GAME_H), int(x * gw):int((x + w) * gw)] = True
    col = bad.sum(0).astype(np.float64); cs = np.concatenate([[0], np.cumsum(col)])
    best, bx = None, 0
    camcols = np.zeros(gw); camcols[int(x * gw):int((x + w) * gw)] = 1; cc = np.concatenate([[0], np.cumsum(camcols)])
    for ox in range(0, gw - W + 1, 8):
        # never show the cam twice; otherwise stay near the centre (game subtitles and action sit there),
        # moving off-centre only when that clearly removes a static overlay (counters, alerts, chat)
        if cc[ox + W] - cc[ox] > 0 and (cc[-1] < gw - W):
            continue
        cost = (cs[ox + W] - cs[ox]) * 0.2 + abs(ox - (gw - W) / 2) * GAME_H * 0.05
        if best is None or cost < best:
            best, bx = cost, ox
    return bx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job"); ap.add_argument("--pick", type=int, default=1)
    ap.add_argument("--layout", choices=["fill", "blur", "facecam", "react"], default="blur")
    ap.add_argument("--title", default="", help="reaction title, e.g. 'Speed REALIZED why GTA 6 took 13 YEARS'")
    ap.add_argument("--title-style", choices=["box", "outline"], default="box")
    ap.add_argument("--title-secs", type=float, default=0, help="0 = whole clip")
    ap.add_argument("--captions", choices=["word", "bubble", "none"], default="word")
    ap.add_argument("--hook", default="")
    ap.add_argument("--border", choices=["vice", "neon", "gold", "none"], default="vice",
                    help="animated neon gradient frame (vice = GTA VI sunset colours)")
    ap.add_argument("--font", choices=["auto", "bangers", "pricedown"], default="auto",
                    help="GTA-style text: Pricedown if installed (not for Vietnamese), else bundled Bangers")
    ap.add_argument("--allow-profanity", action="store_true", help="keep swear words in captions (slurs are always masked)")
    ap.add_argument("--cam", default="auto", help="auto (find the webcam) or x:y:w:h fractions")
    ap.add_argument("--start", type=float); ap.add_argument("--end", type=float)
    ap.add_argument("--outro", default="", help="closing line shown (sunset gradient) over the last seconds")
    ap.add_argument("--voice-hook", help="mp3/wav of a stock or TTS voice reading the hook, played at the start")
    ap.add_argument("--voice-outro", help="mp3/wav of a stock or TTS voice reading the outro, played at the end")
    a = ap.parse_args()
    d = Path(a.job); c = load_json(d / "candidates.json")
    pick = next(x for x in c["candidates"] if x["n"] == a.pick)
    s0 = a.start if a.start is not None else pick["start"]; e0 = a.end if a.end is not None else pick["end"]
    words = load_json(d / "transcript.json")
    out = d / "edits"; out.mkdir(exist_ok=True)
    layout, cam, side = a.layout, a.cam, 'right'
    face_expr = None
    if layout in ('react', 'facecam') and cam == 'auto':
        from facecam import find_cam
        r = find_cam(c['source'], s0, e0)
        if layout == 'react' and r.get('mode') not in ('cam', 'face'):
            sys.exit(f"skipped: no streamer face over gameplay in this moment ({r.get('mode')}: {r.get('reason', '')}). "
                     "React clips need the game on screen with the cam as a separate box. Pick another moment or stream.")
        if layout == 'react':
            from facecam import has_gameplay, face_crop_expr
            if not has_gameplay(c['source'], s0, e0, r['box']):
                sys.exit("skipped: the area outside the webcam is not gameplay (same scene or no game on screen). "
                         "Pick a moment where GTA 6 is on screen.")
            if r.get('mode') == 'face' and r.get('face_track'):
                from common import ffprobe as _fp
                _vs = [x for x in _fp(c['source'])['streams'] if x.get('codec_type') == 'video'][0]
                from facecam import inner_edges
                sw_, sh_ = int(_vs['width']), int(_vs['height'])
                bnd = inner_edges(c['source'], s0, e0, r['face'], sw_, sh_)
                print(f'facecam: cam borders L{bnd[0]} T{bnd[1]} R{bnd[2]} B{bnd[3]} px')
                fe = face_crop_expr(r['face_track'], sw_, sh_, W, TOP, bounds=bnd)
                face_expr = (fe['w'], fe['h'], fe['x'], fe['y'])
                print(f"facecam: no clean cam frame, tracking the face ({r.get('summary', '')})")
        if r.get('mode') in ('cam', 'face'):
            bx = list(r['box'])
            if r['mode'] == 'face':  # no webcam frame: widen the face crop so it is not a blurry close-up
                cx, cy = bx[0] + bx[2] / 2, bx[1] + bx[3] / 2
                bw, bh = min(1.0, bx[2] * 2.6), min(1.0, bx[3] * 2.2)
                bx = [min(max(0.0, cx - bw / 2), 1 - bw), min(max(0.0, cy - bh / 2), 1 - bh), bw, bh]
            cam = ':'.join(f'{v:.4f}' for v in bx)
            side = 'left' if r['box'][0] + r['box'][2] / 2 < 0.5 else 'right'
            print(f"facecam: {r.get('mode')} box {cam} ({r.get('summary', '')})")
        else:
            print(f"facecam: no stable face found ({r.get('reason', '')}), using the blur layout")
            layout = 'blur'
    elif layout in ('react', 'facecam') and cam != 'auto':
        side = 'left' if float(cam.split(':')[0]) + float(cam.split(':')[2]) / 2 < 0.5 else 'right'
    cap_y = CAP_Y[layout]
    title, band = None, None
    if a.title and layout == 'react':
        tf = font_for(a.title, font=a.font)
        n = len(title_lines(a.title, tf, a.title_style))
        if a.title_style == 'box':
            bh = int(n * profile(tf)["title_box"] * profile(tf)["box_lh"]) + 44
            band = (TOP - bh // 2, bh, a.title_secs)
            title = ('box', a.title, TOP, a.title_secs)
        else:
            title = ('outline', a.title, TOP + 40, a.title_secs)
    from common import ffprobe as _probe
    vdur = lambda f: float(_probe(f)["format"]["duration"]) if f else 0.0
    hook_vo, outro_vo = vdur(a.voice_hook), vdur(a.voice_outro)
    hook_secs = max(2.6, hook_vo + 0.5)
    outro_secs = max(2.4, outro_vo + 0.4) if a.outro else 0
    outro_y = 1090 if layout == 'react' else None
    ass = out / f"clip_{a.pick}.ass"
    caps = a.captions
    cap_words = words if caps != 'none' else []
    ass.write_text(build_ass(cap_words, s0, e0, a.hook, cap_y, title=title, caps=caps, profanity=a.allow_profanity, font=a.font,
                             hook_secs=hook_secs, outro=a.outro or None, outro_secs=outro_secs, outro_y=outro_y),
                   encoding="utf-8")
    src = None; gx = None
    if layout == 'react':
        from common import ffprobe
        vs = [x for x in ffprobe(c['source'])['streams'] if x.get('codec_type') == 'video'][0]
        src = (int(vs['width']), int(vs['height']))
        gx = game_offset(c['source'], s0, e0, src, [float(t) for t in cam.split(':')])
    v = video_filter(layout, cam, ass, band=band, cam_side=side, src=src, game_x=gx, face_expr=face_expr, border=a.border)
    mp4 = out / f"clip_{a.pick}.mp4"
    cmd = [tool("ffmpeg"), "-y", "-v", "error", "-ss", f"{s0:.2f}", "-to", f"{e0:.2f}", "-i", c["source"]]
    if a.voice_hook or a.voice_outro:
        # voiceover: original audio ducked to 25 % while the voice speaks, then mixed and normalised
        dur = e0 - s0
        o0 = max(0.0, dur - outro_vo - 0.25)
        duck = []
        if a.voice_hook:
            duck.append(f"between(t,0,{hook_vo + 0.25:.2f})")
        if a.voice_outro:
            duck.append(f"gte(t,{o0 - 0.1:.2f})")
        af = f"[0:a]volume='if({'+'.join(duck)},0.25,1)':eval=frame[bed]"
        mix, k = ["[bed]"], 1
        if a.voice_hook:
            cmd += ["-i", a.voice_hook]
            af += f";[{k}:a]aresample=48000,adelay=150|150,apad[vh]"; mix.append("[vh]"); k += 1
        if a.voice_outro:
            cmd += ["-i", a.voice_outro]
            ms = int(o0 * 1000)
            af += f";[{k}:a]aresample=48000,adelay={ms}|{ms},apad[vx]"; mix.append("[vx]"); k += 1
        af += (f";{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0,"
               f"loudnorm=I=-14:TP=-1.5:LRA=11[ao]")
        cmd += ["-filter_complex", v + ";" + af, "-map", "[vo]", "-map", "[ao]"]
    else:
        cmd += ["-filter_complex", v, "-map", "[vo]", "-map", "0:a?", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
    run(cmd + ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-ar", "48000", "-movflags", "+faststart", str(mp4)])
    info = c.get("info", {})
    save_json(out / f"clip_{a.pick}.json", {"file": str(mp4), "start": s0, "end": e0, "layout": layout, "hook": a.hook or a.title, "title": a.title, "cam": cam, "border": a.border, "font": a.font,
                                            "outro": a.outro, "voice_hook": a.voice_hook, "voice_outro": a.voice_outro,
                                            "source_url": info.get("webpage_url"), "source_title": info.get("title"),
                                            "source_channel": info.get("channel") or info.get("uploader")})
    print(mp4)


if __name__ == "__main__":
    main()
