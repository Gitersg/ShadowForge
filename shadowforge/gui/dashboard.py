"""ShadowForge GUI Dashboard — built with CustomTkinter."""

from __future__ import annotations

import threading
import tkinter as tk
from typing import Any, Callable, Optional

import customtkinter as ctk

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

    def __init__(self, orchestrator: Orchestrator, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        self.orchestrator = orchestrator
        self.config = config or {}
        gui_cfg = self.config.get("gui", {})

        self.title("ShadowForge — Multi-Agent Desktop Automation")
        self.geometry(f"{gui_cfg.get('window_width', 1100)}x{gui_cfg.get('window_height', 750)}")
        self.minsize(900, 600)

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
        sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=self.COLORS["bg_card"])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        logo = ctk.CTkLabel(
            sidebar,
            text="⚡ ShadowForge",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.COLORS["accent"],
        )
        logo.pack(pady=(30, 5), padx=20, anchor="w")

        subtitle = ctk.CTkLabel(
            sidebar,
            text="Local Multi-Agent System",
            font=ctk.CTkFont(size=11),
            text_color=self.COLORS["text_dim"],
        )
        subtitle.pack(padx=20, anchor="w")

        ctk.CTkFrame(sidebar, height=2, fg_color=self.COLORS["accent"]).pack(fill="x", padx=20, pady=20)

        workflows = [
            ("🗂️  Organize Desktop", "organize_desktop"),
            ("🖥️  Screen Audit", "screen_audit"),
            ("📥  Cleanup Downloads", "cleanup_downloads"),
            ("🖱️  Automate Click", "automate_click"),
        ]

        ctk.CTkLabel(
            sidebar, text="WORKFLOWS", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.COLORS["text_dim"],
        ).pack(padx=20, anchor="w")

        for label, workflow in workflows:
            btn = ctk.CTkButton(
                sidebar,
                text=label,
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                text_color=self.COLORS["text"],
                hover_color=self.COLORS["accent_hover"],
                anchor="w",
                height=36,
                command=lambda w=workflow: self._run_workflow(w),
            )
            btn.pack(fill="x", padx=15, pady=3)

        ctk.CTkFrame(sidebar, height=2, fg_color="#2a2a4a").pack(fill="x", padx=20, pady=15)

        self.executor_btn = ctk.CTkButton(
            sidebar,
            text="▶  Start Executor",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.COLORS["success"],
            hover_color="#00a381",
            height=40,
            command=self._toggle_executor,
        )
        self.executor_btn.pack(fill="x", padx=20, pady=5)

        ctk.CTkButton(
            sidebar,
            text="⏹  Stop All",
            font=ctk.CTkFont(size=13),
            fg_color=self.COLORS["danger"],
            hover_color="#c0392b",
            height=36,
            command=self._stop_all,
        ).pack(fill="x", padx=20, pady=5)

        self.status_label = ctk.CTkLabel(
            sidebar,
            text="● Idle",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS["text_dim"],
        )
        self.status_label.pack(side="bottom", pady=20)

    def _build_main_area(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        # Goal input bar
        goal_frame = ctk.CTkFrame(main, fg_color=self.COLORS["bg_card"], corner_radius=12)
        goal_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        goal_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            goal_frame, text="🎯 Goal:", font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COLORS["text"],
        ).grid(row=0, column=0, padx=15, pady=12)

        self.goal_entry = ctk.CTkEntry(
            goal_frame,
            placeholder_text="e.g. organize my desktop and find duplicates",
            font=ctk.CTkFont(size=13),
            height=36,
        )
        self.goal_entry.grid(row=0, column=1, padx=10, pady=12, sticky="ew")

        ctk.CTkButton(
            goal_frame,
            text="Plan & Run",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.COLORS["accent"],
            hover_color=self.COLORS["accent_hover"],
            width=120,
            command=self._plan_and_run,
        ).grid(row=0, column=2, padx=15, pady=12)

        # Agent status cards
        self.agents_frame = ctk.CTkFrame(main, fg_color="transparent")
        self.agents_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._build_agent_cards()

        # Tabbed content: Tasks | History | Logs
        self.tabview = ctk.CTkTabview(main, fg_color=self.COLORS["bg_card"], corner_radius=12)
        self.tabview.grid(row=2, column=0, sticky="nsew")
        self.tabview.add("Tasks")
        self.tabview.add("History")
        self.tabview.add("Messages")

        self.tasks_text = ctk.CTkTextbox(
            self.tabview.tab("Tasks"), font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0f0f23", text_color=self.COLORS["text"],
        )
        self.tasks_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.history_text = ctk.CTkTextbox(
            self.tabview.tab("History"), font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0f0f23", text_color=self.COLORS["text"],
        )
        self.history_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.messages_text = ctk.CTkTextbox(
            self.tabview.tab("Messages"), font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0f0f23", text_color=self.COLORS["text"],
        )
        self.messages_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Stats bar
        self.stats_frame = ctk.CTkFrame(main, fg_color=self.COLORS["bg_card"], corner_radius=10, height=50)
        self.stats_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self.stats_labels: dict[str, ctk.CTkLabel] = {}
        for i, (key, label) in enumerate([
            ("pending", "Pending"), ("running", "Running"),
            ("completed", "Completed"), ("failed", "Failed"),
        ]):
            frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
            frame.pack(side="left", expand=True, fill="x", padx=10, pady=8)
            ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=11),
                         text_color=self.COLORS["text_dim"]).pack()
            val_label = ctk.CTkLabel(frame, text="0", font=ctk.CTkFont(size=20, weight="bold"),
                                     text_color=self.COLORS["accent"])
            val_label.pack()
            self.stats_labels[key] = val_label

    def _build_agent_cards(self) -> None:
        for widget in self.agents_frame.winfo_children():
            widget.destroy()

        agents = self.orchestrator.get_agent_status()
        for i, agent in enumerate(agents):
            card = ctk.CTkFrame(self.agents_frame, fg_color=self.COLORS["bg_card"],
                                corner_radius=10, width=150, height=80)
            card.pack(side="left", padx=5, pady=5)
            card.pack_propagate(False)

            status_color = self.COLORS["success"] if agent["running"] else self.COLORS["text_dim"]
            ctk.CTkLabel(
                card, text=f"● {agent['name'].title()}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=status_color,
            ).pack(padx=10, pady=(10, 2), anchor="w")

            caps = ", ".join(agent["capabilities"][:2])
            ctk.CTkLabel(
                card, text=caps, font=ctk.CTkFont(size=10),
                text_color=self.COLORS["text_dim"],
            ).pack(padx=10, anchor="w")

    def _run_workflow(self, workflow_name: str) -> None:
        def _run() -> None:
            self.orchestrator.run_workflow(workflow_name)
            if not self.orchestrator.executor.is_running:
                self.orchestrator.start_executor()

        threading.Thread(target=_run, daemon=True).start()
        self._log_task(f"▶ Queued workflow: {workflow_name}")

    def _plan_and_run(self) -> None:
        goal = self.goal_entry.get().strip()
        if not goal:
            return

        def _run() -> None:
            result = self.orchestrator.run_task(
                name=f"Plan: {goal[:30]}",
                agent="planner",
                action="analyze_goal",
                params={"goal": goal},
                execute_now=True,
            )
            if result.result:
                workflow = result.result.get("recommended_workflow")
                if workflow:
                    self.orchestrator.run_workflow(workflow)
                    if not self.orchestrator.executor.is_running:
                        self.orchestrator.start_executor()

        threading.Thread(target=_run, daemon=True).start()
        self._log_task(f"🎯 Planning goal: {goal}")

    def _toggle_executor(self) -> None:
        if self.orchestrator.executor.is_running:
            self.orchestrator.stop_executor()
            self.executor_btn.configure(text="▶  Start Executor", fg_color=self.COLORS["success"])
            self.status_label.configure(text="● Idle", text_color=self.COLORS["text_dim"])
        else:
            self.orchestrator.start_executor()
            self.executor_btn.configure(text="⏸  Stop Executor", fg_color=self.COLORS["warning"])
            self.status_label.configure(text="● Running", text_color=self.COLORS["success"])

    def _stop_all(self) -> None:
        self.orchestrator.stop_all()
        self.executor_btn.configure(text="▶  Start Executor", fg_color=self.COLORS["success"])
        self.status_label.configure(text="● Stopped", text_color=self.COLORS["danger"])

    def _on_status_update(self, status: dict[str, Any]) -> None:
        self.after(0, lambda: self._update_display(status))

    def _update_display(self, status: dict[str, Any]) -> None:
        stats = status.get("task_stats", {})
        for key, label in self.stats_labels.items():
            label.configure(text=str(stats.get(key, 0)))

        self.tasks_text.delete("1.0", "end")
        for task in self.orchestrator.planner.get_queue():
            icon = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}.get(
                task.status.value, "•"
            )
            self.tasks_text.insert("end", f"{icon} [{task.agent}] {task.name} — {task.status.value}\n")

        self.history_text.delete("1.0", "end")
        for entry in self.orchestrator.history.get_recent(30):
            self.history_text.insert(
                "end",
                f"[{entry.status}] {entry.agent}.{entry.action} — {entry.timestamp:.0f}\n",
            )

        self.messages_text.delete("1.0", "end")
        for msg in self.orchestrator.message_bus.get_history(20):
            self.messages_text.insert(
                "end",
                f"{msg.sender} → {msg.recipient} [{msg.message_type}]\n",
            )

    def _log_task(self, message: str) -> None:
        self.tasks_text.insert("end", f"{message}\n")

    def _schedule_refresh(self) -> None:
        self._update_display(self.orchestrator.get_system_status())
        self.after(self._refresh_ms, self._schedule_refresh)

    def on_closing(self) -> None:
        self.orchestrator.stop_all()
        self.destroy()