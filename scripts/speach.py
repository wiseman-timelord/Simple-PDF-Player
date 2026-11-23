import threading
import queue
import sounddevice as sd
import numpy as np
from scripts import temporary
import re

# ===============================================================================
#     Simple-PDF-Player: TTS Engine (lazy load / unload)
# ===============================================================================

pipeline = None
_pipeline_lock = threading.Lock()

def get_pipeline():
    """
    Lazy-loads the Kokoro TTS pipeline.
    Callers that need the models (start_playback) should ensure loading
    has completed and temporary.app_state["models_loaded"] is True.
    """
    global pipeline
    with _pipeline_lock:
        if pipeline is None:
            from kokoro import KPipeline
            print("[*] Initializing Kokoro TTS Pipeline...")
            pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
            print("[*] Kokoro TTS Pipeline ready.")
            temporary.app_state["models_loaded"] = True
        return pipeline

def unload_pipeline():
    """Release the Kokoro pipeline and free memory when no more playback is needed."""
    global pipeline
    with _pipeline_lock:
        if pipeline is not None:
            print("[*] Unloading Kokoro TTS Pipeline...")
            # Best-effort cleanup; Kokoro / torch may still hold some resources
            try:
                del pipeline
            except Exception:
                pass
            pipeline = None
            # Encourage GC of large model tensors
            try:
                import gc
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()
            except Exception:
                pass
            temporary.app_state["models_loaded"] = False
            print("[*] Kokoro TTS Pipeline unloaded.")

def ensure_models_loaded(status_callback=None):
    """
    Ensure the TTS pipeline is loaded. Calls status_callback("loading") / 
    status_callback("ready") if provided so the UI can show messages.
    Returns True on success, False on failure.
    """
    if temporary.app_state.get("models_loaded") and pipeline is not None:
        return True
    temporary.app_state["models_loading"] = True
    if status_callback:
        status_callback("loading")
    try:
        get_pipeline()
        temporary.app_state["models_loading"] = False
        if status_callback:
            status_callback("ready")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to load TTS models: {e}")
        temporary.app_state["models_loading"] = False
        temporary.app_state["models_loaded"] = False
        if status_callback:
            status_callback("error")
        return False

def unload_models_if_idle(status_callback=None):
    """
    Unload models only when we are truly finished (no more playlist items
    and not currently playing/paused).
    """
    if not temporary.app_state.get("models_loaded"):
        return
    # Don't unload while still playing or paused mid-document
    if temporary.app_state.get("is_playing") or temporary.app_state.get("is_paused"):
        return
    temporary.app_state["models_loading"] = True
    if status_callback:
        status_callback("unloading")
    unload_pipeline()
    temporary.app_state["models_loading"] = False
    if status_callback:
        status_callback("standby")


