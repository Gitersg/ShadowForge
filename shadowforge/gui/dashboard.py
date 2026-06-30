"""ShadowForge v2 GUI Dashboard — built with CustomTkinter."""

from __future__ import annotations

import os
import threading
from typing import Any, Optional

import customtkinter as ctk

from shadowforge.core.orchestrator import Orchestrator


class Dashboard(ctk.CTk):
    """Main application window for ShadowForge v2."""

    COLORS = {
        "bg_dark": "#1a1a2e",
        "bg_card": "#16213e",
        "accent": "#6C63FF",
        "accent_hover": "#5a52d5",
        "success": "#00b894",
        "warning": "#fdcb6e",
        "danger": "#e17055",
        "text": "#eaeaea",
        "text_dim": "#a0a0b0",
    }

    INTERVAL_OPTIONS = ["1", "2", "3", "5", "10"]

    def __init__(self, orchestrator: Orchestrator, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        self.orchestrator = orchestrator
        self.config = config or {}
        gui_cfg = self.config.get("gui", {})

        self.title("ShadowForge v2 — Multi-Agent Desktop Automation")
        self.geometry(f"{gui_cfg.get('window_width', 1150)}x{gui_cfg.get('window_height', 820)}")
        self.minsize(950, 700)

        ctk.set_appearance_mode(self.config.get("app", {}).get("theme", "dark"))
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=self.COLORS["bg_dark"])
        self._refresh_ms = gui_cfg.get("refresh_interval_ms", 1000)

        self._build_ui()
        self.orchestrator.on_status_change(self._on_status_update)
        self._schedule_refresh()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=self.COLORS["bg_card"])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar, text="⚡ ShadowForge",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=self.COLORS["accent"],
        ).pack(pady=(25, 2), padx=18, anchor="w")

        ctk.CTkLabel(
            sidebar, text="v2.0 — Local Agents",
            font=ctk.CTkFont(size=11), text_color=self.COLORS["text_dim"],
        ).pack(padx=18, anchor="w")

        ctk.CTkFrame(sidebar, height=2, fg_color=self.COLORS["accent"]).pack(fill="x", padx=18, pady=18)

        self.executor_btn = ctk.CTkButton(
            sidebar, text="▶  Start Executor",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.COLORS["success"], hover_color="#00a381", height=42,
            command=self._toggle_executor,
        )
        self.executor_btn.pack(fill="x", padx=18, pady=6)

        ctk.CTkButton(
            sidebar, text="⏹  Stop All",
            font=ctk.CTkFont(size=13),
            fg_color=self.COLORS["danger"], hover_color="#c0392b", height=36,
            command=self._stop_all,
        ).pack(fill="x", padx=18, pady=4)

        ctk.CTkFrame(sidebar, height=2, fg_color="#2a2a4a").pack(fill="x", padx=18, pady=12)

        ctk.CTkLabel(
            sidebar, text="QUICK RUN", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.COLORS["text_dim"],
        ).pack(padx=18, anchor="w")

        for label, wf in [
            ("🖥️  One-Shot Screen Audit", "screen_audit"),
            ("📥  Scan Downloads", "cleanup_downloads"),
        ]:
            ctk.CTkButton(
                sidebar, text=label, font=ctk.CTkFont(size=12),
                fg_color="transparent", text_color=self.COLORS["text"],
                hover_color=self.COLORS["accent_hover"], anchor="w", height=32,
                command=lambda w=wf: self._run_workflow(w),
            ).pack(fill="x", padx=14, pady=2)

        self.status_label = ctk.CTkLabel(
            sidebar, text="● Idle", font=ctk.CTkFont(size=12), text_color=self.COLORS["text_dim"],
        )
        self.status_label.pack(side="bottom", pady=18)

        self.monitor_status_label = ctk.CTkLabel(
            sidebar, text="", font=ctk.CTkFont(size=10), text_color=self.COLORS["text_dim"],
        )
        self.monitor_status_label.pack(side="bottom", pady=(0, 5))

    def _build_main_area(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)

        self._build_tool_panels(main)
        self.agents_frame = ctk.CTkFrame(main, fg_color="transparent")
        self.agents_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self._build_agent_cards()

        self.tabview = ctk.CTkTabview(main, fg_color=self.COLORS["bg_card"], corner_radius=12)
        self.tabview.grid(row=3, column=0, sticky="nsew")
        for tab in ("Tasks", "History", "Messages", "Results"):
            self.tabview.add(tab)

        for tab, attr in [
            ("Tasks", "tasks_text"), ("History", "history_text"),
            ("Messages", "messages_text"), ("Results", "results_text"),
        ]:
            box = ctk.CTkTextbox(
                self.tabview.tab(tab), font=ctk.CTkFont(family="Consolas", size=12),
                fg_color="#0f0f23", text_color=self.COLORS["text"],
            )
            box.pack(fill="both", expand=True, padx=5, pady=5)
            setattr(self, attr, box)

        self.stats_frame = ctk.CTkFrame(main, fg_color=self.COLORS["bg_card"], corner_radius=10)
        self.stats_frame.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.stats_labels: dict[str, ctk.CTkLabel] = {}
        for key, label in [
            ("pending", "Pending"), ("running", "Running"),
            ("completed", "Completed"), ("failed", "Failed"),
            ("captures", "Screenshots"),
        ]:
            frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
            frame.pack(side="left", expand=True, fill="x", padx=8, pady=6)
            ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=10),
                         text_color=self.COLORS["text_dim"]).pack()
            val = ctk.CTkLabel(frame, text="0", font=ctk.CTkFont(size=18, weight="bold"),
                               text_color=self.COLORS["accent"])
            val.pack()
            self.stats_labels[key] = val

    def _tool_card(self, parent: ctk.CTkFrame, title: str, col: int) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=self.COLORS["bg_card"], corner_radius=12)
        card.grid(row=0, column=col, sticky="nsew", padx=4, pady=4)
        ctk.CTkLabel(
            card, text=title, font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.COLORS["accent"],
        ).pack(padx=12, pady=(10, 6), anchor="w")
        return card

    def _build_tool_panels(self, parent: ctk.CTkFrame) -> None:
        panels = ctk.CTkFrame(parent, fg_color="transparent")
        panels.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        panels.grid_columnconfigure((0, 1, 2), weight=1)

        # --- Screen Monitor ---
        mon = self._tool_card(panels, "📸 Screen Monitor", 0)
        ctk.CTkLabel(mon, text="Capture interval (seconds):",
                     font=ctk.CTkFont(size=11), text_color=self.COLORS["text_dim"]).pack(padx=12, anchor="w")
        self.interval_var = ctk.StringVar(value="5")
        ctk.CTkOptionMenu(
            mon, values=self.INTERVAL_OPTIONS, variable=self.interval_var,
            fg_color=self.COLORS["accent"], width=120,
        ).pack(padx=12, pady=4, anchor="w")

        self.monitor_btn = ctk.CTkButton(
            mon, text="Start Interval Capture", fg_color=self.COLORS["success"],
            hover_color="#00a381", command=self._toggle_monitor,
        )
        self.monitor_btn.pack(padx=12, pady=8, anchor="w")

        self.capture_count_label = ctk.CTkLabel(
            mon, text="Captures: 0", font=ctk.CTkFont(size=11), text_color=self.COLORS["text_dim"],
        )
        self.capture_count_label.pack(padx=12, pady=(0, 10), anchor="w")

        # --- Device Scanner ---
        scan = self._tool_card(panels, "📁 Device Scanner & Planner", 1)
        ctk.CTkLabel(scan, text="Folder path to scan:",
                     font=ctk.CTkFont(size=11), text_color=self.COLORS["text_dim"]).pack(padx=12, anchor="w")
        self.path_entry = ctk.CTkEntry(
            scan, placeholder_text=r"e.g. C:\Users\You\Desktop  or  ~/Downloads",
            font=ctk.CTkFont(size=12), height=32,
        )
        self.path_entry.pack(padx=12, pady=4, fill="x")
        self.path_entry.insert(0, os.path.expanduser("~/Desktop"))

        ctk.CTkButton(
            scan, text="Scan & Analyze", fg_color=self.COLORS["accent"],
            hover_color=self.COLORS["accent_hover"], command=self._run_device_scanner,
        ).pack(padx=12, pady=8, anchor="w")

        # --- Smart Automate ---
        auto = self._tool_card(panels, "🖱️ Smart Automate", 2)
        ctk.CTkLabel(auto, text="Find this text on screen:",
                     font=ctk.CTkFont(size=11), text_color=self.COLORS["text_dim"]).pack(padx=12, anchor="w")
        self.target_entry = ctk.CTkEntry(
            scan, placeholder_text='e.g. "Start" or "File"',
            font=ctk.CTkFont(size=12), height=32,
        )
        # fix: parent should be auto not scan
        self.target_entry.destroy()
        self.target_entry = ctk.CTkEntry(
            auto, placeholder_text='e.g. Start Executor, File, Save',
            font=ctk.CTkFont(size=12), height=32,
        )
        self.target_entry.pack(padx=12, pady=4, fill="x")

        ctk.CTkLabel(auto, text="Then press keys (optional):",
                     font=ctk.CTkFont(size=11), text_color=self.COLORS["text_dim"]).pack(padx=12, anchor="w")
        self.keys_entry = ctk.CTkEntry(
            auto, placeholder_text="e.g. enter  |  ctrl+s  |  type:hello",
            font=ctk.CTkFont(size=12), height=32,
        )
        self.keys_entry.pack(padx=12, pady=4, fill="x")

        ctk.CTkButton(
            auto, text="Find & Automate", fg_color=self.COLORS["warning"],
            text_color="#1a1a2e", hover_color="#e6b84d", command=self._run_smart_automate,
        ).pack(padx=12, pady=8, anchor="w")

    def _build_agent_cards(self) -> None:
        for w in self.agents_frame.winfo_children():
            w.destroy()
        for agent in self.orchestrator.get_agent_status():
            card = ctk.CTkFrame(self.agents_frame, fg_color=self.COLORS["bg_card"],
                                corner_radius=10, width=140, height=72)
            card.pack(side="left", padx=4, pady=4)
            card.pack_propagate(False)
            color = self.COLORS["success"] if agent["running"] else self.COLORS["text_dim"]
            ctk.CTkLabel(card, text=f"● {agent['name'].title()}",
                         font=ctk.CTkFont(size=12, weight="bold"), text_color=color).pack(
                padx=8, pady=(8, 0), anchor="w")
            ctk.CTkLabel(card, text=", ".join(agent["capabilities"][:2]),
                         font=ctk.CTkFont(size=9), text_color=self.COLORS["text_dim"]).pack(
                padx=8, anchor="w")

    def _ensure_executor(self) -> None:
        if not self.orchestrator.executor.is_running:
            self.orchestrator.start_executor()
            self.executor_btn.configure(text="⏸  Stop Executor", fg_color=self.COLORS["warning"])
            self.status_label.configure(text="● Running", text_color=self.COLORS["success"])

    def _toggle_monitor(self) -> None:
        mon = self.orchestrator.get_screen_monitor_status()
        if mon.get("running"):
            self.orchestrator.stop_screen_monitor()
            self.monitor_btn.configure(text="Start Interval Capture", fg_color=self.COLORS["success"])
            self._log("⏹ Screen monitor stopped")
        else:
            interval = float(self.interval_var.get())
            self._ensure_executor()
            threading.Thread(
                target=lambda: self.orchestrator.start_screen_monitor(interval), daemon=True
            ).start()
            self.monitor_btn.configure(text="Stop Interval Capture", fg_color=self.COLORS["danger"])
            self._log(f"📸 Screen monitor started — every {interval}s")

    def _run_device_scanner(self) -> None:
        path = self.path_entry.get().strip()
        if not path:
            self._log("❌ Enter a folder path first")
            return

        def _run() -> None:
            self._ensure_executor()
            self.orchestrator.run_workflow("device_scanner", {"scan_path": path, "path": path, "depth": 5})

        threading.Thread(target=_run, daemon=True).start()
        self._log(f"📁 Scanning: {path}")

    def _run_smart_automate(self) -> None:
        target = self.target_entry.get().strip()
        if not target:
            self._log("❌ Enter text to find on screen")
            return
        keys = self.keys_entry.get().strip()

        def _run() -> None:
            self._ensure_executor()
            self.orchestrator.run_workflow("smart_automate", {
                "target_text": target,
                "text": target,
                "keys": keys,
            })

        threading.Thread(target=_run, daemon=True).start()
        self._log(f"🖱️ Smart automate: find '{target}'" + (f" → keys: {keys}" if keys else ""))

    def _run_workflow(self, name: str) -> None:
        def _run() -> None:
            self._ensure_executor()
            self.orchestrator.run_workflow(name)
        threading.Thread(target=_run, daemon=True).start()
        self._log(f"▶ Workflow: {name}")

    def _toggle_executor(self) -> None:
        if self.orchestrator.executor.is_running:
            self.orchestrator.stop_executor()
            self.executor_btn.configure(text="▶  Start Executor", fg_color=self.COLORS["success"])
            self.status_label.configure(text="● Idle", text_color=self.COLORS["text_dim"])
            self.monitor_btn.configure(text="Start Interval Capture", fg_color=self.COLORS["success"])
        else:
            self.orchestrator.start_executor()
            self.executor_btn.configure(text="⏸  Stop Executor", fg_color=self.COLORS["warning"])
            self.status_label.configure(text="● Running", text_color=self.COLORS["success"])

    def _stop_all(self) -> None:
        self.orchestrator.stop_all()
        self.executor_btn.configure(text="▶  Start Executor", fg_color=self.COLORS["success"])
        self.monitor_btn.configure(text="Start Interval Capture", fg_color=self.COLORS["success"])
        self.status_label.configure(text="● Stopped", text_color=self.COLORS["danger"])

    def _on_status_update(self, status: dict[str, Any]) -> None:
        self.after(0, lambda: self._update_display(status))

    def _update_display(self, status: dict[str, Any]) -> None:
        stats = status.get("task_stats", {})
        for key in ("pending", "running", "completed", "failed"):
            if key in self.stats_labels:
                self.stats_labels[key].configure(text=str(stats.get(key, 0)))

        mon = status.get("screen_monitor", {})
        count = mon.get("capture_count", 0)
        self.stats_labels.get("captures", ctk.CTkLabel(self)).configure(text=str(count))
        self.capture_count_label.configure(text=f"Captures: {count}")
        if mon.get("running"):
            self.monitor_status_label.configure(
                text=f"📸 Monitoring every {mon.get('interval_sec', 0)}s")
            self.monitor_btn.configure(text="Stop Interval Capture", fg_color=self.COLORS["danger"])
        else:
            self.monitor_status_label.configure(text="")

        self.tasks_text.delete("1.0", "end")
        for task in self.orchestrator.planner.get_queue():
            icon = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}.get(
                task.status.value, "•")
            line = f"{icon} [{task.agent}] {task.name} — {task.status.value}\n"
            self.tasks_text.insert("end", line)
            if task.result and task.status.value == "completed":
                summary = self._summarize_result(task.action, task.result)
                if summary:
                    self.tasks_text.insert("end", f"    ↳ {summary}\n")

        self.results_text.delete("1.0", "end")
        for task in self.orchestrator.planner.get_completed()[-10:]:
            if task.result:
                self.results_text.insert("end", f"=== {task.name} ===\n")
                self.results_text.insert("end", self._format_result(task.result) + "\n\n")

        self.history_text.delete("1.0", "end")
        for entry in self.orchestrator.history.get_recent(25):
            self.history_text.insert("end", f"[{entry.status}] {entry.agent}.{entry.action}\n")

        self.messages_text.delete("1.0", "end")
        for msg in self.orchestrator.message_bus.get_history(15):
            self.messages_text.insert("end", f"{msg.sender} → {msg.recipient} [{msg.message_type}]\n")

    def _summarize_result(self, action: str, result: dict[str, Any]) -> str:
        if action == "capture_screen":
            return f"Saved {result.get('path', '')}"
        if action == "analyze_summary":
            return f"{result.get('total_files', 0)} files, {result.get('total_size_mb', 0)} MB"
        if action == "find_duplicates":
            return f"{result.get('duplicate_groups', 0)} duplicate groups"
        if action == "find_text":
            pos = result.get("click_position", {})
            return f"Found '{result.get('searched_text')}' at ({pos.get('x')}, {pos.get('y')})" if result.get("success") else "Text not found"
        if action == "click":
            return f"Clicked ({result.get('x')}, {result.get('y')})"
        if action == "execute_keys":
            return f"Keys: {result.get('keys', result.get('typed', 'skipped'))}"
        return ""

    def _format_result(self, result: dict[str, Any]) -> str:
        lines = []
        for key, val in result.items():
            if key in ("files", "groups", "elements", "matches", "plan"):
                continue
            if isinstance(val, dict) and len(str(val)) < 200:
                lines.append(f"  {key}: {val}")
            elif not isinstance(val, (list, dict)):
                lines.append(f"  {key}: {val}")
        for extra in ("category_breakdown", "extension_breakdown", "largest_files"):
            if extra in result:
                lines.append(f"  {extra}: {result[extra]}")
        return "\n".join(lines)

    def _log(self, msg: str) -> None:
        self.tasks_text.insert("end", f"{msg}\n")

    def _schedule_refresh(self) -> None:
        self._update_display(self.orchestrator.get_system_status())
        self.after(self._refresh_ms, self._schedule_refresh)

    def on_closing(self) -> None:
        self.orchestrator.stop_all()
        self.destroy()