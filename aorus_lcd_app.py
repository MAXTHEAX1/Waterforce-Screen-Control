#!/usr/bin/env python3
"""
Waterforce Screen Control - interactive app for the LCD on the Gigabyte AORUS WATERFORCE X 360.

How it works: this program talks to the cooler (using the engine in aorus_lcd.py) and runs a small web
page that only your own PC can reach (127.0.0.1). The page opens in an app-style window (Microsoft Edge
or Chrome in "app" mode), so it looks like a normal program. A tray icon keeps it running in the
background. It remembers the last setting and re-applies it when it starts.

Needs: hidapi, pillow, imageio-ffmpeg (same as the command-line tool). Optional: pystray (tray icon).
Build the .exe with build.bat.
"""
import base64
import collections
import ctypes
import glob
import json
import os
import queue
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if sys.stdout is None:                      # windowed .exe has no console; the engine's print() calls go nowhere
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
import aorus_lcd as lcd
import wsc_logo
from aorus_ui import HTML

APP = "WaterforceScreenControl"          # internal name: settings folder, startup entry, single-instance check
TITLE = "Waterforce Screen Control"       # name shown to you
VERSION = "1.2.1"
IS_WIN = os.name == "nt"
NO_WINDOW = 0x08000000 if IS_WIN else 0
DEVNULL = subprocess.DEVNULL
DATA_DIR = os.environ.get("AORUSLCD_DIR") or os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~/.config"), APP)
os.makedirs(DATA_DIR, exist_ok=True)
THUMB_DIR = os.path.join(DATA_DIR, "thumbs")
FONT_DIR = os.path.join(DATA_DIR, "fonts")
for _d in (THUMB_DIR, FONT_DIR):
    os.makedirs(_d, exist_ok=True)
lcd.FONT_DIR = FONT_DIR                       # fonts you add show up in the Text page
_OLD_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~/.config"), "AorusLCD")
if not os.environ.get("AORUSLCD_DIR") and os.path.isdir(_OLD_DIR) and not os.path.exists(os.path.join(DATA_DIR, "settings.json")):
    try:                                      # carry over settings saved under the earlier name
        import shutil
        for _f in ("settings.json", "logo.png"):
            if os.path.exists(os.path.join(_OLD_DIR, _f)):
                shutil.copy2(os.path.join(_OLD_DIR, _f), os.path.join(DATA_DIR, _f))
    except OSError:
        pass
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
LOG_PATH = os.path.join(DATA_DIR, "app.log")
LHM_TASK = "WaterforceScreenControl-LibreHardwareMonitor"
LOGO_PATH = os.path.join(DATA_DIR, "logo.png")

DEFAULTS = {
    "port": 47615,
    "lhm_url": lcd.LHM_URL,
    "cpu_sensor_id": "",
    "vrm_sensor_id": "",          # pick yours in Settings (boards differ); blank = try to find one automatically
    "lhm_path": "",
    "launch_lhm": True,
    "apply_on_start": True,
    "interval": 1.65,
    "last": None,                 # what was showing last, re-applied at start
    "colors": {},                 # per screen: ["rrggbb", "rrggbb"]
    "screen_cfg": {},             # per screen: numbers on/off, sensors, function items ...
    "media_cache": {"gif": [], "pic": []},
    "text": {"text": "HELLO", "color": "ffffff", "bg": "000000", "size": 56, "font": "arial", "x": 0, "y": 0, "slant": 0, "rotate": 0},
    "theme": {"accent": "#ff6a1a", "bg": "#0d0f14"},
    "unit": "C",                  # temperature unit on the cooler and in the app: "C" or "F"
    "logo_version": 0,
}


# ------------------------------------------------------------------ settings and log
class Settings:
    def __init__(self):
        self.lock = threading.RLock()
        self.data = json.loads(json.dumps(DEFAULTS))
        try:
            with open(SETTINGS_PATH, encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                self.data.update({k: v for k, v in saved.items() if k in DEFAULTS})
        except (OSError, ValueError):
            pass
        if self.data.get("unit") not in lcd.UNITS:
            self.data["unit"] = "C"
        lp, local = str(self.data.get("lhm_path") or ""), os.environ.get("LOCALAPPDATA") or ""
        if lp and local and os.path.normcase(lp).startswith(os.path.normcase(os.path.join(local, "Microsoft", "WinGet"))):
            self.data["lhm_path"] = ""          # an earlier version saved this by itself; it is found automatically

    def get(self, key):
        with self.lock:
            return self.data[key]

    def set(self, key, value):
        with self.lock:
            self.data[key] = value
            self._save()

    def update(self, values):
        with self.lock:
            for k, v in values.items():
                if k in DEFAULTS:
                    self.data[k] = v
            self._save()

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.data))

    def _save(self):
        try:
            tmp = SETTINGS_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp, SETTINGS_PATH)
        except OSError:
            pass


def file_log(text):
    try:
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 500_000:
            os.replace(LOG_PATH, LOG_PATH + ".old")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), text))
    except OSError:
        pass


def thumb_name(what, name):
    return "%s_%s.%s" % (what, re.sub(r"[^A-Za-z0-9_-]", "_", name), "gif" if what == "gif" else "png")


def thumb_url(fname):
    try:
        return "%s?v=%d" % (fname, int(os.path.getmtime(os.path.join(THUMB_DIR, fname))))
    except OSError:
        return None


def make_thumb(what, src_path, name, data, opts):
    """A small preview of what you uploaded, so the dashboard can show the real picture/animation."""
    try:
        out = os.path.join(THUMB_DIR, thumb_name(what, name))
        if what == "pic":
            import io
            from PIL import Image
            Image.open(io.BytesIO(data)).convert("RGB").resize((256, 256)).save(out, "PNG")
        else:
            secs = min(float(opts.get("max_seconds", 10)), 6)
            cmd = [lcd.find_ffmpeg(), "-y", "-v", "error", "-t", str(secs), "-i", src_path, "-an", "-vf",
                   "crop='min(iw,ih)':'min(iw,ih)',scale=200:200:flags=lanczos,fps=10", "-loop", "0", out]
            lcd._run(cmd)
    except Exception:
        file_log(traceback.format_exc())


def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(round(v))))


