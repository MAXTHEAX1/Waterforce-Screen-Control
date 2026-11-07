#!/usr/bin/env python3
"""
aorus_lcd.py (v2.9) - standalone tool for the LCD on the Gigabyte AORUS WATERFORCE X 360
(USB 1044:7A4D). Built from USB captures of the official software. EXPERIMENTAL.

Setup (Windows, use the same Python 3.12 as before):
    py -3.12 -m pip install hidapi pillow imageio-ffmpeg

BEFORE RUNNING: fully quit Gigabyte Control Center / RGB Fusion (tray icon too, and
check Task Manager). Two programs can't talk to the cooler at once.

Commands (replace `python` with `py -3.12` if that is how you ran v1):
    python aorus_lcd.py --probe                 # safe: asks the cooler for its status
    python aorus_lcd.py --list                  # shows the GIF/video files stored on the cooler
    python aorus_lcd.py --gif my.gif            # converts, uploads and plays a GIF/video
    python aorus_lcd.py --gif my.gif --fill 120 # same, repeating a short GIF to fill ~2 min
                                                # (the cooler pauses once per file, not per loop)
    python aorus_lcd.py --delete 3              # deletes stored file number 3 (or use its name); asks first
    python aorus_lcd.py --play 3                # plays stored file number 3 (from --list)
    python aorus_lcd.py --play 2 3              # plays files 2 and 3 in turn
    python aorus_lcd.py --list-pics             # shows the pictures stored on the cooler
    python aorus_lcd.py --pic my.png            # converts to a 320x320 JPEG, uploads and shows it
    python aorus_lcd.py --play-pic 2            # shows stored picture number 2 (several = cycle)
    python aorus_lcd.py --delete-pic 1          # deletes stored picture number 1 (or its name); asks first
    python aorus_lcd.py --text "HELLO"          # custom text screen (as in v1)
    python aorus_lcd.py --image my.png          # simple still image (as in v1)
    python aorus_lcd.py --list-sensors          # shows temperatures LibreHardwareMonitor can see
    python aorus_lcd.py --temps                 # feeds your real CPU temp to temp screen 1
    python aorus_lcd.py --temps --screen 3      # same, for another temp screen
    python aorus_lcd.py --config                # shows the screen settings the cooler holds now
    python aorus_lcd.py --set-sensors cpu-liquid # Enthusiast 04: choose cpu, liquid, vrm (one info) or
                                                # cpu-liquid, cpu-vrm, liquid-vrm (two infos, split layout)
    python aorus_lcd.py --temps --screen 4 --set-sensors cpu-liquid
                                                # same choice, then keeps feeding live temperatures
                                                # (--set-sensors alone only sets it once and exits)
    python aorus_lcd.py --status                # live view of the cooler's own report: fan, pump, liquid
    python aorus_lcd.py --get-colors 4          # shows the two colors stored for temp screen 4
    python aorus_lcd.py --set-colors 4 --color1 ff0000 --color2 00ff80
                                                # sets screen 4's colors (leave one out to keep it)
    python aorus_lcd.py --temps --e2 "..."      # EXPERIMENTAL: sends screen settings (see warning)
    python aorus_lcd.py --explore               # TEST: steps through the built-in screens while
                                                # feeding them made-up sensor numbers (see below)

Notes:
  * GIFs/videos are cropped to a square, scaled to 320x320 and sent as H.264 video,
    which is what the official software sends. The cooler plays them by itself.
  * Files stay on the cooler until you remove them with --delete.
    The cooler has about 40 MB of storage, but files over 4 MB are refused unless --force.
    Use --delete to remove files (permanent, asks you to confirm).
  * Which number plays which file is my best reading of the captures. If the wrong file
    plays, try another number from --list.
  * The first captures showed a keep-alive signal; the GIF capture had none. It is off for
    --gif/--play/--list and on for --text/--image. Override with --heartbeat/--no-heartbeat.

WARNING about --e2: sending one particular screen setting during testing made the cooler's
fans speed up briefly and the LCD restart. It recovered, but treat --e2 as risky and only use
settings you have seen the Gigabyte software itself send. --config (read-only) is safe.

--temps needs LibreHardwareMonitor (free, github.com/LibreHardwareMonitor) running AS
ADMINISTRATOR with Options > Remote Web Server > Run switched on. It also needs the Gigabyte
"AORUS LCD" and "Easy Tuning Engine" services stopped, or they overwrite the numbers with
their own. Keep an eye on the CPU temperature the tool prints, since those services are stopped.

--explore: shows screen 1, 2, 3 ... for 8 seconds each and prints which number it is on.
Write down what each screen shows. Screens that display temperatures, usage or clocks will show
these made-up test values: 77 (byte 3), 82 (byte 11), 33 (byte 10), 64 (byte 8) and 2900 (bytes
5-6). Which number appears where tells me what each sensor field means. Use --from/--to to
test a range and --seconds to change the pause. Afterwards pick your usual screen again in the
Gigabyte software (or with --gif/--play/--text).

FAN / PUMP WARNING: this tool does NOT send your fan/pump speed table. Watch your CPU
temperature on the first runs. If temps climb, press Ctrl+C and reopen the Gigabyte software.
"""
import argparse
import io
import json
import os
import re
import shutil
import struct
import math
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

VID, PID = 0x1044, 0x7A4D
REPORT_LEN = 6144            # every report is 6144 bytes, first byte 0x99
CHUNK = REPORT_LEN - 3       # 0x99, 0xF2, length-low-byte, then up to 6141 data bytes
SIZE = 320                   # LCD image is 320x320
PNG_NAME = "_TXT_.png"       # file name the official software uses for custom text
MAX_UPLOAD = 4 * 1024 * 1024    # cooler has ~40 MB, but a big upload once left it silent; stay small
GIF_MODE = 9                 # e7 09 = GIF/video screen (from the captures)
# the two kinds of stored media: screen number (e7 NN) and list kind (f3/f4/f5 NN)
MEDIA = {"gif": {"mode": 9, "kind": 2, "label": "GIF/video"},
         "pic": {"mode": 8, "kind": 1, "label": "picture"}}
