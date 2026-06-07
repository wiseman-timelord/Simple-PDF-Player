import threading
import queue
import sounddevice as sd
import numpy as np
from scripts import temporary
import re

# ===============================================================================
#     Simple-PDF-Player: TTS Engine
# ===============================================================================

pipeline = None

def get_pipeline():
    """Lazy-loads the Kokoro TTS pipeline so it doesn't slow down app startup."""
    global pipeline
    if pipeline is None:
        from kokoro import KPipeline
        print("[*] Initializing Kokoro TTS Pipeline...")
        pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
        print("[*] Kokoro TTS Pipeline ready.")
    return pipeline

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
# 2 means we keep up to 2 chunks ready and waiting while the current one plays.
_LOOKAHEAD = 2


def start_playback():
    if not temporary.app_state["doc"]:
        return

    temporary.app_state["stop_flag"] = False
    temporary.app_state["is_playing"] = True
    temporary.app_state["is_paused"] = False

    # audio_queue carries tuples of (audio_data: np.ndarray, chars_spoken: int)
    # or the _QUEUE_DONE sentinel.
    audio_queue = queue.Queue(maxsize=_LOOKAHEAD)

    # ------------------------------------------------------------------
    # PRODUCER: walks pages/chunks and synthesises audio into the queue.
    # Runs ahead of playback so audio is ready before it's needed.
    # ------------------------------------------------------------------
    def producer():
        try:
            while not temporary.app_state["stop_flag"]:
                page_idx = temporary.app_state["current_page"]
                if page_idx >= len(temporary.app_state["text_data"]):
                    break

                page_data = temporary.app_state["text_data"][page_idx]
                remaining_text = page_data["text"][temporary.app_state["current_char_index"]:]

                if not remaining_text.strip():
                    # Advance to next page (consumer hasn't touched page state here,
                    # it's safe because only the producer drives the page cursor while
                    # the consumer only advances current_char_index via a callback).
                    temporary.app_state["current_page"] += 1
                    temporary.app_state["current_char_index"] = 0
                    continue

                chunks = split_into_chunks(remaining_text)

                for chunk in chunks:
                    if temporary.app_state["stop_flag"]:
                        return

                    audio_data, chars = synthesise_chunk(chunk)

                    if temporary.app_state["stop_flag"]:
                        return

                    # Block here if the queue is full (consumer is still playing
                    # the previous chunks). This naturally applies back-pressure so
                    # we don't synthesise the entire book into RAM.
                    while not temporary.app_state["stop_flag"]:
                        try:
                            audio_queue.put((audio_data, chars), timeout=0.1)
                            break
                        except queue.Full:
                            continue

                # After all chunks on this page are queued, advance page state
                if not temporary.app_state["stop_flag"]:
                    temporary.app_state["current_page"] += 1
                    temporary.app_state["current_char_index"] = 0

        finally:
            # Always signal the consumer that we're done, even on exception/stop
            try:
                audio_queue.put(_QUEUE_DONE, timeout=1.0)
            except queue.Full:
                pass

    # ------------------------------------------------------------------
    # CONSUMER: pulls synthesised audio from the queue and plays it.
    # Blocks only during actual audio playback, not during synthesis.
    # ------------------------------------------------------------------
    def consumer():
        while not temporary.app_state["stop_flag"]:
            try:
                item = audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is _QUEUE_DONE:
                temporary.app_state["is_playing"] = False
                break

            audio_data, chars = item

            if audio_data is None:
                # Chunk synthesised to silence (e.g. whitespace-only) — just
                # advance the char counter and move on without any audio gap.
                temporary.app_state["current_char_index"] += chars
                audio_queue.task_done()
                continue

            if temporary.app_state["stop_flag"]:
                audio_queue.task_done()
                break

            # Play the chunk and wait for it to finish
            sd.play(audio_data, samplerate=24000)
            while sd.get_stream() is not None and sd.get_stream().active:
                if temporary.app_state["stop_flag"]:
                    sd.stop()
                    audio_queue.task_done()
                    return
                sd.sleep(50)

            temporary.app_state["current_char_index"] += chars
            audio_queue.task_done()

    producer_thread = threading.Thread(target=producer, daemon=True, name="tts-producer")
    consumer_thread = threading.Thread(target=consumer, daemon=True, name="tts-consumer")

    # Store both so stop/pause can signal them via stop_flag
    temporary.app_state["tts_thread"] = consumer_thread
    temporary.app_state["_producer_thread"] = producer_thread

    producer_thread.start()
    consumer_thread.start()


def pause_playback():
    """Pauses playback, holding the current position so it can be resumed."""
    temporary.app_state["stop_flag"] = True
    temporary.app_state["is_playing"] = False
    temporary.app_state["is_paused"] = True
    sd.stop()


def stop_playback():
    """Stops playback entirely and clears the paused state."""
    temporary.app_state["stop_flag"] = True
    temporary.app_state["is_playing"] = False
    temporary.app_state["is_paused"] = False
    sd.stop()