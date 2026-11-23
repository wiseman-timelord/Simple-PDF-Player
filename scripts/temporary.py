# ===============================================================================
#     Simple-PDF-Player: Temporary Globals
# ===============================================================================

app_state = {
    "pdf_path": None,
    "doc": None,
    "text_data": [],      # List of dicts: {"text": str, "chars": int, "words": int, "paragraphs": int, "is_chapter": bool}
    "current_page": 0,
    "current_char_index": 0,
    "is_playing": False,
    "is_paused": False,   # True when paused mid-playback (position is held, audio is stopped)
    "tts_thread": None,
    "_producer_thread": None,
    "stop_flag": False,
    "voice": "af_heart",
    "speed": 1.0,
    "totals": {"chars": 0, "words": 0, "paragraphs": 0, "pages": 0},

    # UI Window Dimensions (taller to fit integrated playlist + player)
    "window_width": 740,
    "window_height": 560,

    # Playlist support
    "playlist": [],           # list of absolute PDF file paths
    "playlist_index": -1,     # currently playing index in playlist (-1 = none)
    "playlist_selected": [],  # list of selected indices (multi-select)
    "playlist_sort_mode": 0,  # 0=AlphaNum 1=FilSiz-SmLg 2=FilSiz-LgSm 3=DateOldNew 4=DateNewOld
    "playback_generation": 0, # incremented on every stop/load to invalidate stale TTS threads

    # TTS model lifecycle
    "models_loaded": False,   # True once Kokoro pipeline has been successfully created
    "models_loading": False,  # True while models are being loaded or unloaded
}

SORT_LABELS = [
    "AlphaNum",
    "FilSiz-SmLg",
    "FilSiz-LgSm",
    "DateOldNew",
    "DateNewOld",
]
