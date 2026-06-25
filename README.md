# Live2D MCP Companion

Интерактивный десктопный компаньон с Live2D-моделью, управляемый через MCP (Model Context Protocol). Работает на Windows.

## Возможности

- **Live2D-персонаж** — анимированная модель Hiyori на десктопе (через PyQt6 + OpenGL)
- **TTS (Text-to-Speech)** — голосовой вывод через Piper TTS (русские голоса: Irina, Denis, Ruslan)
- **STT (Speech-to-Text)** — распознавание речи через faster-whisper
- **MCP сервер** — 36 инструментов для управления персонажем через любой MCP-клиент
- **RAG (Retrieval-Augmented Generation)** — семантический поиск по документам
- **Веб-интерфейс** — управление через браузер на `http://localhost:8766`
- **Музыкальный плеер** — воспроизведение MP3 через pygame
- **Будильник и таймер** — с MCP-уведомлениями
- **Скриншоты** — снимок экрана с реакцией персонажа
- **Игровые режимы** — прятки, танцы, эмоции и др.

## Системные требования

- Windows 10/11
- Python 3.12+
- Видеокарта с поддержкой OpenGL
- Микрофон (для STT)

## Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/nukkerman2000/live2d-mcp.git
cd live2d-mcp
```

### 2. Установить портабельный Python

Скачайте [embeddable Python 3.12](https://www.python.org/downloads/windows/) и распакуйте в папку `python\`.

Либо используйте системный Python.

### 3. Установить зависимости

Запустите `setup_python.bat` или выполните вручную:

```bash
python\python.exe get-pip.py
python\Scripts\pip.exe install -r requirements.txt
```

### 4. Настроить конфиг

Скопируйте `config.example.json` в `config.json` и настройте под себя.

### 5. Загрузить голосовые модели

Скачайте Piper-голоса в папку `voices\`:
- [ru_RU-irina-medium](https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx)
- [ru_RU-denis-medium](https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/denis/medium/ru_RU-denis-medium.onnx)
- [ru_RU-ruslan-medium](https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/ruslan/medium/ru_RU-ruslan-medium.onnx)

### 6. Загрузить Piper TTS бинарники

Скачайте [Piper TTS для Windows](https://github.com/rhasspy/piper/releases) и распакуйте `piper.exe` и DLL в папку `piper\`.

## Запуск

```bash
start.bat
```

После запуска:
- MCP сервер: `http://127.0.0.1:8765/mcp`
- Веб-интерфейс: `http://127.0.0.1:8766`

## MCP Инструменты

Всего 36 инструментов для управления персонажем через MCP.

### Управление моделью

| Инструмент | Описание |
|---|---|
| `switch_model` | Переключение между моделями (hiyori, nagatoro_sprite) |
| `set_emotion` | Установить эмоцию/выражение лица |
| `set_mouth_open` | Управление открытием рта (липсинк) |
| `play_motion` | Воспроизвести анимацию движения |
| `stop_all_motions` | Остановить все анимации |
| `list_motion_groups` | Список доступных групп анимаций |
| `set_eye_position` | Управление направлением взгляда |
| `set_parameter` | Установить любой параметр модели Live2D |

### Окно персонажа

| Инструмент | Описание |
|---|---|
| `show` / `hide` | Показать/скрыть окно персонажа |
| `move_window` | Переместить окно по координатам |
| `resize_window` | Изменить размер окна |
| `center_window` | Центрировать окно на экране |
| `get_status` | Получить статус персонажа и окна |

### TTS / Голос

| Инструмент | Описание |
|---|---|
| `speak` | Озвучить текст через TTS (с липсинком) |
| `list_voices` | Список доступных голосов |
| `stop_speaking` | Остановить воспроизведение |

### Музыка

| Инструмент | Описание |
|---|---|
| `list_tracks` | Список MP3-треков |
| `play_track` / `stop_music` | Воспроизвести/остановить трек |
| `next_track` / `prev_track` | Следующий/предыдущий трек |
| `play_random_track` | Случайный трек |
| `set_loop` / `set_autoplay` | Режимы повтора и автовоспроизведения |
| `set_music_volume` | Громкость музыки |
| `set_mcp_music` | Разрешить MCP управлять музыкой |

### Будильник и таймер

| Инструмент | Описание |
|---|---|
| `set_alarm_text` | Установить будильник (время HH:MM, текст) |
| `set_timer` | Запустить таймер (в минутах) |
| `get_alarm_timer_status` | Статус будильника и таймера |

### Прочее

| Инструмент | Описание |
|---|---|
| `take_screenshot` | Сделать скриншот экрана |
| `list_available_emotions` | Список доступных эмоций |
| `query_documents` | Поиск по документам (RAG) |
| `ingest_file` | Загрузить файл в RAG-индекс |
| `list_documents` | Список проиндексированных документов |
| `rag_status` | Статус RAG-системы |

## Конфигурация

Основные настройки в `config.json`:
- TTS движок, голос, скорость
- Порты MCP и веб-интерфейса
- Включение/отключение STT, музыки, будильника
- Эмоции и анимации для разных режимов
- Фразы для интерактивного общения

## Структура проекта

```
├── run.py                 # Точка входа
├── mcp_server.py          # MCP сервер
├── live2d_display.py      # Отрисовка Live2D (PyQt6 + OpenGL)
├── talk.py                # Логика диалогов и интерактивности
├── tts.py                 # TTS движок (Piper)
├── stt.py                 # Распознавание речи
├── music_player.py        # Музыкальный плеер
├── alarm_timer.py         # Будильник и таймер
├── voice_bridge.py        # Голосовой мост
├── web_ui.py              # Веб-интерфейс (Starlette + uvicorn)
├── mcp_client.py          # MCP клиент
├── phrases.py / .json     # Фразы персонажа
├── ui.js                  # Клиентская часть веб-интерфейса
├── rag/                   # RAG движок
├── play_modes/            # Игровые режимы
└── assets/live2d/         # Live2D модели
```

## Безопасность

Приложение не отправляет данные в интернет (кроме загрузки моделей STT/TTS при первом запуске). MCP сервер слушает только `127.0.0.1`.
