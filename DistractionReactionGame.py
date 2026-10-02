"""
Distraction-Based Reaction Game
ITEC80D - Human Computer Interaction | Laboratory Exercise No. 2

Developer : SURNAME, FIRSTNAME
Framework : Tkinter (Python 3.x)

Enhancements beyond the guide:
- Score system
- Personal-best reaction-time feedback
- Optional sound on errors

Task:
    Click the centre box as soon as it turns GREEN.

Conditions:
    A = low-distraction interface (plain screen)
    B = high-distraction interface (moving/changing shapes and decoy text)

The task, target, timing rules, and number of trials are identical in both
conditions. Every trial remains stored as a dictionary in self.results,
displayed in the interaction log, summarized in the results panel, and
saved to CSV exactly as in the original implementation.
"""

from __future__ import annotations

import csv
import os
import random
import re
import statistics
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk


# ============================================================================
# APPLICATION CONFIGURATION
# Keep experimental timing and task rules fixed for all participants.
# ============================================================================

APP_TITLE = "Distraction-Based Reaction Game"
APP_SUBTITLE = "Human–Computer Interaction • Reaction Time Study"

TRIALS_PER_CONDITION = 10
MIN_WAIT_MS = 1500
MAX_WAIT_MS = 4000
RESPONSE_TIMEOUT_MS = 2000
FEEDBACK_PAUSE_MS = 1200
COUNTDOWN_STEP_MS = 800
DISTRACTOR_REFRESH_MS = 400

MAX_POINTS_PER_TRIAL = 100
NUM_DISTRACTORS = 10

CANVAS_W, CANVAS_H = 600, 320
TARGET_BOX = (220, 110, 380, 210)

# Typography
FONT_FAMILY = "Segoe UI"
MONO_FONT = "Cascadia Mono"

# Theme palette
COLOR_APP_BG = "#F5F7FB"
COLOR_SURFACE = "#FFFFFF"
COLOR_SURFACE_ALT = "#EEF2F7"
COLOR_BORDER = "#D9E0E8"
COLOR_TEXT = "#182230"
COLOR_MUTED = "#687586"

COLOR_WAIT = "#8B95A3"
COLOR_GO = "#2EBD74"
COLOR_GOOD = "#198754"
COLOR_BAD = "#D64545"
COLOR_ACCENT = "#4F46E5"
COLOR_ACCENT_DARK = "#3730A3"
COLOR_TARGET_OUTLINE = "#5D6875"
COLOR_GAME_BG = "#FBFCFE"

# Distractors never use green, so only the target is ever green.
DISTRACTOR_COLORS = [
    "#E65A4F",
    "#F1A43C",
    "#8B5CF6",
    "#4096D8",
    "#E94E91",
    "#D5B83D",
    "#17A5BB",
    "#EE7756",
]
DISTRACTOR_TEXTS = ["WIN!", "NEW!", "CLICK ME!", "BONUS", "HOT!"]

AGE_GROUPS = ["Below 18", "18-20", "21-23", "24-26", "27 and above"]
EXPERIENCE_LEVELS = ["Beginner", "Intermediate", "Advanced"]
ORDER_OPTIONS = ["A then B", "B then A"]

CONDITIONS = {
    "A": {"name": "Low-distraction", "level": "Low", "distractors": 0},
    "B": {
        "name": "High-distraction",
        "level": "High",
        "distractors": NUM_DISTRACTORS,
    },
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "raw_interaction_data")
DATA_FILE = os.path.join(DATA_FOLDER, "raw_data.csv")

CSV_FIELDS = [
    "participant_id",
    "age_group",
    "experience_level",
    "session",
    "condition_order",
    "condition",
    "distraction_level",
    "trial",
    "task",
    "stimulus_type",
    "wait_ms",
    "expected_response",
    "actual_response",
    "reaction_time_ms",
    "correct",
    "early_click",
    "error_type",
    "error_count",
    "stray_clicks",
    "timestamp",
    "session_status",
]


# ============================================================================
# DATA / UTILITY FUNCTIONS
# ============================================================================


def is_valid_participant_code(code):
    """Participant codes must look like P01, P02 ... P99 or P100."""
    return re.fullmatch(r"P\d{2,3}", code) is not None


def summarize(records):
    """Return descriptive statistics for a list of trial dictionaries."""
    total = len(records)
    correct_records = [record for record in records if record["correct"]]
    times = [
        record["reaction_time_ms"]
        for record in correct_records
        if record["reaction_time_ms"] is not None
    ]

    return {
        "trials": total,
        "correct": len(correct_records),
        "accuracy": 100 * len(correct_records) / total if total else 0.0,
        "error_rate": 100 * (total - len(correct_records)) / total if total else 0.0,
        "early_clicks": sum(1 for record in records if record["early_click"]),
        "distractor_clicks": sum(
            1 for record in records if record["error_type"] == "distractor_click"
        ),
        "misses": sum(
            1 for record in records if record["error_type"] == "delayed_response"
        ),
        "stray_clicks": sum(record["stray_clicks"] for record in records),
        "mean": statistics.mean(times) if times else None,
        "median": statistics.median(times) if times else None,
        "min": min(times) if times else None,
        "max": max(times) if times else None,
        "sd": statistics.stdev(times) if len(times) > 1 else None,
    }