def split_into_chunks(text, max_chars=500):
    """Splits text into smaller chunks at sentence endings for smoother TTS playback."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks if chunks else [text]

def synthesise_chunk(text_chunk):
    """
    Synthesises a single text chunk into a numpy float32 audio array.
    Returns (audio_data, char_count) or (None, 0) on failure/stop.
    Does NOT play anything — caller handles playback.
    """
    try:
        pipe = get_pipeline()
        voice = temporary.app_state["voice"]
        speed = temporary.app_state["speed"]

        audio_chunks = []
        for graphemes, phonemes, audio in pipe(text_chunk, voice=voice, speed=speed):
            if temporary.app_state["stop_flag"]:
                return None, 0
            if audio is not None:
                audio_chunks.append(audio)

        if not audio_chunks:
            return None, len(text_chunk)

        import torch
        if isinstance(audio_chunks[0], torch.Tensor):
            audio_data = torch.cat(audio_chunks).cpu().numpy()
        elif isinstance(audio_chunks[0], np.ndarray):
            audio_data = np.concatenate(audio_chunks)
        else:
            audio_data = np.array(audio_chunks)

        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        return audio_data, len(text_chunk)

    except Exception as e:
        print(f"TTS Synthesis Error: {e}")
        import traceback
        traceback.print_exc()
        return None, 0


# Sentinel object placed into the audio queue to signal "no more audio coming"
_QUEUE_DONE = object()

# Queue size: how many pre-generated chunks to buffer ahead of playback.
_LOOKAHEAD = 2


def start_playback(status_callback=None, on_document_finished=None):
    """
    Start (or resume) playback.
    status_callback(msg) is called with "loading" / "ready" / "error" so UI can update.
    on_document_finished() is called when the current document reaches the end
    (so the UI / playlist logic can decide whether to advance or unload models).
    """
    if not temporary.app_state["doc"]:
        return

    # Ensure models are loaded before starting threads
    if not ensure_models_loaded(status_callback=status_callback):
        temporary.app_state["is_playing"] = False
        temporary.app_state["is_paused"] = False
        return

    # Capture the generation at the moment this playback session starts.
    my_generation = temporary.app_state["playback_generation"]

    temporary.app_state["stop_flag"] = False
    temporary.app_state["is_playing"] = True
    temporary.app_state["is_paused"] = False

    audio_queue = queue.Queue(maxsize=_LOOKAHEAD)

    def producer():
        try:
            while (not temporary.app_state["stop_flag"] and
                   temporary.app_state["playback_generation"] == my_generation):
                page_idx = temporary.app_state["current_page"]
                if page_idx >= len(temporary.app_state["text_data"]):
                    break

                page_data = temporary.app_state["text_data"][page_idx]
                remaining_text = page_data["text"][temporary.app_state["current_char_index"]:]

                if not remaining_text.strip():
                    temporary.app_state["current_page"] += 1
                    temporary.app_state["current_char_index"] = 0
                    continue

                chunks = split_into_chunks(remaining_text)

                for chunk in chunks:
                    if (temporary.app_state["stop_flag"] or
                            temporary.app_state["playback_generation"] != my_generation):
                        return

                    audio_data, chars = synthesise_chunk(chunk)

                    if (temporary.app_state["stop_flag"] or
                            temporary.app_state["playback_generation"] != my_generation):
                        return

                    while (not temporary.app_state["stop_flag"] and
                           temporary.app_state["playback_generation"] == my_generation):
                        try:
                            audio_queue.put((audio_data, chars), timeout=0.1)
                            break
                        except queue.Full:
                            continue

                if (not temporary.app_state["stop_flag"] and
                        temporary.app_state["playback_generation"] == my_generation):
                    temporary.app_state["current_page"] += 1
                    temporary.app_state["current_char_index"] = 0

        finally:
            try:
                audio_queue.put(_QUEUE_DONE, timeout=1.0)
            except queue.Full:
                pass

    def consumer():
        finished_naturally = False
        while (not temporary.app_state["stop_flag"] and
               temporary.app_state["playback_generation"] == my_generation):
            try:
                item = audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is _QUEUE_DONE:
                finished_naturally = True
                temporary.app_state["is_playing"] = False
                break

            audio_data, chars = item

            if audio_data is None:
                temporary.app_state["current_char_index"] += chars
                audio_queue.task_done()
                continue

            if (temporary.app_state["stop_flag"] or
                    temporary.app_state["playback_generation"] != my_generation):
                audio_queue.task_done()
                break

            sd.play(audio_data, samplerate=24000)
            while sd.get_stream() is not None and sd.get_stream().active:
                if (temporary.app_state["stop_flag"] or
                        temporary.app_state["playback_generation"] != my_generation):
                    sd.stop()
                    audio_queue.task_done()
                    return
                sd.sleep(50)

            temporary.app_state["current_char_index"] += chars
            audio_queue.task_done()

        if temporary.app_state["playback_generation"] == my_generation:
            temporary.app_state["is_playing"] = False

        # Document reached the end → let UI / playlist decide next action
        if finished_naturally and on_document_finished and \
                temporary.app_state["playback_generation"] == my_generation:
            try:
                on_document_finished()
            except Exception as e:
                print(f"[ERROR] on_document_finished callback failed: {e}")

    producer_thread = threading.Thread(target=producer, daemon=True, name="tts-producer")
    consumer_thread = threading.Thread(target=consumer, daemon=True, name="tts-consumer")

    temporary.app_state["tts_thread"] = consumer_thread
    temporary.app_state["_producer_thread"] = producer_thread

    producer_thread.start()
    consumer_thread.start()


def pause_playback():
    """Pauses playback, holding the current position so it can be resumed."""
    temporary.app_state["stop_flag"] = True
    temporary.app_state["is_playing"] = False
    temporary.app_state["is_paused"] = True
    temporary.app_state["playback_generation"] += 1
    sd.stop()


def stop_playback():
    """Stops playback entirely and clears the paused state."""
    temporary.app_state["stop_flag"] = True
    temporary.app_state["is_playing"] = False
    temporary.app_state["is_paused"] = False
    temporary.app_state["playback_generation"] += 1
    sd.stop()
