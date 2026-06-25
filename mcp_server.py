import os
import sys
import json
import logging
import asyncio
import time
import threading

from mcp.server.fastmcp import FastMCP

# Monkey-patch: allow requests without Accept header
import mcp.server.streamable_http as _sh
_orig_check = _sh.StreamableHTTPServerTransport._check_accept_headers
def _patched_check(self, request):
    has_json, has_sse = _orig_check(self, request)
    accept = request.headers.get("accept", "")
    if not accept:
        has_json = True
    return has_json, has_sse
_sh.StreamableHTTPServerTransport._check_accept_headers = _patched_check

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("MCP-Server")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()

mcp = FastMCP(
    "Live2D Companion",
    instructions="Control a Live2D desktop companion character: emotions, mouth position, eye tracking, visibility, window position, and TTS speech synthesis with lip-sync.",
    host=config.get("mcp_host", "127.0.0.1"),
    port=config.get("mcp_port", 8765),
    json_response=True,
    stateless_http=True
)

widget_ref = None


def set_widget(w):
    global widget_ref
    widget_ref = w


def get_model():
    if widget_ref is None:
        return None
    return widget_ref.live2d_model


@mcp.tool()
def switch_model(model_name: str) -> str:
    """Switch between character models: 'hiyori' (Live2D) or 'nagatoro_sprite' (sprite)."""
    if widget_ref is None:
        return "Error: Widget not initialized"
    try:
        return widget_ref.switch_model(model_name)
    except Exception as e:
        return f"Error switching model: {e}"


@mcp.tool()
def set_emotion(emotion: str) -> str:
    """Set the character's expression/emotion. Check list_available_emotions() for valid values."""
    if not _check_emotion_mcp():
        import tts
        import phrases
        phrases.speak("mcp_emotion_refusal")
        return "Error: MCP emotion control is disabled in web admin"
    from live2d_display import state
    state.set_emotion(emotion)
    return f"Emotion set to: {emotion}"


@mcp.tool()
def set_mouth_open(value: float) -> str:
    """Set mouth opening for lip-sync. Value: 0.0 (closed) to 1.0 (open)."""
    from live2d_display import state
    state.set_mouth_open(value)
    return f"Mouth set to: {value}"


@mcp.tool()
def play_motion(group: str, no: int = 0, priority: int = 2) -> str:
    """Play a motion animation on the character.
    
    Priority: 0=IDLE, 1=NORMAL, 2=FORCE
    Use priority=2 to interrupt current motion.
    """
    from live2d_display import state
    state.play_motion(group, no, priority)
    return f"Playing motion: group={group}, no={no}, priority={priority}"


@mcp.tool()
def stop_all_motions() -> str:
    """Stop all currently playing motions on the character."""
    model = get_model()
    if model:
        try:
            model.StopAllMotions()
            return "All motions stopped"
        except Exception as e:
            return f"Error: {e}"
    return "No model loaded"


@mcp.tool()
def list_motion_groups() -> str:
    """List available motion groups loaded in the current model."""
    model = get_model()
    if model:
        try:
            groups = model.GetMotionGroups()
            return json.dumps(groups)
        except Exception as e:
            return json.dumps({"error": str(e)})
    return "No model loaded"


@mcp.tool()
def set_eye_position(x: float, y: float) -> str:
    """Set eye gaze direction. Values: -1.0 to 1.0 for X and Y axes."""
    from live2d_display import state
    state.set_eye_pos(x, y)
    return f"Eyes set to: ({x}, {y})"


@mcp.tool()
def set_parameter(name: str, value: float) -> str:
    """Set any Live2D model parameter by name and value.
    
    Common parameters: ParamAngleX, ParamAngleY, ParamEyeBallX, ParamEyeBallY,
    ParamMouthOpenY, ParamBodyAngleX, ParamBodyAngleY, ParamBodyAngleZ,
    ParamEyeLOpen, ParamEyeROpen, ParamArmLA, ParamArmRA
    """
    from live2d_display import state
    state.set_param(name, value)
    return f"Parameter {name} set to: {value}"


def _check_hide_mcp() -> bool:
    import alarm_timer
    return alarm_timer.get_settings().get("hide_mcp_enabled", True)

def _check_control_mcp() -> bool:
    import alarm_timer
    return alarm_timer.get_settings().get("control_mcp_enabled", True)

def _check_emotion_mcp() -> bool:
    import alarm_timer
    return alarm_timer.get_settings().get("emotion_mcp_enabled", True)