LHM_URL = "http://127.0.0.1:8085/data.json"   # LibreHardwareMonitor web server


def pkt(cmd, *args, payload=b""):
    """Build one 6144-byte report: 0x99, command, args..., payload, zero padding."""
    data = bytes([0x99, cmd]) + bytes(args) + payload
    if len(data) > REPORT_LEN:
        raise ValueError("payload too large for one report")
    return data.ljust(REPORT_LEN, b"\x00")


def idle():                 return pkt(0xCD, 0xFF)
def status_req():           return pkt(0xDA)
def mode(n):                return pkt(0xE7, n)
def mode_confirm(n):        return pkt(0xEA, n)
def apply_():               return pkt(0xD6)
def refresh():              return pkt(0xB6)
def list_begin(kind=2):     return pkt(0xF3, kind)
def list_count(kind=2):     return pkt(0xF4, kind)
def list_entry(kind, i):    return pkt(0xF5, kind, i)
def list_sync(n, m=GIF_MODE):   return pkt(0xF0, m, *range(1, n + 1))
def play_list(idxs, m=GIF_MODE): return pkt(0xF6, m, 0x05, *idxs)
def mode_info(m=GIF_MODE):  return pkt(0xFD, m)
def version_req():          return pkt(0xFA, 0x42)


def upload_start(size, name):
    return pkt(0xF1, 0x01, payload=struct.pack(">I", size)
               + bytes([len(name) + 1]) + name.encode() + b"\x00")


def upload_data(chunk):
    return pkt(0xF2, len(chunk) & 0xFF, payload=chunk)


def upload_end(size, op):    # op 0x03 after the PNG, 0x02 after the video
    return pkt(0xF1, op, payload=struct.pack(">I", size))


def delete_cmd(name):       # files live on the cooler's "B:" drive
    path = "B:/" + name
    return pkt(0xFE, len(path), payload=path.encode())
def config_get():            return pkt(0xDF)
def colors_get(screen):      return pkt(0xEA, screen)
def colors_set(screen, c1, c2):   # e4 <screen> R G B R G B (seen in captures)
    return pkt(0xE4, screen, *c1, *c2)
def config_set(b):          return pkt(0xE2, *b)


# Enthusiast 04 sensor choices. Byte 4 = CPU, byte 6 = Liquid, byte 7 = VRM, last byte 5, exactly as
# the Gigabyte software sent them (all six combinations were seen in captures). One sensor shows one
# temperature; two sensors give the split layout with two colors.
SENSOR_MODES = {"cpu": (4,), "liquid": (6,), "vrm": (7,),
                "cpu-liquid": (4, 6), "cpu-vrm": (4, 7), "liquid-vrm": (6, 7)}


def sensor_settings(choice):
    b = [0] * 10
    for i in SENSOR_MODES[choice]:
        b[i] = 1
    b[9] = 5
    return bytes(b)


# Bit positions in the 10-byte screen-settings packet (e2), read from the Gigabyte software's captures.
FLAG_BITS = {"fan": 0, "clocks": 1, "pump": 2, "model": 3, "temp": 4, "threads": 5, "liquid": 6, "vrm": 7}
FUNCTION_ITEMS = ("model", "fan", "pump", "temp", "liquid", "clocks", "threads")   # the 7 boxes on "Function"
FUNCTION_DEFAULT = ("fan", "pump", "temp", "liquid", "clocks", "threads")          # model name left out for now
INTERVALS = (2, 3, 5, 10, 15, 30)       # seconds between items on Function (Gigabyte's box showed 5)
NUMBER_SCREENS = (1, 2, 3, 4, 6)
UNITS = ("C", "F")                      # temperature unit shown by the cooler (byte 8 of the e2 packet: 1 = Fahrenheit)


def default_cfg(screen):
    if screen == 4:
        return {"numbers": True, "sensors": "cpu"}
    if screen == 6:
        return {"numbers": True, "items": list(FUNCTION_DEFAULT), "interval": 5}
    return {"numbers": True, "model": False, "metric": "temp"}         # Enthusiast 01-03


def clean_cfg(screen, cfg):
    """Fill in anything missing and drop anything unknown, so a bad value can never reach the cooler."""
    out = default_cfg(screen)
    cfg = cfg if isinstance(cfg, dict) else {}
    out["numbers"] = bool(cfg.get("numbers", True))
    if screen == 4:
        if cfg.get("sensors") in SENSOR_MODES:
            out["sensors"] = cfg["sensors"]
    elif screen == 6:
        items = cfg.get("items")
        if isinstance(items, list):
            out["items"] = [i for i in FUNCTION_ITEMS if i in items]
        try:
            iv = int(cfg.get("interval", out["interval"]))
            if iv in INTERVALS:
                out["interval"] = iv
        except (TypeError, ValueError):
            pass
    else:
        out["model"] = bool(cfg.get("model", False))
        if cfg.get("metric") in ("temp", "clocks", "none"):
            out["metric"] = cfg["metric"]
    return out