# ------------------------------------------------------------------ engine (owns the cooler)
class Engine(threading.Thread):
    """One thread talks to the cooler, so commands never overlap. Everything the page asks for is a
    "job" queued here; the page polls the state to see progress."""

    def __init__(self, st):
        super().__init__(daemon=True, name="engine")
        self.st = st
        self.q = queue.Queue()
        self.c = None
        self.connected = False
        self.cooler_error = "Looking for the cooler..."
        self.feed_screen = None
        self.readings = {"cpu": None, "vrm": None, "liquid": None, "fan": None, "pump": None}
        self.lhm = {"ok": False, "error": "Not checked yet", "temps": [], "checked": False}
        self.busy = None
        self.converting = None
        self.events = collections.deque(maxlen=40)
        self.eid = 0
        cache = st.get("media_cache")
        self.media = {"gif": list(cache.get("gif", [])), "pic": list(cache.get("pic", []))}
        self.mode = st.get("last")
        if self.mode and self.mode.get("kind") in ("temp", "builtin") and \
                self.mode.get("screen") not in lcd.NUMBER_SCREENS:
            self.mode = None                  # that screen was removed from the app
            st.set("last", None)
        self.stop_evt = threading.Event()
        self.applied_once = False
        self.lhm_launched = False
        self.lhm_install = {"state": "idle", "step": "", "progress": None, "error": "", "warnings": [],
                            "reboot": False}          # state: idle / running / done / failed
        self.install_lock = threading.Lock()
        self.lhm_run_id = None
        self.feed_wait = 90.0                 # seconds to wait for LibreHardwareMonitor's feed after setup
        self._exe_cache = (0.0, "")
        self.started = time.time()

    # ---- events / state
    def log(self, level, text):
        self.eid += 1
        self.events.append({"id": self.eid, "level": level, "text": text})
        file_log("[%s] %s" % (level, text))

    def snapshot(self):
        busy = self.busy
        if self.converting:
            busy = {"label": self.converting, "progress": None}
        return {
            "version": VERSION,
            "title": TITLE,
            "custom_logo": os.path.exists(LOGO_PATH),
            "fonts": lcd.custom_fonts(),
            "thumbs": self.thumb_map(),
            "text_img": thumb_url("text_last.png"),
            "connected": self.connected,
            "cooler_error": self.cooler_error,
            "lhm": {"ok": self.lhm["ok"], "error": self.lhm["error"], "temps": self.lhm["temps"],
                    "checked": self.lhm.get("checked", True)},
            "lhm_install": dict(self.lhm_install),
            "lhm_exe": self.lhm_exe(),
            "readings": dict(self.readings),
            "mode": self.mode,
            "feed_screen": self.feed_screen,
            "busy": busy,
            "events": list(self.events),
            "media": self.media,
            "settings": self.st.snapshot(),
        }

    def thumb_map(self):
        names = {"gif": set(self.media["gif"]), "pic": set(self.media["pic"])}
        m = self.mode
        if m and m.get("kind") in names:
            names[m["kind"]].update(m.get("names", []))
        out = {}
        for what, ns in names.items():
            for n in ns:
                u = thumb_url(thumb_name(what, n))
                if u:
                    out["%s/%s" % (what, n)] = u
        return out

    def submit(self, label, fn, *a, **kw):
        self.q.put((label, fn, a, kw))

    # ---- connection
    def _connect(self):
        try:
            self.c = lcd.Cooler(heartbeat=False)
        except SystemExit as e:
            self.connected, self.cooler_error = False, str(e)
            return
        except Exception as e:                                  # e.g. the hid library is missing
            self.connected, self.cooler_error = False, "Can't open the USB library: %s" % e
            return
        self.connected, self.cooler_error = True, ""
        self.log("info", "Connected to the cooler.")

    def _disconnect(self, why):
        try:
            if self.c:
                self.c.close()
        except Exception:
            pass
        self.c = None
        self.connected, self.cooler_error = False, why

    # ---- main loop
    def run(self):
        threading.Thread(target=self._lhm_loop, daemon=True, name="lhm").start()
        next_status = next_feed = 0.0
        while not self.stop_evt.is_set():
            if not self.connected:
                self._connect()
                if not self.connected:
                    self._drain_jobs_with_error()
                    time.sleep(2.0)
                    continue
                if not self.applied_once:
                    self.applied_once = True
                    if self.st.get("apply_on_start") and self.st.get("last"):
                        self.submit("Restoring your last setting", self.job_apply_last)
            try:
                label, fn, a, kw = self.q.get(timeout=0.1)
            except queue.Empty:
                label = None
            if label is not None:
                self._run_job(label, fn, a, kw)
                continue
            now = time.time()
            try:
                if self.feed_screen and now >= next_feed:
                    self._feed()
                    next_feed = now + float(self.st.get("interval"))
                if now >= next_status:
                    self._poll()
                    next_status = now + 3.0
            except SystemExit as e:
                self.log("error", "Lost the cooler: %s" % e)
                self._disconnect(str(e))

    def _drain_jobs_with_error(self):
        while True:
            try:
                self.q.get_nowait()
            except queue.Empty:
                return
            self.log("error", "The cooler isn't connected, so that didn't happen.")

    def _run_job(self, label, fn, a, kw):
        self.busy = {"label": label, "progress": None}
        try:
            fn(*a, **kw)
        except SystemExit as e:
            msg = str(e)
            self.log("error", msg)
            if "Write failed" in msg:
                self._disconnect(msg)
        except Exception as e:
            self.log("error", "%s failed: %s" % (label, e))
            file_log(traceback.format_exc())
        finally:
            self.busy = None

    def _feed(self):
        cpu = self.readings["cpu"]
        if cpu is None:
            return
        vrm = self.readings["vrm"]
        self.c.send(lcd.telemetry(b3=clamp(cpu), b56=1280, b8=clamp(vrm) if vrm is not None else 36,
                                  b10=16, b11=60))

    def _poll(self):
        r = self.c.request(lcd.status_req(), 0xDA, timeout=0.8)
        if r and len(r) > 13:
            d = lcd.decode_status(r)
            self.readings.update(fan=d["fan_rpm?"], pump=d["pump_rpm?"], liquid=d["liquid?"])

    # ---- LibreHardwareMonitor poller (separate thread, never touches the cooler)
    def _lhm_loop(self):
        while not self.stop_evt.is_set():
            url = self.st.get("lhm_url")
            try:
                temps = lcd.fetch_temps(url)
                self.lhm = {"ok": True, "error": "", "checked": True,
                            "temps": [[sid, name, round(v, 1)] for sid, name, v in temps][:80]}
                cpu = lcd.pick_cpu(temps, self.st.get("cpu_sensor_id") or None)
                vrm = lcd.pick_vrm(temps, self.st.get("vrm_sensor_id") or None)
                self.readings["cpu"] = cpu
                self.readings["vrm"] = vrm
            except Exception as e:
                self.lhm = {"ok": False, "error": "Can't reach LibreHardwareMonitor (%s)" % e, "temps": [],
                            "checked": True}
                self.readings["cpu"] = self.readings["vrm"] = None
                self._maybe_launch_lhm()
            time.sleep(float(self.st.get("interval")))

    def _maybe_launch_lhm(self):
        """Start LibreHardwareMonitor through its login task if it isn't running. Waits a little after the app
        starts, because at login the task may already be launching it."""
        if self.lhm_launched or not self.st.get("launch_lhm") or time.time() - self.started < 25:
            return
        if self.lhm_install["state"] == "running":
            return
        exe = self.lhm_exe()
        if not exe:
            return
        self.lhm_launched = True
        if lhm_running():
            return
        if IS_WIN and _cmd(["schtasks", "/run", "/tn", LHM_TASK], timeout=20)[0] == 0:
            self.log("info", "Started LibreHardwareMonitor.")
            return
        # LibreHardwareMonitor must run as administrator, which only its login task can do without a prompt.
        self.log("info", "LibreHardwareMonitor isn't running and has no start-at-login task. Press the "
                         "LibreHardwareMonitor button on the Dashboard to set it up.")

    def lhm_exe(self):
        """Where LibreHardwareMonitor.exe is (remembered for a few seconds: the page asks every second)."""
        stamp, found = self._exe_cache
        if time.time() - stamp > 5:
            found = find_lhm_exe(self.st.get("lhm_path"))
            self._exe_cache = (time.time(), found)
        return found

    def _set_install(self, **kw):
        self.lhm_install = dict(self.lhm_install, **kw)

    def start_lhm_setup(self):
        """One click: download and set up LibreHardwareMonitor (and its sensor driver), switch on its data feed,
        make it start at every login and start it now. Returns at once; the page follows lhm_install."""
        if not IS_WIN:
            raise SystemExit("LibreHardwareMonitor setup only works on Windows.")
        with self.install_lock:
            if self.lhm_install["state"] == "running":
                return False
            self._set_install(state="running", step="Waiting for Windows' permission prompt...", progress=0.0,
                              error="", warnings=[], reboot=False)
        threading.Thread(target=self._lhm_setup_thread, daemon=True, name="lhm-setup").start()
        return True

    def _lhm_setup_thread(self):
        self.log("info", "Setting up LibreHardwareMonitor... choose Yes on the Windows permission prompt.")
        m = re.search(r":(\d+)", self.st.get("lhm_url") or "")
        params = {"exe": self.st.get("lhm_path"), "port": m.group(1) if m else "8085", "user": current_user()}
        self.lhm_run_id = secrets.token_hex(8)
        try:
            res = run_helper("setup", params, timeout=900, run_id=self.lhm_run_id,
                             on_update=lambda step, prog: self._set_install(step=step, progress=prog))
        except SetupError as e:
            self._fail_install(str(e))
            return
        except Exception as e:
            file_log(traceback.format_exc())
            self._fail_install("Something unexpected went wrong: %s. Click Show details." % e)
            return
        self._exe_cache = (0.0, "")
        self.lhm_launched = True
        warnings = list(res.get("warnings") or [])
        reboot = bool(res.get("reboot"))
        self._set_install(step="Waiting for LibreHardwareMonitor to start sending temperatures...", progress=0.97,
                          warnings=warnings, reboot=reboot)
        time.sleep(3.0)                      # (when repairing, the old feed may not have dropped yet)
        end = time.time() + self.feed_wait
        while time.time() < end and not self.lhm["ok"]:
            time.sleep(1.0)
        for w in warnings:
            self.log("error", w)
        if self.lhm["ok"]:
            self._set_install(state="done", step="", progress=1.0)
            self.log("info", "LibreHardwareMonitor is running and sending temperatures.")
        elif reboot:
            self._fail_install("The setup finished, but Windows needs to restart to finish installing the sensor "
                               "driver. Restart your PC; LibreHardwareMonitor then starts by itself.", warnings)
        else:
            self._fail_install("LibreHardwareMonitor is installed and was started, but I can't reach its data feed "
                               "yet. Give it a minute and press Try again, or restart your PC once.", warnings)

    def _fail_install(self, text, warnings=None):
        self._set_install(state="failed", step="", progress=None, error=text,
                          warnings=list(warnings) if warnings is not None else self.lhm_install["warnings"])
        self.log("error", text)

    def lhm_task_remove(self):
        """Stop LibreHardwareMonitor starting by itself at login (needs administrator rights, so Windows asks)."""
        def work():
            try:
                run_helper("remove-task", {}, timeout=240)
                self.log("info", "LibreHardwareMonitor will no longer start by itself at login.")
            except SetupError as e:
                self.log("error", str(e))
            except Exception as e:
                file_log(traceback.format_exc())
                self.log("error", "Couldn't remove the start-at-login task: %s" % e)
        threading.Thread(target=work, daemon=True, name="lhm-task").start()

    # ---- jobs (run on the engine thread)
    def _set_mode(self, mode, feed_screen=None):
        self.mode = mode
        self.feed_screen = feed_screen
        self.st.set("last", mode)

    def screen_cfg(self, screen):
        return lcd.clean_cfg(screen, self.st.get("screen_cfg").get(str(screen)))

    def save_cfg(self, screen, cfg):
        merged = dict(self.screen_cfg(screen))
        merged.update(cfg or {})
        allcfg = dict(self.st.get("screen_cfg"))
        allcfg[str(screen)] = lcd.clean_cfg(screen, merged)
        self.st.set("screen_cfg", allcfg)

    def job_screen(self, screen, cfg=None):
        """Show a temperature screen. cfg (optional) = new options for it, e.g. {"numbers": False}."""
        if screen not in lcd.NUMBER_SCREENS:
            raise SystemExit("That screen isn't available.")
        c = self.c
        if cfg is not None:
            self.save_cfg(screen, cfg)
        cur = self.screen_cfg(screen)
        c.send(lcd.mode(screen)); time.sleep(0.4)
        want = lcd.screen_settings(screen, cur, tick=float(self.st.get("interval")), unit=self.st.get("unit"))
        r = c.request(lcd.config_get(), 0xDF, timeout=1.5)
        have = bytes(r[2:12]) if r else None
        if have != want:                          # only send settings when the cooler isn't already set
            c.send(lcd.config_set(want)); time.sleep(0.3)
        colors = self.st.get("colors").get(str(screen))
        have_c = lcd.read_colors(c, screen)
        if colors:
            want_c = (lcd.parse_color(colors[0]), lcd.parse_color(colors[1]))
            if have_c != want_c:
                c.send(lcd.colors_set(screen, *want_c)); time.sleep(0.2)
        elif have_c:                              # first visit: learn the cooler's current colors for the page
            allc = dict(self.st.get("colors"))
            allc[str(screen)] = [lcd.hexcolor(have_c[0]), lcd.hexcolor(have_c[1])]
            self.st.set("colors", allc)
        mode = {"kind": "temp", "screen": screen}
        if screen == 4:
            mode["sensors"] = cur["sensors"]
        self._set_mode(mode, screen)
        self.log("info", "Showing screen %d." % screen)

    def job_colors(self, screen, c1, c2):
        """c1/c2 may be None (that zone isn't used on this screen): keep what the cooler has."""
        cur = lcd.read_colors(self.c, screen) if (c1 is None or c2 is None) else None
        col1 = lcd.parse_color(c1) if c1 else (cur[0] if cur else (255, 255, 255))
        col2 = lcd.parse_color(c2) if c2 else (cur[1] if cur else (255, 255, 255))
        self.c.send(lcd.colors_set(screen, col1, col2)); time.sleep(0.3)
        colors = dict(self.st.get("colors"))
        colors[str(screen)] = [lcd.hexcolor(col1), lcd.hexcolor(col2)]
        self.st.set("colors", colors)
        self.log("info", "Colors updated.")

    def _play(self, what, names):
        listed = lcd.list_files(self.c, quiet=True, what=what)
        self._remember_media(what, listed)
        idxs = [listed.index(n) + 1 for n in names if n in listed]
        if not idxs:
            return False
        lcd.play(self.c, idxs, len(listed), what)
        return True

    def _remember_media(self, what, listed):
        self.media[what] = list(listed)
        cache = dict(self.st.get("media_cache"))
        cache[what] = list(listed)
        self.st.set("media_cache", cache)

    def _restore_mode(self):
        m = self.mode
        if not m:
            return
        if m["kind"] == "temp":
            self.c.send(lcd.mode(m["screen"]))
        elif m["kind"] == "text":
            self.c.send(lcd.mode(7)); time.sleep(0.02); self.c.send(lcd.refresh())
        elif m["kind"] in ("gif", "pic"):
            self._play(m["kind"], m["names"])

    def job_media_refresh(self, what):
        self._remember_media(what, lcd.list_files(self.c, quiet=True, what=what))
        self._restore_mode()
        self.log("info", "Loaded the list of %s files." % ("GIF" if what == "gif" else "picture"))

    def job_media_play(self, what, names):
        if not self._play(what, names):
            raise SystemExit("None of those files are on the cooler any more. Reload the list.")
        self._set_mode({"kind": what, "names": list(names)})
        self.log("info", "Playing %s." % ", ".join(names))

    def job_media_delete(self, what, name):
        lcd.delete_file(self.c, name, what, ask=False)
        try:
            os.remove(os.path.join(THUMB_DIR, thumb_name(what, name)))
        except OSError:
            pass
        self._remember_media(what, lcd.list_files(self.c, quiet=True, what=what))
        if self.media[what]:
            self._set_mode({"kind": what, "names": [self.media[what][0]]})
        self.log("info", "Deleted %s." % name)

    def job_store(self, data, name, what):
        def progress(f):
            self.busy = {"label": "Uploading %s" % name, "progress": f}
        lcd.store_and_play(self.c, data, name, what, progress=progress)
        self._remember_media(what, lcd.list_files(self.c, quiet=True, what=what))
        self._set_mode({"kind": what, "names": [name]})
        self.log("info", "%s is on the cooler and playing." % name)

    def job_text(self, text, style):
        style = lcd.clean_text_style(style)
        png = lcd.make_png(text=text, style=style)
        c = self.c
        c.stop.clear()
        beat = threading.Thread(target=c._beat, daemon=True)      # keep-alive during the upload, like the CLI
        beat.start()
        try:
            c.send(lcd.mode(7)); time.sleep(0.4); c.send(lcd.mode_confirm(7)); time.sleep(0.4)
            c.send(lcd.upload_start(len(png), lcd.PNG_NAME)); time.sleep(0.02)
            c.send(lcd.upload_data(png)); time.sleep(0.02)
            c.send(lcd.upload_end(len(png), 0x03)); time.sleep(0.18)
            c.send(lcd.apply_()); time.sleep(0.04); c.send(lcd.apply_()); time.sleep(1.0)
            c.send(lcd.mode(7)); time.sleep(0.02); c.send(lcd.refresh())
        finally:
            c.stop.set()
            beat.join(timeout=1)
        try:
            with open(os.path.join(THUMB_DIR, "text_last.png"), "wb") as f:
                f.write(png)
        except OSError:
            pass
        saved = dict(style)
        saved["text"] = text
        self.st.set("text", saved)
        self._set_mode({"kind": "text", "text": text})
        self.log("info", "Text sent to the cooler.")

    def job_apply_last(self):
        last = self.st.get("last")
        if not last:
            return
        k = last.get("kind")
        if k == "temp":
            self.job_screen(last["screen"])
        elif k in ("gif", "pic"):
            if self._play(k, last.get("names", [])):
                self._set_mode(last)
            else:
                self.log("error", "The file you last had playing isn't on the cooler.")
        elif k == "text":
            self.c.send(lcd.mode(7)); time.sleep(0.4); self.c.send(lcd.refresh())
            self._set_mode(last)

    # ---- uploads: convert first (slow, no cooler needed), then queue the upload job
    def start_upload(self, what, path, filename, opts):
        def work():
            try:
                self.converting = "Converting %s..." % filename
                force = bool(opts.get("force"))
                if what == "gif":
                    data = lcd.convert_to_mkv(path, "30", float(opts.get("max_seconds", 10)),
                                              float(opts.get("fill", 0)), None if force else lcd.MAX_UPLOAD)
                    name = lcd.safe_name(filename, opts.get("name") or None)
                    if len(data) > lcd.MAX_UPLOAD and not force:
                        raise SystemExit("That file came out at %.1f MB, over the %.0f MB limit. Use a "
                                         "shorter or simpler clip, or a shorter loop length." %
                                         (len(data) / 1e6, lcd.MAX_UPLOAD / 1048576))
                else:
                    data = lcd.make_jpeg(path, opts.get("fit", "crop"))
                    name = lcd.safe_pic_name(filename, opts.get("name") or None)
                make_thumb(what, path, name, data, opts)
                self.converting = None
                self.submit("Uploading %s" % name, self.job_store, data, name, what)
            except SystemExit as e:
                self.log("error", str(e))
            except Exception as e:
                self.log("error", "Couldn't convert %s: %s" % (filename, e))
                file_log(traceback.format_exc())
            finally:
                self.converting = None
                try:
                    os.remove(path)
                except OSError:
                    pass
        threading.Thread(target=work, daemon=True, name="convert").start()