@mcp.tool()
def show() -> str:
    """Show the character window on desktop."""
    if not _check_hide_mcp():
        if widget_ref:
            widget_ref._start_trapped_animation()
        else:
            import phrases
            phrases.speak("mcp_show_refusal")
        return "Error: MCP hide/show is disabled in web admin"
    from live2d_display import state
    state.set_visible(True)
    return "Character shown"


@mcp.tool()
def hide() -> str:
    """Hide the character window from desktop."""
    if not _check_hide_mcp():
        import phrases
        phrases.speak("mcp_hide_refusal")
        return "Error: MCP hide/show is disabled in web admin"
    if widget_ref:
        widget_ref._start_hide_animation()
    return "Character hiding"


@mcp.tool()
def move_window(x: int, y: int) -> str:
    """Move the character window to specified screen coordinates."""
    if not _check_control_mcp():
        import tts
        import phrases; phrases.speak("mcp_control_refusal")
        return "Error: MCP control is disabled in web admin"
    if widget_ref:
        try:
            widget_ref.move(x, y)
            return f"Window moved to: ({x}, {y})"
        except Exception as e:
            return f"Error: {e}"
    return "Widget not initialized"


@mcp.tool()
def resize_window(width: int, height: int) -> str:
    """Resize the character window. Min: 200x300, Max: 1200x1800."""
    if not _check_control_mcp():
        import tts
        import phrases; phrases.speak("mcp_control_refusal")
        return "Error: MCP control is disabled in web admin"
    w = max(200, min(1200, width))
    h = max(300, min(1800, height))
    if widget_ref:
        try:
            widget_ref.resize(w, h)
            return f"Window resized to: ({w}, {h})"
        except Exception as e:
            return f"Error: {e}"
    return "Widget not initialized"


@mcp.tool()
def center_window() -> str:
    """Center the character window on the screen."""
    if not _check_control_mcp():
        import tts
        import phrases; phrases.speak("mcp_control_refusal")
        return "Error: MCP control is disabled in web admin"
    if widget_ref:
        try:
            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            widget_ref.move(
                screen.width() // 2 - widget_ref.width() // 2,
                screen.height() // 2 - widget_ref.height() // 2
            )
            return "Window centered"
        except Exception as e:
            return f"Error: {e}"
    return "Widget not initialized"


@mcp.tool()
def get_status() -> str:
    """Get current character and window status."""
    from live2d_display import state
    info = {
        "emotion": state.get_emotion(),
        "mouth_open": state.get_mouth_open(),
        "eye_x": state.get_eye_pos()[0],
        "eye_y": state.get_eye_pos()[1],
        "visible": state.is_visible(),
        "render_mode": state.get_render_mode(),
        "model_name": state.get_model_name(),
    }
    if widget_ref:
        try:
            g = widget_ref.geometry()
            info["window"] = {"x": g.x(), "y": g.y(), "width": g.width(), "height": g.height()}
        except Exception:
            pass
    return json.dumps(info, indent=2)


@mcp.tool()
def list_available_emotions() -> str:
    """List all available emotion/expression names for the current model."""
    if not _check_emotion_mcp():
        import phrases
        phrases.speak("mcp_emotion_refusal")
        return "Error: MCP emotion control is disabled in web admin"
    from live2d_display import state, SPRITE_MAP
    if state.get_render_mode() == "sprite":
        return json.dumps(list(SPRITE_MAP.keys()))
    model = get_model()
    if model:
        try:
            ids = model.GetExpressionIds()
            if ids:
                return json.dumps(ids)
        except Exception:
            pass
    return json.dumps([])


@mcp.tool()
async def speak(text: str, voice: str = "") -> str:
    """Make the character speak text using TTS (Russian voices available).
    
    The character's mouth will animate in sync with the speech.
    Use list_voices() to see all available voices.
    XTTS voices: xtts:Claribel Dervla, xtts:Daisy Studious, etc. (58 total)
    Piper voices: ru_RU-irina-medium, ru_RU-denis-medium, ru_RU-ruslan-medium
    """
    import tts
    return await asyncio.to_thread(tts.speak, text, voice or None)


@mcp.tool()
def list_voices() -> str:
    """List available TTS voices for speech synthesis."""
    import tts
    return json.dumps(tts.list_voices(), indent=2)


@mcp.tool()
def stop_speaking() -> str:
    """Stop current speech playback immediately."""
    import tts
    tts.stop_speaking()
    return "Speech stopped"


@mcp.tool()
def list_tracks() -> str:
    """List available MP3 tracks from the mp3 folder."""
    import music_player
    tracks = music_player.list_tracks()
    return json.dumps(tracks, indent=2, ensure_ascii=False)