def screen_settings(screen, cfg, tick=1.65, unit="C"):
    """The 10 bytes for the e2 packet. Numbers off = every flag cleared, which is what the Gigabyte
    software sent when its 'Carousel Information' switch was turned off on Enthusiast 02 and 03.
    unit "F" sets byte 8, the 'Temperature Unit' switch of the Gigabyte software (the cooler converts
    the Celsius readings it is sent, so the telemetry itself always stays in Celsius)."""
    cfg = clean_cfg(screen, cfg)
    b = [0] * 10
    if screen == 4:
        b[9] = 5
        if cfg["numbers"]:
            for i in SENSOR_MODES[cfg["sensors"]]:
                b[i] = 1
    elif screen == 6:
        b[9] = max(1, min(255, round(cfg["interval"] / tick)))   # the cooler counts updates (one per ~1.65 s), not seconds
        if cfg["numbers"]:
            for name in cfg["items"]:
                b[FLAG_BITS[name]] = 1
    else:
        b[9] = 1
        if cfg["numbers"]:
            if cfg["model"]:
                b[FLAG_BITS["model"]] = 1
            if cfg["metric"] == "temp":
                b[FLAG_BITS["temp"]] = 1
            elif cfg["metric"] == "clocks":
                b[FLAG_BITS["clocks"]] = 1
    if cfg["numbers"] and unit == "F":
        b[8] = 1
    return bytes(b)


def parse_hex10(text):
    b = bytes.fromhex(text.replace(" ", "").replace(",", ""))
    if len(b) != 10:
        raise SystemExit("--e2 needs exactly 10 bytes, e.g. \"00 01 00 01 00 00 00 00 00 01\"")
    return b


def telemetry(b3=77, b56=2900, b8=64, b10=33, b11=82):
    """Sensor packet the official software sends every ~1.65 s (layout copied from captures;
    the meaning of each field is still being worked out)."""
    return pkt(0xE0, 0x01, b3, 0x18, b56 >> 8, b56 & 0xFF, 0x10, b8, 0x00, b10, b11)


def parse_color(text):
    """'ff8000' or '#FF8000' -> (255, 128, 0)."""
    t = text.strip().lstrip("#")
    if len(t) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in t):
        raise SystemExit("'%s' is not a color. Use 6 hex digits like ff8000 (red green blue)." % text)
    return tuple(int(t[i:i + 2], 16) for i in (0, 2, 4))


def hexcolor(c):
    return "%02x%02x%02x" % tuple(c)


def parse_entry(r):
    """Reply to f5: 99 f5 02 <index> <u16 name length> <name>."""
    n = r[5]                       # byte 4 is a flag (1 on the picture entry I saw), not part of the length
    return bytes(r[6:6 + n]).decode("utf-8", "replace").rstrip("\x00")


# ---------------------------------------------------------------- image / video prep
TEXT_FONTS = {      # key: (Windows font file, fallbacks)
    "arial": ("arial.ttf", "DejaVuSans.ttf"),
    "arial-bold": ("arialbd.ttf", "DejaVuSans-Bold.ttf"),
    "segoe": ("segoeui.ttf", "DejaVuSans.ttf"),
    "segoe-bold": ("segoeuib.ttf", "DejaVuSans-Bold.ttf"),
    "verdana": ("verdana.ttf", "DejaVuSans.ttf"),
    "consolas": ("consola.ttf", "DejaVuSansMono.ttf"),
    "impact": ("impact.ttf", "DejaVuSans-Bold.ttf"),
    "times": ("times.ttf", "DejaVuSerif.ttf"),
}
FONT_DIR = None          # the app sets this to the folder holding fonts you added


def custom_fonts():
    """File names of the fonts you added (.ttf/.otf)."""
    if not FONT_DIR or not os.path.isdir(FONT_DIR):
        return []
    return sorted(f for f in os.listdir(FONT_DIR) if f.lower().endswith((".ttf", ".otf", ".ttc")))


TEXT_DEFAULT = {"color": "ffffff", "bg": "000000", "size": 56, "font": "arial", "x": 0, "y": 0, "slant": 0, "rotate": 0}


def clean_text_style(style):
    out = dict(TEXT_DEFAULT)
    style = style if isinstance(style, dict) else {}
    try:
        out["color"] = hexcolor(parse_color(str(style.get("color", out["color"]))))
        out["bg"] = hexcolor(parse_color(str(style.get("bg", out["bg"]))))
    except SystemExit:
        pass
    for k, lo, hi in (("size", 12, 200), ("x", -160, 160), ("y", -160, 160), ("slant", -45, 45), ("rotate", -180, 180)):
        try:
            out[k] = max(lo, min(hi, int(style.get(k, out[k]))))
        except (TypeError, ValueError):
            pass
    f = style.get("font")
    if f in TEXT_FONTS:
        out["font"] = f
    elif isinstance(f, str) and f.startswith("file:") and f[5:] in custom_fonts():
        out["font"] = f
    return out


