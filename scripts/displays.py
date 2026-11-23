from nicegui import ui
from scripts import temporary
from scripts import speach
from scripts import utility
import os

# ===============================================================================
#     Simple-PDF-Player: User Interface (integrated playlist + player)
# ===============================================================================

progress_label = None
filename_label = None
play_button = None
playlist_list_container = None
sort_button = None
drop_zone = None

def _status_callback(msg):
    """Called by speach during model load/unload so the filename label updates."""
    if not filename_label:
        return
    if msg == "loading":
        filename_label.text = "Loading TTS Models..."
    elif msg == "unloading":
        filename_label.text = "Unloading TTS Models..."
    elif msg == "standby":
        filename_label.text = "Standby Mode, Models Unloaded"
    elif msg == "ready":
        update_filename()
    elif msg == "error":
        filename_label.text = "TTS Model Load Failed"
    try:
        filename_label.update()
    except Exception:
        pass

def update_filename():
    """Refresh the main status / filename line according to current state."""
    if not filename_label:
        return
    if temporary.app_state.get("models_loading"):
        return
    if (not temporary.app_state.get("models_loaded")
            and not temporary.app_state.get("is_playing")
            and not temporary.app_state.get("is_paused")):
        filename_label.text = "Standby Mode, Models Unloaded"
        return
    path = temporary.app_state.get("pdf_path")
    if path:
        name = os.path.splitext(os.path.basename(path))[0]
        truncated = name[:48] + '…' if len(name) > 48 else name
        filename_label.text = truncated
    else:
        filename_label.text = 'No file loaded'

def update_progress():
    if progress_label:
        progress_label.text = utility.get_progress()
    if play_button:
        if temporary.app_state["is_playing"]:
            play_button.props('icon=pause color=white')
        elif temporary.app_state["is_paused"]:
            play_button.props('icon=play_arrow color=amber')
        else:
            play_button.props('icon=play_arrow color=white')
    update_filename()

