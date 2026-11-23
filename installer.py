import os
import subprocess
import sys
import platform
import traceback
from datetime import datetime

# ===============================================================================
#     Simple-PDF-Player: Installer (v2 – hardware-aware)
# ===============================================================================

def get_venv_python(venv_dir="venv"):
    if sys.platform == "win32":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def detect_hardware():
    """Collect basic hardware information and attempt to detect x86-64-v2 support."""
    info = {
        "timestamp": datetime.now().isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "architecture": platform.architecture(),
        "cpu_count": os.cpu_count(),
    }

    # Try to get more detailed CPU name on Windows
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["wmic", "cpu", "get", "Name,NumberOfCores,NumberOfLogicalProcessors /value"],
                text=True, stderr=subprocess.DEVNULL, timeout=10
            )
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("Name="):
                    info["cpu_name"] = line.split("=", 1)[1].strip()
                elif line.startswith("NumberOfCores="):
                    info["cores"] = line.split("=", 1)[1].strip()
                elif line.startswith("NumberOfLogicalProcessors="):
                    info["logical_processors"] = line.split("=", 1)[1].strip()
        except Exception:
            info["cpu_name"] = info.get("processor", "unknown")

    # Heuristic: Core 2 Duo / very old CPUs typically lack SSE4.2 (X86_V2)
    # We also do a runtime test later after numpy is installed.
    cpu_lower = (info.get("cpu_name") or info.get("processor") or "").lower()
    old_cpu_markers = [
        "core(tm)2", "core 2", "core2", "pentium dual", "pentium(r) dual",
        "athlon 64", "sempron", "phenom", "conroe", "penryn", "wolfdale",
        "yorkfield", "allendale"
    ]
    info["likely_old_cpu"] = any(m in cpu_lower for m in old_cpu_markers)
    info["supports_x86_v2"] = None  # unknown until runtime test

    return info


