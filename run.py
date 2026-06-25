import os
import sys
import json
import logging
import threading
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("Run")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    config = load_config()

    logger.info("Starting Live2D Display...")
    from live2d_display import start_display, set_widget
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = start_display(config)
    set_widget(widget)

    import mcp_server
    mcp_server.set_widget(widget)

    logger.info(f"Starting MCP Streamable HTTP server on {config.get('mcp_host', '127.0.0.1')}:{config.get('mcp_port', 8765)}")

    t = threading.Thread(target=mcp_server.run_mcp_server, daemon=True)
    t.start()

    import web_ui
    web_ui.set_companion(widget)
    web_port = config.get("web_port", 8766)
    wt = threading.Thread(target=web_ui.run_web_ui, daemon=True)
    wt.start()

    # Microphone reaction: when speech is recognized, react with emotion
    import stt
    import phrases
    import random
    from PyQt6.QtCore import QMetaObject, Qt

    def on_speech(text):
        try:
            from live2d_display import state
            emotions = ["joy", "surprise", "amusement", "admiration", "curiosity"]
            state.set_emotion(random.choice(emotions))
        except Exception:
            pass
        try:
            import urllib.request as ur
            import json as j
            payload = j.dumps({
                "model": "google_gemma-3-1b-it",
                "messages": [
                    {"role": "system", "content": "You are a cute anime girl. Answer briefly in Russian, 1-2 sentences. Be playful and kind. Keep answers very short."},
                    {"role": "user", "content": text}
                ],
                "max_tokens": 100,
                "temperature": 0.7,
                "stream": False
            })
            req = ur.Request("http://localhost:11434/v1/chat/completions", data=payload.encode(), method="POST")
            req.add_header("Content-Type", "application/json")
            resp = ur.urlopen(req, timeout=15)
            data = j.loads(resp.read())
            reply = data["choices"][0]["message"]["content"]
            import tts
            tts.speak(reply)
        except Exception:
            pass

    stt.set_transcript_cb(on_speech)

    addr = f"{config.get('mcp_host', '127.0.0.1')}:{config.get('mcp_port', 8765)}"
    web_addr = f"{config.get('mcp_host', '127.0.0.1')}:{web_port}"
    print("=" * 60)
    print(f"  MCP Server: http://{addr}/mcp")
    print(f"  Web UI:     http://{web_addr}")
    print("=" * 60)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