def _music_mcp_allowed() -> bool:
    import alarm_timer
    return alarm_timer.get_settings().get("music_mcp_enabled", True)


@mcp.tool()
def play_track(name: str) -> str:
    """Play an MP3 track by filename."""
    import music_player
    import tts
    if not _music_mcp_allowed():
        import phrases; phrases.speak("mcp_music_refusal")
        return "Error: MCP music control is disabled in web admin"
    import phrases; phrases.speak("mcp_music_play")
    threading.Thread(target=lambda: (time.sleep(2.5), music_player.play_track(name)), daemon=True).start()
    return f"Playing: {name}"


@mcp.tool()
def stop_music() -> str:
    """Stop current music playback."""
    import music_player
    import tts
    if not _music_mcp_allowed():
        import phrases; phrases.speak("mcp_music_refusal")
        return "Error: MCP music control is disabled in web admin"
    import phrases; phrases.speak("mcp_music_stop")
    threading.Thread(target=lambda: (time.sleep(2.5), music_player.stop()), daemon=True).start()
    return "Music stopped"


@mcp.tool()
def next_track() -> str:
    """Skip to next track."""
    import music_player
    import tts
    if not _music_mcp_allowed():
        import phrases; phrases.speak("mcp_music_refusal")
        return "Error: MCP music control is disabled in web admin"
    import phrases; phrases.speak("mcp_music_switch")
    threading.Thread(target=lambda: (time.sleep(2.5), music_player.play_next()), daemon=True).start()
    return "Next track"


@mcp.tool()
def prev_track() -> str:
    """Go to previous track."""
    import music_player
    import tts
    if not _music_mcp_allowed():
        import phrases; phrases.speak("mcp_music_refusal")
        return "Error: MCP music control is disabled in web admin"
    import phrases; phrases.speak("mcp_music_switch")
    threading.Thread(target=lambda: (time.sleep(2.5), music_player.play_prev()), daemon=True).start()
    return "Previous track"


@mcp.tool()
def play_random_track() -> str:
    """Play a random track."""
    import music_player
    import tts
    if not _music_mcp_allowed():
        import phrases; phrases.speak("mcp_music_refusal")
        return "Error: MCP music control is disabled in web admin"
    import phrases; phrases.speak("mcp_music_play")
    threading.Thread(target=lambda: (time.sleep(2.5), music_player.play_random()), daemon=True).start()
    return "Playing random track"


@mcp.tool()
def set_loop(loop: bool) -> str:
    """Enable or disable loop for current track."""
    import music_player
    music_player.set_loop(loop)
    return f"Loop: {loop}"


@mcp.tool()
def set_autoplay(autoplay: bool) -> str:
    """Enable or disable autoplay (play next track automatically)."""
    import music_player
    music_player.set_autoplay(autoplay)
    return f"Autoplay: {autoplay}"


@mcp.tool()
def set_music_volume(volume: float) -> str:
    """Set music volume (0.0 to 1.0)."""
    import music_player
    music_player.set_volume(int(volume * 1000))
    return f"Volume: {volume}"


@mcp.tool()
def set_mcp_music(enabled: bool = True, track: str = "") -> str:
    """Let the model control music playback. Pass enabled=true to allow, false to deny. Optionally specify a track to play."""
    import alarm_timer
    import music_player
    import tts
    cfg = alarm_timer.get_settings()
    if not cfg.get("music_mcp_enabled", True):
        import phrases; phrases.speak("mcp_music_refusal")
        return "Error: MCP music control is disabled in web admin"
    alarm_timer.save_settings({"music_mcp_enabled": enabled})
    if enabled and track:
        import phrases; phrases.speak("mcp_music_play")
        threading.Thread(target=lambda: (time.sleep(2.5), music_player.play_track(track)), daemon=True).start()
        return f"MCP Music: enabled={enabled}, track={track}"
    elif enabled:
        import phrases; phrases.speak("mcp_music_play")
        threading.Thread(target=lambda: (time.sleep(2.5), music_player.play_random()), daemon=True).start()
        return f"MCP Music: enabled={enabled}, track=random"
    else:
        import phrases; phrases.speak("mcp_music_stop")
        threading.Thread(target=lambda: (time.sleep(2.5), music_player.stop()), daemon=True).start()
        return f"MCP Music: enabled={enabled}, track={track or 'random'}"