def write_hardware_txt(info, path="data/hardware.txt"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "Simple-PDF-Player – Hardware Report",
        "=" * 50,
        f"Generated : {info.get('timestamp')}",
        f"Python    : {info.get('python')}",
        f"Platform  : {info.get('platform')}",
        f"Machine   : {info.get('machine')}",
        f"Processor : {info.get('processor')}",
        f"CPU Name  : {info.get('cpu_name', 'n/a')}",
        f"Cores     : {info.get('cores', 'n/a')} (logical: {info.get('logical_processors', 'n/a')})",
        f"Likely old CPU (pre-x86-64-v2): {info.get('likely_old_cpu')}",
        f"Supports X86_V2 (runtime): {info.get('supports_x86_v2')}",
        "",
        "Notes:",
        "- Modern NumPy (2.x) and many ML wheels require x86-64-v2 (SSE4.2 etc.).",
        "- Core 2 Duo / early Phenom / similar CPUs need older NumPy (1.26.x).",
        "- On very old CPUs TTS (Kokoro/torch) may be slow or unavailable.",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[*] Hardware info saved")


def test_numpy_import(venv_python):
    """Return (ok: bool, error_message: str|None)"""
    try:
        result = subprocess.run(
            [venv_python, "-c", "import numpy; print(numpy.__version__)"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, (result.stderr or result.stdout or "unknown error").strip()
    except Exception as e:
        return False, str(e)


def install_compatible_numpy(venv_python, force_old=False):
    """Install a NumPy that can actually import on this CPU."""
    if force_old:
        print("[*] Using compatible NumPy 1.26.4 for this CPU...")
        subprocess.check_call([venv_python, "-m", "pip", "install", "--force-reinstall", "numpy==1.26.4"])
        return

    # First try whatever is already installed / latest
    ok, msg = test_numpy_import(venv_python)
    if ok:
        print(f"[*] NumPy OK (version {msg})")
        return

    # Modern NumPy wheels require x86-64-v2; fall back quietly on older CPUs
    if "X86_V2" in msg or "baseline optimizations" in msg:
        print("[*] Modern NumPy requires newer CPU instructions – switching to compatible NumPy 1.26.4...")
        subprocess.check_call([venv_python, "-m", "pip", "install", "--force-reinstall", "numpy==1.26.4"])
        ok2, msg2 = test_numpy_import(venv_python)
        if ok2:
            print(f"[*] Compatible NumPy ready (version {msg2})")
        else:
            print("[!] Compatible NumPy could not be loaded on this CPU.")
            print("        " + (msg2 or "")[:300])
    else:
        print("[*] Switching to compatible NumPy 1.26.4...")
        subprocess.check_call([venv_python, "-m", "pip", "install", "--force-reinstall", "numpy==1.26.4"])


def main():
    print("===============================================================================")
    print("    Simple-PDF-Player: Installer")
    print("===============================================================================")

    venv_dir = "venv"
    venv_python = get_venv_python(venv_dir)

    # --- Hardware detection (before anything else) ---
    print("[*] Detecting hardware...")
    hw = detect_hardware()
    print(f"    CPU      : {hw.get('cpu_name') or hw.get('processor')}")
    print(f"    Likely old (pre-x86-64-v2): {hw.get('likely_old_cpu')}")

    # Create data dir early so we can always write hardware.txt
    os.makedirs("data", exist_ok=True)
    write_hardware_txt(hw)

    # --- Virtual environment ---
    print("[*] Creating virtual environment...")
    if not os.path.exists(venv_dir):
        try:
            subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
        except subprocess.CalledProcessError:
            print("[ERROR] Failed to create virtual environment. Ensure Python 3.11/3.12 is installed and in PATH.")
            return
    else:
        print("[*] Virtual environment already exists.")

    if not os.path.exists(venv_python):
        print("[ERROR] Virtual environment created, but Python executable not found inside it.")
        return

    print("[*] Upgrading pip...")
    try:
        subprocess.check_call([venv_python, "-m", "pip", "install", "--upgrade", "pip"])
    except subprocess.CalledProcessError:
        print("[ERROR] Failed to upgrade pip.")

    # --- Install core dependencies ---
    # On known-old CPUs we pre-pin numpy so the rest of the install has a working numpy.
    print("[*] Installing dependencies into the virtual environment...")
    base_deps = [
        "nicegui",
        "pywebview",
        "kokoro",
        "PyMuPDF",
        "sounddevice",
    ]

    if hw.get("likely_old_cpu"):
        print("[*] Older CPU detected – installing compatible NumPy 1.26.4...")
        try:
            subprocess.check_call([venv_python, "-m", "pip", "install", "numpy==1.26.4"])
        except subprocess.CalledProcessError:
            print("[*] Could not pre-install compatible NumPy; will retry after main install")
        deps = base_deps  # numpy already handled
    else:
        deps = base_deps + ["numpy"]

    try:
        subprocess.check_call([venv_python, "-m", "pip", "install"] + deps)
    except subprocess.CalledProcessError:
        print("[ERROR] Failed to install one or more dependencies.")
        # Continue anyway so we still create the data files and give a useful report

    # --- Post-install NumPy compatibility check / repair ---
    print("[*] Verifying NumPy can import on this CPU...")
    install_compatible_numpy(venv_python, force_old=hw.get("likely_old_cpu", False))

    # Re-test and update hardware report
    ok, ver_or_err = test_numpy_import(venv_python)
    hw["supports_x86_v2"] = ok and "1.26" not in str(ver_or_err)  # rough heuristic
    hw["numpy_version"] = ver_or_err if ok else f"FAILED: {ver_or_err}"
    write_hardware_txt(hw)  # rewrite with final status

    # --- Always create the data files the app expects ---
    print("[*] Creating directories and config files...")
    os.makedirs("data", exist_ok=True)

    if not os.path.exists("data/program.json"):
        import json
        program_defaults = {
            "voice": "af_heart",
            "speed": 1.0,
            "last_file": None,
            "window_width": 740,
            "window_height": 350,
            "playlist_open": False,
            "playlist_width": 740,
            "playlist_height": 400,
        }
        with open("data/program.json", "w", encoding="utf-8") as f:
            json.dump(program_defaults, f, indent=4)
        print("    created data/program.json")

    if not os.path.exists("data/playlist.json"):
        import json
        with open("data/playlist.json", "w", encoding="utf-8") as f:
            json.dump({"playlist": [], "playlist_index": -1}, f, indent=4)
        print("    created data/playlist.json")

    # --- Model caching (best-effort) ---
    print("[*] Downloading and caching AI models for offline use...")
    print("    (This may take a few minutes on the first install)...")

    models_ok = True
    try:
        print("    -> Downloading Spacy dictionary (en_core_web_sm)...")
        subprocess.check_call([venv_python, "-m", "spacy", "download", "en_core_web_sm"])
    except subprocess.CalledProcessError as e:
        models_ok = False
        print("[WARNING] Spacy model download failed.")
        print("          On very old CPUs this is often caused by NumPy / thinc binary incompatibility.")
        print("          The rest of the application may still work; TTS phonemizer quality can be reduced.")

    try:
        print("    -> Downloading Kokoro TTS models and default voice...")
        cache_script = (
            "from kokoro import KPipeline; "
            "p = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M'); "
            "list(p('Test', voice='af_heart'))"
        )
        subprocess.check_call([venv_python, "-c", cache_script])
        print("[*] Kokoro models cached successfully.")
    except subprocess.CalledProcessError:
        models_ok = False
        print("[WARNING] Kokoro model cache failed.")
        print("          Torch / Kokoro may not support this CPU. TTS will not work until a compatible")
        print("          torch wheel is available or you run on a newer machine.")

    if models_ok:
        print("[*] AI models cached successfully.")
    else:
        print("[*] Installation finished with warnings (see above).")
        print("    Check data/hardware.txt for details about your CPU.")

    print()
    print("[*] Installation complete. You can now launch the application.")

if __name__ == "__main__":
    main()