def build_ui():
    global progress_label, filename_label, play_button, playlist_list_container, sort_button, drop_zone

    ui.add_head_html('''<style>
        body { margin: 0; padding: 0; overflow: hidden; }
        .playlist-item { cursor: pointer; padding: 5px 10px; border-radius: 4px; user-select: none; }
        .playlist-item:hover { background: rgba(255,255,255,0.08); }
        .playlist-item.selected { background: rgba(33,150,243,0.35); }
        .playlist-item.playing { border-left: 3px solid #42a5f5; }
        .playlist-drop-zone { border: 2px dashed #555; border-radius: 6px;
                             min-height: 140px; color: #888;
                             transition: border-color 0.15s, background 0.15s; }
        .playlist-drop-zone.drag-over { border-color: #2196f3; background: rgba(33,150,243,0.08); color: #2196f3; }
        .section-bar { min-height: 36px; }
    </style>
    <script>
    window.__spp_last_drop_paths = [];
    document.addEventListener("drop", function(ev) {
        try {
            const paths = [];
            if (ev.dataTransfer && ev.dataTransfer.files) {
                for (let i = 0; i < ev.dataTransfer.files.length; i++) {
                    const f = ev.dataTransfer.files[i];
                    const p = f.path || f.name;
                    if (p) paths.push(p);
                }
            }
            window.__spp_last_drop_paths = paths;
        } catch (e) {}
    }, true);
    </script>
    ''')

    with ui.card().classes(
        'w-full h-screen q-pa-sm bg-grey-10 text-white column no-shadow'
    ).style('border-radius: 0; box-sizing: border-box;'):

        # ---- Title ----
        ui.label('Simple-PDF-Player').classes('text-h6 text-weight-bold text-center w-full q-mb-xs')

        # ---- Top Add / Remove ----
        with ui.row().classes('w-full items-center justify-center q-gutter-sm section-bar'):
            ui.button('Add', on_click=add_pdfs_to_playlist).props('flat dense color=white').tooltip('Add PDF file(s)')
            ui.button('Remove', on_click=remove_selected).props('flat dense color=white').tooltip('Remove selected from playlist')

        # ---- Playlist (drop zone + scrollable list) ----
        drop_zone = ui.element('div').classes('playlist-drop-zone w-full q-mb-xs').style(
            'flex: 1 1 auto; display: flex; flex-direction: column; overflow: hidden;'
        )
        with drop_zone:
            with ui.scroll_area().classes('w-full').style('flex: 1 1 auto; min-height: 120px;'):
                playlist_list_container = ui.column().classes('w-full q-pa-xs')

        # Wire drag-and-drop (Explorer → playlist)
        drop_zone.on('dragover', _on_drag_over)
        drop_zone.on('dragleave', _on_drag_leave)
        drop_zone.on('drop', _on_drop)

        # ---- Bottom playlist controls: Add, Remove, Sort, Shuffle, Clear ----
        with ui.row().classes('w-full items-center justify-center q-gutter-xs section-bar q-mb-sm'):
            ui.button('Add', on_click=add_pdfs_to_playlist).props('flat dense color=white')
            ui.button('Remove', on_click=remove_selected).props('flat dense color=white')
            sort_button = ui.button(
                temporary.SORT_LABELS[temporary.app_state.get("playlist_sort_mode", 0)],
                on_click=cycle_sort_mode
            ).props('flat dense color=white').tooltip('Cycle playlist sort mode')
            ui.button('Shuffle', on_click=shuffle_playlist).props('flat dense color=white')
            ui.button('Clear', on_click=clear_playlist).props('flat dense color=white')

        # ---- Player area: filename (left) | progress (right) ----
        with ui.row().classes('w-full items-center no-wrap q-px-sm q-py-xs bg-grey-9 rounded'):
            filename_label = ui.label('Standby Mode, Models Unloaded').classes(
                'text-body2 text-grey-5 ellipsis'
            ).style('flex: 1 1 auto; min-width: 0;')
            progress_label = ui.label('C0/W0/p0/P0 / C0/W0/p0/P0').classes(
                'text-body2 text-right text-grey-4 q-ml-sm'
            ).style('flex: 0 0 auto; white-space: nowrap;')

        # ---- Transport controls ----
        with ui.row().classes('w-full items-center justify-center q-gutter-sm q-mt-sm'):
            ui.button('⏮', on_click=skip_start).props('flat rounded size=md color=white').tooltip('Skip Start')
            ui.button('⏹', on_click=stop).props('flat rounded size=md color=white').tooltip('Stop')
            play_button = ui.button(on_click=play_pause).props(
                'flat rounded size=md color=white icon=play_arrow'
            ).tooltip('Play / Pause')
            ui.button('📄', on_click=skip_page).props('flat rounded size=md color=white').tooltip('Next Page')
            ui.button('📖', on_click=skip_chapter).props('flat rounded size=md color=white').tooltip('Next Chapter')
            ui.button(icon='folder_open', on_click=open_files).props(
                'flat rounded size=md color=white'
            ).tooltip('Open File(s)')
            ui.button(icon='settings', on_click=open_config).props(
                'flat rounded size=md color=white'
            ).tooltip('Settings')

    ui.timer(0.5, update_progress)
    refresh_playlist_list()


# ---------------------------------------------------------------------------
# Drag-and-drop helpers
# ---------------------------------------------------------------------------

def _on_drag_over(e):
    try:
        if drop_zone:
            drop_zone.classes(add='drag-over')
    except Exception:
        pass

def _on_drag_leave(e):
    try:
        if drop_zone:
            drop_zone.classes(remove='drag-over')
    except Exception:
        pass

async def _on_drop(e):
    """Handle files dropped from Explorer onto the playlist area."""
    try:
        if drop_zone:
            drop_zone.classes(remove="drag-over")
    except Exception:
        pass

    paths = []
    try:
        args = getattr(e, "args", None) or {}
        files = args.get("files") or []
        if isinstance(files, list):
            for f in files:
                if isinstance(f, dict):
                    pth = f.get("path") or f.get("name")
                else:
                    pth = str(f)
                if pth and str(pth).lower().endswith(".pdf"):
                    paths.append(str(pth))
    except Exception as ex:
        print(f"[drop] parse error: {ex}")

    if not paths:
        try:
            result = await ui.run_javascript("window.__spp_last_drop_paths || []")
            if isinstance(result, list):
                for pth in result:
                    s = str(pth)
                    if s.lower().endswith(".pdf") and (os.path.sep in s or s.startswith("/") or os.path.isfile(s)):
                        paths.append(s)
        except Exception as ex:
            print(f"[drop] js paths error: {ex}")

    if not paths:
        await add_pdfs_to_playlist()
        return

    _add_paths_to_playlist(paths)