@mcp.tool()
def set_alarm_text(time: str = "", text: str = "", enabled: bool = None) -> str:
    """Set MCP alarm time (HH:MM) and text. Pass enabled=true/false to toggle. Leave text/time empty to keep current."""
    import alarm_timer
    import tts
    cfg = alarm_timer.get_settings()
    if not cfg.get("alarm_mcp_enabled", True):
        import phrases; phrases.speak("mcp_alarm_refusal")
        return "Error: MCP alarm setting is disabled in web admin"
    data = {}
    if text:
        data["alarm_mcp_text"] = text
    if time:
        data["alarm_mcp_time"] = time
    if enabled is not None:
        data["alarm_mcp_enabled"] = enabled
    alarm_timer.save_settings(data)
    if enabled is not False and time:
        import phrases
        phrases.speak("mcp_alarm_set", time=time)
    return f"MCP Alarm: time={time or 'unchanged'}, text={text or 'unchanged'}, enabled={enabled}"


@mcp.tool()
def set_timer(minutes: float = 5, text: str = "", enabled: bool = None) -> str:
    """Set MCP timer duration in minutes and text. Starts the timer immediately.
    Pass enabled=false to stop. Leave text empty to keep current."""
    import alarm_timer
    import tts
    cfg = alarm_timer.get_settings()
    if not cfg.get("timer_mcp_enabled", True):
        import phrases; phrases.speak("mcp_timer_refusal")
        return "Error: MCP timer setting is disabled in web admin"
    duration = max(1, int(minutes * 60))
    data = {"timer_mcp_duration": duration}
    if text:
        data["timer_mcp_text"] = text
    if enabled is not False:
        data["timer_mcp_enabled"] = True
        alarm_timer.start_mcp_timer(duration)
    else:
        data["timer_mcp_enabled"] = False
        alarm_timer.stop_mcp_timer()
    alarm_timer.save_settings(data)
    if enabled is not False:
        sec = duration
        if sec >= 60:
            mins = sec // 60
            sec_rem = sec % 60
            import phrases
            if sec_rem:
                phrases.speak("mcp_timer_set_mins_secs", mins=mins, secs=sec_rem)
            else:
                phrases.speak("mcp_timer_set_mins", mins=mins)
        else:
            import phrases
            phrases.speak("mcp_timer_set_secs", secs=sec)
    return f"MCP Timer: {minutes}min, text={text or 'unchanged'}"


@mcp.tool()
def get_alarm_timer_status() -> str:
    """Get current alarm and timer settings and status."""
    import alarm_timer
    s = alarm_timer.get_settings()
    return json.dumps(s, indent=2, ensure_ascii=False)


@mcp.tool()
def take_screenshot(delay_ms: int = 0) -> str:
    """Take a desktop screenshot. Returns base64 PNG image data. Optionally wait delay_ms before capture. The character will react with emotion and speech when the screenshot is taken."""
    import json
    import tts
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not cfg.get("screenshot_mcp_enabled", False):
            import phrases; phrases.speak("mcp_screenshot_refusal")
            return "Error: MCP screenshot is disabled in web admin"
    except Exception:
        return "Error: Cannot read config"
    w = widget_ref
    if w is None:
        return "Error: Widget not available"
    try:
        b64 = w.take_screenshot_threadsafe(delay_ms)
        if b64:
            return b64
        return "Error: Screenshot failed"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def query_documents(query: str, limit: int = 10) -> str:
    """Search ingested documents for relevant content using semantic search (RAG). Returns text chunks with relevance scores.
    
    Query searches across previously ingested files in the documents directory.
    Results include file path, chunk index, text preview, and relevance score (0-1).
    """
    try:
        from rag.rag_engine import query_documents as _query
        result = _query(query, limit)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def ingest_file(file_path: str) -> str:
    """Ingest a file into the RAG index for semantic search. Supports TXT, MD, PDF, and code files.
    
    The file must be under the project docs directory or the MCP directory.
    After ingestion, the content becomes searchable via query_documents().
    """
    try:
        from rag.rag_engine import ingest_file as _ingest
        result = _ingest(file_path)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_documents() -> str:
    """List all files currently indexed in the RAG system with their chunk counts."""
    try:
        from rag.rag_engine import list_files as _list
        result = _list()
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def rag_status() -> str:
    """Get RAG system status: total chunks, indexed files, and docs directory location."""
    try:
        from rag.rag_engine import status as _status
        result = _status()
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


def run_mcp_server():
    """Run MCP Streamable HTTP server (call from a background thread)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(mcp.run_streamable_http_async())


async def run_mcp_server_stdio():
    """Run MCP server with stdio transport (for opencode local mode)."""
    await mcp.run_stdio_async()


if __name__ == "__main__":
    if "--stdio" in sys.argv:
        asyncio.run(run_mcp_server_stdio())
    else:
        run_mcp_server()