# ------------------------------------------------------------------ Windows helpers
def app_command():
    """The command Windows should run at login."""
    if getattr(sys, "frozen", False):
        return '"%s" --minimized' % sys.executable
    pyw = sys.executable.replace("python.exe", "pythonw.exe")
    return '"%s" "%s" --minimized' % (pyw, os.path.abspath(__file__))


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_enabled():
    if not IS_WIN:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP)
            return True
    except OSError:
        return False


def autostart_set(on):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, app_command())
        else:
            try:
                winreg.DeleteValue(k, APP)
            except OSError:
                pass


# ------------------------------------------------------------------ LibreHardwareMonitor: find, install, start
# LibreHardwareMonitor (LHM) is the free program that reads the PC's sensors; this app asks its local web
# server for the CPU temperature. Since version 0.9.5 LHM also needs the free "PawnIO" driver. The setup
# below downloads both from their official GitHub pages. Everything that needs administrator rights runs in
# ONE elevated copy of this program, started after Windows' permission prompt (see lhm_elevated_main).
LHM_API = "https://api.github.com/repos/LibreHardwareMonitor/LibreHardwareMonitor/releases/latest"
LHM_ZIP_URLS = (
    "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/latest/download/LibreHardwareMonitor.zip",
    "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/download/v0.9.6/LibreHardwareMonitor.zip",
)
PAWNIO_URLS = (
    "https://github.com/namazso/PawnIO.Setup/releases/latest/download/PawnIO_setup.exe",
)
PAWNIO_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO"
LHM_EXE_NAME = "LibreHardwareMonitor.exe"
HELPER_FLAG = "--lhm-elevated"


class SetupError(Exception):
    """A problem that is explained to you in plain words."""


def program_files():
    return os.environ.get("ProgramFiles") or r"C:\Program Files"


def lhm_home():
    """This app's own folder under Program Files. Only administrators can change files there, which matters
    because LibreHardwareMonitor runs with administrator rights: nobody else should be able to swap it."""
    return os.path.join(program_files(), APP)


def lhm_run_dir():
    """Where the administrator step writes its progress. Ordinary programs can read this folder but not write
    to it, so the administrator step never writes into a folder that someone else controls."""
    return os.path.join(lhm_home(), "run")


