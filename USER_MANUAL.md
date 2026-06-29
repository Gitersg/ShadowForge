# ShadowForge User Manual

**Version 1.0**  
**Local Multi-Agent Desktop Automation System**

---

## Welcome

Thank you for choosing **ShadowForge**.

ShadowForge is a desktop automation application that runs entirely on your computer. It uses multiple specialized agents to observe your screen, manage files, plan tasks, and perform automation — without requiring internet access or cloud services.

This manual will guide you through installation, daily use, and all available features.

---

## System Requirements

Before installing ShadowForge, ensure your computer meets the following requirements:

| Requirement | Details |
|-------------|---------|
| Operating System | Windows 10 or later (primary); macOS/Linux supported via manual setup |
| Python | Version 3.10 or newer |
| Storage | At least 500 MB free disk space |
| RAM | 4 GB minimum recommended |
| Display | 1280×720 minimum resolution |
| Internet | Required only for first-time dependency installation |

**Optional:** Tesseract OCR (improves text recognition from screenshots)

---

## Installation

### Step 1: Install Python

1. Visit [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Download Python 3.10 or newer
3. During installation, enable **"Add Python to PATH"**
4. Complete the installation and restart your computer if prompted

### Step 2: Download ShadowForge

**Option A — Download ZIP (Recommended for most users)**

1. Go to [https://github.com/Gitersg/ShadowForge](https://github.com/Gitersg/ShadowForge)
2. Click **Code** → **Download ZIP**
3. Extract the ZIP file to your preferred location (e.g. `Documents\ShadowForge`)

**Option B — Clone with Git**

```bash
git clone https://github.com/Gitersg/ShadowForge.git
cd ShadowForge
```

### Step 3: Verify the Download

Open the extracted folder. You should see the following files:

```
ShadowForge/
├── main.py                 ← Application entry point
├── INSTALL_AND_RUN.bat     ← First-time setup and launch (Windows)
├── RUN_SHADOWFORGE.bat     ← Quick launch (Windows)
├── START_HERE.txt          ← Quick reference guide
├── USER_MANUAL.md          ← This document
├── README.md
├── config.json
├── requirements.txt
└── shadowforge/            ← Application source code
```

> **Note:** ShadowForge does not include a `.exe` installer. The application runs through Python. The provided `.bat` files handle this automatically.

### Step 4: First Launch

1. Open the ShadowForge folder
2. Double-click **`INSTALL_AND_RUN.bat`**
3. Wait 1–2 minutes while dependencies install (first run only)
4. The ShadowForge dashboard will open automatically

**Subsequent launches:** Double-click **`RUN_SHADOWFORGE.bat`**

---

## Application Overview

When ShadowForge opens, you will see the main dashboard. The interface is divided into the following sections:

### Left Sidebar

Contains workflow shortcuts and system controls (Start, Stop).

### Agent Status Panel

Displays the status of four core agents:

- **Vision** — Screen observation and text recognition
- **File** — File and folder management
- **Automation** — Mouse and keyboard control
- **Planner** — Task analysis and workflow selection

A green indicator means the agent is active and ready.

### Goal Input Bar

Allows you to describe a task in plain language. ShadowForge will analyze your request and select the appropriate workflow.

### Main Content Area

Three tabs provide real-time information:

- **Tasks** — Current and completed operations
- **History** — Record of all agent actions
- **Messages** — Internal agent communication log

### Status Bar

Shows task counts: Pending, Running, Completed, and Failed.

---

## Getting Started

### Before Running Any Workflow

Always start the task executor before running workflows:

1. Click **▶ Start Executor** in the left sidebar
2. The status indicator will change to **Running**
3. You may now select any workflow

To stop processing:

- **⏸ Stop Executor** — Pauses task execution
- **⏹ Stop All** — Stops all agents and tasks

---

## Features

### 1. Screen Audit

**Description**  
Captures your current screen, extracts visible text, and identifies user interface elements such as buttons and panels.

**How to Use**

1. Click **▶ Start Executor**
2. Select **Screen Audit** from the sidebar
3. Monitor progress in the **Tasks** tab

**What Happens**

| Step | Action |
|------|--------|
| 1 | Full screen capture |
| 2 | Text extraction (OCR) |
| 3 | UI element detection |

**Output Location**  
Screenshots are saved to:

```
[Your ShadowForge Folder]\data\screenshots\
```

Example filename: `screen_1782745249.png`

---

### 2. Organize Desktop

**Description**  
Scans your Desktop, identifies duplicate files, and generates an organization plan sorted by file type (images, documents, videos, code, etc.).

**How to Use**

1. Click **▶ Start Executor**
2. Select **Organize Desktop** from the sidebar
3. Review results in the **Tasks** and **History** tabs

**What Happens**

| Step | Action |
|------|--------|
| 1 | Desktop folder scan |
| 2 | Duplicate file detection (MD5 hash comparison) |
| 3 | Organization plan by file category |

**Default Behavior**  
File organization operates in **preview mode** by default. ShadowForge shows what changes would be made without moving files. This ensures safe testing.

---

### 3. Cleanup Downloads

**Description**  
Analyzes your Downloads folder, detects duplicate files, and identifies empty directories that can be removed.

**How to Use**

1. Click **▶ Start Executor**
2. Select **Cleanup Downloads** from the sidebar
3. Review the duplicate report and cleanup summary

**What Happens**

| Step | Action |
|------|--------|
| 1 | Downloads folder scan |
| 2 | Duplicate detection |
| 3 | Empty folder identification |

---

### 4. Automate Click

**Description**  
Captures the screen, locates specified text, and performs an automated mouse click at that position.

**How to Use**

1. Click **▶ Start Executor**
2. Select **Automate Click** from the sidebar
3. ShadowForge will capture, locate, and click automatically

**Important**  
This feature controls your mouse and keyboard. Ensure no critical applications are open and that you intend to perform the automated action before running this workflow.

---

### 5. Natural Language Goals

**Description**  
Describe what you want to accomplish in everyday language. ShadowForge analyzes your goal and automatically selects the most appropriate workflow.

**How to Use**

1. Click **▶ Start Executor**
2. Enter your goal in the input field at the top of the dashboard
3. Click **Plan & Run**

**Example Goals**

| Enter This | ShadowForge Will |
|------------|------------------|
| "organize my desktop" | Run Organize Desktop workflow |
| "scan my screen" | Run Screen Audit workflow |
| "clean up downloads" | Run Cleanup Downloads workflow |
| "find duplicate files" | Scan and detect duplicates |

Results appear in the **Tasks** tab as they execute.

---

## Understanding the Dashboard Tabs

### Tasks Tab

Displays the live task queue. Each entry shows:

- Agent responsible
- Task name
- Current status (Pending, Running, Completed, Failed)

Status icons:

- ⏳ Pending
- 🔄 Running
- ✅ Completed
- ❌ Failed

### History Tab

A permanent log of all actions performed by ShadowForge agents. Useful for reviewing past operations and verifying results.

### Messages Tab

Shows internal communication between agents. Intended for advanced users and diagnostics.

---

## File and Data Locations

All data generated by ShadowForge is stored locally on your computer inside the project folder. Nothing is uploaded to external servers.

| Data Type | Location |
|-----------|----------|
| Screenshots | `data/screenshots/` |
| Action history | `data/history.json` |
| Application logs | `logs/shadowforge.log` |
| Configuration | `config.json` |

**Example (Windows):**  
If ShadowForge is installed at `C:\Users\YourName\Documents\ShadowForge`, screenshots will be saved to:

```
C:\Users\YourName\Documents\ShadowForge\data\screenshots\
```

These folders are created automatically on first use.

---

## Configuration

ShadowForge behavior can be customized by editing `config.json` in the project root folder.

| Setting | Description |
|---------|-------------|
| `agents.vision.screenshot_dir` | Custom screenshot save location |
| `agents.file.organize_categories` | File type categories for organization |
| `agents.automation.pause_between_actions` | Delay between automated actions (seconds) |
| `agents.automation.failsafe` | Move mouse to corner to abort automation |
| `gui.theme` | Interface theme (`dark` or `light`) |
| `logging.level` | Log detail level (`INFO`, `DEBUG`, `WARNING`) |

Restart ShadowForge after making changes.

---

## Command Line Usage

For users who prefer terminal operation or wish to integrate ShadowForge into scripts:

```bash
# Activate the environment (Windows)
venv\Scripts\activate

# Launch the graphical interface
python main.py

# Run a workflow without the GUI
python main.py --cli --workflow screen_audit

# Available workflows
python main.py --cli --workflow organize_desktop
python main.py --cli --workflow cleanup_downloads
python main.py --cli --workflow automate_click
```

---

## Extending ShadowForge (Plugins)

ShadowForge supports custom agents through its plugin system.

1. Navigate to the `plugins/` folder
2. Copy `example_agent.py` and rename it (e.g. `my_agent.py`)
3. Modify the agent logic within the new file
4. Restart ShadowForge — your agent will be detected and loaded automatically

Refer to `plugins/example_agent.py` for the required structure.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Application does not open | Ensure Python 3.10+ is installed with PATH enabled. Run `INSTALL_AND_RUN.bat` and review any error messages. |
| "Python not found" error | Reinstall Python and check **"Add Python to PATH"** during setup. |
| Tasks remain in Pending status | Click **▶ Start Executor** before running workflows. |
| OCR or text extraction warning | Install Tesseract OCR, or continue without it — screen capture and UI detection still function normally. |
| No screenshots found | Check `data/screenshots/` inside your ShadowForge folder. Run Screen Audit with the executor started. |
| Automation clicks unexpectedly | Enable failsafe in `config.json`. Move the mouse to any screen corner to abort. |
| Permission errors during file scan | Run workflows on folders you own (Desktop, Documents). Avoid system-protected directories. |

---

## Privacy and Security

ShadowForge is designed with privacy as a core principle:

- **Fully local operation** — No data leaves your computer
- **No cloud APIs** — No OpenAI, Google, or third-party services required
- **No account required** — No registration or login
- **Offline capable** — After initial setup, runs without internet
- **Transparent logging** — All actions recorded locally for your review

---

## Quick Reference

| I want to… | Action |
|------------|--------|
| Install for the first time | Double-click `INSTALL_AND_RUN.bat` |
| Open the application | Double-click `RUN_SHADOWFORGE.bat` |
| Capture my screen | Start Executor → Screen Audit |
| Organize files | Start Executor → Organize Desktop |
| Clean Downloads folder | Start Executor → Cleanup Downloads |
| Describe a task in plain English | Type goal → Plan & Run |
| View captured screenshots | Open `data/screenshots/` folder |
| Review past actions | Open the **History** tab |
| Stop all activity | Click **⏹ Stop All** |

---

## Support

- **Documentation:** [https://github.com/Gitersg/ShadowForge](https://github.com/Gitersg/ShadowForge)
- **User Manual:** `USER_MANUAL.md` (this file)
- **Issues and feedback:** GitHub Issues on the repository above

---

**ShadowForge** — Your desktop. Your agents. Your rules. Fully offline.

© 2026 ShadowForge. All rights reserved.