# web_ui.py - Web Interface for MCP Live2D Control

import asyncio
import json
import logging
import os
import sys
import threading
import time
import platform

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Companion reference (set by run.py)
_companion = None

def set_companion(companion):
    global _companion
    _companion = companion

def get_companion():
    return _companion

import tts
import music_player
import stt
import phrases

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

logger = logging.getLogger('WebUI')
HOST = '0.0.0.0'
PORT = 8766
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

SCRIPT_JS = open(os.path.join(BASE_DIR, 'ui.js'), 'r', encoding='utf-8').read()

HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MCP Live2D Control</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#1a1a2e;color:#eee;display:flex;justify-content:center;align-items:center;min-height:100vh}
.card{background:#16213e;border-radius:16px;padding:32px;width:580px;max-width:95vw;box-shadow:0 8px 32px rgba(0,0,0,.5)}
h1{font-size:1.4rem;margin-bottom:16px;text-align:center;color:#e94560}
.tabs{display:flex;flex-wrap:wrap;gap:3px;margin-bottom:16px}
.tab{padding:6px 10px;border:none;border-radius:6px 6px 0 0;cursor:pointer;background:#0f3460;color:#888;font-size:.78rem;flex:0 0 auto;transition:.2s}
.tab.active{background:#e94560;color:#fff}
.panel{display:none}
.panel.active{display:block}
label{display:block;font-size:.85rem;margin-bottom:4px;color:#aaa}
select,input[type=range],textarea{width:100%;padding:10px;border:1px solid #333;border-radius:8px;background:#0f3460;color:#eee;font-size:.95rem;margin-bottom:12px}
textarea{resize:vertical;min-height:60px;font-family:inherit}
.row{display:flex;gap:8px;align-items:center;margin-bottom:12px}
.btn{padding:8px 16px;border:none;border-radius:8px;font-size:.85rem;cursor:pointer;transition:.2s}
.btn.primary{background:#e94560;color:#fff}
.btn.primary:hover{background:#d63851}
.btn.secondary{background:#333;color:#eee}
.btn.secondary:hover{background:#444}
.btn.danger{background:#555;color:#eee}
.btn.danger:hover{background:#666}
.btn.small{padding:4px 10px;font-size:.75rem}
.btn.green{background:#2d8a4e;color:#fff}
.btn.green:hover{background:#24703f}
.status{text-align:center;font-size:.75rem;padding:6px;border-radius:6px;margin-top:8px}
.status.ok{background:#1a3a2e;color:#4ade80}
.status.err{background:#3a1a1e;color:#f87171}
.toggle-wrap{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.toggle{position:relative;width:48px;height:26px;cursor:pointer}
.toggle input{display:none}
.toggle .slider{position:absolute;inset:0;background:#555;border-radius:13px;transition:.3s}
.toggle .slider::before{content:'';position:absolute;width:20px;height:20px;left:3px;bottom:3px;background:#fff;border-radius:50%;transition:.3s}
.toggle input:checked+.slider{background:#e94560}
.toggle input:checked+.slider::before{transform:translateX(22px)}
.game-row{display:flex;gap:8px;align-items:center;margin-bottom:6px}
.game-row input{flex:1;padding:6px 8px;border:1px solid #333;border-radius:6px;background:#0f3460;color:#eee;font-size:.8rem}
.game-row .gicon{font-size:1.2rem;width:28px;text-align:center}
.mtrack{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;margin-bottom:4px;cursor:pointer}
.mtrack:hover{background:#0f3460}
.mtrack.playing{background:#2d8a4e}
hr{border:none;border-top:1px solid #333;margin:12px 0}
</style>
</head>
<body>
<div class="card">
<h1>&#128172; Live2D Control</h1>



<div class="tabs" id="tabsContainer">
<button class="tab" onclick="showTab('tts',this)">&#128266; TTS</button>
<button class="tab" onclick="showTab('games',this)">&#127918; Games</button>
<button class="tab" onclick="showTab('music',this)">&#127925; Music</button>
<button class="tab" onclick="showTab('live',this)">&#127922; Live</button>
<button class="tab" onclick="showTab('alarm',this)">&#9200; Alarm</button>
<button class="tab" onclick="showTab('timer',this)">&#9201; Timer</button>
<button class="tab" onclick="showTab('screenshot',this)">&#128248; Screenshot</button>
<button class="tab" onclick="showTab('random',this)">&#127922; Random</button>
<button class="tab active" onclick="showTab('mic',this)">&#127908; Mic</button>
<button class="tab" onclick="showTab('llm',this)">&#129302; LLM</button>
<button class="tab" onclick="showTab('character',this)">&#128100; Character</button>
<button class="tab" onclick="showTab('model',this)">&#128187; Model</button>
<button class="tab" onclick="showTab('mcp',this)">&#9881; MCP</button>
<button class="tab" onclick="showTab('system',this)">&#128295; System</button>
</div>

<div id="panel-tts" class="panel">
<div class="toggle-wrap">
<label class="toggle">
<input type="checkbox" id="enabled" checked onchange="toggleEnabled()">
<span class="slider"></span>
</label>
<span id="enabledLabel">Включено</span>
</div>
<label for="ttsEngine">Движок TTS</label>
<select id="ttsEngine" onchange="onEngineChange()"></select>
<label for="voice">Голос/Модель</label>
<select id="voice"></select>
<label for="volume">Громкость: <span id="volLabel">100%</span></label>
<input type="range" id="volume" min="0" max="100" value="100" oninput="setVolume(this.value)">
<label for="speed">Скорость: <span id="speedLabel">1.0x</span></label>
<input type="range" id="speed" min="25" max="300" value="100" oninput="setSpeed(this.value)">
<label for="outputDevice">Устройство вывода</label>
<select id="outputDevice"><option value="">(по умолчанию)</option></select>
<button class="btn secondary small" onclick="saveDefault()">&#128190; Сохранить настройки</button>
<hr>
<label for="text">Текст</label>
<textarea id="text" placeholder="Введите текст...">Привет! Я твой виртуальный компаньон.</textarea>
<div class="row">
<button class="btn primary" id="speakBtn" onclick="speak()">&#9654; Сказать</button>
<button class="btn danger" id="stopBtn" onclick="stopSpeak()">&#9632; Стоп</button>
</div>
</div>

<div id="panel-games" class="panel">
<label>Редактирование игр</label>
<div id="gameList"></div>
<hr>
<label>Общий текст приглашения</label>
<textarea id="gameInviteText" placeholder="По умолчанию: Давай поиграем!"></textarea>
<button class="btn secondary small" onclick="saveGameSettings()">&#128190; Сохранить все</button>
</div>

<div id="panel-music" class="panel">
<div class="row">
<button class="btn primary" onclick="musicPlay()">&#9654; Play</button>
<button class="btn danger" onclick="musicStop()">&#9632; Stop</button>
<button class="btn secondary" onclick="musicPrev()">&#9664; Prev</button>
<button class="btn secondary" onclick="musicNext()">&#9654; Next</button>
</div>
<div class="row">
<button class="btn secondary small" onclick="musicRandom()">&#128256; Random</button>
<button class="btn secondary small" id="loopBtn" onclick="toggleLoop()">&#128257; Loop</button>
<button class="btn secondary small" id="autoBtn" onclick="toggleAutoplay()">&#9654;&#9654; Autoplay</button>
</div>
<label for="musicVol">Громкость музыки: <span id="musicVolLabel">50%</span></label>
<input type="range" id="musicVol" min="0" max="100" value="50" oninput="setMusicVolume(this.value)">
<button class="btn secondary small" onclick="saveMusicVol()">&#128190; Сохранить громкость</button>
<div id="musicStatus" class="status ok">&#9679; Готов</div>
<hr>
<label>Треки</label>
<div id="trackList"></div>
<button class="btn secondary small" onclick="loadTracks()">&#128260; Обновить список</button>
<hr>
</div>

<div id="panel-live" class="panel">
<label for="liveInterval">Интервал (сек)</label>
<input type="number" id="liveInterval" min="5" max="300" value="30">
<label for="livePhrases">Фразы (по одной на строке)</label>
<textarea id="livePhrases" rows="5" placeholder="Привет!..."></textarea>
<button class="btn primary small" onclick="saveLive()">&#128190; Сохранить</button>
<div id="liveStatus" class="status ok">&#9679; Готов</div>
</div>

<div id="panel-alarm" class="panel">
<div class="toggle-wrap">
<label class="toggle">
<input type="checkbox" id="alarmEnabled" onchange="saveAlarmTimer()">
<span class="slider"></span>
</label>
<span id="alarmEnabledLabel">Выключено</span>
</div>
<label for="alarmTime">Время</label>
<input type="time" id="alarmTime" value="08:00">
<label for="alarmText">Текст</label>
<textarea id="alarmText" rows="2" placeholder="Текст..."></textarea>
<label for="alarmSong">Песня (оставь пусто, если не нужно)</label>
<select id="alarmSong"><option value="">(без песни)</option></select>
<label for="alarmRepeat">Повторов</label>
<input type="number" id="alarmRepeat" min="0" value="1" style="width:80px"> <small>(0 = безлимит)</small>
<label for="alarmReplay">Интервал повтора текста (сек, 0 = выкл)</label>
<input type="number" id="alarmReplay" min="0" value="0" style="width:80px">
<label for="alarmStopAfter">Авто-выкл через (сек, 0 = не выключать)</label>
<input type="number" id="alarmStopAfter" min="0" value="0" style="width:80px">
<div class="row">
<label class="toggle">
<input type="checkbox" id="alarmAutoRepeat" onchange="saveAlarmTimer()">
<span class="slider"></span>
</label>
<span id="alarmAutoLabel">Автоповтор</span>
</div>
<button class="btn primary small" onclick="saveAlarmTimer()">&#128190; Сохранить</button>
<div id="alarmStatus" class="status ok">&#9679; Готов</div>
</div>

<div id="panel-timer" class="panel">
<div class="toggle-wrap">
<label class="toggle">
<input type="checkbox" id="timerEnabled" onchange="saveAlarmTimer()">
<span class="slider"></span>
</label>
<span id="timerEnabledLabel">Выключено</span>
</div>
<label for="timerDuration">Длительность (сек)</label>
<input type="number" id="timerDuration" min="5" value="300">
<label for="timerText">Текст</label>
<textarea id="timerText" rows="2" placeholder="Текст..."></textarea>
<label for="timerSong">Песня (оставь пусто, если не нужно)</label>
<select id="timerSong"><option value="">(без песни)</option></select>
<label for="timerRepeat">Повторов</label>
<input type="number" id="timerRepeat" min="0" value="1" style="width:80px"> <small>(0 = безлимит)</small>
<label for="timerReplay">Интервал повтора текста (сек, 0 = выкл)</label>
<input type="number" id="timerReplay" min="0" value="0" style="width:80px">
<label for="timerStopAfter">Авто-выкл через (сек, 0 = не выключать)</label>
<input type="number" id="timerStopAfter" min="0" value="0" style="width:80px">
<div class="row">
<label class="toggle">
<input type="checkbox" id="timerAutoRepeat" onchange="saveAlarmTimer()">
<span class="slider"></span>
</label>
<span id="timerAutoLabel">Автоповтор</span>
</div>
<button class="btn primary small" onclick="saveAlarmTimer()">&#128190; Сохранить</button>
<div id="timerStatus" class="status ok">&#9679; Готов</div>
</div>

<div id="panel-screenshot" class="panel">
<div class="toggle-wrap">
<label class="toggle">
<input type="checkbox" id="screenshotEnabled" onchange="saveScreenshotSettings()">
<span class="slider"></span>
</label>
<span id="screenshotEnabledLabel">Выключено</span>
</div>
<label for="screenshotDelay">Задержка (мс)</label>
<input type="number" id="screenshotDelay" min="0" max="10000" value="500">
<div class="row">
<button class="btn primary" onclick="testScreenshot()">&#128247; Тест</button>
<button class="btn danger" onclick="clearScreenshot()">&#128465; Очистить</button>
<button class="btn secondary" onclick="saveScreenshotSettings()">&#128190; Сохранить</button>
</div>
<div id="screenshotPreview" style="display:none;margin-top:12px;text-align:center">
<img id="screenshotImg" style="max-width:100%;border-radius:8px;border:1px solid #555">
</div>
<div id="screenshotStatus" class="status ok">&#9679; Готов</div>
</div>

<div id="panel-random" class="panel">
<h3>🎲 Случайные фразы при кликах</h3>
<p style="color:#aaa;font-size:.85rem;margin-bottom:12px">Фразы из этого списка будут случайно выбираться при клике по персонажу (когда включён режим Random Clicks в меню).</p>
<label for="randomInterval">Интервал (сек)</label>
<input type="number" id="randomInterval" min="1" max="300" value="10">
<label for="randomPhrases">Фразы (по одной на строке)</label>
<textarea id="randomPhrases" rows="8" placeholder="привет!..."></textarea>
<div class="row">
<button class="btn primary" onclick="saveRandomPhrases()">&#128190; Сохранить</button>
<button class="btn secondary" onclick="loadRandomPhrases()">&#128260; Обновить</button>
</div>
<div id="randomStatus" class="status ok">&#9679; Готов</div>
</div>

<div id="panel-mic" class="panel">
<h3>🎤 Микрофон (STT)</h3>
<div class="toggle-wrap">
<label class="toggle">
<input type="checkbox" id="micEnabled" onchange="toggleMic()">
<span class="slider"></span>
</label>
<span id="micEnabledLabel">Выключено</span>
</div>
<label for="micLang">Язык распознавания</label>
<select id="micLang">
<option value="ru">Русский</option>
<option value="en">English</option>
<option value="auto">Auto</option>
</select>
<label for="micModel">Модель Whisper</label>
<select id="micModel">
<option value="tiny">Tiny</option>
<option value="base">Base</option>
<option value="small">Small</option>
<option value="medium">Medium</option>
</select>
<label for="micDevice">Устройство ввода</label>
<select id="micDevice"><option value="">(по умолчанию)</option></select>
<label for="micSensitivity">Чувствительность (VAD): <span id="micSensitivityLabel">0.050</span></label>
<input type="range" id="micSensitivity" min="0" max="100" value="5" oninput="setMicSensitivity(this.value)">
<label for="micTranscript">Распознанный текст</label>
<textarea id="micTranscript" rows="4" readonly placeholder="Пока ничего..."></textarea>
<div class="row">
<button class="btn primary" onclick="startMic()" id="micStartBtn">▶ Старт</button>
<button class="btn danger" onclick="stopMic()" id="micStopBtn" disabled>⏹ Стоп</button>
<button class="btn secondary" onclick="testMic()">🎤 Тест микрофона</button>
<button class="btn secondary" onclick="saveMicSettings()">💾 Сохранить</button>
</div>
<div id="micStatus" class="status ok">● Готов</div>
</div>

<div id="panel-llm" class="panel">
<h3>🤖 LLM (Языковая модель)</h3>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="llmEnabled" onchange="toggleLlmGlobal(this.checked)"><span class="slider"></span></label>
<span id="llmEnabledLabel">LLM: Выключено</span>
</div>
<p style="color:#aaa;font-size:.85rem;margin:8px 0">Выберите провайдера (только один активен)</p>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="llmOllamaEnabled" onchange="toggleLlm('ollama',this.checked)"><span class="slider"></span></label>
<span id="llmOllamaLabel">🦙 Ollama</span>
</div>
<div id="llmOllamaFields" style="display:none;margin:0 0 8px 24px">
<label for="ollamaHost">Хост</label>
<input type="text" id="ollamaHost" value="localhost" placeholder="localhost">
<label for="ollamaPort">Порт</label>
<input type="number" id="ollamaPort" value="11434" min="1" max="65535">
<label for="ollamaModel">Модель</label>
<select id="ollamaModel"></select>
</div>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="llmLmstudioEnabled" onchange="toggleLlm('lmstudio',this.checked)"><span class="slider"></span></label>
<span id="llmLmstudioLabel">💻 LM Studio</span>
</div>
<div id="llmLmstudioFields" style="display:none;margin:0 0 8px 24px">
<label for="lmstudioHost">Хост</label>
<input type="text" id="lmstudioHost" value="localhost" placeholder="localhost">
<label for="lmstudioPort">Порт</label>
<input type="number" id="lmstudioPort" value="1234" min="1" max="65535">
<label for="lmstudioModel">Модель</label>
<select id="lmstudioModel"></select>
</div>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="llmDeepseekEnabled" onchange="toggleLlm('deepseek',this.checked)"><span class="slider"></span></label>
<span id="llmDeepseekLabel">🔮 DeepSeek Free</span>
</div>
<div id="llmDeepseekFields" style="display:none;margin:0 0 8px 24px">
<label for="deepseekKey">API ключ</label>
<input type="password" id="deepseekKey" placeholder="sk-...">
<label for="deepseekModel">Модель</label>
<select id="deepseekModel">
<option value="deepseek-chat">deepseek-chat</option>
<option value="deepseek-reasoner">deepseek-reasoner</option>
</select>
</div>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="llmProxyEnabled" onchange="toggleLlm('proxy',this.checked)"><span class="slider"></span></label>
<span id="llmProxyLabel">⚡ Ollama Proxy</span>
</div>
<div id="llmProxyFields" style="display:none;margin:0 0 8px 24px">
<label for="proxyHost">Хост</label>
<input type="text" id="proxyHost" value="localhost" placeholder="localhost">
<label for="proxyPort">Порт</label>
<input type="number" id="proxyPort" value="4000" min="1" max="65535">
<label for="proxyKey">API ключ</label>
<input type="password" id="proxyKey" placeholder="sk-...">
<label for="proxyModel">Модель</label>
<select id="proxyModel"></select>
</div>
<hr>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="llmVoiceEnabled" onchange="toggleLlmVoice(this.checked)"><span class="slider"></span></label>
<span id="llmVoiceLabel">🗣 Озвучка ответов</span>
</div>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="llmMcpMode" onchange="toggleLlmMcpMode(this.checked)"><span class="slider"></span></label>
<span id="llmMcpModeLabel">🎙 Режим микрофона (заполняет текст, отправка вручную)</span>
</div>
<hr>
<div class="row">
<button class="btn primary" onclick="testLlmConnections()">🔌 Тест</button>
<button class="btn secondary" onclick="saveLlmSettings()">💾 Сохранить</button>
<button class="btn secondary" onclick="loadLlmStatus()">🔄 Обновить</button>
</div>
<div id="llmStatus" class="status ok">● Готов</div>
<div style="margin:0;padding:10px;background:#1a1a2e;border-radius:8px;margin-top:12px">
<h4 style="margin:0 0 8px 0">💬 Чат с LLM</h4>
<div id="llmChatMessages" style="max-height:200px;overflow-y:auto;margin-bottom:8px;font-size:.85rem;line-height:1.4">
<div style="color:#888;text-align:center;padding:20px">Начните диалог...</div>
</div>
<textarea id="llmChatText" style="width:100%;height:50px;margin-bottom:6px;resize:vertical;box-sizing:border-box" placeholder="Напиши сообщение..."></textarea>
<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
<select id="llmChatVoice" style="flex:1;max-width:200px"><option value="">(голос по умолч.)</option></select>
<button class="btn primary" onclick="llmChat()">💬 Отправить</button>
<button class="btn secondary" onclick="llmChatClear()">🗑 Очистить</button>
</div>
</div>
</div>

<div id="panel-character" class="panel">
<h3>👤 Карточка персонажа</h3>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="presetEnabled" onchange="togglePreset(this.checked)"><span class="slider"></span></label>
<span id="presetEnabledLabel">Пресет: Включено</span>
</div>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="charScreenshotEnabled" onchange="toggleCharScreenshot(this.checked)"><span class="slider"></span></label>
<span id="charScreenshotLabel">Скриншот: Включено</span>
</div>
<label for="presetList">Выберите пресет</label>
<select id="presetList" onchange="selectPreset(this.value)"></select>
<label for="customModelPath">Или укажите путь к модели вручную</label>
<input type="text" id="customModelPath" placeholder="assets/live2d/МояМодель/model.json">
<div class="row">
<button class="btn primary" onclick="saveCharacterPreset()">💾 Сохранить</button>
<button class="btn secondary" onclick="loadCharacterPresets()">🔄 Обновить</button>
</div>
<div id="characterStatus" class="status ok">● Готов</div>
</div>

<div id="panel-model" class="panel">
<h3>🔄 Переключение модели</h3>
<p style="color:#aaa;font-size:.85rem;margin-bottom:12px">Выберите модель персонажа:</p>
<div id="modelList"></div>
<div id="modelStatus" class="status ok">● Готов</div>
</div>

<div id="panel-mcp" class="panel">
<h3>⚙️ Управление MCP</h3>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="mcpGlobalEnabled" onchange="saveMcpConfig()"><span class="slider"></span></label>
<span id="mcpGlobalLabel">Глобальный MCP: Включено</span>
</div>
<p style="color:#aaa;font-size:.85rem;margin:8px 0">Разрешения для модели ИИ</p>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="mcpMusicPerm" onchange="saveMcpConfig()"><span class="slider"></span></label>
<span id="mcpMusicPermLabel">Управление музыкой</span>
</div>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="mcpAlarmPerm" onchange="saveMcpConfig()"><span class="slider"></span></label>
<span id="mcpAlarmPermLabel">Управление будильником</span>
</div>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="mcpTimerPerm" onchange="saveMcpConfig()"><span class="slider"></span></label>
<span id="mcpTimerPermLabel">Управление таймером</span>
</div>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="mcpScreenshotPerm" onchange="saveMcpConfig()"><span class="slider"></span></label>
<span id="mcpScreenshotPermLabel">Скриншоты</span>
</div>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="mcpHidePerm" onchange="saveMcpConfig()"><span class="slider"></span></label>
<span id="mcpHidePermLabel">Скрытие персонажа</span>
</div>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="mcpControlPerm" onchange="saveMcpConfig()"><span class="slider"></span></label>
<span id="mcpControlPermLabel">Управление персонажем</span>
</div>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="mcpEmotionPerm" onchange="saveMcpConfig()"><span class="slider"></span></label>
<span id="mcpEmotionPermLabel">Эмоции персонажа</span>
</div>
<hr>
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="mcpServerEnabled" onchange="toggleMcpServer(this.checked)"><span class="slider"></span></label>
<span id="mcpServerLabel">MCP сервер: Включено</span>
</div>
<hr>
<h4>🎤 TTS</h4>
<label for="mcpTtsEngine">Движок</label>
<select id="mcpTtsEngine" onchange="mcpTtsEngineChange()"></select>
<label for="mcpTtsVoice">Голос</label>
<select id="mcpTtsVoice"></select>
<label for="mcpTtsVolume">Громкость: <span id="mcpTtsVolLabel">100%</span></label>
<input type="range" id="mcpTtsVolume" min="0" max="100" value="100" oninput="mcpTtsSetVolume(this.value)">
<div class="toggle-wrap">
<label class="toggle"><input type="checkbox" id="mcpTtsEnabled" onchange="mcpTtsToggle()"><span class="slider"></span></label>
<span id="mcpTtsEnabledLabel">TTS: Включено</span>
</div>
<div class="row">
<button class="btn primary" onclick="saveMcpConfig()">💾 Сохранить</button>
<button class="btn secondary" onclick="loadMcpConfig()">🔄 Обновить</button>
</div>
<div id="mcpStatus" class="status ok">● Готов</div>
</div>

<div id="panel-system" class="panel">
<h3>🛠 Системная информация</h3>
<div id="systemInfo" style="font-size:.85rem;line-height:1.6;margin-bottom:12px;background:#0f3460;padding:12px;border-radius:8px">Загрузка...</div>
<hr>
<div class="row">
<button class="btn secondary" onclick="loadSystemInfo()">🔄 Обновить</button>
</div>
<div id="systemStatus" class="status ok">● Готов</div>
</div>

<div id="status" class="status ok">&#9679; Готов</div>
</div>

<div id="diag" style="font-size:11px;color:#888;margin-top:8px;border-top:1px solid #333;padding-top:4px;max-height:60px;overflow:auto"></div>

<script src="/ui.js?v=4"></script>
<script>
var diag=document.getElementById('diag');
function log(m){if(diag)diag.innerHTML+='<br>'+m;console.log(m)}
window.onerror=function(msg,url,line){log('❌ '+msg+' at '+url+':'+line);return true}
function showTab(n,e){if(!e){log('❌ showTab('+n+'): e is null');return}var p=document.getElementById('panel-'+n);if(!p){log('❌ showTab('+n+'): panel-'+n+' not found');return}document.querySelectorAll('.panel').forEach(function(x){x.classList.remove('active')});document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active')});p.classList.add('active');e.classList.add('active');setTimeout(function(){var m={tts:loadEngines,games:loadGames,music:loadTracks,live:loadLive,alarm:loadAlarmTimer,timer:loadAlarmTimer,screenshot:loadScreenshotSettings,random:loadRandomPhrases,mic:loadMicSettings,llm:loadLlmStatus,character:loadCharacterPresets,mcp:loadMcpConfig,system:loadSystemInfo};if(m[n]){log('→ '+n);Promise.resolve(m[n]()).then(function(){log('✓ '+n)}).catch(function(e){log('❌ '+n+': '+e.message)})}else{log('⚠ showTab('+n+'): no loader')}},50)}
document.querySelectorAll('.tab')[8].click()
</script>
</body>
</html>"""


def make_response(data):
    return JSONResponse(data)


async def handle_index(request):
    html = HTML.replace('?t=0', '?t=' + str(int(time.time())))
    return HTMLResponse(html, headers={'Cache-Control': 'no-cache, no-store, must-revalidate'})


async def handle_ui_js(request):
    try:
        js = open(os.path.join(BASE_DIR, 'ui.js'), 'r', encoding='utf-8').read()
    except:
        js = ''
    return Response(js, media_type='application/javascript', headers={'Cache-Control': 'no-cache, no-store, must-revalidate'})


async def handle_settings(request):
    c = get_companion()
    if hasattr(c, 'handle_settings'):
        return await c.handle_settings(request)
    try:
        vol = tts.get_volume()
        spd = tts.get_speed()
        en = tts.is_enabled()
        dv = tts.get_default_voice() or ''
        eng = tts.get_engine()
        return make_response({'volume': vol, 'speed': spd, 'enabled': en, 'default_voice': dv, 'tts_engine': eng})
    except Exception as e:
        return make_response({'volume': 0.5, 'speed': 1.0, 'enabled': True, 'default_voice': '', 'tts_engine': 'piper'})


async def handle_save_settings(request):
    c = get_companion()
    if hasattr(c, 'handle_save_settings'):
        return await c.handle_save_settings(request)
    body = await request.json()
    try:
        if 'volume' in body: tts.set_volume(body['volume'])
        if 'speed' in body: tts.set_speed(body['speed'])
        if 'enabled' in body: tts.set_enabled(body['enabled'])
        if 'default_voice' in body: tts.set_default_voice(body['default_voice'])
        if 'tts_engine' in body: tts.set_engine(body['tts_engine'])
        if 'output_device' in body: tts.set_output_device(body['output_device'])
    except Exception as e:
        logger.error(f'Save settings error: {e}')
    return make_response({'status': 'ok'})


async def handle_tts_engines(request):
    c = get_companion()
    if hasattr(c, 'handle_tts_engines'):
        return await c.handle_tts_engines(request)
    try:
        eng = tts.list_engines()
        cur = tts.get_engine()
        return make_response({'engines': eng, 'current_engine': cur})
    except Exception as e:
        return make_response({'engines': ['piper', 'xtts'], 'current_engine': 'piper'})


async def handle_voices(request):
    c = get_companion()
    if hasattr(c, 'handle_voices'):
        return await c.handle_voices(request)
    try:
        v = tts.list_voices()
        v = [x.replace('.onnx', '').replace('.json', '') for x in v]
        return make_response({'voices': v})
    except Exception as e:
        return make_response({'voices': []})


async def handle_speak(request):
    c = get_companion()
    if hasattr(c, 'handle_speak'):
        return await c.handle_speak(request)
    body = await request.json()
    text = body.get('text', '')
    voice = body.get('voice', '')
    try:
        tts.speak(text, voice)
        return make_response({'status': 'ok', 'result': 'Готово'})
    except Exception as e:
        return make_response({'error': str(e)})


async def handle_stop(request):
    c = get_companion()
    if hasattr(c, 'handle_stop'):
        return await c.handle_stop(request)
    try:
        tts.stop_speaking()
    except:
        pass
    return make_response({'status': 'ok'})


async def handle_output_devices(request):
    c = get_companion()
    if hasattr(c, 'handle_output_devices'):
        return await c.handle_output_devices(request)
    try:
        devices = tts.list_output_devices()
        current = tts.get_output_device()
        dev_list = [{'id': d.get('id', i), 'name': d.get('name', str(d))} for i, d in enumerate(devices)] if devices else []
        return make_response({'devices': dev_list, 'current': current})
    except Exception as e:
        return make_response({'devices': [], 'current': None})


async def handle_games(request):
    c = get_companion()
    if hasattr(c, 'handle_games'):
        return await c.handle_games(request)
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except:
        cfg = {}
    game_texts = cfg.get('game_texts', {})
    all_games = {
        'hide_seek': {'id': 'hide_seek', 'icon': '🙈', 'start_text': 'Давай поиграем в прятки! Найди меня!'},
        'tag': {'id': 'tag', 'icon': '🏃', 'start_text': 'Давай поиграем! Щёлкни по мне!'},
        'dance': {'id': 'dance', 'icon': '💃', 'start_text': 'Потанцуем! Повторяй за мной!'},
        'compliment': {'id': 'compliment', 'icon': '💕', 'start_text': 'Я скажу тебе кое-что приятное!'},
        'emotion_game': {'id': 'emotion_game', 'icon': '🎭', 'start_text': 'Давай поиграем! Угадай мою эмоцию!'},
        'mimic': {'id': 'mimic', 'icon': '🪞', 'start_text': 'Давай поиграем! Повторяй за мной!'},
    }
    for gid, g in all_games.items():
        if gid in game_texts and game_texts[gid]:
            g['start_text'] = game_texts[gid]
    return make_response({'games': list(all_games.values()), 'invite_text': cfg.get('game_invite_text', 'Давай поиграем!')})


async def handle_save_game_settings(request):
    c = get_companion()
    if hasattr(c, 'handle_save_game_settings'):
        return await c.handle_save_game_settings(request)
    return make_response({'status': 'ok'})


async def handle_tracks(request):
    c = get_companion()
    if hasattr(c, 'handle_tracks'):
        return await c.handle_tracks(request)
    try:
        tracks = music_player.list_tracks() or []
        current = music_player.current_track() or ''
        loop = music_player.get_loop() if hasattr(music_player, 'get_loop') else False
        autoplay = music_player.get_autoplay() if hasattr(music_player, 'get_autoplay') else False
        vol = music_player.get_volume() if hasattr(music_player, 'get_volume') else 50
        return make_response({'tracks': tracks, 'current': current, 'loop': loop, 'autoplay': autoplay, 'volume': vol / 100.0})
    except Exception as e:
        return make_response({'tracks': [], 'current': '', 'loop': False, 'autoplay': False, 'volume': 0.5})


async def handle_music_play(request):
    c = get_companion()
    if hasattr(c, 'handle_music_play'):
        return await c.handle_music_play(request)
    body = await request.json()
    track = body.get('track', '')
    try:
        music_player.play_track(track)
        return make_response({'status': 'ok'})
    except Exception as e:
        return make_response({'error': str(e)})


async def handle_play(request):
    return await handle_music_play(request)


async def handle_music_stop(request):
    c = get_companion()
    if hasattr(c, 'handle_music_stop'):
        return await c.handle_music_stop(request)
    try:
        music_player.stop()
    except:
        pass
    return make_response({'status': 'ok'})


async def handle_music_next(request):
    c = get_companion()
    if hasattr(c, 'handle_music_next'):
        return await c.handle_music_next(request)
    try:
        music_player.play_next()
        return make_response({'result': 'Next'})
    except Exception as e:
        return make_response({'error': str(e)})


async def handle_music_prev(request):
    c = get_companion()
    if hasattr(c, 'handle_music_prev'):
        return await c.handle_music_prev(request)
    try:
        music_player.play_prev()
        return make_response({'result': 'Prev'})
    except Exception as e:
        return make_response({'error': str(e)})


async def handle_music_random(request):
    c = get_companion()
    if hasattr(c, 'handle_music_random'):
        return await c.handle_music_random(request)
    try:
        music_player.play_random()
        return make_response({'result': 'Random'})
    except Exception as e:
        return make_response({'error': str(e)})


async def handle_music_loop(request):
    c = get_companion()
    if hasattr(c, 'handle_music_loop'):
        return await c.handle_music_loop(request)
    try:
        body = await request.json()
        loop = body.get('loop', True)
        music_player.set_loop(loop)
    except:
        pass
    return make_response({'status': 'ok'})


async def handle_music_autoplay(request):
    c = get_companion()
    if hasattr(c, 'handle_music_autoplay'):
        return await c.handle_music_autoplay(request)
    try:
        body = await request.json()
        autoplay = body.get('autoplay', True)
        music_player.set_autoplay(autoplay)
    except:
        pass
    return make_response({'status': 'ok'})


async def handle_music_volume(request):
    c = get_companion()
    if hasattr(c, 'handle_music_volume'):
        return await c.handle_music_volume(request)
    try:
        body = await request.json()
        vol = body.get('volume', 0.5)
        music_player.set_volume(int(vol * 100))
    except:
        pass
    return make_response({'status': 'ok'})


async def handle_save_music_vol(request):
    c = get_companion()
    if hasattr(c, 'handle_save_music_vol'):
        return await c.handle_save_music_vol(request)
    try:
        body = await request.json()
        vol = body.get('volume', 0.5)
        music_player.set_volume(int(vol * 100))
    except:
        pass
    return make_response({'status': 'ok'})


async def handle_live_settings(request):
    c = get_companion()
    if hasattr(c, 'handle_live_settings'):
        return await c.handle_live_settings(request)
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        phrases = cfg.get('live_phrases', ['Привет!', 'Как дела?', 'Давай играть!', 'Скучаю по тебе!'])
        interval = cfg.get('live_interval', 30)
        return make_response({'interval': interval, 'phrases': phrases})
    except:
        return make_response({'interval': 30, 'phrases': ['Привет!', 'Как дела?', 'Давай играть!', 'Скучаю по тебе!']})


async def handle_save_live(request):
    c = get_companion()
    if hasattr(c, 'handle_save_live'):
        return await c.handle_save_live(request)
    try:
        body = await request.json()
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        if 'interval' in body:
            cfg['live_interval'] = body['interval']
        if 'phrases' in body:
            cfg['live_phrases'] = body['phrases']
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except:
        pass
    return make_response({'status': 'ok'})


async def handle_alarm_timer_settings(request):
    c = get_companion()
    if hasattr(c, 'handle_alarm_timer_settings'):
        return await c.handle_alarm_timer_settings(request)
    return make_response({'alarm': {'enabled': False, 'time': '08:00', 'text': 'Подъём!', 'song': '', 'repeat': 1, 'replay_interval': 0, 'stop_after': 0, 'auto_repeat': False}, 'timer': {'enabled': False, 'duration': 300, 'text': 'Таймер!', 'song': '', 'repeat': 1, 'replay_interval': 0, 'stop_after': 0, 'auto_repeat': False}})


async def handle_save_alarm_timer(request):
    c = get_companion()
    if hasattr(c, 'handle_save_alarm_timer'):
        return await c.handle_save_alarm_timer(request)
    return make_response({'status': 'ok'})


async def handle_screenshot_settings(request):
    c = get_companion()
    if hasattr(c, 'handle_screenshot_settings'):
        return await c.handle_screenshot_settings(request)
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        return make_response({'enabled': cfg.get('screenshot_enabled', False), 'delay': cfg.get('screenshot_delay', 500)})
    except:
        return make_response({'enabled': False, 'delay': 500})


async def handle_save_screenshot_settings(request):
    c = get_companion()
    if hasattr(c, 'handle_save_screenshot_settings'):
        return await c.handle_save_screenshot_settings(request)
    try:
        body = await request.json()
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        if 'enabled' in body:
            cfg['screenshot_enabled'] = body['enabled']
        if 'delay' in body:
            cfg['screenshot_delay'] = body['delay']
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except:
        pass
    return make_response({'status': 'ok'})


async def handle_screenshot_test(request):
    c = get_companion()
    if hasattr(c, 'handle_screenshot_test'):
        return await c.handle_screenshot_test(request)
    try:
        body = await request.json()
        delay = body.get('delay', 0)
    except:
        delay = 0
    try:
        if delay > 0:
            await asyncio.sleep(delay / 1000.0)
        from PIL import ImageGrab
        import base64
        from io import BytesIO
        img = ImageGrab.grab()
        buf = BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return make_response({'image': b64})
    except Exception as e:
        logger.error(f'Screenshot error: {e}')
        return make_response({'image': None, 'error': str(e)})


async def handle_screenshot_clear(request):
    c = get_companion()
    if hasattr(c, 'handle_screenshot_clear'):
        return await c.handle_screenshot_clear(request)
    try:
        ss_path = os.path.join(BASE_DIR, '_screenshot.png')
        if os.path.exists(ss_path):
            os.remove(ss_path)
    except:
        pass
    return make_response({'status': 'ok'})


async def handle_random_phrases(request):
    c = get_companion()
    if hasattr(c, 'handle_random_phrases'):
        return await c.handle_random_phrases(request)
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        phrases = cfg.get('random_phrases', ['Привет!', 'Как дела?', 'Скучаю по тебе!', 'Давай играть!', 'Ты сегодня красиво выглядишь!', 'Расскажи что-нибудь интересное', 'Обними меня!', 'Как настроение?'])
        interval = cfg.get('random_interval', 10)
        return make_response({'phrases': phrases, 'interval': interval})
    except:
        return make_response({'phrases': ['Привет!', 'Как дела?', 'Скучаю по тебе!', 'Давай играть!', 'Ты сегодня красиво выглядишь!', 'Расскажи что-нибудь интересное', 'Обними меня!', 'Как настроение?'], 'interval': 10})


async def handle_save_random_phrases(request):
    c = get_companion()
    if hasattr(c, 'handle_save_random_phrases'):
        return await c.handle_save_random_phrases(request)
    try:
        body = await request.json()
        phrases_list = body.get('phrases', [])
        interval = body.get('interval', 10)
        phrases._save(phrases_list)
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        cfg['random_phrases'] = phrases_list
        cfg['random_interval'] = interval
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f'Save random phrases error: {e}')
    return make_response({'status': 'ok'})


async def handle_mic_settings(request):
    c = get_companion()
    if hasattr(c, 'handle_mic_settings'):
        return await c.handle_mic_settings(request)
    if request.method == 'POST':
        try:
            body = await request.json()
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            mic = cfg.setdefault('mic', {})
            if 'lang' in body:
                mic['lang'] = body['lang']
            if 'model' in body:
                mic['model'] = body['model']
                stt.set_model_size(body['model'])
            if 'device_id' in body:
                mic['device_id'] = body['device_id']
            if 'vad_threshold' in body:
                mic['vad_threshold'] = body['vad_threshold']
                stt.set_vad_threshold(body['vad_threshold'])
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f'Save mic config error: {e}')
        return make_response({'status': 'ok'})
    try:
        devices = stt.list_audio_devices()
        dev_list = [{'id': d.get('id', i), 'name': d.get('name', str(d))} for i, d in enumerate(devices)] if devices else []
        listening = stt.is_listening()
        last_text = stt.get_last_transcript() if listening else ''
        vad = stt.get_vad_threshold()
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except:
            cfg = {}
        mic = cfg.get('mic', {})
        return make_response({'devices': dev_list, 'device_id': mic.get('device_id'), 'lang': mic.get('lang', 'ru'), 'model': mic.get('model', 'tiny'), 'vad_threshold': mic.get('vad_threshold', 0.05), 'listening': listening, 'last_transcript': last_text})
    except Exception as e:
        return make_response({'error': str(e)})


async def handle_mic_start(request):
    c = get_companion()
    if hasattr(c, 'handle_mic_start'):
        return await c.handle_mic_start(request)
    try:
        body = await request.json()
        device_id = body.get('device_id')
        lang = body.get('lang', 'ru')
        stt.start_listening(lang=lang, device_id=device_id)
        return make_response({'status': 'ok'})
    except Exception as e:
        return make_response({'error': str(e)})


async def handle_mic_stop(request):
    c = get_companion()
    if hasattr(c, 'handle_mic_stop'):
        return await c.handle_mic_stop(request)
    try:
        stt.stop_listening()
        return make_response({'status': 'ok'})
    except Exception as e:
        return make_response({'error': str(e)})


async def handle_mic_test(request):
    c = get_companion()
    if hasattr(c, 'handle_mic_test'):
        return await c.handle_mic_test(request)
    try:
        import numpy as np
        import sounddevice as sd
        body = await request.json() if request.method == 'POST' else {}
        device_id = body.get('device_id') if isinstance(body, dict) else None
        duration = 3
        rec = sd.rec(int(duration * 16000), samplerate=16000, channels=1, device=device_id, dtype='float32')
        sd.wait()
        max_amp = float(np.max(np.abs(rec)))
        if max_amp < 0.01:
            return make_response({'text': '(тишина)', 'max_amp': max_amp})
        text = stt.transcribe(rec[:, 0]) if hasattr(stt, 'transcribe') else '(тест пройден)'
        return make_response({'text': text, 'max_amp': max_amp})
    except Exception as e:
        return make_response({'text': f'(ошибка: {e})'})


async def handle_mic_transcript(request):
    c = get_companion()
    if hasattr(c, 'handle_mic_transcript'):
        return await c.handle_mic_transcript(request)
    return make_response({'text': stt.get_last_transcript(), 'listening': stt.is_listening()})


async def handle_mic_vad(request):
    c = get_companion()
    if hasattr(c, 'handle_mic_vad'):
        return await c.handle_mic_vad(request)
    try:
        body = await request.json()
        stt.set_vad_threshold(body.get('threshold', 0.002))
        return make_response({'status': 'ok'})
    except Exception as e:
        return make_response({'error': str(e)})


async def handle_llm_connections(request):
    c = get_companion()
    if hasattr(c, 'handle_llm_connections'):
        return await c.handle_llm_connections(request)
    if request.method == 'POST':
        try:
            body = await request.json()
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            llm = cfg.setdefault('llm', {})
            if 'enabled' in body:
                llm['enabled'] = body['enabled']
            if 'provider' in body:
                prov = body['provider']
                # Mutual exclusion: disable all, enable selected
                for p in ['ollama', 'lmstudio', 'deepseek', 'proxy']:
                    llm.setdefault(p, {})['enabled'] = (p == prov) and body.get('enabled', True)
                if 'host' in body:
                    llm.setdefault(prov, {})['host'] = body['host']
                if 'port' in body:
                    llm.setdefault(prov, {})['port'] = body['port']
                if 'model' in body:
                    llm.setdefault(prov, {})['model'] = body['model']
                if 'api_key' in body:
                    llm.setdefault(prov, {})['api_key'] = body['api_key']
            if 'voice_enabled' in body:
                llm['voice_enabled'] = body['voice_enabled']
            if 'mcp_mode' in body:
                llm['mcp_mode'] = body['mcp_mode']
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f'Save LLM config error: {e}')
        return make_response({'status': 'ok'})
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except:
        cfg = {}
    llm = cfg.get('llm', {})
    return make_response({
        'enabled': llm.get('enabled', False),
        'ollama': {'enabled': llm.get('ollama', {}).get('enabled', False), 'host': llm.get('ollama', {}).get('host', 'localhost'), 'port': llm.get('ollama', {}).get('port', 11434), 'model': llm.get('ollama', {}).get('model', '')},
        'lmstudio': {'enabled': llm.get('lmstudio', {}).get('enabled', False), 'host': llm.get('lmstudio', {}).get('host', 'localhost'), 'port': llm.get('lmstudio', {}).get('port', 1234), 'model': llm.get('lmstudio', {}).get('model', '')},
        'deepseek': {'enabled': llm.get('deepseek', {}).get('enabled', False), 'api_key': llm.get('deepseek', {}).get('api_key', ''), 'model': llm.get('deepseek', {}).get('model', 'deepseek-chat')},
        'proxy': {'enabled': llm.get('proxy', {}).get('enabled', False), 'host': llm.get('proxy', {}).get('host', 'localhost'), 'port': llm.get('proxy', {}).get('port', 4000), 'api_key': llm.get('proxy', {}).get('api_key', 'sk-ollama-proxy-key'), 'model': llm.get('proxy', {}).get('model', 'qwen3:8b')},
        'voice_enabled': llm.get('voice_enabled', True),
        'mcp_mode': llm.get('mcp_mode', False),
    })


async def handle_llm_test(request):
    c = get_companion()
    if hasattr(c, 'handle_llm_test'):
        return await c.handle_llm_test(request)
    try:
        body = await request.json()
        provider = body.get('provider', 'ollama')
        import httpx
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except:
            cfg = {}
        llm = cfg.get('llm', {})
        prov_cfg = llm.get(provider, {})
        models = []
        if provider == 'ollama':
            host = prov_cfg.get('host', 'localhost')
            port = prov_cfg.get('port', 11434)
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f'http://{host}:{port}/api/tags')
                data = r.json()
                models = [m['name'] for m in data.get('models', [])]
        elif provider == 'lmstudio':
            host = prov_cfg.get('host', 'localhost')
            port = prov_cfg.get('port', 1234)
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f'http://{host}:{port}/v1/models')
                data = r.json()
                models = [m['id'] for m in data.get('data', [])]
        elif provider == 'deepseek':
            api_key = prov_cfg.get('api_key', '')
            model = prov_cfg.get('model', 'deepseek-chat')
            if api_key:
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.post(
                        'https://api.deepseek.com/v1/chat/completions',
                        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                        json={'model': model, 'messages': [{'role': 'user', 'content': 'test'}], 'max_tokens': 1}
                    )
                    if r.status_code == 200:
                        models = [model]
            else:
                models = []
        elif provider == 'proxy':
            host = prov_cfg.get('host', 'localhost')
            port = prov_cfg.get('port', 4000)
            api_key = prov_cfg.get('api_key', 'sk-ollama-proxy-key')
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f'http://{host}:{port}/v1/models',
                    headers={'Authorization': f'Bearer {api_key}'})
                data = r.json()
                models = [m['id'] for m in data.get('data', [])]
        return make_response({'provider': provider, 'models': models, 'status': 'ok'})
    except Exception as e:
        logger.error(f'LLM test error: {e}')
        return make_response({'provider': provider if 'provider' in locals() else 'ollama', 'models': [], 'status': 'error', 'error': str(e)})


async def handle_llm_chat(request):
    c = get_companion()
    if hasattr(c, 'handle_llm_chat'):
        return await c.handle_llm_chat(request)
    try:
        body = await request.json()
        text = body.get('text', '')
        provider = body.get('provider', '')
        voice = body.get('voice', '')
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except:
            cfg = {}
        llm_cfg = cfg.get('llm', {})
        if not provider:
            # Auto-detect active provider
            for p in ['ollama', 'lmstudio', 'deepseek', 'proxy']:
                if llm_cfg.get(p, {}).get('enabled', False):
                    provider = p
                    break
        if not provider:
            return make_response({'error': 'Нет активного провайдера LLM'})

        import httpx
        prov_cfg = llm_cfg.get(provider, {})
        reply = ''
        if provider == 'ollama':
            host = prov_cfg.get('host', 'localhost')
            port = prov_cfg.get('port', 11434)
            model = prov_cfg.get('model', '') or 'llama3.2'
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(f'http://{host}:{port}/api/chat',
                    json={'model': model, 'messages': [{'role': 'user', 'content': text}], 'stream': False})
                data = r.json()
                reply = data.get('message', {}).get('content', '(пусто)')
        elif provider == 'lmstudio':
            host = prov_cfg.get('host', 'localhost')
            port = prov_cfg.get('port', 1234)
            model = prov_cfg.get('model', '') or 'local-model'
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(f'http://{host}:{port}/v1/chat/completions',
                    json={'model': model, 'messages': [{'role': 'user', 'content': text}]})
                data = r.json()
                reply = data.get('choices', [{}])[0].get('message', {}).get('content', '(пусто)')
        elif provider == 'deepseek':
            api_key = prov_cfg.get('api_key', '')
            model = prov_cfg.get('model', 'deepseek-chat')
            if not api_key:
                return make_response({'error': 'API ключ DeepSeek не указан'})
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    'https://api.deepseek.com/v1/chat/completions',
                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                    json={'model': model, 'messages': [{'role': 'user', 'content': text}], 'stream': False}
                )
                data = r.json()
                reply = data.get('choices', [{}])[0].get('message', {}).get('content', '(пусто)')
        elif provider == 'proxy':
            host = prov_cfg.get('host', 'localhost')
            port = prov_cfg.get('port', 4000)
            api_key = prov_cfg.get('api_key', 'sk-ollama-proxy-key')
            model = prov_cfg.get('model', 'qwen3:8b')
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(f'http://{host}:{port}/v1/chat/completions',
                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                    json={'model': model, 'messages': [{'role': 'user', 'content': text}], 'stream': False})
                data = r.json()
                reply = data.get('choices', [{}])[0].get('message', {}).get('content', '(пусто)')

        # TTS if voice enabled
        speak_enabled = body.get('speak', llm_cfg.get('voice_enabled', True))
        if reply and speak_enabled:
            try:
                stt.pause()
                tts.speak(reply, voice)
                stt.resume()
            except Exception as e:
                logger.error(f'LLM TTS error: {e}')
                try:
                    stt.resume()
                except:
                    pass

        # Trigger character reaction
        c = get_companion()
        if c is not None and hasattr(c, 'handle_speech'):
            try:
                await c.handle_speech(reply)
            except:
                pass

        return make_response({'reply': reply, 'provider': provider})
    except Exception as e:
        logger.error(f'LLM chat error: {e}')
        return make_response({'error': str(e)})


async def handle_character_presets(request):
    c = get_companion()
    if hasattr(c, 'handle_character_presets'):
        return await c.handle_character_presets(request)
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        custom_path = cfg.get('custom_model_path', '')
        preset_enabled = cfg.get('preset_enabled', True)
        model_path = cfg.get('model_path', '')
        presets = [{'path': model_path or 'default', 'name': 'Стандартный'}]
        if custom_path:
            presets.append({'path': custom_path, 'name': 'Пользовательский'})
        return make_response({'presets': presets, 'current': custom_path or model_path or 'default', 'preset_enabled': preset_enabled, 'custom_path': custom_path, 'screenshot_mcp_enabled': cfg.get('screenshot_mcp_enabled', True)})
    except:
        return make_response({'presets': [{'path': 'default', 'name': 'Стандартный'}], 'current': 'default', 'preset_enabled': True, 'custom_path': '', 'screenshot_mcp_enabled': True})


async def handle_character_preset(request):
    c = get_companion()
    if hasattr(c, 'handle_character_preset'):
        return await c.handle_character_preset(request)
    try:
        body = await request.json()
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        if 'enabled' in body:
            cfg['preset_enabled'] = body['enabled']
        if 'preset' in body and body['preset']:
            cfg['model_path'] = body['preset']
        if 'custom_path' in body:
            cfg['custom_model_path'] = body['custom_path']
        if 'screenshot_enabled' in body:
            cfg['screenshot_enabled'] = body['screenshot_enabled']
        if 'screenshot_mcp_enabled' in body:
            cfg['screenshot_mcp_enabled'] = body['screenshot_mcp_enabled']
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f'Save character preset error: {e}')
    return make_response({'status': 'ok'})


async def handle_system_info(request):
    c = get_companion()
    if hasattr(c, 'handle_system_info'):
        return await c.handle_system_info(request)
    try:
        import psutil
        ram = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        uptime_sec = int(time.time() - psutil.boot_time())
        days = uptime_sec // 86400
        hours = (uptime_sec % 86400) // 3600
        mins = (uptime_sec % 3600) // 60
        info = {
            'os': f'{platform.system()} {platform.release()}',
            'cpu': f'{platform.processor() or "N/A"} ({cpu_percent}%)',
            'ram': f'{ram.total // (1024**3)} GB ({ram.percent}% used)',
            'python': platform.python_version(),
            'hostname': platform.node(),
            'uptime': f'{days}д {hours}ч {mins}м',
            'mcp': {'running': False, 'port': 8765, 'num_tools': 0},
        }
        return make_response(info)
    except Exception as e:
        return make_response({'os': platform.system(), 'python': platform.python_version(), 'hostname': platform.node(), 'uptime': 'N/A', 'error': str(e)})


async def handle_mcp_toggle(request):
    c = get_companion()
    if hasattr(c, 'handle_mcp_toggle'):
        return await c.handle_mcp_toggle(request)
    return make_response({'status': 'ok'})


async def handle_mcp_config(request):
    c = get_companion()
    if hasattr(c, 'handle_mcp_config'):
        return await c.handle_mcp_config(request)
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        return make_response({
            'global_enabled': cfg.get('mcp_enabled', True),
            'music_mcp_enabled': cfg.get('music_mcp_enabled', True),
            'alarm_mcp_enabled': cfg.get('alarm_mcp_enabled', True),
            'timer_mcp_enabled': cfg.get('timer_mcp_enabled', True),
            'screenshot_mcp_enabled': cfg.get('screenshot_mcp_enabled', True),
            'hide_mcp_enabled': cfg.get('hide_mcp_enabled', True),
            'control_mcp_enabled': cfg.get('control_mcp_enabled', True),
            'emotion_mcp_enabled': cfg.get('emotion_mcp_enabled', True),
            'mcp_server_running': True,
        })
    except:
        return make_response({'global_enabled': True, 'music_mcp_enabled': True, 'alarm_mcp_enabled': True, 'timer_mcp_enabled': True, 'screenshot_mcp_enabled': True, 'hide_mcp_enabled': True, 'control_mcp_enabled': True, 'emotion_mcp_enabled': True, 'mcp_server_running': False})


async def handle_save_mcp_config(request):
    c = get_companion()
    if hasattr(c, 'handle_save_mcp_config'):
        return await c.handle_save_mcp_config(request)
    try:
        body = await request.json()
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        global_enabled = body.get('global_enabled', False)
        for key in ['mcp_enabled', 'music_mcp_enabled', 'alarm_mcp_enabled', 'timer_mcp_enabled', 'screenshot_mcp_enabled', 'hide_mcp_enabled', 'control_mcp_enabled', 'emotion_mcp_enabled']:
            mapped = 'global_enabled' if key == 'mcp_enabled' else key
            if mapped in body:
                value = body[mapped]
                if key != 'mcp_enabled':
                    value = value and global_enabled
                cfg[key] = value
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f'Save MCP config error: {e}')
    return make_response({'status': 'ok'})


async def handle_models(request):
    """List available models and current model."""
    from live2d_display import MODELS, state
    models_list = []
    for mk, mv in MODELS.items():
        models_list.append({
            "id": mk,
            "label": mv["label"],
            "type": mv["type"],
            "current": mk == state.get_model_name(),
        })
    return make_response({
        "models": models_list,
        "current": state.get_model_name(),
    })


async def handle_switch_model(request):
    """Switch to a different model."""
    from live2d_display import MODELS
    body = await request.json()
    model_name = body.get("model", "")
    if model_name not in MODELS:
        return make_response({"status": "error", "error": f"Unknown model: {model_name}"})
    c = get_companion()
    if c is None or not hasattr(c, 'switch_model'):
        return make_response({"status": "error", "error": "Widget not available"})
    try:
        result = c.switch_model(model_name)
        return make_response({"status": "ok", "result": result})
    except Exception as e:
        return make_response({"status": "error", "error": str(e)})


async def handle_toggle_screenshot_mcp(request):
    try:
        body = await request.json()
        enabled = body.get('enabled', True)
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        cfg['screenshot_mcp_enabled'] = enabled
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return make_response({'status': 'ok', 'enabled': enabled})
    except Exception as e:
        logger.error(f'Toggle screenshot MCP error: {e}')
        return make_response({'status': 'error', 'enabled': None})

routes = [
    Route('/', endpoint=handle_index),
    Route('/ui.js', endpoint=handle_ui_js),
    Route('/api/settings', endpoint=handle_settings),
    Route('/api/save_settings', endpoint=handle_save_settings, methods=['POST']),
    Route('/api/tts_engines', endpoint=handle_tts_engines),
    Route('/api/voices', endpoint=handle_voices),
    Route('/api/speak', endpoint=handle_speak, methods=['POST']),
    Route('/api/stop', endpoint=handle_stop, methods=['POST']),
    Route('/api/output_devices', endpoint=handle_output_devices),
    Route('/api/games', endpoint=handle_games),
    Route('/api/save_game_settings', endpoint=handle_save_game_settings, methods=['POST']),
    Route('/api/tracks', endpoint=handle_tracks),
    Route('/api/play', endpoint=handle_play, methods=['POST']),
    Route('/api/music_play', endpoint=handle_music_play, methods=['POST']),
    Route('/api/music_stop', endpoint=handle_music_stop, methods=['POST']),
    Route('/api/music_next', endpoint=handle_music_next, methods=['POST']),
    Route('/api/music_prev', endpoint=handle_music_prev, methods=['POST']),
    Route('/api/music_random', endpoint=handle_music_random, methods=['POST']),
    Route('/api/music_loop', endpoint=handle_music_loop, methods=['POST']),
    Route('/api/music_autoplay', endpoint=handle_music_autoplay, methods=['POST']),
    Route('/api/music_volume', endpoint=handle_music_volume, methods=['POST']),
    Route('/api/save_music_vol', endpoint=handle_save_music_vol, methods=['POST']),
    Route('/api/live_settings', endpoint=handle_live_settings),
    Route('/api/save_live', endpoint=handle_save_live, methods=['POST']),
    Route('/api/alarm_timer_settings', endpoint=handle_alarm_timer_settings),
    Route('/api/save_alarm_timer', endpoint=handle_save_alarm_timer, methods=['POST']),
    Route('/api/screenshot_settings', endpoint=handle_screenshot_settings),
    Route('/api/save_screenshot_settings', endpoint=handle_save_screenshot_settings, methods=['POST']),
    Route('/api/screenshot_test', endpoint=handle_screenshot_test, methods=['POST']),
    Route('/api/screenshot_clear', endpoint=handle_screenshot_clear, methods=['POST']),
    Route('/api/random_phrases', endpoint=handle_random_phrases),
    Route('/api/save_random_phrases', endpoint=handle_save_random_phrases, methods=['POST']),
    Route('/api/mic_settings', endpoint=handle_mic_settings, methods=['GET', 'POST']),
    Route('/api/mic_start', endpoint=handle_mic_start, methods=['POST']),
    Route('/api/mic_stop', endpoint=handle_mic_stop, methods=['POST']),
    Route('/api/mic_test', endpoint=handle_mic_test, methods=['POST']),
    Route('/api/mic_vad', endpoint=handle_mic_vad, methods=['POST']),
    Route('/api/llm_chat', endpoint=handle_llm_chat, methods=['POST']),
    Route('/api/llm_connections', endpoint=handle_llm_connections, methods=['GET', 'POST']),
    Route('/api/llm_test', endpoint=handle_llm_test, methods=['POST']),
    Route('/api/character_presets', endpoint=handle_character_presets),
    Route('/api/character_preset', endpoint=handle_character_preset, methods=['POST']),
    Route('/api/system_info', endpoint=handle_system_info),
    Route('/api/mcp_toggle', endpoint=handle_mcp_toggle, methods=['POST']),
    Route('/api/mcp_config', endpoint=handle_mcp_config),
    Route('/api/save_mcp_config', endpoint=handle_save_mcp_config, methods=['POST']),
    Route('/api/toggle_screenshot_mcp', endpoint=handle_toggle_screenshot_mcp, methods=['POST']),
    Route('/api/mic_transcript', endpoint=handle_mic_transcript),
    Route('/api/models', endpoint=handle_models),
    Route('/api/switch_model', endpoint=handle_switch_model, methods=['POST']),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
]

@asynccontextmanager
async def lifespan(app):
    logger.info('Web UI started on %s:%s', HOST, PORT)
    yield

app = Starlette(debug=False, routes=routes, middleware=middleware, lifespan=lifespan)


def run_web_ui(host=HOST, port=PORT):
    import uvicorn
    config = uvicorn.Config(app, host=host, port=port, log_level='info')
    server = uvicorn.Server(config)
    server.run()

if __name__ == '__main__':
    import uvicorn
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    uvicorn.run(app, host=HOST, port=PORT)