def current_user():
    name = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    dom = os.environ.get("USERDOMAIN") or ""
    return ("%s\\%s" % (dom, name)) if (dom and name) else name


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def admin_only_path(path):
    """True when only administrators can change files at this path (Program Files, Windows)."""
    p = os.path.normcase(os.path.realpath(path))
    for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "SystemRoot"):
        base = os.environ.get(var)
        if base:
            b = os.path.normcase(os.path.realpath(base))
            if p.startswith(b.rstrip("\\/") + os.sep):
                return True
    return False


def valid_lhm_exe(path):
    return bool(path) and os.path.basename(path).lower() == LHM_EXE_NAME.lower() and os.path.isfile(path)


def find_lhm_exe(custom=""):
    """Where LibreHardwareMonitor.exe is: the path you saved, this app's own copy, or the usual winget places."""
    cands = [custom] if custom else []
    cands.append(os.path.join(lhm_home(), "LibreHardwareMonitor", LHM_EXE_NAME))
    for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("ProgramFiles")):
        if base:
            cands += glob.glob(os.path.join(base, "Microsoft", "WinGet", "Packages",
                                            "LibreHardwareMonitor.LibreHardwareMonitor_*", LHM_EXE_NAME))
            cands += glob.glob(os.path.join(base, "WinGet", "Packages",
                                            "LibreHardwareMonitor.LibreHardwareMonitor_*", LHM_EXE_NAME))
    pf = os.environ.get("ProgramFiles")
    if pf:
        cands.append(os.path.join(pf, "LibreHardwareMonitor", LHM_EXE_NAME))
    for c in cands:
        if c and os.path.exists(c):
            return c
    return ""


def lhm_running():
    if not IS_WIN:
        return False
    try:
        r = subprocess.run(["tasklist", "/fi", "imagename eq LibreHardwareMonitor.exe", "/nh"],
                           capture_output=True, text=True, stdin=DEVNULL, creationflags=NO_WINDOW, timeout=10)
        return "LibreHardwareMonitor" in r.stdout
    except Exception:
        return False


def _cmd(cmd, timeout=60):
    """Run a program with no window and no console. Returns (exit code, its output as text)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=timeout,
                           stdin=DEVNULL, creationflags=NO_WINDOW)
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        return -1, "no answer after %d seconds" % timeout
    except OSError as e:
        return -1, str(e)


def pawnio_installed():
    if not IS_WIN:
        return False
    import winreg
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, PAWNIO_KEY, 0, winreg.KEY_READ | view) as k:
                winreg.QueryValueEx(k, "DisplayVersion")
                return True
        except OSError:
            continue
    return False


# ---- downloading
def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "%s/%s" % (APP, VERSION), "Accept": "*/*"})
    return urllib.request.urlopen(req, timeout=timeout)


def download_file(url, dest, on_progress=None, min_bytes=50_000):
    tmp = dest + ".part"
    try:
        with _get(url) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if on_progress and total:
                    on_progress(min(1.0, done / total))
        size = os.path.getsize(tmp)
        if size < min_bytes:
            raise ValueError("only %d bytes came back" % size)
        os.replace(tmp, dest)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def pick_lhm_asset(release):
    """From GitHub's description of a release, the download link of the normal LibreHardwareMonitor zip.
    Only the two known names are accepted (the other builds need extra Windows components)."""
    best, best_score = None, 0
    for a in (release or {}).get("assets", []):
        name = str(a.get("name", "")).lower()
        url = a.get("browser_download_url")
        if not url:
            continue
        score = 100 if name == "librehardwaremonitor.zip" else 90 if name == "librehardwaremonitor-net472.zip" else 0
        if score > best_score:
            best, best_score = url, score
    return best


def lhm_zip_urls():
    urls = []
    try:
        with _get(LHM_API, timeout=20) as r:
            link = pick_lhm_asset(json.loads(r.read().decode("utf-8")))
        if link:
            urls.append(link)
    except Exception:
        pass                                  # GitHub's API can be rate-limited; the fixed links below still work
    return urls + [u for u in LHM_ZIP_URLS if u not in urls]


def check_zip(path):
    import zipfile
    if not zipfile.is_zipfile(path):
        raise ValueError("that isn't a zip file")


def check_exe(path):
    with open(path, "rb") as f:
        if f.read(2) != b"MZ":
            raise ValueError("that isn't a Windows program")


def safe_extract(zip_path, dest):
    """Unpack a zip, refusing any entry that would land outside the destination folder."""
    import shutil
    import zipfile
    root = os.path.realpath(dest)
    os.makedirs(root, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            target = os.path.realpath(os.path.join(root, info.filename))
            if target != root and not target.startswith(root + os.sep):
                raise SetupError("The download contains an unsafe file path, so I stopped.")
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def find_exe_in(folder):
    for dirpath, _dirs, files in os.walk(folder):
        if LHM_EXE_NAME in files:
            return os.path.join(dirpath, LHM_EXE_NAME)
    return ""


# ---- LibreHardwareMonitor's own settings file and the start-at-login task
def write_lhm_config(exe, port):
    """Switch on LibreHardwareMonitor's 'Remote Web Server' (the data feed this app reads) and make it start
    hidden in the tray. Settings you already had in that file are kept."""
    import xml.etree.ElementTree as ET
    path = os.path.splitext(exe)[0] + ".config"
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        root = None
    if root is None or root.tag != "configuration":
        root = ET.Element("configuration")
    section = root.find("appSettings")
    if section is None:
        section = ET.SubElement(root, "appSettings")

    def put(key, value):
        for node in section.findall("add"):
            if node.get("key") == key:
                node.set("value", value)
                return
        ET.SubElement(section, "add", {"key": key, "value": value})

    put("runWebServerMenuItem", "true")
    put("listenerIp", "127.0.0.1")
    put("listenerPort", str(port))
    put("startMinMenuItem", "true")
    put("minTrayMenuItem", "true")
    put("minCloseMenuItem", "true")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return path


def lhm_task_xml(exe, user=""):
    """Task Scheduler definition: start LibreHardwareMonitor at login with the highest rights and never stop it.
    Without a user name it applies to any administrator who logs in."""
    from xml.sax.saxutils import escape
    if user:
        trigger_user = "<UserId>%s</UserId>" % escape(user)
        principal = ("<UserId>%s</UserId><LogonType>InteractiveToken</LogonType>"
                     "<RunLevel>HighestAvailable</RunLevel>" % escape(user))
    else:
        trigger_user = ""
        principal = "<GroupId>S-1-5-32-544</GroupId><RunLevel>HighestAvailable</RunLevel>"
    return ('<?xml version="1.0" encoding="UTF-16"?>\n'
            '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
            ' <RegistrationInfo><Description>Starts LibreHardwareMonitor at login so Waterforce Screen Control '
            'can read your temperatures.</Description></RegistrationInfo>\n'
            ' <Triggers><LogonTrigger><Enabled>true</Enabled>%s</LogonTrigger></Triggers>\n'
            ' <Principals><Principal id="Author">%s</Principal></Principals>\n'
            ' <Settings>\n'
            '  <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n'
            '  <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n'
            '  <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n'
            '  <AllowHardTerminate>true</AllowHardTerminate>\n'
            '  <StartWhenAvailable>false</StartWhenAvailable>\n'
            '  <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>\n'
            '  <AllowStartOnDemand>true</AllowStartOnDemand>\n'
            '  <Enabled>true</Enabled>\n'
            '  <Hidden>false</Hidden>\n'
            '  <RunOnlyIfIdle>false</RunOnlyIfIdle>\n'
            '  <WakeToRun>false</WakeToRun>\n'
            '  <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>\n'
            '  <Priority>7</Priority>\n'
            ' </Settings>\n'
            ' <Actions Context="Author"><Exec><Command>%s</Command><WorkingDirectory>%s</WorkingDirectory></Exec></Actions>\n'
            '</Task>\n' % (trigger_user, principal, escape(exe), escape(os.path.dirname(exe))))


def lhm_task_exists():
    if not IS_WIN:
        return False
    code, _ = _cmd(["schtasks", "/query", "/tn", LHM_TASK], timeout=15)
    return code == 0


# ---- the administrator part (runs in an elevated copy of this program)
class Report:
    """What the administrator step tells the normal app: a progress file, a log file and, last, a result file.
    They are written into lhm_run_dir() (a folder only administrators can write to), under this run's own name."""

    def __init__(self, run_id):
        self.dir = lhm_run_dir()
        os.makedirs(self.dir, exist_ok=True)
        self.p_log = os.path.join(self.dir, "log-%s.txt" % run_id)
        self.p_prog = os.path.join(self.dir, "progress-%s.json" % run_id)
        self.p_res = os.path.join(self.dir, "result-%s.json" % run_id)
        keep = {os.path.basename(p) for p in (self.p_log, self.p_prog, self.p_res)}
        try:
            for n in os.listdir(self.dir):          # earlier runs are no longer needed
                if n not in keep:
                    try:
                        os.remove(os.path.join(self.dir, n))
                    except OSError:
                        pass
        except OSError:
            pass
        self.lines = []
        self.warnings = []

    def line(self, text):
        self.lines.append("%s  %s" % (time.strftime("%H:%M:%S"), text))
        self._put(self.p_log, "\n".join(self.lines) + "\n")

    def step(self, text, progress=None):
        self.line(text)
        self._put(self.p_prog, json.dumps({"step": text, "progress": progress}))

    def warn(self, text):
        self.warnings.append(text)
        self.line("WARNING: " + text)

    def finish(self, ok, **extra):
        data = dict(extra)
        data["ok"] = ok
        data["warnings"] = list(self.warnings)
        self._put(self.p_res, json.dumps(data))

    @staticmethod
    def _put(path, text):
        tmp = path + ".tmp"
        for _attempt in range(4):               # Windows refuses to replace a file the other side is reading right now
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(text)
                os.replace(tmp, path)           # replaces the file in one step, so a reader never sees half of it
                return
            except OSError:
                time.sleep(0.05)