def _add_paths_to_playlist(paths):
    """Add one or more absolute PDF paths to the playlist; select the first added."""
    if not paths:
        return
    pl = temporary.app_state["playlist"]
    first_new_idx = None
    added = 0
    for p in paths:
        p = os.path.abspath(p)
        if not p.lower().endswith('.pdf'):
            continue
        if not os.path.isfile(p):
            continue
        if p in pl:
            if first_new_idx is None:
                first_new_idx = pl.index(p)
            continue
        pl.append(p)
        if first_new_idx is None:
            first_new_idx = len(pl) - 1
        added += 1

    if first_new_idx is not None:
        temporary.app_state["playlist_index"] = first_new_idx
        temporary.app_state["playlist_selected"] = [first_new_idx]
        # Load first added/selected into player (do not auto-start)
        utility.load_pdf(pl[first_new_idx])

    if added or first_new_idx is not None:
        utility.save_playlist()
        refresh_playlist_list()
        update_filename()
        update_progress()
        if added:
            ui.notify(f'Added {added} PDF(s)')


# ---------------------------------------------------------------------------
# Playlist list rendering & selection
# ---------------------------------------------------------------------------

def refresh_playlist_list():
    if playlist_list_container is None:
        return
    playlist_list_container.clear()
    playlist = temporary.app_state.get("playlist", [])
    playing_idx = temporary.app_state.get("playlist_index", -1)
    selected = set(temporary.app_state.get("playlist_selected") or [])

    with playlist_list_container:
        if not playlist:
            ui.label('Playlist empty — drop PDFs here or use Add').classes(
                'text-grey-6 q-pa-md text-center w-full text-caption'
            )
            return

        for i, path in enumerate(playlist):
            name = os.path.basename(path)
            is_playing = (i == playing_idx)
            is_sel = (i in selected)
            classes = 'playlist-item w-full'
            if is_sel:
                classes += ' selected'
            if is_playing:
                classes += ' playing'

            def make_handlers(index=i, p=path):
                def on_click(e=None):
                    # Ctrl/Meta multi-select if available; otherwise single select
                    mods = {}
                    try:
                        mods = (getattr(e, 'args', None) or {})
                    except Exception:
                        pass
                    ctrl = bool(mods.get('ctrlKey') or mods.get('metaKey'))
                    sel = list(temporary.app_state.get("playlist_selected") or [])
                    if ctrl:
                        if index in sel:
                            sel.remove(index)
                        else:
                            sel.append(index)
                    else:
                        sel = [index]
                    temporary.app_state["playlist_selected"] = sel
                    temporary.app_state["playlist_index"] = index
                    refresh_playlist_list()

                def on_dblclick(e=None):
                    temporary.app_state["playlist_index"] = index
                    temporary.app_state["playlist_selected"] = [index]
                    utility.load_pdf(p)
                    utility.save_playlist()
                    update_filename()
                    update_progress()
                    refresh_playlist_list()
                    speach.start_playback(
                        status_callback=_status_callback,
                        on_document_finished=_on_document_finished,
                    )

                return on_click, on_dblclick

            click, dblclick = make_handlers()
            marker = '▶ ' if is_playing else '   '
            row = ui.row().classes(classes).style('cursor: pointer;')
            with row:
                ui.label(f'{marker}{name}').classes('text-body2 ellipsis').style('max-width: 100%;')
            row.on('click', click)
            row.on('dblclick', dblclick)


# ---------------------------------------------------------------------------
# Sort / Shuffle / Clear / Remove
# ---------------------------------------------------------------------------

