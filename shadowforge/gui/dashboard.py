"""ShadowForge v2.1 GUI Dashboard."""

from __future__ import annotations

import os
import threading
from tkinter import filedialog
from typing import Any, Optional

import customtkinter as ctk

from shadowforge.agents.quick_actions import QUICK_ACTIONS, list_quick_actions
from shadowforge.core.orchestrator import Orchestrator


class Dashboard(ctk.CTk):
    """Main application window for ShadowForge."""

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

        self.title("ShadowForge v2.1 — Multi-Agent Desktop Automation")
        self.geometry(f"{gui_cfg.get('window_width', 1150)}x{gui_cfg.get('window_height', 820)}")
        self.minsize(950, 700)

        ctk.set_appearance_mode(self.config.get("app", {}).get("theme", "dark"))
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=self.COLORS["bg_dark"])
        self._refresh_ms = gui_cfg.get("refresh_interval_ms", 1000)
        self._latest_scan_path = ""

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
            sidebar, text="v2.1 — Local Agents",
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
        for tab in ("Tasks", "Results", "History", "Messages"):
            self.tabview.add(tab)

        for tab, attr in [
            ("Tasks", "tasks_text"), ("Results", "results_text"),
            ("History", "history_text"), ("Messages", "messages_text"),
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
            ("completed", "Done"), ("failed", "Failed"), ("captures", "Screenshots"),
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

        # Screen Monitor
        mon = self._tool_card(panels, "📸 Screen Monitor", 0)
        ctk.CTkLabel(mon, text="Interval (seconds):", font=ctk.CTkFont(size=11),
                     text_color=self.COLORS["text_dim"]).pack(padx=12, anchor="w")
        self.interval_var = ctk.StringVar(value="5")
        ctk.CTkOptionMenu(mon, values=self.INTERVAL_OPTIONS, variable=self.interval_var,
                          fg_color=self.COLORS["accent"], width=120).pack(padx=12, pady=4, anchor="w")
        self.monitor_btn = ctk.CTkButton(
            mon, text="Start Interval Capture", fg_color=self.COLORS["success"],
            hover_color="#00a381", command=self._toggle_monitor,
        )
        self.monitor_btn.pack(padx=12, pady=8, anchor="w")
        self.capture_count_label = ctk.CTkLabel(
            mon, text="Captures: 0", font=ctk.CTkFont(size=11), text_color=self.COLORS["text_dim"],
        )
        self.capture_count_label.pack(padx=12, pady=(0, 10), anchor="w")

        # Folder Scanner
        scan = self._tool_card(panels, "📁 Folder Scanner", 1)
        ctk.CTkLabel(scan, text="Folder to scan:", font=ctk.CTkFont(size=11),
                     text_color=self.COLORS["text_dim"]).pack(padx=12, anchor="w")

        path_row = ctk.CTkFrame(scan, fg_color="transparent")
        path_row.pack(padx=12, pady=4, fill="x")
        self.path_entry = ctk.CTkEntry(path_row, font=ctk.CTkFont(size=12), height=32)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.path_entry.insert(0, os.path.expanduser("~/Desktop"))
        ctk.CTkButton(path_row, text="Browse", width=70, fg_color="#2a2a4a",
                      command=self._browse_folder).pack(side="right")

        ctk.CTkButton(
            scan, text="Scan Folder", fg_color=self.COLORS["accent"],
            hover_color=self.COLORS["accent_hover"], command=self._run_folder_scanner,
        ).pack(padx=12, pady=8, anchor="w")

        self.scan_status_label = ctk.CTkLabel(
            scan, text="", font=ctk.CTkFont(size=10), text_color=self.COLORS["text_dim"],
        )
        self.scan_status_label.pack(padx=12, pady=(0, 10), anchor="w")

        # Quick Actions
        quick = self._tool_card(panels, "⚡ Quick Actions", 2)
        ctk.CTkLabel(quick, text="Pick an action (3s countdown):", font=ctk.CTkFont(size=11),
                     text_color=self.COLORS["text_dim"]).pack(padx=12, anchor="w")

        action_labels = [v["label"] for v in QUICK_ACTIONS.values()]
        self.action_var = ctk.StringVar(value=action_labels[0])
        ctk.CTkOptionMenu(
            quick, values=action_labels, variable=self.action_var,
            fg_color=self.COLORS["warning"], text_color="#1a1a2e", width=200,
        ).pack(padx=12, pady=4, anchor="w")

        self.quick_extra_entry = ctk.CTkEntry(
            quick, placeholder_text="Text or hotkey (for custom actions only)",
            font=ctk.CTkFont(size=11), height=30,
        )
        self.quick_extra_entry.pack(padx=12, pady=4, fill="x")

        ctk.CTkButton(
            quick, text="▶  Run Action", fg_color=self.COLORS["warning"],
            text_color="#1a1a2e", hover_color="#e6b84d", command=self._run_quick_action,
        ).pack(padx=12, pady=8, anchor="w")

    def _browse_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select folder to scan")
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)

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

    def _action_id_from_label(self, label: str) -> str:
        for aid, spec in QUICK_ACTIONS.items():
            if spec["label"] == label:
                return aid
        return "show_desktop"

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
                target=lambda: self.orchestrator.start_screen_monitor(interval), daemon=True,
            ).start()
            self.monitor_btn.configure(text="Stop Interval Capture", fg_color=self.COLORS["danger"])
            self._log(f"📸 Screen monitor — every {interval}s")

    def _run_folder_scanner(self) -> None:
        path = self.path_entry.get().strip()
        if not path:
            self._log("❌ Enter or browse to a folder first")
            return
        self._latest_scan_path = path
        self.scan_status_label.configure(text=f"Scanning: {path}")

        def _run() -> None:
            self._ensure_executor()
            self.orchestrator.run_folder_scan(path)

        threading.Thread(target=_run, daemon=True).start()
        self._log(f"📁 Fresh scan started: {path}")

    def _run_quick_action(self) -> None:
        action_id = self._action_id_from_label(self.action_var.get())
        extra = self.quick_extra_entry.get().strip()

        def _run() -> None:
            self._ensure_executor()
            self.orchestrator.run_quick_action(
                action_id,
                custom_text=extra if action_id == "type_custom" else "",
                custom_keys=extra if action_id == "custom_hotkey" else "",
                countdown=3,
            )

        threading.Thread(target=_run, daemon=True).start()
        self._log(f"⚡ Quick action in 3s: {self.action_var.get()}")

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
        if "captures" in self.stats_labels:
            self.stats_labels["captures"].configure(text=str(count))
        self.capture_count_label.configure(text=f"Captures: {count}")

        self.tasks_text.delete("1.0", "end")
        for task in self.orchestrator.planner.get_queue():
            icon = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}.get(
                task.status.value, "•")
            self.tasks_text.insert("end", f"{icon} [{task.agent}] {task.name} — {task.status.value}\n")
            if task.result and task.status.value == "completed":
                summary = self._summarize_result(task.action, task.result)
                if summary:
                    self.tasks_text.insert("end", f"    ↳ {summary}\n")

        self.results_text.delete("1.0", "end")
        report = self.orchestrator._last_folder_report
        if report:
            scanned = report.get("scanned_path") or report.get("path", self._latest_scan_path)
            self.results_text.insert("end", f"═══ FOLDER SCAN REPORT ═══\n")
            self.results_text.insert("end", f"Scanned path: {scanned}\n\n")
            if report.get("total_files") is not None:
                self.results_text.insert("end", f"Total files:  {report.get('total_files')}\n")
                self.results_text.insert("end", f"Total size:   {report.get('total_size_mb', report.get('total_size_mb', '?'))} MB\n")
            if report.get("file_count") is not None:
                self.results_text.insert("end", f"Total files:  {report.get('file_count')}\n")
                self.results_text.insert("end", f"Total size:   {report.get('total_size_mb')} MB\n")
            if report.get("unique_extensions"):
                self.results_text.insert("end", f"File types:   {report.get('unique_extensions')} unique extensions\n")
            if report.get("category_breakdown"):
                self.results_text.insert("end", f"Categories:   {report.get('category_breakdown')}\n")
            if report.get("extension_breakdown"):
                self.results_text.insert("end", f"Top types:    {report.get('extension_breakdown')}\n")
            if report.get("duplicate_groups") is not None:
                self.results_text.insert("end", f"Duplicates:   {report.get('duplicate_groups')} groups ({report.get('duplicate_files', 0)} extra files)\n")
            if report.get("largest_files"):
                self.results_text.insert("end", f"\nLargest files:\n")
                for f in report.get("largest_files", [])[:5]:
                    self.results_text.insert("end", f"  • {f.get('name')} — {f.get('size_mb')} MB\n")
            self.scan_status_label.configure(text=f"Last scan: {scanned}")

        qa = self.orchestrator._last_quick_action_result
        if qa and not report.get("total_files") and not report.get("file_count"):
            self.results_text.insert("end", f"\n═══ QUICK ACTION ═══\n{qa}\n")

        self.history_text.delete("1.0", "end")
        for entry in self.orchestrator.history.get_recent(20):
            self.history_text.insert("end", f"[{entry.status}] {entry.agent}.{entry.action}\n")

        self.messages_text.delete("1.0", "end")
        for msg in self.orchestrator.message_bus.get_history(12):
            self.messages_text.insert("end", f"{msg.sender} → {msg.recipient}\n")

    def _summarize_result(self, action: str, result: dict[str, Any]) -> str:
        if action == "scan_directory":
            return f"{result.get('file_count', 0)} files @ {result.get('path', '')}"
        if action == "analyze_summary":
            return f"{result.get('total_files', 0)} files, {result.get('total_size_mb', 0)} MB @ {result.get('scanned_path', '')}"
        if action == "find_duplicates":
            return f"{result.get('duplicate_groups', 0)} duplicate groups"
        if action == "capture_screen":
            return f"Saved {os.path.basename(result.get('path', ''))}"
        if action == "run_quick_action":
            return f"Ran: {result.get('label', result.get('action_id', ''))}"
        return ""

    def _log(self, msg: str) -> None:
        self.tasks_text.insert("end", f"{msg}\n")

    def _schedule_refresh(self) -> None:
        self._update_display(self.orchestrator.get_system_status())
        self.after(self._refresh_ms, self._schedule_refresh)

    def on_closing(self) -> None:
        self.orchestrator.stop_all()
        self.destroy()