def download_first(urls, dest, rep, label, lo, hi, min_bytes, check, hint=""):
    last = ""
    for u in urls:
        rep.line("Downloading %s" % u)
        try:
            download_file(u, dest, lambda f: rep.step("Downloading %s... %d%%" % (label, f * 100), lo + (hi - lo) * f),
                          min_bytes)
            check(dest)
            return u
        except Exception as e:
            last = "%s: %s" % (u, e)
            rep.line("  didn't work: %s" % last)
    raise SetupError("I couldn't download %s. Is this PC online? The last error was: %s%s" % (label, last, hint))


def helper_install_lhm(rep, custom):
    """The path of LibreHardwareMonitor.exe; downloads it into this app's Program Files folder if needed."""
    import shutil
    if custom and os.path.isfile(custom):
        if not valid_lhm_exe(custom):
            raise SetupError("The path saved in Settings (%s) isn't a file called %s." % (custom, LHM_EXE_NAME))
        rep.line("Using the copy you chose: %s" % custom)
        return custom
    if custom:
        rep.line("The path saved in Settings (%s) doesn't exist, so I'm ignoring it." % custom)
    exe = find_lhm_exe("")
    if exe and admin_only_path(exe):
        rep.line("LibreHardwareMonitor is already here: %s" % exe)
        return exe
    if exe:
        rep.line("There is a copy at %s, but ordinary programs can change files in that folder and this copy will "
                 "run with administrator rights. Installing a separate one in Program Files instead." % exe)
    base = lhm_home()
    stage = os.path.join(base, "_download")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage, exist_ok=True)
    zip_path = os.path.join(stage, "LibreHardwareMonitor.zip")
    rep.step("Looking for the newest LibreHardwareMonitor...", 0.05)
    download_first(lhm_zip_urls(), zip_path, rep, "LibreHardwareMonitor", 0.08, 0.40, 200_000, check_zip,
                   " You can also download LibreHardwareMonitor.zip yourself from "
                   "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases, unpack it, and choose "
                   "'Use my own copy instead' in Settings.")
    rep.step("Unpacking LibreHardwareMonitor...", 0.42)
    unpacked = os.path.join(stage, "unpacked")
    safe_extract(zip_path, unpacked)
    found = find_exe_in(unpacked)
    if not found:
        raise SetupError("The LibreHardwareMonitor download didn't contain %s." % LHM_EXE_NAME)
    dest = os.path.join(base, "LibreHardwareMonitor")
    shutil.rmtree(dest, ignore_errors=True)
    shutil.move(os.path.dirname(found), dest)
    shutil.rmtree(stage, ignore_errors=True)
    rep.line("Installed LibreHardwareMonitor in %s" % dest)
    return os.path.join(dest, LHM_EXE_NAME)


def helper_install_pawnio(rep):
    """Make sure the PawnIO driver is there. Returns (what happened, whether Windows wants a restart)."""
    import shutil
    if pawnio_installed():
        rep.line("The PawnIO driver is already installed.")
        return "already installed", False
    stage = os.path.join(lhm_home(), "_download")
    os.makedirs(stage, exist_ok=True)
    path = os.path.join(stage, "PawnIO_setup.exe")
    try:
        rep.step("Downloading the PawnIO driver...", 0.50)
        download_first(PAWNIO_URLS, path, rep, "the PawnIO driver", 0.50, 0.62, 20_000, check_exe)
        rep.step("Installing the PawnIO driver...", 0.66)
        code, out = _cmd([path, "-install", "-silent"], timeout=300)
    except SetupError as e:
        rep.warn("%s Without that driver LibreHardwareMonitor can't read your CPU temperature. "
                 "You can install it yourself from https://pawnio.eu" % e)
        return "not installed", False
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    rep.line("PawnIO installer finished with code %s %s" % (code, out[:300]))
    if code in (0, 3010) or pawnio_installed():
        return "installed", code == 3010
    rep.warn("The PawnIO driver installer reported error %s. Without that driver LibreHardwareMonitor can't read "
             "your CPU temperature. You can install it yourself from https://pawnio.eu" % code)
    return "not installed", False


def helper_stop_lhm(rep):
    code, _out = _cmd(["taskkill", "/F", "/IM", LHM_EXE_NAME], timeout=20)
    if code == 0:
        rep.line("Stopped the running LibreHardwareMonitor so its settings can be changed.")
        time.sleep(1.5)


def helper_make_task(rep, exe, user):
    xml_path = os.path.join(lhm_home(), "lhm_task.xml")
    os.makedirs(lhm_home(), exist_ok=True)
    last = ""
    for who in ([user, ""] if user else [""]):
        with open(xml_path, "w", encoding="utf-16") as f:
            f.write(lhm_task_xml(exe, who))
        code, out = _cmd(["schtasks", "/create", "/tn", LHM_TASK, "/xml", xml_path, "/f"], timeout=40)
        rep.line("Creating the start-at-login task for %s: exit code %s %s" % (who or "any administrator", code, out[:300]))
        if code == 0:
            return True
        last = out
    rep.warn("Windows wouldn't create the start-at-login task (%s). LibreHardwareMonitor is running now, but after a "
             "restart you will need to press the setup button again." % (last or "no details"))
    return False


def helper_start_lhm(rep, exe):
    code, out = _cmd(["schtasks", "/run", "/tn", LHM_TASK], timeout=30)
    if code == 0:
        rep.line("Started LibreHardwareMonitor through its task.")
        return
    rep.line("The task didn't start it (%s %s); starting it directly." % (code, out[:200]))
    subprocess.Popen([exe], cwd=os.path.dirname(exe), stdin=DEVNULL, creationflags=0x00000208)   # detached


def helper_setup(opts, rep):
    try:
        port = int(opts.get("port") or 8085)
    except ValueError:
        port = 8085
    if not 1 <= port <= 65535:
        port = 8085
    rep.step("Checking what is already installed...", 0.02)
    exe = helper_install_lhm(rep, opts.get("exe", ""))
    pawn, reboot = helper_install_pawnio(rep)
    rep.step("Turning on LibreHardwareMonitor's data feed...", 0.78)
    helper_stop_lhm(rep)
    cfg = write_lhm_config(exe, port)
    rep.line("Wrote %s" % cfg)
    rep.step("Making it start by itself at every login...", 0.86)
    helper_make_task(rep, exe, opts.get("user", ""))
    rep.step("Starting LibreHardwareMonitor...", 0.94)
    helper_start_lhm(rep, exe)
    return {"exe": exe, "pawnio": pawn, "reboot": reboot}


def helper_remove_task(rep):
    rep.step("Removing the start-at-login task...", 0.5)
    _cmd(["schtasks", "/delete", "/tn", LHM_TASK, "/f"], timeout=30)
    code, _ = _cmd(["schtasks", "/query", "/tn", LHM_TASK], timeout=15)
    if code == 0:
        raise SetupError("Windows wouldn't remove the task %s." % LHM_TASK)
    return {}


def lhm_elevated_main(argv):
    """Entry point of the administrator copy: ['setup'|'remove-task', '--name', 'value', ...]."""
    args = list(argv)
    opts = {"action": args.pop(0) if args and not args[0].startswith("--") else "setup"}
    while len(args) >= 2 and args[0].startswith("--"):
        opts[args[0][2:]] = args[1]
        args = args[2:]
    run_id = opts.get("run") or "manual"
    if not re.fullmatch(r"[0-9a-z]{1,32}", run_id):
        run_id = "manual"
    rep = Report(run_id)
    rep.line("%s %s - %s (running as administrator: %s)" % (TITLE, VERSION, opts["action"], is_admin()))
    try:
        action = opts["action"]
        if action == "setup":
            res = helper_setup(opts, rep)
        elif action == "remove-task":
            res = helper_remove_task(rep)
        else:
            raise SetupError("Unknown request '%s'." % action)
        rep.line("Done.")
        rep.finish(True, **res)
    except SetupError as e:
        rep.line("FAILED: %s" % e)
        rep.finish(False, error=str(e))
    except BaseException as e:                  # anything unexpected is written down instead of vanishing
        rep.line(traceback.format_exc())
        rep.finish(False, error="Something unexpected went wrong: %s" % e)


# ---- starting the administrator copy and following it (normal app side)
class _ShellExecuteInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("fMask", ctypes.c_uint32), ("hwnd", ctypes.c_void_p),
                ("lpVerb", ctypes.c_wchar_p), ("lpFile", ctypes.c_wchar_p), ("lpParameters", ctypes.c_wchar_p),
                ("lpDirectory", ctypes.c_wchar_p), ("nShow", ctypes.c_int), ("hInstApp", ctypes.c_void_p),
                ("lpIDList", ctypes.c_void_p), ("lpClass", ctypes.c_wchar_p), ("hkeyClass", ctypes.c_void_p),
                ("dwHotKey", ctypes.c_uint32), ("hIconOrMonitor", ctypes.c_void_p), ("hProcess", ctypes.c_void_p)]