def cycle_sort_mode():
    mode = (temporary.app_state.get("playlist_sort_mode", 0) + 1) % len(temporary.SORT_LABELS)
    temporary.app_state["playlist_sort_mode"] = mode
    if sort_button:
        sort_button.text = temporary.SORT_LABELS[mode]
    _apply_sort()
    utility.save_playlist()
    refresh_playlist_list()
    ui.notify(f'Sort: {temporary.SORT_LABELS[mode]}')

def _apply_sort():
    pl = temporary.app_state["playlist"]
    if len(pl) < 2:
        return
    mode = temporary.app_state.get("playlist_sort_mode", 0)
    current_path = None
    idx = temporary.app_state.get("playlist_index", -1)
    if 0 <= idx < len(pl):
        current_path = pl[idx]

    def size_of(p):
        try:
            return os.path.getsize(p)
        except OSError:
            return 0

    def mtime_of(p):
        try:
            return os.path.getmtime(p)
        except OSError:
            return 0

    if mode == 0:  # AlphaNum
        pl.sort(key=lambda p: os.path.basename(p).lower())
    elif mode == 1:  # FilSiz-SmLg
        pl.sort(key=size_of)
    elif mode == 2:  # FilSiz-LgSm
        pl.sort(key=size_of, reverse=True)
    elif mode == 3:  # DateOldNew
        pl.sort(key=mtime_of)
    elif mode == 4:  # DateNewOld
        pl.sort(key=mtime_of, reverse=True)

    if current_path and current_path in pl:
        temporary.app_state["playlist_index"] = pl.index(current_path)
    # Clear multi-select after reorder (indices changed)
    temporary.app_state["playlist_selected"] = (
        [temporary.app_state["playlist_index"]]
        if temporary.app_state["playlist_index"] >= 0 else []
    )

def shuffle_playlist():
    import random
    pl = temporary.app_state["playlist"]
    if len(pl) < 2:
        return
    current_path = None
    idx = temporary.app_state.get("playlist_index", -1)
    if 0 <= idx < len(pl):
        current_path = pl[idx]
    random.shuffle(pl)
    if current_path and current_path in pl:
        temporary.app_state["playlist_index"] = pl.index(current_path)
    temporary.app_state["playlist_selected"] = (
        [temporary.app_state["playlist_index"]]
        if temporary.app_state["playlist_index"] >= 0 else []
    )
    utility.save_playlist()
    refresh_playlist_list()
    ui.notify('Playlist shuffled')

def remove_selected():
    sel = sorted(temporary.app_state.get("playlist_selected") or [], reverse=True)
    pl = temporary.app_state["playlist"]
    if not sel:
        # Fall back to current index
        idx = temporary.app_state.get("playlist_index", -1)
        if 0 <= idx < len(pl):
            sel = [idx]
    if not sel:
        ui.notify('No item selected')
        return
    for i in sel:
        if 0 <= i < len(pl):
            pl.pop(i)
    # Fix index
    if not pl:
        temporary.app_state["playlist_index"] = -1
        temporary.app_state["playlist_selected"] = []
    else:
        idx = min(temporary.app_state.get("playlist_index", 0), len(pl) - 1)
        temporary.app_state["playlist_index"] = idx
        temporary.app_state["playlist_selected"] = [idx]
    utility.save_playlist()
    refresh_playlist_list()
    ui.notify('Removed selected')

def clear_playlist():
    temporary.app_state["playlist"] = []
    temporary.app_state["playlist_index"] = -1
    temporary.app_state["playlist_selected"] = []
    utility.save_playlist()
    refresh_playlist_list()
    ui.notify('Playlist cleared')


# ---------------------------------------------------------------------------
# Add / Open File(s)
# ---------------------------------------------------------------------------

async def add_pdfs_to_playlist():
    from nicegui import run
    def get_filepaths():
        from tkinter import filedialog
        return filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
    results = await run.io_bound(get_filepaths)
    if results:
        _add_paths_to_playlist(list(results))

