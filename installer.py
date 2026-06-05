import os
import subprocess
import sys

def main():
    print("===============================================================================")
    print("    Simple-PDF-Player: Installer")
    print("===============================================================================")

    venv_dir = "venv"
    venv_python = os.path.join(venv_dir, "Scripts", "python.exe")

    print("[*] Creating virtual environment...")
    if not os.path.exists(venv_dir):
        try:
            subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
        except subprocess.CalledProcessError:
            print("[ERROR] Failed to create virtual environment. Ensure Python 3.12 is installed and in PATH.")
            return
    else:
        print("[*] Virtual environment already exists.")

    if not os.path.exists(venv_python):
        print("[ERROR] Virtual environment created, but Python executable not found inside it.")
        return

    print("[*] Upgrading pip for Python 3.12 compatibility...")
    try:
        subprocess.check_call([venv_python, "-m", "pip", "install", "--upgrade", "pip"])
    except subprocess.CalledProcessError:
        print("[ERROR] Failed to upgrade pip.")

    print("[*] Installing dependencies into the virtual environment...")
    dependencies = [
        "nicegui", 
        "pywebview",
        "kokoro", 
        "PyMuPDF", 
        "sounddevice", 
        "numpy"
    ]
    try:
        subprocess.check_call([venv_python, "-m", "pip", "install"] + dependencies)
    except subprocess.CalledProcessError:
        print("[ERROR] Failed to install dependencies.")

    print("[*] Creating directories and persistent files...")
    os.makedirs("data", exist_ok=True)
    
    if not os.path.exists("data/persistent.json"):
        with open("data/persistent.json", "w") as f:
            f.write("{}")

    # --- OFFLINE CACHING SEQUENCE ---
    print("[*] Downloading and caching AI models for offline use...")
    print("    (This may take a few minutes on the first install)...")
    try:
        # 1. Download Spacy English dictionary
        print("    -> Downloading Spacy dictionary...")
        subprocess.check_call([venv_python, "-m", "spacy", "download", "en_core_web_sm"])
        
        # 2. Trigger Kokoro Pipeline and default voice download
        print("    -> Downloading Kokoro TTS models and default voice...")
        cache_script = (
            "from kokoro import KPipeline; "
            "p = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M'); "
            "list(p('Test', voice='af_heart'))"
        )
        subprocess.check_call([venv_python, "-c", cache_script])
        print("[*] AI models cached successfully.")
        
    except subprocess.CalledProcessError:
        print("[ERROR] Failed to download AI models. The program may require internet on first run.")

    print("[*] Installation complete. The application is ready to run offline.")

if __name__ == "__main__":
    main()