def shell_runas(argv):
    """Start this program again with administrator rights (Windows shows its permission prompt).
    Returns a handle to follow the new process with, or None."""
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(_ShellExecuteInfo)]
    shell32.ShellExecuteExW.restype = ctypes.c_int
    exe = sys.executable
    args = list(argv) if getattr(sys, "frozen", False) else [os.path.abspath(__file__)] + list(argv)
    info = _ShellExecuteInfo()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x40 | 0x100                   # SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC
    info.lpVerb = "runas"
    info.lpFile = exe
    info.lpParameters = subprocess.list2cmdline(args)
    info.lpDirectory = os.path.dirname(exe)
    info.nShow = 0
    ole32 = ctypes.WinDLL("ole32")
    hr = ole32.CoInitializeEx(None, 2)
    try:
        ok = shell32.ShellExecuteExW(ctypes.byref(info))
        err = ctypes.get_last_error()
    finally:
        if hr in (0, 1):
            ole32.CoUninitialize()
    if not ok:
        if err == 1223:
            raise SetupError("You chose No on Windows' permission prompt, so nothing was changed. Press the button "
                             "again and choose Yes.")
        raise SetupError("Windows wouldn't start the administrator step (error %d). You can also right-click "
                         "the program, choose Run as administrator, and press the button again." % err)
    return info.hProcess or None


def _process_done(handle):
    k32 = ctypes.WinDLL("kernel32")
    k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    k32.WaitForSingleObject.restype = ctypes.c_uint32
    return k32.WaitForSingleObject(handle, 0) == 0


def _close_handle(handle):
    try:
        k32 = ctypes.WinDLL("kernel32")
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        k32.CloseHandle(handle)
    except Exception:
        pass


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


SETUP_LOG = os.path.join(DATA_DIR, "lhm_setup.log")


def read_setup_log(run_id=None, max_lines=80):
    """The last lines the administrator step wrote down (live while it runs, a saved copy afterwards)."""
    paths = []
    if run_id:
        paths.append(os.path.join(lhm_run_dir(), "log-%s.txt" % run_id))
    paths.append(SETUP_LOG)
    for p in paths:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                lines = [ln.rstrip("\n") for ln in f.readlines()]
            if lines:
                return lines[-max_lines:]
        except OSError:
            continue
    return []


