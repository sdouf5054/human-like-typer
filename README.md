# Human-Like Typer v1.0

A Windows utility that automatically types text from your clipboard or manual input with human-like timing, typos, and corrections.

## Features

**8-Stage Timing Pipeline**
Base delay with Gaussian variance, word boundary pauses, punctuation pauses, newline pauses, Shift key penalty, double-letter acceleration, burst typing micro-pauses, and fatigue simulation that gradually slows typing over long texts.

**3 Typo Types + Auto-Correction**
Adjacent key errors (QWERTY-based), character transposition, and double-strike mistakes. Each typo can trigger a realistic correction sequence: recognition pause, burst backspace, retype delay, and re-entry of the correct character.

**Focus Monitor**
Captures the active window title at typing start. Automatically pauses if focus shifts to another window and resumes when you return.

**Preset System**
4 built-in presets (Default, Fast & Accurate, Slow & Natural, Sloppy Beginner) plus custom preset save/load. Presets store all settings including timing, typo, trigger key, auto-clipboard, countdown, and preprocessing options. The last-used preset is remembered across sessions via `config.json`.

**Auto-Clipboard Mode**
When enabled, pressing the trigger key reads the current clipboard content and starts typing immediately -- no need to click "Use this text" first.

**Built-in Test Panel**
Preview typing behavior inside the app without sending keystrokes to external applications. Runs the full timing and typo pipeline against sample texts in a side-by-side view (original vs. typed output).

**Statistics and Visualization**
After each run, view CPM/WPM, delay distribution histogram, per-character delay scatter plot, and typo breakdown. Requires matplotlib.

**Hotkey Control**
Configurable trigger key (F1-F12, default F9) for start/pause/resume. ESC for immediate hard stop.

## Requirements

- Python 3.11+
- Windows 10/11 (focus monitor uses Win32 API; disabled on other platforms)
- English input mode recommended (Korean IME should be off unless typing Korean)

## Installation

```bash
# Create environment (micromamba or conda)
micromamba create -n human-like-typer python=3.11 -y
micromamba activate human-like-typer

# Install dependencies
pip install customtkinter pynput pyperclip matplotlib
```

## Usage

```bash
python main.py
```

Or use the included `run.bat` which activates the environment automatically.

**Basic workflow:**

1. Select a preset from the top dropdown, or adjust settings via the Settings button.
2. Paste or type your text in the Input Source panel, then click "Use this text". Alternatively, enable Auto-Clipboard mode to skip this step.
3. Switch to your target application (e.g. a text editor or browser input field).
4. Press the trigger key (default F9). After the countdown, typing begins.
5. Press the trigger key again to pause/resume. Press ESC to stop immediately.
6. After completion, click the Stats button to view timing charts and typo statistics.

## Project Structure

```
human-like-typer/
  main.py                  Entry point
  preset_manager.py        Preset load/save + config.json management
  run.bat                  Quick launcher (micromamba)
  config.json              Auto-generated session config (gitignored)
  core/
    clipboard.py           Clipboard reader (pyperclip)
    focus_monitor.py       Active window focus tracking (Win32)
    keyboard_map.py        QWERTY adjacent key map + Shift mappings
    text_preprocessor.py   CRLF normalization, trimming, newline handling
    timing_model.py        8-stage per-character delay calculator
    typo_model.py          Typo generation + correction action sequences
    typer_engine.py        Main engine: state machine + threading + key simulation
  gui/
    app.py                 Main window, preset/settings integration
    input_panel.py         Clipboard preview + direct text input tabs
    control_panel.py       Start/pause/stop, hotkeys, progress, log
    settings_panel.py      Timing/typo/advanced settings (separate window)
    stats_dialog.py        Post-run statistics + matplotlib charts
    test_panel.py          Built-in typing simulation preview
  presets/
    default.json           Balanced defaults
    fast_accurate.json     Fast typist, low error rate, burst ON
    slow_natural.json      Slow and careful, all timing options ON
    sloppy_beginner.json   Slow with high typo rate and strong fatigue
    custom/                User-saved presets (gitignored)
```

## License

MIT
