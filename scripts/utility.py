import fitz  # PyMuPDF
import json
import os
from scripts import temporary

# ===============================================================================
#     Simple-PDF-Player: Utility Functions
# ===============================================================================

def load_pdf(filepath):
    """Load a PDF, fully resetting playback state so a new file can be played immediately."""
    from scripts import speach
    # Always stop any ongoing playback first to kill old producer/consumer threads
    speach.stop_playback()

    if temporary.app_state["doc"]:
        try:
            temporary.app_state["doc"].close()
        except Exception:
            pass
        
    doc = fitz.open(filepath)
    temporary.app_state["pdf_path"] = filepath
    temporary.app_state["doc"] = doc
    temporary.app_state["text_data"] = []
    temporary.app_state["current_page"] = 0
    temporary.app_state["current_char_index"] = 0
    temporary.app_state["is_playing"] = False
    temporary.app_state["is_paused"] = False
    temporary.app_state["stop_flag"] = False
    # Invalidate any lingering TTS threads from previous playback
    temporary.app_state["playback_generation"] += 1
    
    totals = {"chars": 0, "words": 0, "paragraphs": 0, "pages": 0}
    
    for page in doc:
        text = page.get_text("text")
        words = len(text.split())
        chars = len(text)
        paragraphs = len([p for p in text.split('\n') if p.strip()])
        
        is_chapter = any(line.lower().startswith("chapter") for line in text.split('\n') if line.strip())
        
        temporary.app_state["text_data"].append({
            "text": text,
            "chars": chars,
            "words": words,
            "paragraphs": paragraphs,
            "is_chapter": is_chapter
        })
        
        totals["chars"] += chars
        totals["words"] += words
        totals["paragraphs"] += paragraphs
        totals["pages"] += 1

    temporary.app_state["totals"] = totals

    # Keep playlist selection in sync if this file is already in the list
    try:
        idx = temporary.app_state["playlist"].index(filepath)
        temporary.app_state["playlist_index"] = idx
    except ValueError:
        # Not in playlist – leave index alone (caller may add it)
        pass

def get_progress():
    page_idx = temporary.app_state["current_page"]
    totals = temporary.app_state["totals"]
    
    if not temporary.app_state["doc"]:
        return "C0/W0/p0/P0 / C0/W0/p0/P0"
    
    if page_idx >= len(temporary.app_state["text_data"]):
        cur_c, cur_w, cur_p, cur_P = totals["chars"], totals["words"], totals["paragraphs"], totals["pages"]
    else:
        total_chars = sum(p["chars"] for p in temporary.app_state["text_data"][:page_idx]) + temporary.app_state["current_char_index"]
        current_text_chunk = temporary.app_state["text_data"][page_idx]["text"][:temporary.app_state["current_char_index"]]
        total_words = sum(p["words"] for p in temporary.app_state["text_data"][:page_idx]) + len(current_text_chunk.split())
        total_paragraphs = sum(p["paragraphs"] for p in temporary.app_state["text_data"][:page_idx]) + len([prg for prg in current_text_chunk.split('\n') if prg.strip()])
        
        cur_P = page_idx if temporary.app_state["current_char_index"] == 0 and page_idx == 0 else page_idx + 1
        cur_c, cur_w, cur_p = total_chars, total_words, total_paragraphs
    
    max_c = totals["chars"]
    max_w = totals["words"]
    max_p = totals["paragraphs"]
    max_P = totals["pages"]
    
    return f"C{cur_c}/W{cur_w}/p{cur_p}/P{cur_P} / C{max_c}/W{max_w}/p{max_p}/P{max_P}"

def save_program():
    """Save program settings (voice, speed, window size, sort mode) to data/program.json"""
    data = {
        "voice": temporary.app_state["voice"],
        "speed": temporary.app_state["speed"],
        "last_file": temporary.app_state["pdf_path"],
        "window_width": temporary.app_state.get("window_width", 740),
        "window_height": temporary.app_state.get("window_height", 560),
        "playlist_sort_mode": temporary.app_state.get("playlist_sort_mode", 0),
    }
    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "program.json"), "w") as f:
        json.dump(data, f, indent=4)

# Backward-compatible aliases
save_persistent = save_program

def load_program():
    """Load program settings from data/program.json (or legacy persistent.json)"""
    fpath = os.path.join("data", "program.json")
    legacy = os.path.join("data", "persistent.json")
    if not os.path.exists(fpath) and os.path.exists(legacy):
        fpath = legacy  # one-time migration path
    if os.path.exists(fpath):
        with open(fpath, "r") as f:
            data = json.load(f)
            temporary.app_state["voice"] = data.get("voice", "af_heart")
            temporary.app_state["speed"] = data.get("speed", 1.0)
            temporary.app_state["window_width"] = data.get("window_width", 740)
            temporary.app_state["window_height"] = data.get("window_height", 560)
            temporary.app_state["playlist_sort_mode"] = data.get("playlist_sort_mode", 0)

# Backward-compatible aliases
load_persistent = load_program

def save_playlist():
    """Persist the current playlist to data/playlist.json"""
    os.makedirs("data", exist_ok=True)
    data = {
        "playlist": temporary.app_state.get("playlist", []),
        "playlist_index": temporary.app_state.get("playlist_index", -1)
    }
    with open(os.path.join("data", "playlist.json"), "w") as f:
        json.dump(data, f, indent=4)

def load_playlist():
    """Load playlist from data/playlist.json (missing or invalid entries are dropped)"""
    fpath = os.path.join("data", "playlist.json")
    if not os.path.exists(fpath):
        temporary.app_state["playlist"] = []
        temporary.app_state["playlist_index"] = -1
        return
    try:
        with open(fpath, "r") as f:
            data = json.load(f)
        raw = data.get("playlist", [])
        # Keep only existing PDF files
        cleaned = [p for p in raw if isinstance(p, str) and p.lower().endswith(".pdf") and os.path.isfile(p)]
        temporary.app_state["playlist"] = cleaned
        idx = data.get("playlist_index", -1)
        if 0 <= idx < len(cleaned):
            temporary.app_state["playlist_index"] = idx
        else:
            temporary.app_state["playlist_index"] = -1
    except Exception:
        temporary.app_state["playlist"] = []
        temporary.app_state["playlist_index"] = -1

def shutdown():
    print("===============================================================================")
    print("    Simple-PDF-Player: Shutdown")
    print("===============================================================================")
    
    from scripts import speach
    speach.stop_playback()
    try:
        speach.unload_pipeline()
    except Exception:
        pass
    
    if temporary.app_state["doc"]:
        try:
            temporary.app_state["doc"].close()
        except Exception:
            pass
        temporary.app_state["doc"] = None
        
    save_program()
    save_playlist()
    print("[*] Shutdown complete.")