def run_helper(action, params, on_update=None, timeout=600, run_id=None):
    """Start the administrator copy, follow its progress, and return its result. Raises SetupError on a problem.
    Each run has its own random name, so an old result can never be mistaken for this one."""
    run_id = run_id or secrets.token_hex(8)
    p_res = os.path.join(lhm_run_dir(), "result-%s.json" % run_id)
    p_prog = os.path.join(lhm_run_dir(), "progress-%s.json" % run_id)
    argv = [action, "--run", run_id]
    for k, v in params.items():
        if v not in (None, ""):
            argv += ["--" + k, str(v)]
    handle = None
    try:
        if is_admin():                          # already an administrator: no permission prompt needed
            threading.Thread(target=lhm_elevated_main, args=(argv,), daemon=True, name="lhm-admin").start()
        else:
            handle = shell_runas([HELPER_FLAG] + argv)
        end = time.time() + timeout
        gone_since = None
        while time.time() < end:
            res = _read_json(p_res)
            if res is not None:
                if res.get("ok"):
                    return res
                raise SetupError(res.get("error") or "The setup didn't finish.")
            prog = _read_json(p_prog)
            if prog and on_update:
                on_update(prog.get("step") or "", prog.get("progress"))
            if handle is not None and _process_done(handle):
                gone_since = gone_since or time.time()
                if time.time() - gone_since > 3:
                    raise SetupError("The administrator step closed without finishing. Click Show details to see "
                                     "what it wrote down.")
            time.sleep(0.4)
        raise SetupError("Windows didn't answer in time. If you didn't see a permission prompt, try again.")
    finally:
        if handle is not None:
            _close_handle(handle)
        try:                                    # keep a copy of what happened, where you can find it
            lines = read_setup_log(run_id, max_lines=500)
            if lines:
                with open(SETUP_LOG, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
        except OSError:
            pass


# ------------------------------------------------------------------ web server
class Server:
    def __init__(self, engine, st, port):
        self.engine, self.st, self.port = engine, st, port
        self.token = secrets.token_hex(16)
        self.httpd = None
        self.quit_cb = None
        self.logo_cb = None

    def start(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            server_version = APP
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            # --- helpers
            def _ok_host(self):
                host = (self.headers.get("Host") or "").lower()
                return host in ("127.0.0.1:%d" % outer.port, "localhost:%d" % outer.port)

            def _send(self, code, body, ctype="application/json"):
                if isinstance(body, (dict, list)):
                    body = json.dumps(body).encode()
                elif isinstance(body, str):
                    body = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", ctype + ("; charset=utf-8" if "text" in ctype else ""))
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _json(self):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b""
                return json.loads(raw.decode("utf-8") or "{}")

            def _authed(self):
                return self._ok_host() and secrets.compare_digest(self.headers.get("X-Token") or "", outer.token)

            # --- routes
            def do_GET(self):
                if not self._ok_host():
                    return self._send(403, {"error": "bad host"})
                if self.path == "/api/ping":
                    return self._send(200, {"app": APP})
                if self.path in ("/", "/index.html"):
                    page = HTML.replace("__TOKEN__", outer.token)
                    page = page.replace("__THEME__", json.dumps(outer.st.get("theme")))
                    return self._send(200, page, "text/html")
                if self.path.startswith("/thumb/"):
                    fname = os.path.basename(self.path[7:].split("?")[0])
                    fpath = os.path.join(THUMB_DIR, fname)
                    if re.match(r"^[A-Za-z0-9_.-]+$", fname) and os.path.isfile(fpath):
                        with open(fpath, "rb") as f:
                            return self._send(200, f.read(), "image/gif" if fname.endswith(".gif") else "image/png")
                    return self._send(404, {"error": "no preview"})
                m = re.match(r"^/icon/(\d{2,3})\.png$", self.path.split("?")[0])
                if m and int(m.group(1)) in ICON_SIZES:
                    try:
                        return self._send(200, icon_png(int(m.group(1))), "image/png")
                    except Exception:
                        return self._send(404, {"error": "no icon"})
                if self.path.split("?")[0] == "/logo.png":
                    try:
                        with open(LOGO_PATH, "rb") as f:
                            return self._send(200, f.read(), "image/png")
                    except OSError:
                        return self._send(200, wsc_logo.png_bytes(), "image/png")
                if self.path == "/api/state":
                    if not self._authed():
                        return self._send(403, {"error": "forbidden"})
                    return self._send(200, outer.engine.snapshot())
                if self.path == "/api/system":
                    if not self._authed():
                        return self._send(403, {"error": "forbidden"})
                    return self._send(200, outer.system_info())
                self._send(404, {"error": "not found"})

            def do_POST(self):
                if not self._authed():
                    return self._send(403, {"error": "forbidden"})
                try:
                    if self.path == "/api/upload":
                        return self._send(200, outer.handle_upload(self))
                    if self.path == "/api/logo":
                        return self._send(200, outer.handle_logo(self))
                    if self.path == "/api/font":
                        return self._send(200, outer.handle_font(self))
                    body = self._json()
                    return self._send(200, outer.handle(self.path, body))
                except SystemExit as e:
                    return self._send(200, {"ok": False, "error": str(e)})
                except Exception as e:
                    file_log(traceback.format_exc())
                    return self._send(200, {"ok": False, "error": str(e)})

        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True, name="http").start()

    # --- actions
    def system_info(self):
        info = {"autostart": autostart_enabled(), "windows": IS_WIN, "lhm_task": False, "pawnio": False,
                "lhm_exe": self.engine.lhm_exe()}
        if IS_WIN:
            try:
                info["lhm_task"] = lhm_task_exists()
                info["pawnio"] = pawnio_installed()
            except Exception as e:
                info["error"] = str(e)
        return info

    def handle(self, path, b):
        e = self.engine
        ok = {"ok": True}
        if path == "/api/screen":
            screen = int(b["screen"])
            if screen not in lcd.NUMBER_SCREENS:
                raise SystemExit("That screen isn't available.")
            if isinstance(b.get("cfg"), dict):
                e.save_cfg(screen, b["cfg"])          # saved at once, so the page shows it straight away
            e.submit("Switching screen", e.job_screen, screen)
            return ok
        if path == "/api/colors":
            e.submit("Setting colors", e.job_colors, int(b["screen"]), b.get("c1"), b.get("c2"))
            return ok
        if path == "/api/unit":
            unit = "F" if str(b.get("unit", "C")).upper() == "F" else "C"
            self.st.set("unit", unit)
            m = e.mode
            if m and m.get("kind") == "temp":        # a temperature screen is showing: tell the cooler now
                e.submit("Changing the temperature unit", e.job_screen, m["screen"])
            return ok
        if path == "/api/media/refresh":
            e.submit("Loading files", e.job_media_refresh, b["what"])
            return ok
        if path == "/api/media/play":
            e.submit("Playing", e.job_media_play, b["what"], list(b["names"]))
            return ok
        if path == "/api/media/delete":
            e.submit("Deleting", e.job_media_delete, b["what"], b["name"])
            return ok
        if path == "/api/text":
            text = str(b.get("text", "")).strip("\n")
            if not text.strip():
                raise SystemExit("Type some text first.")
            style = lcd.clean_text_style(b.get("style"))
            saved = dict(style)
            saved["text"] = text[:80]
            self.st.set("text", saved)
            e.submit("Sending text", e.job_text, text[:80], style)
            return ok
        if path == "/api/text/preview":
            text = str(b.get("text", "")).strip("\n") or " "
            import io
            png = lcd.make_png(text=text[:80], style=b.get("style"))
            return {"ok": True, "png": base64.b64encode(png).decode(), "bytes": len(png)}
        if path == "/api/logo/remove":
            try:
                os.remove(LOGO_PATH)
            except OSError:
                pass
            self.st.set("logo_version", int(self.st.get("logo_version")) + 1)
            if self.logo_cb:
                self.logo_cb()
            return ok
        if path == "/api/settings":
            allowed = {"cpu_sensor_id", "vrm_sensor_id", "lhm_path", "launch_lhm", "apply_on_start", "lhm_url",
                       "theme"}
            vals = {k: v for k, v in b.items() if k in allowed}
            if "theme" in vals:
                t = vals["theme"] if isinstance(vals["theme"], dict) else {}
                hexre = re.compile(r"^#[0-9a-fA-F]{6}$")
                vals["theme"] = {k: (t.get(k) if hexre.match(str(t.get(k, ""))) else DEFAULTS["theme"][k])
                                 for k in ("accent", "bg")}
            self.st.update(vals)
            if "lhm_path" in vals or "launch_lhm" in vals:
                e.lhm_launched = False
                e._exe_cache = (0.0, "")
            return ok
        if path == "/api/autostart":
            autostart_set(bool(b["on"]))
            return ok
        if path == "/api/lhm/task":
            if b.get("on"):
                e.start_lhm_setup()                    # (re)creating the task is part of the setup
            else:
                e.lhm_task_remove()
            return ok
        if path == "/api/lhm/setup":
            e.start_lhm_setup()
            return ok
        if path == "/api/lhm/log":
            return {"ok": True, "lines": read_setup_log(e.lhm_run_id, max_lines=120)}
        if path == "/api/font/remove":
            name = os.path.basename(str(b.get("name", "")))
            if name in lcd.custom_fonts():
                os.remove(os.path.join(FONT_DIR, name))
            return ok
        if path == "/api/lhm/launch":
            e.lhm_launched = False
            e._maybe_launch_lhm()
            return ok
        if path == "/api/quit":
            if self.quit_cb:
                threading.Timer(0.3, self.quit_cb).start()
            return ok
        raise SystemExit("Unknown request %s" % path)

    def handle_font(self, h):
        n = int(h.headers.get("Content-Length") or 0)
        if n <= 0 or n > 30 * 1024 * 1024:
            raise SystemExit("That font file is empty or too large.")
        import urllib.parse
        orig = os.path.basename(urllib.parse.unquote(h.headers.get("X-Filename", "font.ttf")))
        ext = os.path.splitext(orig)[1].lower()
        if ext not in (".ttf", ".otf", ".ttc"):
            h.rfile.read(n)
            raise SystemExit("Choose a .ttf (or .otf) font file.")
        raw = h.rfile.read(n)
        base = re.sub(r"[^A-Za-z0-9 _.-]", "_", os.path.splitext(orig)[0]).strip()[:40] or "font"
        fname = base + ext
        path = os.path.join(FONT_DIR, fname)
        with open(path, "wb") as f:
            f.write(raw)
        try:
            from PIL import ImageFont
            ImageFont.truetype(path, 40).getmask("Ag")
        except Exception:
            os.remove(path)
            raise SystemExit("I couldn't read that file as a font.")
        return {"ok": True, "font": "file:" + fname}

    def handle_logo(self, h):
        n = int(h.headers.get("Content-Length") or 0)
        if n <= 0 or n > 20 * 1024 * 1024:
            raise SystemExit("That logo file is empty or too large.")
        raw = h.rfile.read(n)
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(raw))
            img.load()
            img = img.convert("RGBA")
        except Exception:
            raise SystemExit("I couldn't read that as a picture. Use a PNG, JPG, WEBP or ICO file.")
        img.thumbnail((256, 256))
        img.save(LOGO_PATH, format="PNG")
        self.st.set("logo_version", int(self.st.get("logo_version")) + 1)
        if self.logo_cb:
            self.logo_cb()
        return {"ok": True}

    def handle_upload(self, h):
        what = h.headers.get("X-What", "gif")
        if what not in ("gif", "pic"):
            raise SystemExit("Unknown file type.")
        filename = os.path.basename(base64.b64decode(h.headers.get("X-Filename", "")).decode("utf-8") or "file")
        opts = json.loads(h.headers.get("X-Opts") or "{}")
        n = int(h.headers.get("Content-Length") or 0)
        if n <= 0 or n > 600 * 1024 * 1024:
            raise SystemExit("That file is empty or too large.")
        ext = os.path.splitext(filename)[1][:8] or ".bin"
        fd, path = tempfile.mkstemp(suffix=ext, prefix="aorus_")
        with os.fdopen(fd, "wb") as f:
            left = n
            while left > 0:
                chunk = h.rfile.read(min(65536, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        self.engine.start_upload(what, path, filename, opts)
        return {"ok": True}


# ------------------------------------------------------------------ sharp icons (taskbar, window, tray)
# The window is an Edge/Chrome "app" window. On its own it builds the taskbar icon from the page's tiny
# 16-pixel favicon and stretches it, which looks blurry. So we (1) offer the page properly sized, smoothly
# scaled icons, and (2) on Windows put sharp icons of exactly the right size on that window ourselves.
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def logo_image():
    """The logo that is in use now (your own upload, or the built-in one) as a square RGBA picture."""
    import io
    from PIL import Image
    try:
        img = Image.open(LOGO_PATH).convert("RGBA")
    except Exception:
        img = Image.open(io.BytesIO(wsc_logo.png_bytes())).convert("RGBA")
    w, h = img.size
    if w != h:                                   # a wide or tall logo: pad it to a square, never squash it
        side = max(w, h)
        sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        sq.paste(img, ((side - w) // 2, (side - h) // 2))
        img = sq
    return img


def icon_at(size, base=None):
    """The logo scaled to size x size pixels with smooth edges (small sizes get a touch of sharpening)."""
    from PIL import Image, ImageFilter
    img = (base if base is not None else logo_image()).resize((size, size), Image.LANCZOS)
    if size <= 48:
        img = img.filter(ImageFilter.UnsharpMask(radius=0.6, percent=70, threshold=0))
    return img


def icon_png(size):
    import io
    buf = io.BytesIO()
    icon_at(size).save(buf, format="PNG")
    return buf.getvalue()


class _WinApi:
    """The handful of Windows calls needed to give the app window its own icon. Kept small and separate from
    the logic below so the logic can be tested without Windows."""
    WM_SETICON, WM_GETICON, ICON_SMALL, ICON_BIG, SMTO_ABORTIFHUNG = 0x0080, 0x007F, 0, 1, 0x0002

    def __init__(self, user32=None, gdi32=None):
        from ctypes import wintypes as wt
        self.user32 = user32 or ctypes.windll.user32
        self.gdi32 = gdi32 or ctypes.windll.gdi32
        u, g = self.user32, self.gdi32
        self._proc_type = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(wt.BOOL, wt.HWND, wt.LPARAM)

        i32, u32, u16 = ctypes.c_int32, ctypes.c_uint32, ctypes.c_uint16     # fixed sizes, like Windows' LONG/DWORD/WORD

        class _XYZ(ctypes.Structure):
            _fields_ = [("v", i32 * 9)]

        class _V5Header(ctypes.Structure):           # BITMAPV5HEADER, 124 bytes
            _fields_ = [("size", u32), ("width", i32), ("height", i32), ("planes", u16), ("bits", u16),
                        ("compression", u32), ("size_image", u32), ("xppm", i32), ("yppm", i32),
                        ("clr_used", u32), ("clr_important", u32),
                        ("red", u32), ("green", u32), ("blue", u32), ("alpha", u32),
                        ("cs_type", u32), ("endpoints", _XYZ), ("gamma_r", u32), ("gamma_g", u32),
                        ("gamma_b", u32), ("intent", u32), ("profile_data", u32),
                        ("profile_size", u32), ("reserved", u32)]

        class _IconInfo(ctypes.Structure):           # ICONINFO
            _fields_ = [("is_icon", i32), ("x", u32), ("y", u32), ("mask", ctypes.c_void_p), ("color", ctypes.c_void_p)]

        self._V5Header, self._IconInfo = _V5Header, _IconInfo
        u.EnumWindows.argtypes = [self._proc_type, wt.LPARAM]
        u.EnumWindows.restype = wt.BOOL
        u.IsWindowVisible.argtypes = [wt.HWND]
        u.IsWindowVisible.restype = wt.BOOL
        for fn in (u.GetClassNameW, u.GetWindowTextW):
            fn.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
            fn.restype = ctypes.c_int
        u.SendMessageTimeoutW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, wt.UINT, wt.UINT,
                                          ctypes.POINTER(ctypes.c_size_t)]
        u.SendMessageTimeoutW.restype = ctypes.c_size_t
        u.CreateIconIndirect.argtypes = [ctypes.POINTER(_IconInfo)]
        u.CreateIconIndirect.restype = wt.HANDLE
        g.CreateDIBSection.argtypes = [wt.HDC, ctypes.c_void_p, wt.UINT, ctypes.POINTER(ctypes.c_void_p),
                                       wt.HANDLE, wt.DWORD]
        g.CreateDIBSection.restype = wt.HANDLE
        g.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, wt.UINT, wt.UINT, ctypes.c_void_p]
        g.CreateBitmap.restype = wt.HANDLE
        g.DeleteObject.argtypes = [wt.HANDLE]
        g.DeleteObject.restype = wt.BOOL
        self._dpi_fn = getattr(u, "GetDpiForWindow", None)      # Windows 10 (1607) and newer
        if self._dpi_fn is not None:
            self._dpi_fn.argtypes = [wt.HWND]
            self._dpi_fn.restype = wt.UINT

    def windows(self):
        """(handle, class name, title) of every visible Edge/Chrome-style top-level window."""
        found = []

        def one(hwnd, _lparam):
            try:
                if self.user32.IsWindowVisible(hwnd):
                    cls = ctypes.create_unicode_buffer(256)
                    self.user32.GetClassNameW(hwnd, cls, 256)
                    if cls.value == "Chrome_WidgetWin_1":
                        title = ctypes.create_unicode_buffer(512)
                        self.user32.GetWindowTextW(hwnd, title, 512)
                        found.append((hwnd, cls.value, title.value))
            except Exception:
                pass
            return True

        proc = self._proc_type(one)              # keep a reference while Windows is calling it
        self.user32.EnumWindows(proc, 0)
        return found

    def dpi(self, hwnd):
        try:
            return int(self._dpi_fn(hwnd)) or 96 if self._dpi_fn else 96
        except Exception:
            return 96

    def get_icon(self, hwnd, kind):
        out = ctypes.c_size_t(0)
        ok = self.user32.SendMessageTimeoutW(hwnd, self.WM_GETICON, kind, 0, self.SMTO_ABORTIFHUNG, 500,
                                             ctypes.byref(out))
        return out.value if ok else None

    def set_icon(self, hwnd, kind, hicon):
        out = ctypes.c_size_t(0)
        return bool(self.user32.SendMessageTimeoutW(hwnd, self.WM_SETICON, kind, hicon, self.SMTO_ABORTIFHUNG, 500,
                                                    ctypes.byref(out)))

    def make_icon(self, img):
        """A Windows icon handle from a PIL RGBA picture (keeps the soft, transparent edges)."""
        w, h = img.size
        hdr = self._V5Header()
        hdr.size = ctypes.sizeof(hdr)
        hdr.width, hdr.height, hdr.planes, hdr.bits = w, -h, 1, 32          # negative height = top row first
        hdr.compression = 3                                                  # BI_BITFIELDS
        hdr.red, hdr.green, hdr.blue, hdr.alpha = 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000
        hdr.cs_type = 0x57696E20                                             # "Win " = default colour space
        bits = ctypes.c_void_p()
        color = self.gdi32.CreateDIBSection(None, ctypes.byref(hdr), 0, ctypes.byref(bits), None, 0)
        mask = self.gdi32.CreateBitmap(w, h, 1, 1, None)
        try:
            if not color or not mask or not bits.value:
                return None
            data = img.convert("RGBA").tobytes("raw", "BGRA")
            ctypes.memmove(bits.value, data, len(data))
            info = self._IconInfo(True, 0, 0, mask, color)
            return self.user32.CreateIconIndirect(ctypes.byref(info)) or None
        finally:
            for bmp in (color, mask):
                if bmp:
                    self.gdi32.DeleteObject(bmp)


class WindowIcons:
    """Keeps sharp, correctly sized icons on the app window. Edge may put its own blurry one back (for example
    when the page's favicon reloads), so this checks regularly and only acts when the icon is not ours."""
    TITLE_PREFIX = TITLE

    def __init__(self, api, version_fn, log=None, image_fn=None):
        self.api, self.version_fn, self.log = api, version_fn, log or (lambda text: None)
        self.image_fn = image_fn or icon_at
        self.cache, self.cache_version = {}, None
        self.fast_until = 0.0
        self.logged = 0
        self.boost()

    def boost(self, seconds=60):
        """Check twice a second for a while (a window was just opened)."""
        self.fast_until = time.time() + seconds

    def _handle(self, px):
        ver = self.version_fn()
        if ver != self.cache_version:
            self.cache, self.cache_version = {}, ver
        if px not in self.cache:
            self.cache[px] = self.api.make_icon(self.image_fn(px))
        return self.cache[px]

    def apply_once(self):
        changed = 0
        for hwnd, _cls, title in self.api.windows():
            if not title.startswith(self.TITLE_PREFIX):
                continue
            dpi = self.api.dpi(hwnd)
            for kind, base in ((self.api.ICON_BIG, 32), (self.api.ICON_SMALL, 16)):
                px = max(16, int(round(base * dpi / 96.0)))
                handle = self._handle(px)
                if handle and self.api.get_icon(hwnd, kind) != handle:
                    if self.api.set_icon(hwnd, kind, handle):
                        changed += 1
                        if self.logged < 12:
                            self.logged += 1
                            self.log("Set the window's %s icon (%d px, screen scaling %d%%)"
                                     % ("large" if kind == self.api.ICON_BIG else "small", px, round(dpi * 100 / 96)))
        return changed

    def run_forever(self):
        failures = 0
        while True:
            try:
                self.apply_once()
            except Exception as ex:
                failures += 1
                if failures <= 3:
                    self.log("Window icon update problem: %s" % ex)
            time.sleep(0.5 if time.time() < self.fast_until else 2.5)


WINDOW_ICONS = None


def start_window_icons(version_fn):
    """Windows only. Starts the background check that keeps the sharp icons on the app window."""
    global WINDOW_ICONS
    if not IS_WIN:
        return None
    try:
        WINDOW_ICONS = WindowIcons(_WinApi(), version_fn, file_log)
        threading.Thread(target=WINDOW_ICONS.run_forever, daemon=True).start()
    except Exception as ex:
        file_log("Couldn't start the window icon helper: %s" % ex)
        WINDOW_ICONS = None
    return WINDOW_ICONS


def make_dpi_aware():
    """Tell Windows this program handles screen scaling itself, so it reports the true icon sizes
    (otherwise the tray icon is made 16 px small and then stretched on 125-200% screens)."""
    if not IS_WIN:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)      # per monitor
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ------------------------------------------------------------------ window, tray, startup
def find_browser():
    cands = []
    for var in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if base:
            cands += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                      os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    for p in cands:
        if os.path.exists(p):
            return p
    return None


def open_window(url):
    if WINDOW_ICONS:
        WINDOW_ICONS.boost()                 # check for the new window twice a second for a minute
    exe = find_browser()
    if exe:
        profile = os.path.join(DATA_DIR, "window")
        try:
            subprocess.Popen([exe, "--app=%s" % url, "--user-data-dir=%s" % profile, "--window-size=1180,800",
                              "--no-first-run", "--no-default-browser-check",
                              "--disable-sync", "--disable-features=msImplicitSignin"])   # no Edge sign-in/sync pop-up
            return
        except OSError:
            pass
    webbrowser.open(url)


def already_running(port):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/ping" % port, timeout=1.5) as r:
            return json.loads(r.read().decode()).get("app") == APP
    except Exception:
        return False


def port_free(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def tray_size():
    """The tray icon size Windows wants on this screen (16 px at 100%, 24 px at 150%, ...)."""
    if IS_WIN:
        try:
            n = int(ctypes.windll.user32.GetSystemMetrics(49))          # SM_CXSMICON
            if 12 <= n <= 128:
                return n
        except Exception:
            pass
    return 64


def tray_image():
    from PIL import Image, ImageDraw
    try:
        return icon_at(tray_size())
    except Exception:
        pass
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=(18, 21, 28, 255), outline=(255, 106, 26, 255), width=5)
    d.ellipse((20, 20, 44, 44), fill=(255, 106, 26, 255))
    return img


def make_tray(url, quit_cb):
    try:
        import pystray
    except Exception:
        return None
    menu = pystray.Menu(pystray.MenuItem("Open", lambda: open_window(url), default=True),
                        pystray.MenuItem("Quit", lambda: quit_cb()))
    return pystray.Icon(APP, tray_image(), TITLE, menu)


def main():
    if HELPER_FLAG in sys.argv:                  # the administrator step started by the setup button
        lhm_elevated_main(sys.argv[sys.argv.index(HELPER_FLAG) + 1:])
        return
    make_dpi_aware()
    minimized = "--minimized" in sys.argv
    st = Settings()
    port = int(st.get("port"))
    url = "http://127.0.0.1:%d/" % port
    if not port_free(port):
        if already_running(port):
            if not minimized:
                open_window(url)             # a copy is already running: just show its window
            return
        port = 0                             # something else owns the port; pick any free one
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        url = "http://127.0.0.1:%d/" % port

    file_log("---- %s %s starting (port %d)" % (TITLE, VERSION, port))
    engine = Engine(st)
    server = Server(engine, st, port)
    stop = threading.Event()
    icon_holder = {}

    def quit_app():
        engine.stop_evt.set()
        stop.set()
        icon = icon_holder.get("icon")
        if icon:
            try:
                icon.stop()
            except Exception:
                pass
        os._exit(0)

    server.quit_cb = quit_app
    engine.start()
    server.start()
    start_window_icons(lambda: (int(st.get("logo_version") or 0)))
    if not minimized:
        open_window(url)
    icon = make_tray(url, quit_app)
    if icon:
        icon_holder["icon"] = icon

        def logo_changed():
            try:
                icon.icon = tray_image()
            except Exception:
                pass
        server.logo_cb = logo_changed
        icon.run()                           # blocks until Quit
    else:
        while not stop.wait(1.0):
            pass


if __name__ == "__main__":
    main()