def load_font(key, size):
    from PIL import ImageFont
    if isinstance(key, str) and key.startswith("file:") and key[5:] in custom_fonts():
        try:
            return ImageFont.truetype(os.path.join(FONT_DIR, key[5:]), size)
        except OSError:
            pass
    for name in TEXT_FONTS.get(key, TEXT_FONTS["arial"]) + ("DejaVuSans.ttf",):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def make_png(text=None, image_path=None, style=None):
    from PIL import Image, ImageDraw
    if image_path:
        img = Image.open(image_path).convert("RGB").resize((SIZE, SIZE))
    else:
        st = clean_text_style(style)
        img = Image.new("RGB", (SIZE, SIZE), parse_color(st["bg"]))
        font = load_font(st["font"], st["size"])
        mask = Image.new("L", (SIZE, SIZE), 0)            # the letters on their own, so they can be slanted
        ImageDraw.Draw(mask).multiline_text((SIZE // 2 + st["x"], SIZE // 2 + st["y"]), text, fill=255,
                                            font=font, anchor="mm", align="center",
                                            spacing=max(2, st["size"] // 6))
        if st["slant"]:
            k = math.tan(math.radians(st["slant"]))        # + leans right (like italics), - leans left
            cy = SIZE / 2 + st["y"]
            mask = mask.transform((SIZE, SIZE), Image.Transform.AFFINE, (1, k, -k * cy, 0, 1, 0),
                                  resample=Image.Resampling.BICUBIC)
        if st["rotate"]:                                   # + turns clockwise, around the middle of the text
            mask = mask.rotate(-st["rotate"], center=(SIZE / 2 + st["x"], SIZE / 2 + st["y"]),
                               resample=Image.Resampling.BICUBIC)
        img.paste(parse_color(st["color"]), mask=mask)
    for colors in (256, 64, 32, 16, 8, 4, 2):    # the official software sends 8-bit RGBA
        q = img.quantize(colors=colors).convert("RGBA")
        buf = io.BytesIO()
        q.save(buf, format="PNG", optimize=True, compress_level=9)
        png = buf.getvalue()
        if len(png) <= CHUNK:
            return png
    raise SystemExit("Image is too complex for a still image (needs > %d bytes). "
                     "Try simpler artwork, or use --gif for richer content." % CHUNK)


def make_jpeg(path, fit="crop"):
    """320x320 baseline JPEG, quality 90, 4:2:0 - the same as the Gigabyte software sends for pictures."""
    from PIL import Image, ImageOps
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)           # respect phone-photo rotation
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
        img = Image.alpha_composite(bg, img)     # transparent areas become black
    img = img.convert("RGB")
    if fit == "pad":
        img = ImageOps.pad(img, (SIZE, SIZE), color=(0, 0, 0), method=Image.LANCZOS)
    else:
        img = ImageOps.fit(img, (SIZE, SIZE), method=Image.LANCZOS)
    for q in (90, 85, 80, 70, 60):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q, subsampling=2, progressive=False, optimize=False)
        data = buf.getvalue()
        if len(data) <= 300 * 1024:
            return data
    return data


def safe_pic_name(path, name):
    base = name or os.path.splitext(os.path.basename(path))[0]
    base = re.sub(r"[^A-Za-z0-9_-]", "_", base).lower()[:32] or "pic"
    return base + ".jpg"


def _run(cmd):
    """subprocess.run that never opens a console window and never needs a console (the windowed .exe has none)."""
    return subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def find_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    raise SystemExit("ffmpeg not found. Run: py -3.12 -m pip install imageio-ffmpeg")


def media_duration(path):
    """Length of a media file in seconds, read from ffmpeg's header printout (None if unknown)."""
    r = _run([find_ffmpeg(), "-i", path])
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def repeat_clip(path, fill, max_bytes=None):
    """Repeat a finished clip a whole number of times so the stored file is about `fill` seconds
    long. The cooler pauses and goes black each time it reaches the end of a file, so a longer
    file means fewer pauses. No re-encoding, so quality stays the same."""
    length = media_duration(path)
    if not length or length <= 0:
        print("Couldn't read the clip length, so it was not repeated.")
        return path
    n = int(fill // length)
    if max_bytes:
        fit = max_bytes // max(1, os.path.getsize(path))
        if n > fit:
            print("Limiting to %d repeats so the file stays under %.0f MB (use --force to go past that)."
                  % (max(fit, 1), max_bytes / 1048576))
            n = fit
    if n < 2:
        print("Clip is %.1f s, already close to --fill %.0f s; not repeated." % (length, fill))
        return path
    out = os.path.join(os.path.dirname(path), "looped.mkv")
    cmd = [find_ffmpeg(), "-y", "-v", "error", "-stream_loop", str(n - 1), "-i", path,
           "-c", "copy", "-f", "matroska", out]
    r = _run(cmd)
    if r.returncode != 0 or not os.path.exists(out):
        raise SystemExit("Repeating the clip failed:\n" + r.stderr)
    print("Clip is %.1f s; repeated %d times -> about %.1f s." % (length, n, length * n))
    return out


def convert_to_mkv(src, fps, max_seconds, fill=0, max_bytes=None):
    """Same format the official software uploads: H.264 Main, 320x320, yuv420p, Matroska."""
    out = os.path.join(tempfile.mkdtemp(), "clip.mkv")
    vf = ("crop='min(iw,ih)':'min(iw,ih)',scale=%d:%d:flags=lanczos,fps=%s,format=yuv420p"
          % (SIZE, SIZE, fps))
    cmd = [find_ffmpeg(), "-y", "-v", "error", "-i", src, "-t", str(max_seconds), "-an",
           "-vf", vf, "-c:v", "libx264", "-profile:v", "main", "-level", "2.1",
           "-bf", "0", "-refs", "1", "-crf", "24", "-maxrate", "1500k", "-bufsize", "3000k",
           "-f", "matroska", out]
    r = _run(cmd)
    if r.returncode != 0 or not os.path.exists(out):
        raise SystemExit("Conversion failed:\n" + r.stderr)
    if fill and fill > 0:
        out = repeat_clip(out, fill, max_bytes)
    with open(out, "rb") as f:
        return f.read()


def safe_name(path, name):
    base = name or os.path.splitext(os.path.basename(path))[0]
    base = re.sub(r"[^A-Za-z0-9_-]", "_", base)[:32] or "clip"
    return base + ".mkv"


# ---------------------------------------------------------------- cooler connection
class Cooler:
    def __init__(self, heartbeat):
        import hid
        devs = hid.enumerate(VID, PID)
        if not devs:
            raise SystemExit("Cooler (1044:7A4D) not found. Is it plugged in, and is "
                             "Gigabyte software fully closed?")
        self.dev = hid.device()
        self.dev.open_path(devs[0]["path"])
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.thread = None
        self.heartbeat = heartbeat
        if heartbeat:
            self.thread = threading.Thread(target=self._beat, daemon=True)
            self.thread.start()

    def send(self, data):
        with self.lock:
            n = self.dev.write(data)
        if n < 0:
            raise SystemExit("Write failed: %s\nThe cooler has stopped accepting data (it is probably "
                             "busy or stuck). Wait 5 minutes without sending anything; if that "
                             "doesn't help, restart the PC." % self.dev.error())

    def recv(self, timeout=1.0):
        r = self.dev.read(512, int(timeout * 1000))
        if not r:
            return None
        r = bytes(r)
        return r if r[0] == 0x99 else b"\x99" + r

    def request(self, data, cmd, timeout=1.0):
        """Send a packet and wait for the cooler's reply with the same command byte."""
        self.send(data)
        end = time.time() + timeout
        while time.time() < end:
            r = self.recv(max(0.05, end - time.time()))
            if r and len(r) > 1 and r[1] == cmd:
                return r
        return None

    def _beat(self):
        while not self.stop.is_set():
            try:
                self.send(idle())
            except Exception:
                return
            time.sleep(0.048)

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=1)
        self.dev.close()


# ---------------------------------------------------------------- high-level actions
def read_colors(c, screen):
    """Ask the cooler for the two colors stored for a screen. Reply: 99 ea <screen> R G B R G B."""
    r = c.request(colors_get(screen), 0xEA, timeout=2.0)
    if not r or len(r) < 9 or r[2] != screen:
        return None
    return tuple(r[3:6]), tuple(r[6:9])


def get_colors(c, screen):
    cur = read_colors(c, screen)
    if not cur:
        raise SystemExit("No reply for screen %d's colors. Is the screen number right (1-6)? "
                         "Are the Gigabyte services stopped?" % screen)
    print("Screen %d colors: color 1 = %s, color 2 = %s" % (screen, hexcolor(cur[0]), hexcolor(cur[1])))


def set_colors(c, screen, col1, col2):
    """Colors are two RGB triples. A value left out keeps what the cooler has now, which is what
    the Gigabyte software does (it always sends both)."""
    cur = read_colors(c, screen)
    if (col1 is None or col2 is None) and not cur:
        raise SystemExit("Couldn't read screen %d's current colors, so I can't keep the one you left "
                         "out. Give both colors, or check the screen number." % screen)
    new1 = col1 if col1 is not None else cur[0]
    new2 = col2 if col2 is not None else cur[1]
    if cur:
        print("Was:  color 1 = %s, color 2 = %s" % (hexcolor(cur[0]), hexcolor(cur[1])))
    c.send(colors_set(screen, new1, new2))
    time.sleep(0.3)
    after = read_colors(c, screen)
    print("Sent: color 1 = %s, color 2 = %s" % (hexcolor(new1), hexcolor(new2)))
    if after:
        print("Cooler now reports: color 1 = %s, color 2 = %s" % (hexcolor(after[0]), hexcolor(after[1])))


def set_sensors(c, choice, screen=4):
    """Choose what Enthusiast 04 shows. Same steps as the Gigabyte software: switch to the screen,
    send the settings, then read them back."""
    new = sensor_settings(choice)
    c.send(mode(screen)); time.sleep(0.4)
    c.send(config_set(new)); time.sleep(0.3)
    r = c.request(config_get(), 0xDF, timeout=2.0)
    got = bytes(r[2:12]) if r else None
    print("Sent sensor choice '%s' to screen %d: %s" % (choice, screen, new.hex(" ")))
    if got is None:
        print("No read-back from the cooler. Check the screen; run --config to see its settings.")
    elif got == new:
        print("Cooler reports the same settings. Done.")
    else:
        print("Cooler reports different settings: %s" % got.hex(" "))


def list_files(c, quiet=False, tries=1, wait=3.0, what="gif"):
    """Enter the GIF (or picture) screen and read the stored file names, like the official software."""
    M = MEDIA[what]
    r = None
    for attempt in range(1, tries + 1):
        c.send(mode(M["mode"])); time.sleep(0.4)
        c.send(list_begin(M["kind"])); time.sleep(0.5)
        r = c.request(list_count(M["kind"]), 0xF4, timeout=2.0)
        if r:
            break
        if attempt < tries:
            print("  no reply yet (try %d of %d), waiting..." % (attempt, tries))
            time.sleep(wait)
    if not r:
        raise SystemExit("No reply to the file-count request. Make sure Gigabyte Control Center, "
                         "the two Gigabyte services and SignalRGB are closed, or restart the PC.")
    names = []
    for i in range(r[3]):
        e = c.request(list_entry(M["kind"], i), 0xF5)
        names.append(parse_entry(e) if e else "?")
        time.sleep(0.02)
    c.send(mode_info(M["mode"])); time.sleep(0.02)
    c.send(version_req())
    if not quiet:
        print("%s files on the cooler:" % (M["label"][0].upper() + M["label"][1:]))
        for i, n in enumerate(names, 1):
            print("  %d: %s" % (i, n))
        if not names:
            print("  (none)")
    return names


def play(c, idxs, count, what="gif"):
    m = MEDIA[what]["mode"]
    for i in idxs:
        if not 1 <= i <= count:
            raise SystemExit("File number %d doesn't exist (there are %d)." % (i, count))
    c.send(version_req()); time.sleep(0.02)
    c.send(list_sync(count, m)); time.sleep(0.02)
    c.send(list_sync(count, m)); time.sleep(0.02)
    c.send(play_list(idxs, m))
    print("Playing file number(s): %s" % ", ".join(map(str, idxs)))


def delete_file(c, target, what="gif", ask=True):
    m = MEDIA[what]["mode"]
    names = list_files(c, what=what)
    if target.isdigit():
        i = int(target)
        if not 1 <= i <= len(names):
            raise SystemExit("File number %d doesn't exist (there are %d)." % (i, len(names)))
        name = names[i - 1]
    elif target in names:
        name = target
    else:
        raise SystemExit("No file named '%s' on the cooler. Use %s to see the names."
                         % (target, "--list-pics" if what == "pic" else "--list"))
    if ask and input("Permanently delete '%s' from the cooler? (y/N) " % name).strip().lower() != "y":
        raise SystemExit("Cancelled.")
    c.send(delete_cmd(name)); time.sleep(2.0)
    c.send(version_req()); time.sleep(0.05)
    remaining = list_files(c, what=what)
    if name in remaining:
        raise SystemExit("The cooler still lists '%s'; the delete didn't take effect." % name)
    print("Deleted '%s'." % name)
    if remaining:
        c.send(list_sync(len(remaining), m)); time.sleep(0.02)
        c.send(play_list([1], m))
        print("Now playing file 1.")


def upload(c, data, name, end_op, pace, progress=None):
    print("Uploading %s (%d bytes)..." % (name, len(data)))
    c.send(upload_start(len(data), name)); time.sleep(0.02)
    sent = 0
    for off in range(0, len(data), CHUNK):
        chunk = data[off:off + CHUNK]
        c.send(upload_data(chunk)); time.sleep(pace)
        sent += len(chunk)
        if progress:
            progress(sent / len(data))
        if len(data) > 100000 and (off // CHUNK) % 25 == 0:
            print("  %d%%" % (100 * sent // len(data)))
    c.send(upload_end(len(data), end_op)); time.sleep(0.18)
    for _ in range(2):
        r = c.request(apply_(), 0xD6)
        print("  apply reply:", r[:6].hex() if r else "none")
        time.sleep(0.04)


def store_and_play(c, data, name, what, progress=None):
    """Upload a file, wait until the cooler lists it, then play it. Used for GIFs and pictures."""
    names = list_files(c, quiet=True, what=what)
    if name in names:
        raise SystemExit("'%s' already exists on the cooler. Pick another name with --name." % name)
    upload(c, data, name, 0x02, 0.012, progress)
    # a bigger file takes the cooler longer to store, so give it time and keep asking
    patience = int(10 + 15 * len(data) / 1e6)
    print("Waiting for the cooler to finish storing the file (up to %d s)..." % patience)
    names, deadline = [], time.time() + patience
    while time.time() < deadline:
        time.sleep(3.0)
        try:
            names = list_files(c, quiet=True, tries=1, what=what)
        except SystemExit:
            names = []                      # not answering yet; try again
        if name in names:
            break
    if name not in names:
        raise SystemExit("'%s' isn't in the cooler's list after %d s. It may still be "
                         "storing it: wait a few minutes, then list the files. Don't upload "
                         "again until it answers." % (name, patience))
    names = list_files(c, what=what)
    play(c, [names.index(name) + 1], len(names), what)


def fetch_temps(url):
    """Read every temperature sensor from LibreHardwareMonitor's web server."""
    with urllib.request.urlopen(url, timeout=3) as r:
        tree = json.loads(r.read().decode("utf-8", "replace"))
    out = []

    def walk(node):
        sid = node.get("SensorId") or ""
        if "/temperature/" in sid:
            m = re.search(r"-?\d+(?:[.,]\d+)?", str(node.get("Value", "")))
            if m:
                out.append((sid, node.get("Text", ""), float(m.group().replace(",", "."))))
        for ch in node.get("Children") or []:
            walk(ch)

    walk(tree)
    return out


def pick_cpu(temps, sensor_id=None):
    if sensor_id:
        for sid, _, v in temps:
            if sid == sensor_id:
                return v
        return None
    cpu = [t for t in temps if t[0].startswith(("/intelcpu/", "/amdcpu/"))]
    for key in ("package", "tctl", "tdie", "core max", "average"):
        for _, name, v in cpu:
            if key in name.lower():
                return v
    return max((v for _, _, v in cpu), default=None)      # otherwise the hottest core


def pick_vrm(temps, sensor_id=None):
    """VRM temperature: the sensor you name with --vrm-sensor-id, otherwise the first motherboard
    sensor whose name contains 'vrm' or 'mos'. Returns None if there isn't one."""
    if sensor_id:
        for sid, _, v in temps:
            if sid == sensor_id:
                return v
        return None
    for sid, name, v in temps:
        if sid.startswith(("/intelcpu/", "/amdcpu/", "/gpu")):
            continue
        if any(k in name.lower() for k in ("vrm", "mos")):
            return v
    return None


def list_sensors(url):
    try:
        temps = fetch_temps(url)
    except Exception as e:
        raise SystemExit("Can't reach LibreHardwareMonitor at %s (%s).\nStart it as administrator "
                         "and switch on Options > Remote Web Server > Run." % (url, e))
    if not temps:
        print("Connected, but no temperature sensors were found. Is LibreHardwareMonitor "
              "running as administrator?")
    for sid, name, v in temps:
        print("%-40s %-28s %.1f" % (sid, name, v))
    print("\nCPU temperature the tool uses: %s" % (pick_cpu(temps),))
    vrm = pick_vrm(temps)
    print("VRM temperature found automatically: %s" % (vrm if vrm is not None else
          "none (the tool sends a fixed 36 until you pick one with --vrm-sensor-id)"))


def decode_status(r):
    """Fields of the cooler's own status report (reply to da). Meanings are my reading of the captures
    and are not confirmed: fan/pump speed as little-endian 16-bit numbers, then single bytes."""
    return {"fan_rpm?": r[2] | (r[3] << 8), "pump_rpm?": r[5] | (r[6] << 8),
            "byte8": r[8], "byte9": r[9], "byte10": r[10], "liquid?": r[13]}


def watch_status(c, interval):
    print("Reading the cooler's own status every %.0f s. Ctrl+C to stop. Names ending in ? are guesses.\n"
          % interval)
    while True:
        r = c.request(status_req(), 0xDA, timeout=2.0)
        if r and len(r) > 13:
            d = decode_status(r)
            print("  ".join("%s=%s" % kv for kv in d.items()) + "    raw: " + r[2:14].hex(" "))
        else:
            print("no reply")
        time.sleep(interval)


def run_temps(c, screen, interval, url, sensor_id, e2=None, vrm_id=None):
    c.send(mode(screen)); time.sleep(0.25)
    if e2:
        c.send(config_set(e2)); time.sleep(0.25)
    print("Feeding temp screen %d with your CPU temperature. Ctrl+C to stop." % screen)
    warned = False
    vrm_warned = False
    while True:
        try:
            temps = fetch_temps(url)
        except Exception as e:
            temps = []
            if not warned:
                print("Can't reach LibreHardwareMonitor (%s). Start it as administrator and "
                      "switch on Options > Remote Web Server > Run." % e)
                warned = True
        v = pick_cpu(temps, sensor_id)
        if v is None and temps and not warned:
            print("No CPU temperature found. Run --list-sensors and use --sensor-id.")
            warned = True
        if v is not None:
            warned = False
            t = max(0, min(255, int(round(v))))
            vv = pick_vrm(temps, vrm_id)
            if vv is None and vrm_id and not vrm_warned:
                print("VRM sensor '%s' not found; sending a fixed 36. Check --list-sensors." % vrm_id)
                vrm_warned = True
            vrm = max(0, min(255, int(round(vv)))) if vv is not None else 36
            c.send(telemetry(b3=t, b56=1280, b8=vrm, b10=16, b11=60))
            print("CPU %d C   VRM %d C %s  " % (t, vrm, "" if vv is not None else "(fixed)"),
                  end="\r", flush=True)
        time.sleep(interval)


def explore(c, first, last, seconds):
    print("Test values being sent: byte3=77 byte11=82 byte10=33 byte8=64 bytes5-6=2900")
    print("Watch the LCD and write down what each screen shows. Ctrl+C to stop.\n")
    for n in range(first, last + 1):
        print("Screen %d - look at the LCD now..." % n)
        c.send(mode(n))
        end = time.time() + seconds
        while time.time() < end:
            c.send(telemetry())
            time.sleep(1.65)
    print("\nDone. Pick your usual screen again in the Gigabyte software, or use --gif/--play/--text.")


def main():
    ap = argparse.ArgumentParser(description="AORUS WATERFORCE X LCD tool (v2.9)")
    ap.add_argument("--probe", action="store_true", help="ask the cooler for status and print it")
    ap.add_argument("--list", action="store_true", help="list GIF/video files stored on the cooler")
    ap.add_argument("--gif", help="GIF or video file to convert, upload and play")
    ap.add_argument("--delete", metavar="NUMBER_OR_NAME", help="delete a stored GIF/video from the cooler")
    ap.add_argument("--list-pics", action="store_true", help="list the pictures stored on the cooler")
    ap.add_argument("--pic", metavar="FILE", help="picture to convert (320x320 JPEG), upload and show")
    ap.add_argument("--delete-pic", metavar="NUMBER_OR_NAME", help="delete a stored picture from the cooler")
    ap.add_argument("--play-pic", type=int, nargs="+", metavar="N", help="show stored picture number(s)")
    ap.add_argument("--fit", choices=["crop", "pad"], default="crop",
                    help="how --pic fits a non-square picture: crop (default) or pad with black")
    ap.add_argument("--play", type=int, nargs="+", metavar="N", help="play stored file number(s)")
    ap.add_argument("--explore", action="store_true", help="step through built-in screens with test sensor values")
    ap.add_argument("--from", dest="first", type=int, default=1, help="first screen number for --explore")
    ap.add_argument("--to", dest="last", type=int, default=12, help="last screen number for --explore")
    ap.add_argument("--seconds", type=float, default=8.0, help="seconds per screen for --explore")
    ap.add_argument("--temps", action="store_true", help="feed real CPU temperature to a temp screen")
    ap.add_argument("--list-sensors", action="store_true", help="list temperature sensors from LibreHardwareMonitor")
    ap.add_argument("--screen", type=int, default=1, help="temp screen number for --temps (default 1)")
    ap.add_argument("--interval", type=float, default=1.65, help="seconds between updates for --temps")
    ap.add_argument("--lhm-url", default=LHM_URL, help="LibreHardwareMonitor data.json address")
    ap.add_argument("--sensor-id", help="exact SensorId to use for --temps (see --list-sensors)")
    ap.add_argument("--vrm-sensor-id", help="SensorId to show as the VRM temperature (see --list-sensors)")
    ap.add_argument("--config", action="store_true", help="read the cooler's current screen settings")
    ap.add_argument("--status", action="store_true", help="show the cooler's own status (fan, pump, liquid) every 2 s")
    ap.add_argument("--get-colors", type=int, metavar="SCREEN", help="read the two colors stored for a temp screen")
    ap.add_argument("--set-colors", type=int, metavar="SCREEN", help="set a temp screen's colors (use with --color1 and/or --color2)")
    ap.add_argument("--color1", metavar="RRGGBB", help="first color, 6 hex digits, e.g. ff0000")
    ap.add_argument("--color2", metavar="RRGGBB", help="second color, 6 hex digits, e.g. 00ff80")
    ap.add_argument("--set-sensors", choices=sorted(SENSOR_MODES), metavar="CHOICE",
                    help="Enthusiast 04 only: what to show. One of: " + ", ".join(sorted(SENSOR_MODES)))
    ap.add_argument("--e2", help='10 hex bytes of screen settings to send, e.g. "00 01 00 01 00 00 00 00 00 01"')
    ap.add_argument("--text", help="text to show on the LCD")
    ap.add_argument("--image", help="PNG/JPG still image (must compress to ~6 KB)")
    ap.add_argument("--name", help="name to store the GIF under on the cooler")
    ap.add_argument("--fps", default="30", help="frame rate for converted GIFs (default 30)")
    ap.add_argument("--max-seconds", type=float, default=10.0, help="trim clips to this length")
    ap.add_argument("--fill", type=float, default=0, metavar="SECONDS",
                    help="repeat the clip to make the stored file about this long (fewer pauses "
                         "between loops), e.g. --fill 30")
    ap.add_argument("--force", action="store_true", help="allow uploads over 4 MB")
    ap.add_argument("--heartbeat", action="store_true", help="force the keep-alive on")
    ap.add_argument("--no-heartbeat", action="store_true", help="force the keep-alive off")
    args = ap.parse_args()
    if not (args.probe or args.list or args.gif or args.play or args.text or args.image
            or args.explore or args.temps or args.list_sensors or args.config or args.e2 or args.delete\
            or args.get_colors is not None or args.set_colors is not None
            or args.list_pics or args.pic or args.delete_pic or args.play_pic or args.set_sensors\
            or args.status):
        ap.error("choose one of --probe --list --gif --play --delete --list-pics --pic --play-pic "
                 "--delete-pic --text --image --explore --temps --list-sensors --config "
                 "--get-colors --set-colors --set-sensors --status")
    for sc in (args.get_colors, args.set_colors):
        if sc is not None and not 1 <= sc <= 6:
            ap.error("screen number must be 1-6 (the built-in temperature screens)")
    if args.set_colors is not None and not (args.color1 or args.color2):
        ap.error("--set-colors needs --color1 and/or --color2, e.g. --color1 ff0000 --color2 00ff80")
    if args.list_sensors:
        list_sensors(args.lhm_url)
        return

    if args.set_sensors and args.temps and args.screen != 4:
        ap.error("--set-sensors with --temps only works for Enthusiast 04: add --screen 4")
    if args.set_sensors:
        print("This sends a screen-settings packet (e2). The exact packet is one the Gigabyte software "
              "itself sends, but a different e2 once made the cooler restart its screen.")
        if input("Continue? (y/N) ").strip().lower() != "y":
            raise SystemExit("Cancelled.")
    if args.e2:
        print("WARNING: sending screen settings made the cooler restart its screen during testing.")
        if input("Continue anyway? (y/N) ").strip().lower() != "y":
            raise SystemExit("Cancelled.")

    still = bool(args.text or args.image)
    beat = still                       # on for the still-image path (as tested), off otherwise
    if args.heartbeat:
        beat = True
    if args.no_heartbeat:
        beat = False

    png = make_png(args.text, args.image) if still else None
    jpg, jname = None, None
    if args.pic:
        jpg = make_jpeg(args.pic, args.fit)
        jname = safe_pic_name(args.pic, args.name)
        print("Converted: %s, %d bytes (320x320 JPEG)" % (jname, len(jpg)))
    mkv, name = None, None
    if args.gif:
        mkv = convert_to_mkv(args.gif, args.fps, args.max_seconds, args.fill,
                             None if args.force else MAX_UPLOAD)
        name = safe_name(args.gif, args.name)
        print("Converted: %s, %d bytes" % (name, len(mkv)))
        if len(mkv) > MAX_UPLOAD and not args.force:
            raise SystemExit("That's %.1f MB; I stop at %.0f MB because the cooler only has about "
                             "40 MB in total. Use a shorter/simpler GIF (--max-seconds, --fps), a "
                             "smaller --fill, or add --force."
                             % (len(mkv) / 1e6, MAX_UPLOAD / 1048576))

    c = Cooler(heartbeat=beat)
    try:
        if args.probe:
            c.send(status_req())
            r = c.recv(2.0)
            print("reply (%d bytes): %s" % (len(r) if r else 0, r.hex() if r else "none"))
            return
        if args.config:
            r = c.request(config_get(), 0xDF)
            print("current screen settings: %s" % (r[2:12].hex(" ") if r else "no reply"))
            return
        if args.status:
            watch_status(c, 2.0)
            return
        if args.set_sensors and not args.temps:
            set_sensors(c, args.set_sensors)
            return
        if args.get_colors is not None:
            get_colors(c, args.get_colors)
            return
        if args.set_colors is not None:
            set_colors(c, args.set_colors,
                       parse_color(args.color1) if args.color1 else None,
                       parse_color(args.color2) if args.color2 else None)
            return
        if args.temps:
            first_e2 = (sensor_settings(args.set_sensors) if args.set_sensors
                        else parse_hex10(args.e2) if args.e2 else None)
            run_temps(c, args.screen, args.interval, args.lhm_url, args.sensor_id, first_e2,
                      args.vrm_sensor_id)
            return
        if args.e2:
            c.send(config_set(parse_hex10(args.e2)))
            print("Sent screen settings.")
            return
        if args.explore:
            explore(c, args.first, args.last, args.seconds)
            return
        if args.list:
            list_files(c)
            return
        if args.delete:
            delete_file(c, args.delete)
            return
        if args.play:
            names = list_files(c)
            play(c, args.play, len(names))
            return
        if args.list_pics:
            list_files(c, what="pic")
            return
        if args.delete_pic:
            delete_file(c, args.delete_pic, "pic")
            return
        if args.play_pic:
            names = list_files(c, what="pic")
            play(c, args.play_pic, len(names), "pic")
            return
        if jpg:
            store_and_play(c, jpg, jname, "pic")
            return
        if mkv:
            store_and_play(c, mkv, name, "gif")
            return
        # still image / custom text (same sequence as v1, which worked)
        print("Uploading %d-byte image..." % len(png))
        c.send(mode(7)); time.sleep(0.4); c.send(mode_confirm(7)); time.sleep(0.4)
        c.send(upload_start(len(png), PNG_NAME)); time.sleep(0.02)
        c.send(upload_data(png)); time.sleep(0.02)
        c.send(upload_end(len(png), 0x03)); time.sleep(0.18)
        c.send(apply_()); time.sleep(0.04); c.send(apply_()); time.sleep(1.0)
        c.send(mode(7)); time.sleep(0.02); c.send(refresh())
        if beat:
            print("Done. Keeping connection alive - press Ctrl+C to quit.")
            while True:
                time.sleep(1)
        print("Done.")
    except KeyboardInterrupt:
        pass
    finally:
        c.close()


if __name__ == "__main__":
    main()
