import fitz  # PyMuPDF
import json
import os
from scripts import temporary

# ===============================================================================
#     Simple-PDF-Player: Utility Functions
# ===============================================================================

def load_pdf(filepath):
    if temporary.app_state["doc"]:
        temporary.app_state["doc"].close()
        
    doc = fitz.open(filepath)
    temporary.app_state["pdf_path"] = filepath
    temporary.app_state["doc"] = doc
    temporary.app_state["text_data"] = []
    temporary.app_state["current_page"] = 0
    temporary.app_state["current_char_index"] = 0
    
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

def save_persistent():
    data = {
        "voice": temporary.app_state["voice"],
        "speed": temporary.app_state["speed"],
        "last_file": temporary.app_state["pdf_path"],
        "window_width": temporary.app_state.get("window_width", 650),
        "window_height": temporary.app_state.get("window_height", 300)
    }
    with open(os.path.join("data", "persistent.json"), "w") as f:
        json.dump(data, f, indent=4)

def load_persistent():
    fpath = os.path.join("data", "persistent.json")
    if os.path.exists(fpath):
        with open(fpath, "r") as f:
            data = json.load(f)
            temporary.app_state["voice"] = data.get("voice", "af_heart")
            temporary.app_state["speed"] = data.get("speed", 1.0)
            temporary.app_state["window_width"] = data.get("window_width", 650)
            temporary.app_state["window_height"] = data.get("window_height", 330)

def shutdown():
    print("===============================================================================")
    print("    Simple-PDF-Player: Shutdown")
    print("===============================================================================")
    
    from scripts import speach
    speach.stop_playback()
    
    if temporary.app_state["doc"]:
        temporary.app_state["doc"].close()
        temporary.app_state["doc"] = None
        
    save_persistent()
    print("[*] Shutdown complete.")