def format_ms(value):
    """Format a millisecond value for display."""
    return "n/a" if value is None else f"{value:.1f} ms"


def format_record_line(record):
    """Return one presentation line for the interaction log."""
    if record["correct"]:
        outcome = f"{record['reaction_time_ms']:.0f} ms   CORRECT"
    else:
        outcome = "-- ms   " + record["error_type"].replace("_", " ").upper()
    return f"{record['condition']} | Trial {record['trial']:>2} | {outcome}"


def write_rows(path, records, status, append=True):
    """Write trial records to CSV; add a header only when starting a new file."""
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    write_header = (not append) or (not os.path.isfile(path))

    with open(
        path,
        "a" if append else "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)

        if write_header:
            writer.writeheader()

        for record in records:
            row = dict(record)
            row["correct"] = "Yes" if record["correct"] else "No"
            row["early_click"] = "Yes" if record["early_click"] else "No"
            row["session_status"] = status
            writer.writerow(row)


def session_already_saved(code, session):
    """Return True when a complete session already exists for the participant."""
    if not os.path.isfile(DATA_FILE):
        return False

    try:
        with open(DATA_FILE, newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                if (
                    row["participant_id"] == code
                    and row["session"] == str(session)
                    and row["session_status"] == "complete"
                ):
                    return True
    except (OSError, KeyError):
        return False

    return False


# ============================================================================
# MAIN APPLICATION
# ============================================================================


class DistractionReactionGame:
    """Tkinter application for the two-condition reaction-time experiment."""

    def __init__(self, root):
        self.root = root

        # Window configuration.
        self.root.title(APP_TITLE)
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_APP_BG)

        # Data storage: one dictionary per trial.
        self.results = []
        self.session_info = {}

        # Game state.
        self.state = "IDLE"
        self.condition_sequence = []
        self.condition_index = 0
        self.current_condition = "A"
        self.trial_number = 0
        self.stimulus_time = 0.0
        self.current_wait_ms = 0
        self.stray_clicks = 0

        # Enhancements retained from the original implementation.
        self.score = 0
        self.best_rt = None

        # Scheduled callbacks (cancel safely on Reset/Exit).
        self.jobs = {
            "wait": None,
            "timeout": None,
            "feedback": None,
            "countdown": None,
            "distractor": None,
        }

        self._configure_styles()
        self._build_variables()
        self.build_widgets()
        self.reset_display()

        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Put the participant code field in focus immediately.
        self.code_entry.focus_set()

    # ------------------------------------------------------------------
    # Theme / widgets
    # ------------------------------------------------------------------

    def _configure_styles(self):
        """Configure a consistent ttk theme without changing game behavior."""
        style = ttk.Style(self.root)

        # Use a native theme when available, while overriding the relevant
        # controls for a consistent cross-platform appearance.
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            ".",
            font=(FONT_FAMILY, 10),
            background=COLOR_APP_BG,
            foreground=COLOR_TEXT,
        )
        style.configure(
            "App.TFrame",
            background=COLOR_APP_BG,
        )
        style.configure(
            "Card.TFrame",
            background=COLOR_SURFACE,
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Section.TLabelframe",
            background=COLOR_SURFACE,
            foreground=COLOR_TEXT,
            bordercolor=COLOR_BORDER,
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Section.TLabelframe.Label",
            background=COLOR_SURFACE,
            foreground=COLOR_TEXT,
            font=(FONT_FAMILY, 10, "bold"),
        )
        style.configure(
            "Field.TLabel",
            background=COLOR_SURFACE,
            foreground=COLOR_MUTED,
            font=(FONT_FAMILY, 9, "bold"),
        )
        style.configure(
            "Value.TLabel",
            background=COLOR_SURFACE,
            foreground=COLOR_TEXT,
        )
        style.configure(
            "Primary.TButton",
            background=COLOR_ACCENT,
            foreground="white",
            borderwidth=0,
            padding=(16, 9),
            font=(FONT_FAMILY, 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("active", COLOR_ACCENT_DARK), ("disabled", "#AAB1C0")],
            foreground=[("disabled", "#EFF1F6")],
        )
        style.configure(
            "Secondary.TButton",
            background=COLOR_SURFACE_ALT,
            foreground=COLOR_TEXT,
            borderwidth=0,
            padding=(12, 9),
            font=(FONT_FAMILY, 10, "bold"),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#E2E7EE"), ("disabled", "#E9EDF2")],
            foreground=[("disabled", "#9AA3AF")],
        )
        style.configure(
            "TEntry",
            fieldbackground=COLOR_SURFACE,
            foreground=COLOR_TEXT,
            padding=7,
        )
        style.configure(
            "TCombobox",
            fieldbackground=COLOR_SURFACE,
            foreground=COLOR_TEXT,
            padding=6,
        )
        style.configure(
            "TSpinbox",
            fieldbackground=COLOR_SURFACE,
            foreground=COLOR_TEXT,
            padding=6,
        )
        style.configure(
            "Info.TLabel",
            background=COLOR_SURFACE_ALT,
            foreground=COLOR_MUTED,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "Status.TLabel",
            background=COLOR_SURFACE_ALT,
            foreground=COLOR_TEXT,
            font=(FONT_FAMILY, 9, "bold"),
        )
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=COLOR_SURFACE_ALT,
            background=COLOR_ACCENT,
            lightcolor=COLOR_ACCENT,
            darkcolor=COLOR_ACCENT,
            bordercolor=COLOR_SURFACE_ALT,
        )

    def _build_variables(self):
        """Create Tkinter variables used by the form and status display."""
        self.code_var = tk.StringVar()
        self.age_var = tk.StringVar()
        self.experience_var = tk.StringVar()
        self.session_var = tk.StringVar(value="1")
        self.order_var = tk.StringVar(value=ORDER_OPTIONS[0])

        self.status_var = tk.StringVar()
        self.part_var = tk.StringVar()
        self.trial_var = tk.StringVar()
        self.score_var = tk.StringVar()

        self.sound_var = tk.BooleanVar(value=False)

    def build_widgets(self):
        """Build the application shell and all UI sections."""
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_rowconfigure(3, weight=0)
        self.root.grid_rowconfigure(4, weight=0)

        self.build_header()
        self.build_participant_panel()
        self.build_control_bar()
        self.build_status_bar()
        self.build_game_area()
        self.build_results_panel()

    def build_header(self):
        """Build the title and concise game instructions."""
        header = ttk.Frame(self.root, style="App.TFrame")
        header.grid(
            row=0,
            column=0,
            columnspan=2,
            padx=28,
            pady=(22, 12),
            sticky="ew",
        )

        title = tk.Label(
            header,
            text=APP_TITLE,
            font=(FONT_FAMILY, 24, "bold"),
            bg=COLOR_APP_BG,
            fg=COLOR_TEXT,
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            header,
            text=APP_SUBTITLE,
            font=(FONT_FAMILY, 10),
            bg=COLOR_APP_BG,
            fg=COLOR_MUTED,
        )
        subtitle.pack(anchor="w", pady=(2, 9))

        instruction_text = (
            "Wait for the centre box to turn GREEN and show “CLICK NOW!”, "
            "then click as quickly as possible. Ignore every other object."
        )
        instructions = tk.Label(
            header,
            text=instruction_text,
            font=(FONT_FAMILY, 10),
            bg=COLOR_SURFACE_ALT,
            fg=COLOR_TEXT,
            anchor="w",
            justify="left",
            padx=14,
            pady=10,
        )
        instructions.pack(fill="x")

    def build_participant_panel(self):
        """Build the anonymous participant and session details card."""
        frame = ttk.LabelFrame(
            self.root,
            text="  Participant details  ",
            style="Section.TLabelframe",
        )
        frame.grid(
            row=1,
            column=0,
            columnspan=2,
            padx=28,
            pady=4,
            sticky="ew",
        )

        fields = [
            ("Anonymous code", "code"),
            ("Age group", "age"),
            ("Experience", "experience"),
            ("Session #", "session"),
            ("Condition order", "order"),
        ]

        for column, (label_text, field_key) in enumerate(fields):
            frame.grid_columnconfigure(column, weight=1)

            ttk.Label(
                frame,
                text=label_text.upper(),
                style="Field.TLabel",
            ).grid(
                row=0,
                column=column,
                padx=(14 if column == 0 else 8, 8),
                pady=(12, 5),
                sticky="w",
            )

            if field_key == "code":
                widget = ttk.Entry(
                    frame,
                    textvariable=self.code_var,
                    width=13,
                )
                self.code_entry = widget
            elif field_key == "age":
                widget = ttk.Combobox(
                    frame,
                    textvariable=self.age_var,
                    values=AGE_GROUPS,
                    state="readonly",
                    width=16,
                )
                age_widget = widget
            elif field_key == "experience":
                widget = ttk.Combobox(
                    frame,
                    textvariable=self.experience_var,
                    values=EXPERIENCE_LEVELS,
                    state="readonly",
                    width=16,
                )
                experience_widget = widget
            elif field_key == "session":
                widget = ttk.Spinbox(
                    frame,
                    from_=1,
                    to=20,
                    textvariable=self.session_var,
                    width=7,
                )
                session_widget = widget
            else:
                widget = ttk.Combobox(
                    frame,
                    textvariable=self.order_var,
                    values=ORDER_OPTIONS,
                    state="readonly",
                    width=13,
                )
                order_widget = widget

            widget.grid(
                row=1,
                column=column,
                padx=(14 if column == 0 else 8, 8),
                pady=(0, 12),
                sticky="ew",
            )

        ttk.Label(
            frame,
            text="Use a code such as P01 or P12. Do not enter your real name.",
            style="Info.TLabel",
        ).grid(
            row=2,
            column=0,
            columnspan=5,
            padx=14,
            pady=(0, 10),
            sticky="w",
        )

        self.input_widgets = [
            self.code_entry,
            age_widget,
            experience_widget,
            session_widget,
            order_widget,
        ]

    def build_control_bar(self):
        """Build the main action buttons."""
        bar = ttk.Frame(self.root, style="App.TFrame")
        bar.grid(
            row=2,
            column=0,
            columnspan=2,
            padx=28,
            pady=(10, 5),
            sticky="ew",
        )

        self.start_btn = ttk.Button(
            bar,
            text="▶  Start Game",
            command=self.start_game,
            style="Primary.TButton",
        )
        self.reset_btn = ttk.Button(
            bar,
            text="Reset",
            command=self.reset_game,
            style="Secondary.TButton",
        )
        self.restart_btn = ttk.Button(
            bar,
            text="Restart",
            command=self.restart_game,
            style="Secondary.TButton",
        )
        self.export_btn = ttk.Button(
            bar,
            text="Export CSV",
            command=self.export_csv,
            style="Secondary.TButton",
        )
        self.help_btn = ttk.Button(
            bar,
            text="Help",
            command=self.show_help,
            style="Secondary.TButton",
        )
        self.exit_btn = ttk.Button(
            bar,
            text="Exit",
            command=self.exit_app,
            style="Secondary.TButton",
        )

        button_group = [self.start_btn, self.reset_btn, self.restart_btn]
        utility_group = [self.export_btn, self.help_btn, self.exit_btn]

        for button in button_group:
            button.pack(side="left", padx=(0, 7))

        ttk.Separator(bar, orient="vertical").pack(
            side="left",
            fill="y",
            padx=5,
            pady=2,
        )

        for button in utility_group:
            button.pack(side="left", padx=(7, 0))

        ttk.Checkbutton(
            bar,
            text="Sound on errors",
            variable=self.sound_var,
        ).pack(side="right", padx=4)

    def build_status_bar(self):
        """Build the live session status and progress strip."""
        card = tk.Frame(
            self.root,
            bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            bd=0,
        )
        card.grid(
            row=3,
            column=0,
            columnspan=2,
            padx=28,
            pady=(8, 8),
            sticky="new",
        )

        status_left = tk.Frame(card, bg=COLOR_SURFACE)
        status_left.pack(
            side="left",
            fill="x",
            expand=True,
            padx=14,
            pady=11,
        )

        self.status_badge = tk.Label(
            status_left,
            textvariable=self.status_var,
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_SURFACE_ALT,
            fg=COLOR_TEXT,
            padx=10,
            pady=6,
        )
        self.status_badge.pack(side="left", padx=(0, 7))

        for variable, prefix in (
            (self.part_var, "Part"),
            (self.trial_var, "Trial"),
            (self.score_var, "Score"),
        ):
            label = tk.Label(
                status_left,
                textvariable=variable,
                font=(FONT_FAMILY, 10, "bold"),
                bg=COLOR_SURFACE,
                fg=COLOR_TEXT,
                padx=8,
            )
            label.pack(side="left")

        self.progress = ttk.Progressbar(
            card,
            length=260,
            mode="determinate",
            maximum=TRIALS_PER_CONDITION * len(CONDITIONS),
        )
        self.progress.pack(
            side="right",
            padx=(10, 16),
            pady=15,
        )

        # The game/results panels are placed in their own row beneath the bar.
        self.root.grid_rowconfigure(4, weight=1)

    def build_game_area(self):
        """Build the reaction-game canvas and feedback area."""
        left = tk.Frame(
            self.root,
            bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            bd=0,
        )
        left.grid(
            row=4,
            column=0,
            padx=(28, 10),
            pady=(0, 22),
            sticky="n",
        )

        title_row = tk.Frame(left, bg=COLOR_SURFACE)
        title_row.pack(fill="x", padx=16, pady=(15, 8))

        tk.Label(
            title_row,
            text="Reaction Area",
            font=(FONT_FAMILY, 12, "bold"),
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
        ).pack(side="left")

        self.condition_badge = tk.Label(
            title_row,
            text="Condition —",
            font=(FONT_FAMILY, 9, "bold"),
            bg=COLOR_SURFACE_ALT,
            fg=COLOR_MUTED,
            padx=9,
            pady=4,
        )
        self.condition_badge.pack(side="right")

        canvas_frame = tk.Frame(
            left,
            bg=COLOR_SURFACE_ALT,
            padx=10,
            pady=10,
        )
        canvas_frame.pack(padx=16, pady=(0, 4))

        self.canvas = tk.Canvas(
            canvas_frame,
            width=CANVAS_W,
            height=CANVAS_H,
            bg=COLOR_GAME_BG,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            bd=0,
        )
        self.canvas.pack()

        self.target_rect = self.canvas.create_rectangle(
            *TARGET_BOX,
            fill=COLOR_WAIT,
            outline=COLOR_TARGET_OUTLINE,
            width=3,
            tags=("target",),
        )

        center_x = (TARGET_BOX[0] + TARGET_BOX[2]) // 2
        center_y = (TARGET_BOX[1] + TARGET_BOX[3]) // 2

        self.target_text = self.canvas.create_text(
            center_x,
            center_y,
            text="",
            font=(FONT_FAMILY, 18, "bold"),
            fill="white",
            tags=("target",),
        )

        self.banner_text = self.canvas.create_text(
            CANVAS_W // 2,
            40,
            text="",
            font=(FONT_FAMILY, 16, "bold"),
            fill=COLOR_TEXT,
        )

        self.canvas.bind("<Button-1>", self.on_canvas_click)

        self.feedback_label = tk.Label(
            left,
            text="",
            font=(FONT_FAMILY, 12, "bold"),
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            height=2,
            wraplength=CANVAS_W,
            justify="center",
        )
        self.feedback_label.pack(
            fill="x",
            padx=18,
            pady=(7, 13),
        )

    def build_results_panel(self):
        """Build the interaction log and session results panel."""
        right = tk.Frame(
            self.root,
            bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            bd=0,
        )
        right.grid(
            row=4,
            column=1,
            padx=(10, 28),
            pady=(0, 22),
            sticky="n",
        )

        tk.Label(
            right,
            text="Session Overview",
            font=(FONT_FAMILY, 12, "bold"),
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
        ).pack(
            anchor="w",
            padx=16,
            pady=(15, 8),
        )

        list_frame = tk.Frame(
            right,
            bg=COLOR_SURFACE_ALT,
            padx=8,
            pady=8,
        )
        list_frame.pack(
            fill="x",
            padx=16,
        )

        self.listbox = tk.Listbox(
            list_frame,
            width=49,
            height=11,
            font=(MONO_FONT, 9),
            bg=COLOR_GAME_BG,
            fg=COLOR_TEXT,
            selectbackground="#DDE3FF",
            selectforeground=COLOR_TEXT,
            relief="flat",
            bd=0,
            activestyle="none",
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.listbox.yview,
        )
        self.listbox.configure(yscrollcommand=scrollbar.set)

        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")

        tk.Label(
            right,
            text="Results",
            font=(FONT_FAMILY, 11, "bold"),
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
        ).pack(
            anchor="w",
            padx=16,
            pady=(13, 7),
        )

        text_frame = tk.Frame(
            right,
            bg=COLOR_SURFACE_ALT,
            padx=8,
            pady=8,
        )
        text_frame.pack(
            fill="x",
            padx=16,
        )

        self.results_text = tk.Text(
            text_frame,
            width=49,
            height=15,
            font=(MONO_FONT, 9),
            state="disabled",
            bg=COLOR_GAME_BG,
            fg=COLOR_TEXT,
            wrap="word",
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=8,
            pady=8,
        )
        text_scroll = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.results_text.yview,
        )
        self.results_text.configure(yscrollcommand=text_scroll.set)

        self.results_text.pack(side="left", fill="both", expand=True)
        text_scroll.pack(side="left", fill="y")

        tk.Label(
            right,
            text="Data are automatically saved to raw_interaction_data/raw_data.csv.",
            font=(FONT_FAMILY, 8),
            bg=COLOR_SURFACE,
            fg=COLOR_MUTED,
            anchor="w",
            justify="left",
        ).pack(
            anchor="w",
            padx=16,
            pady=(8, 15),
        )

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def set_target(self, text, fill):
        self.canvas.itemconfigure(self.target_rect, fill=fill)
        self.canvas.itemconfigure(self.target_text, text=text)

    def set_banner(self, text):
        self.canvas.itemconfigure(self.banner_text, text=text)

    def set_feedback(self, text, color):
        self.feedback_label.configure(text=text, fg=color)

    def set_results_text(self, text):
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert(tk.END, text)
        self.results_text.configure(state="disabled")

    def update_trial_label(self):
        self.trial_var.set(f"Trial {self.trial_number} / {TRIALS_PER_CONDITION}")

    def update_score_label(self):
        self.score_var.set(f"Score {self.score}")

    def update_condition_badge(self):
        """Update only the visual condition label; experimental behavior is unchanged."""
        if not self.condition_sequence:
            self.condition_badge.configure(text="Condition —")
            return

        condition = CONDITIONS[self.current_condition]
        self.condition_badge.configure(
            text=f"{self.current_condition}  •  {condition['name']}",
        )

    def update_status_visual(self, text):
        """Keep the status badge visually aligned with the current state."""
        self.status_var.set(text)

        if text.startswith("Status: GO"):
            self.status_badge.configure(
                bg="#E7F8EF",
                fg=COLOR_GOOD,
            )
        elif "error" in text.lower() or "failed" in text.lower():
            self.status_badge.configure(
                bg="#FBEAEA",
                fg=COLOR_BAD,
            )
        elif "complete" in text.lower():
            self.status_badge.configure(
                bg="#E7F8EF",
                fg=COLOR_GOOD,
            )
        else:
            self.status_badge.configure(
                bg=COLOR_SURFACE_ALT,
                fg=COLOR_TEXT,
            )

    def points_for(self, record):
        """Score: 0 for an error; otherwise 100 minus 1 point per 10 ms, min 10."""
        if not record["correct"]:
            return 0
        return max(10, MAX_POINTS_PER_TRIAL - int(record["reaction_time_ms"] // 10))

    def set_inputs_enabled(self, enabled):
        for widget in self.input_widgets:
            if not enabled:
                widget.configure(state="disabled")
            elif isinstance(widget, ttk.Combobox):
                widget.configure(state="readonly")
            else:
                widget.configure(state="normal")

    def refresh_controls(self):
        """Disable controls that should not be used while a game is running."""
        running = self.state not in ("IDLE", "FINISHED")

        self.start_btn.state(["disabled"] if running else ["!disabled"])
        self.export_btn.state(
            ["disabled"] if (running or not self.results) else ["!disabled"]
        )
        self.set_inputs_enabled(not running)

    def reset_display(self):
        """Return the interface to the initial state while keeping participant fields."""
        self.cancel_all()

        self.results = []
        self.state = "IDLE"
        self.trial_number = 0
        self.score = 0
        self.best_rt = None
        self.condition_sequence = []
        self.condition_index = 0
        self.current_condition = "A"

        self.update_score_label()
        self.update_condition_badge()

        self.canvas.delete("distractor")
        self.set_target("", COLOR_WAIT)
        self.set_banner("Press Start Game when ready")
        self.set_feedback("", COLOR_TEXT)
        self.listbox.delete(0, tk.END)
        self.set_results_text("Results will appear here after the session.")

        self.update_status_visual("Status: Ready")
        self.part_var.set("Part —")
        self.update_trial_label()
        self.progress["value"] = 0

        self.refresh_controls()

    # ------------------------------------------------------------------
    # Scheduling helpers
    # ------------------------------------------------------------------

    def schedule(self, name, delay_ms, callback):
        self.cancel(name)
        self.jobs[name] = self.root.after(delay_ms, callback)

    def cancel(self, name):
        if self.jobs[name] is not None:
            try:
                self.root.after_cancel(self.jobs[name])
            except (tk.TclError, ValueError):
                pass
            finally:
                self.jobs[name] = None

    def cancel_all(self):
        for name in self.jobs:
            self.cancel(name)

    # ------------------------------------------------------------------
    # Input validation / session start
    # ------------------------------------------------------------------

    def read_participant_info(self):
        """Validate participant fields and return a session dictionary."""
        code = self.code_var.get().strip().upper()

        if not is_valid_participant_code(code):
            messagebox.showwarning(
                "Invalid code",
                "Enter an anonymous code such as P01 or P12.",
            )
            return None

        if not self.age_var.get():
            messagebox.showwarning(
                "Missing information",
                "Please select an age group.",
            )
            return None

        if not self.experience_var.get():
            messagebox.showwarning(
                "Missing information",
                "Please select an experience level.",
            )
            return None

        try:
            session = int(self.session_var.get())
            if session < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Invalid session",
                "Session number must be a whole number (1 or more).",
            )
            return None

        self.code_var.set(code)

        return {
            "participant_id": code,
            "age_group": self.age_var.get(),
            "experience_level": self.experience_var.get(),
            "session": session,
            "condition_order": self.order_var.get(),
        }

    def start_game(self):
        if self.state not in ("IDLE", "FINISHED"):
            return

        info = self.read_participant_info()
        if info is None:
            return

        if session_already_saved(info["participant_id"], info["session"]):
            if not messagebox.askyesno(
                "Possible duplicate",
                f"{info['participant_id']} session {info['session']} is already saved.\n"
                "Continue anyway? (the new rows will be saved as another run)",
            ):
                return

        self.reset_display()

        self.session_info = info
        self.condition_sequence = (
            ["A", "B"] if info["condition_order"] == "A then B" else ["B", "A"]
        )
        self.condition_index = 0

        self.begin_condition()

    def restart_game(self):
        if self.reset_game():
            self.start_game()

    def reset_game(self):
        """Stop a running session and save partial data as incomplete."""
        running = self.state not in ("IDLE", "FINISHED")

        if running:
            if not messagebox.askyesno(
                "Reset",
                "A session is in progress.\n"
                "Reset now? Partial data will be saved as 'incomplete'.",
            ):
                return False

            self.cancel_all()

            if self.results:
                self.save_session("incomplete")

        self.reset_display()
        return True

    # ------------------------------------------------------------------
    # Game flow
    # ------------------------------------------------------------------

    def begin_condition(self):
        self.current_condition = self.condition_sequence[self.condition_index]
        self.trial_number = 0

        self.part_var.set(
            f"Part {self.condition_index + 1} of {len(self.condition_sequence)}"
        )
        self.update_trial_label()
        self.update_condition_badge()

        if CONDITIONS[self.current_condition]["distractors"] > 0:
            self.distractor_loop()

        self.run_countdown(3)

    def run_countdown(self, remaining):
        self.state = "COUNTDOWN"
        self.refresh_controls()

        if remaining == 0:
            self.set_banner("")
            self.next_trial()
            return

        self.set_target("", COLOR_WAIT)
        self.set_banner(f"Get ready...  {remaining}")
        self.set_feedback("", COLOR_TEXT)
        self.update_status_visual("Status: Get ready")

        self.schedule(
            "countdown",
            COUNTDOWN_STEP_MS,
            lambda: self.run_countdown(remaining - 1),
        )

    def next_trial(self):
        self.trial_number += 1
        self.stray_clicks = 0
        self.state = "WAITING"

        self.set_banner("")
        self.set_target("WAIT", COLOR_WAIT)
        self.set_feedback("Wait for the GREEN box...", COLOR_TEXT)
        self.update_status_visual("Status: Waiting for the green box")
        self.update_trial_label()

        self.current_wait_ms = random.randint(MIN_WAIT_MS, MAX_WAIT_MS)
        self.schedule("wait", self.current_wait_ms, self.show_stimulus)

    def show_stimulus(self):
        self.state = "STIMULUS"

        self.set_target("CLICK NOW!", COLOR_GO)
        self.set_feedback("Click the GREEN box now!", COLOR_GOOD)
        self.update_status_visual("Status: GO!")

        self.canvas.update_idletasks()
        self.stimulus_time = time.perf_counter()
        self.schedule("timeout", RESPONSE_TIMEOUT_MS, self.handle_timeout)

    def handle_timeout(self):
        self.finish_trial(
            False,
            "delayed_response",
            "no_response",
            None,
            False,
        )

    # ------------------------------------------------------------------
    # Mouse handling
    # ------------------------------------------------------------------

    def identify_click(self, x, y):
        """Return 'target', 'distractor' or 'background' for the click position."""
        tags = set()

        for item in self.canvas.find_overlapping(x, y, x, y):
            tags.update(self.canvas.gettags(item))

        if "target" in tags:
            return "target"
        if "distractor" in tags:
            return "distractor"
        return "background"

    def on_canvas_click(self, event):
        if self.state not in ("WAITING", "STIMULUS"):
            return

        clicked = self.identify_click(event.x, event.y)

        if clicked == "background":
            self.stray_clicks += 1
            return

        actual = (
            "target_box"
            if clicked == "target"
            else "distractor_object"
        )

        if self.state == "WAITING":
            self.finish_trial(
                False,
                "early_click",
                actual,
                None,
                True,
            )
            return

        reaction_ms = (time.perf_counter() - self.stimulus_time) * 1000

        if clicked == "target":
            self.finish_trial(
                True,
                "",
                actual,
                reaction_ms,
                False,
            )
        else:
            self.finish_trial(
                False,
                "distractor_click",
                actual,
                reaction_ms,
                False,
            )

    # ------------------------------------------------------------------
    # Trial recording / feedback
    # ------------------------------------------------------------------

    def build_record(self, correct, error_type, actual, reaction_ms, early):
        condition = CONDITIONS[self.current_condition]

        record = dict(self.session_info)
        record.update(
            {
                "condition": self.current_condition,
                "distraction_level": condition["level"],
                "trial": self.trial_number,
                "task": "Click the target box when it turns green",
                "stimulus_type": "Green target box",
                "wait_ms": self.current_wait_ms,
                "expected_response": "target_box",
                "actual_response": actual,
                "reaction_time_ms": (
                    round(reaction_ms, 2) if reaction_ms is not None else None
                ),
                "correct": correct,
                "early_click": early,
                "error_type": error_type,
                "error_count": 0 if correct else 1,
                "stray_clicks": self.stray_clicks,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )
        return record

    def finish_trial(self, correct, error_type, actual, reaction_ms, early):
        self.cancel("wait")
        self.cancel("timeout")

        self.state = "FEEDBACK"

        record = self.build_record(
            correct,
            error_type,
            actual,
            reaction_ms,
            early,
        )
        self.results.append(record)

        self.listbox.insert(tk.END, format_record_line(record))
        self.listbox.see(tk.END)

        self.progress["value"] = len(self.results)

        self.score += self.points_for(record)
        self.update_score_label()

        self.set_target("", COLOR_WAIT)
        self.show_feedback(record)
        self.update_status_visual("Status: Feedback")

        self.schedule(
            "feedback",
            FEEDBACK_PAUSE_MS,
            self.after_feedback,
        )

    def show_feedback(self, record):
        if record["correct"]:
            text = (
                f"CORRECT!  Reaction Time: "
                f"{record['reaction_time_ms']:.0f} ms"
                f"  (+{self.points_for(record)} pts)"
            )

            if self.best_rt is None or record["reaction_time_ms"] < self.best_rt:
                if self.best_rt is not None:
                    text += "\nNEW PERSONAL BEST!"
                self.best_rt = record["reaction_time_ms"]

            self.set_feedback(text, COLOR_GOOD)
            return

        if self.sound_var.get():
            self.root.bell()

        messages = {
            "early_click": "TOO EARLY! Wait for the GREEN box.",
            "distractor_click": "WRONG TARGET! Click only the green box.",
            "delayed_response": (
                f"TOO SLOW! No click within "
                f"{RESPONSE_TIMEOUT_MS // 1000} seconds."
            ),
        }

        self.set_feedback(
            messages[record["error_type"]],
            COLOR_BAD,
        )

    def after_feedback(self):
        if self.trial_number < TRIALS_PER_CONDITION:
            self.next_trial()
        else:
            self.finish_condition()

    def finish_condition(self):
        self.cancel("distractor")
        self.canvas.delete("distractor")

        self.condition_index += 1

        if self.condition_index < len(self.condition_sequence):
            messagebox.showinfo(
                "Part complete",
                f"Part {self.condition_index} of "
                f"{len(self.condition_sequence)} finished.\n"
                "Take a short break, then click OK to start the next part.",
            )
            self.begin_condition()
        else:
            self.finish_session()

    def finish_session(self):
        self.cancel_all()
        self.state = "FINISHED"

        saved = self.save_session("complete")

        self.show_results()
        self.set_target("DONE", COLOR_WAIT)
        self.set_banner("")
        self.set_feedback("Session complete. Thank you!", COLOR_GOOD)

        self.update_status_visual(
            "Status: Complete - data saved"
            if saved
            else "Status: Complete - SAVE FAILED"
        )
        self.refresh_controls()

        if saved:
            messagebox.showinfo(
                "Finished",
                f"Session complete!\nData saved to:\n{DATA_FILE}",
            )

    # ------------------------------------------------------------------
    # High-distraction condition
    # ------------------------------------------------------------------

    def distractor_loop(self):
        self.draw_distractors()
        self.schedule(
            "distractor",
            DISTRACTOR_REFRESH_MS,
            self.distractor_loop,
        )

    def random_position_outside_target(self):
        """Pick a point outside the target box plus a safety margin."""
        margin = 35
        x1, y1, x2, y2 = TARGET_BOX

        for _ in range(60):
            x = random.randint(30, CANVAS_W - 30)
            y = random.randint(30, CANVAS_H - 30)

            if not (
                x1 - margin < x < x2 + margin
                and y1 - margin < y < y2 + margin
            ):
                return x, y

        return 40, 40

    def draw_distractors(self):
        self.canvas.delete("distractor")

        for index in range(
            CONDITIONS[self.current_condition]["distractors"]
        ):
            x, y = self.random_position_outside_target()
            color = random.choice(DISTRACTOR_COLORS)
            size = random.randint(14, 30)

            if index < 2:
                self.canvas.create_text(
                    x,
                    y,
                    text=random.choice(DISTRACTOR_TEXTS),
                    fill=color,
                    font=(FONT_FAMILY, 14, "bold"),
                    tags=("distractor",),
                )
                continue

            shape = random.choice(("oval", "rect", "triangle"))

            if shape == "oval":
                self.canvas.create_oval(
                    x - size,
                    y - size,
                    x + size,
                    y + size,
                    fill=color,
                    outline="",
                    tags=("distractor",),
                )
            elif shape == "rect":
                self.canvas.create_rectangle(
                    x - size,
                    y - size,
                    x + size,
                    y + size,
                    fill=color,
                    outline="",
                    tags=("distractor",),
                )
            else:
                self.canvas.create_polygon(
                    x,
                    y - size,
                    x - size,
                    y + size,
                    x + size,
                    y + size,
                    fill=color,
                    outline="",
                    tags=("distractor",),
                )

        self.canvas.tag_lower("distractor")

    # ------------------------------------------------------------------
    # Results / saving / export
    # ------------------------------------------------------------------

    def show_results(self):
        lines = []
        summaries = {}

        for key in ("A", "B"):
            records = [
                record
                for record in self.results
                if record["condition"] == key
            ]
            stats = summarize(records)
            summaries[key] = stats

            lines += [
                f"CONDITION {key} - {CONDITIONS[key]['name']}",
                (
                    f"  Trials: {stats['trials']}   "
                    f"Correct: {stats['correct']} ({stats['accuracy']:.1f}%)"
                ),
                f"  Error rate: {stats['error_rate']:.1f}%",
                (
                    f"  Early: {stats['early_clicks']}   "
                    f"Distractor clicks: {stats['distractor_clicks']}"
                ),
                (
                    f"  Missed: {stats['misses']}   "
                    f"Stray clicks: {stats['stray_clicks']}"
                ),
                (
                    f"  Mean: {format_ms(stats['mean'])}   "
                    f"Median: {format_ms(stats['median'])}"
                ),
                (
                    f"  Fastest: {format_ms(stats['min'])}   "
                    f"Slowest: {format_ms(stats['max'])}"
                ),
                f"  Std dev: {format_ms(stats['sd'])}",
                "",
            ]

        if (
            summaries["A"]["mean"] is not None
            and summaries["B"]["mean"] is not None
        ):
            difference = summaries["B"]["mean"] - summaries["A"]["mean"]
            lines.append(
                f"Mean reaction time difference (B - A): {difference:+.1f} ms"
            )

        lines.append(f"Final score: {self.score}")
        self.set_results_text("\n".join(lines))

    def save_session(self, status):
        """Append the current session to the CSV file."""
        try:
            write_rows(
                DATA_FILE,
                self.results,
                status,
            )
            return True
        except OSError as error:
            messagebox.showerror(
                "Save failed",
                f"Could not write the data file:\n{error}",
            )
            return False

    def export_csv(self):
        if not self.results:
            return

        suggestion = (
            f"{self.session_info['participant_id']}"
            f"_session{self.session_info['session']}.csv"
        )

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=suggestion,
            filetypes=[("CSV files", "*.csv")],
        )

        if not path:
            return

        try:
            write_rows(
                path,
                self.results,
                "complete",
                append=False,
            )
            messagebox.showinfo(
                "Exported",
                f"Saved a copy to:\n{path}",
            )
        except OSError as error:
            messagebox.showerror(
                "Export failed",
                str(error),
            )

    # ------------------------------------------------------------------
    # Help / exit
    # ------------------------------------------------------------------

    def show_help(self):
        messagebox.showinfo(
            "How to Play",
            "1. Enter your anonymous code, age group, experience, and session number.\n"
            "2. Click Start Game.\n"
            "3. Wait for the centre box to turn GREEN (it says CLICK NOW!).\n"
            "4. Click the green box as fast as you can.\n\n"
            "Clicking before it turns green, or on any other object, is an error.\n"
            "Some objects may move or change colour - ignore them.\n"
            "Reset stops the session. Restart begins again. Exit closes the game.\n"
            "If you feel uncomfortable at any time, click Reset or Exit.",
        )

    def exit_app(self):
        running = self.state not in ("IDLE", "FINISHED")

        if running:
            if not messagebox.askyesno(
                "Exit",
                "A session is in progress.\n"
                "Exit now? Partial data will be saved as 'incomplete'.",
            ):
                return

            self.cancel_all()

            if self.results:
                self.save_session("incomplete")

        self.cancel_all()
        self.root.destroy()


# ============================================================================
# ENTRY POINT
# ============================================================================


def main():
    root = tk.Tk()
    DistractionReactionGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