async def open_files():
    """Open File(s): multi-select PDFs, add to playlist, load first."""
    from nicegui import run
    def get_filepaths():
        from tkinter import filedialog
        return filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
    results = await run.io_bound(get_filepaths)
    if results:
        _add_paths_to_playlist(list(results))


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------

def skip_start():
    speach.stop_playback()
    temporary.app_state["current_page"] = 0
    temporary.app_state["current_char_index"] = 0
    update_progress()

def stop():
    speach.stop_playback()
    update_progress()

def _on_document_finished():
    """Advance to next playlist item, or unload models if list is done."""
    pl = temporary.app_state.get("playlist", [])
    idx = temporary.app_state.get("playlist_index", -1)
    next_idx = idx + 1
    if 0 <= next_idx < len(pl):
        next_path = pl[next_idx]
        temporary.app_state["playlist_index"] = next_idx
        temporary.app_state["playlist_selected"] = [next_idx]
        utility.load_pdf(next_path)
        utility.save_playlist()
        refresh_playlist_list()
        update_filename()
        update_progress()
        speach.start_playback(
            status_callback=_status_callback,
            on_document_finished=_on_document_finished,
        )
    else:
        speach.unload_models_if_idle(status_callback=_status_callback)
        update_filename()
        update_progress()

def play_pause():
    if temporary.app_state["is_playing"]:
        speach.pause_playback()
    else:
        speach.start_playback(
            status_callback=_status_callback,
            on_document_finished=_on_document_finished,
        )
    update_progress()

def skip_page():
    was_playing = temporary.app_state["is_playing"]
    speach.stop_playback()
    if temporary.app_state["current_page"] < len(temporary.app_state["text_data"]) - 1:
        temporary.app_state["current_page"] += 1
    temporary.app_state["current_char_index"] = 0
    if was_playing:
        speach.start_playback(
            status_callback=_status_callback,
            on_document_finished=_on_document_finished,
        )

def skip_chapter():
    was_playing = temporary.app_state["is_playing"]
    speach.stop_playback()
    current = temporary.app_state["current_page"]
    for i in range(current + 1, len(temporary.app_state["text_data"])):
        if temporary.app_state["text_data"][i]["is_chapter"]:
            temporary.app_state["current_page"] = i
            temporary.app_state["current_char_index"] = 0
            break
    else:
        temporary.app_state["current_page"] = max(0, len(temporary.app_state["text_data"]) - 1)
        temporary.app_state["current_char_index"] = 0
    if was_playing:
        speach.start_playback(
            status_callback=_status_callback,
            on_document_finished=_on_document_finished,
        )


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------

def open_config():
    with ui.dialog().props('persistent').style('width: 320px') as dialog, \
         ui.card().classes('bg-grey-10 text-white q-pa-md').style('border-radius: 10px; width: 100%'):
        ui.label("Configuration").classes('text-h6 text-center w-full')
        with ui.row().classes('w-full items-center q-mt-md no-wrap'):
            ui.label("Voice:").classes('text-weight-bold').style('min-width: 50px')
            voice_options = ['af_heart', 'af_bella', 'af_nicole', 'am_adam', 'am_michael']
            voice_select = ui.select(voice_options, value=temporary.app_state["voice"]).classes('w-full bg-grey-9')
        with ui.row().classes('w-full items-center q-mt-sm no-wrap'):
            ui.label("Speed:").classes('text-weight-bold').style('min-width: 50px')
            speed_options = ['0.5x', '0.75x', '1.0x', '1.25x', '1.5x', '2.0x']
            speed_select = ui.select(
                speed_options, value=f'{temporary.app_state["speed"]}x'
            ).classes('w-full bg-grey-9')
        with ui.row().classes('w-full justify-end q-mt-md'):
            ui.button('Cancel', on_click=dialog.close).props('flat color=white')
            ui.button(
                'Save',
                on_click=lambda: save_config(voice_select.value, speed_select.value, dialog)
            ).props('color=primary')
        dialog.open()

def save_config(voice, speed_str, dialog):
    temporary.app_state["voice"] = voice
    temporary.app_state["speed"] = float(speed_str.replace('x', ''))
    utility.save_program()
    dialog.close()
