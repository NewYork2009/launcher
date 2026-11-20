"""Сапёр — тёмная классика с флажками, таймером и рекордами.

Запуск:  python main.py  (или двойной щелчок по Minesweeper.bat)
ЛКМ — открыть · ПКМ — флажок · клик по цифре с нужными флагами — открыть соседей ·
N — новая игра · 1/2/3 — сложность
"""
from __future__ import annotations

import json
import os
import sys
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter.messagebox import showinfo

sys.path.insert(0, str(os.path.dirname(os.path.abspath(__file__))))

from game import DIFFICULTIES, Game

CELL = 30
RECORD_PATH = os.path.join(os.path.expanduser("~"), ".minesweeper_best.json")

PALETTE = {
    "bg": "#0e1014",
    "board": "#191e2b",
    "panel": "#12161f",
    "edge": "#252b38",
    "hidden": "#26304a",
    "hidden_hi": "#31406b",
    "open": "#10131b",
    "grid": "#0a0c11",
    "text": "#e8ecf4",
    "muted": "#8b95a7",
    "accent": "#22d3ee",
    "danger": "#f87171",
    "ok": "#34d399",
    "mine": "#2b1520",
}

NUMBER_COLORS = {
    1: "#60a5fa",
    2: "#34d399",
    3: "#f87171",
    4: "#a78bfa",
    5: "#fbbf24",
    6: "#22d3ee",
    7: "#e879f9",
    8: "#94a3b8",
}

FLAG = "🚩"
MINE = "💣"


def load_best() -> dict[str, float]:
    try:
        with open(RECORD_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_best(best: dict[str, float]) -> None:
    try:
        with open(RECORD_PATH, "w", encoding="utf-8") as fh:
            json.dump(best, fh, ensure_ascii=False)
    except OSError:
        pass


def fmt_time(seconds: float) -> str:
    if seconds >= 60:
        return f"{int(seconds // 60)}:{seconds % 60:04.1f}"
    return f"{seconds:.1f}"


class MinesweeperApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Сапёр")
        self.configure(bg=PALETTE["bg"])
        self.resizable(False, False)
        self.best = load_best()
        self.difficulty = "Легко"
        self.start_time: float | None = None
        self.finished_seconds: float | None = None
        self.game = Game(*DIFFICULTIES[self.difficulty])
        from tkinter import font as tkfont

        family = next(
            (
                f
                for f in ("Segoe UI", "SF Pro Text", "Ubuntu", "DejaVu Sans")
                if f in tkfont.families()
            ),
            "TkDefaultFont",
        )
        self.font_body = tkfont.Font(family=family, size=11)
        self.font_title = tkfont.Font(family=family, size=13, weight="bold")
        self.font_num = tkfont.Font(family=family, size=13, weight="bold")
        self.font_symbol = tkfont.Font(family=family, size=14)
        self.font_small = tkfont.Font(family=family, size=9)

        self.top = tk.Frame(self, bg=PALETTE["panel"])
        self.canvas = tk.Canvas(self, bg=PALETTE["board"], bd=0, highlightthickness=0)
        self.top.pack(fill="x")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_flag)
        self.bind("<n>", lambda e: self.new_game())
        self.bind("<Key-1>", lambda e: self.set_difficulty("Легко"))
        self.bind("<Key-2>", lambda e: self.set_difficulty("Средне"))
        self.bind("<Key-3>", lambda e: self.set_difficulty("Сложно"))
        self.build_top()
        self.apply_difficulty(self.difficulty)
        self.update_clock()

    def build_top(self) -> None:
        for child in self.top.winfo_children():
            child.destroy()
        self.mines_label = tk.Label(
            self.top, text="", font=self.font_body, bg=PALETTE["panel"], fg=PALETTE["danger"]
        )
        self.mines_label.pack(side="left", padx=(12, 4), pady=8)
        self.best_label = tk.Label(
            self.top, text="", font=self.font_small, bg=PALETTE["panel"], fg=PALETTE["muted"]
        )
        self.best_label.pack(side="left", padx=4)
        self.time_label = tk.Label(
            self.top, text="0.0", font=self.font_body, bg=PALETTE["panel"], fg=PALETTE["accent"]
        )
        self.time_label.pack(side="right", padx=(4, 12))
        row = tk.Frame(self.top, bg=PALETTE["panel"])
        row.pack(side="right")
        self.diff_buttons: dict[str, tk.Button] = {}
        for name in DIFFICULTIES:
            btn = tk.Button(
                row,
                text=name,
                command=lambda n=name: self.set_difficulty(n),
                font=self.font_small,
                relief="flat",
                bd=0,
                padx=8,
                cursor="hand2",
            )
            btn.pack(side="left", padx=3, pady=6)
            self.diff_buttons[name] = btn
        self.new_btn = tk.Button(
            row,
            text="Новая",
            command=self.new_game,
            font=self.font_small,
            relief="flat",
            bd=0,
            padx=8,
            cursor="hand2",
        )
        self.new_btn.pack(side="left", padx=(3, 8), pady=6)
        self.hint_best()

    def hint_best(self) -> None:
        record = self.best.get(self.difficulty)
        self.best_label.configure(
            text=f"рекорд: {fmt_time(record)}" if record else "рекорд: —"
        )

    def apply_difficulty(self, name: str) -> None:
        cols, rows, mines = DIFFICULTIES[name]
        self.geometry(f"{cols * CELL}x{rows * CELL + 44}")
        for btn_name, btn in self.diff_buttons.items():
            btn.configure(
                bg=PALETTE["hidden_hi"] if btn_name == name else PALETTE["hidden"],
                fg=PALETTE["text"],
            )

    def set_difficulty(self, name: str) -> None:
        self.difficulty = name
        self.new_game()

    def new_game(self) -> None:
        self.game = Game(*DIFFICULTIES[self.difficulty])
        self.start_time = None
        self.finished_seconds = None
        cols, rows, mines = DIFFICULTIES[self.difficulty]
        self.geometry(f"{cols * CELL}x{rows * CELL + 44}")
        for btn_name, btn in self.diff_buttons.items():
            btn.configure(bg=PALETTE["hidden_hi"] if btn_name == self.difficulty else PALETTE["hidden"])
        self.hint_best()
        self.render()

    def cell_from_event(self, event: tk.Event) -> tuple[int, int]:
        return event.x // CELL, event.y // CELL

    def on_click(self, event: tk.Event) -> None:
        x, y = self.cell_from_event(event)
        game = self.game
        if (x, y) in game.revealed and game.planted:
            hit = game.chord(x, y)
        elif (x, y) in game.flags:
            return
        else:
            if game.lost or game.won:
                return
            hit = game.reveal(x, y)
        if self.start_time is None and not game.lost and not game.won and game.revealed:
            self.start_time = time.monotonic()
        if hit:
            self.finish(lose=True)
        elif game.won:
            self.finish(lose=False)
        self.render()

    def on_flag(self, event: tk.Event) -> None:
        x, y = self.cell_from_event(event)
        if self.start_time is None and not self.game.planted:
            self.start_time = time.monotonic()
        self.game.toggle_flag(x, y)
        self.render()

    def finish(self, lose: bool) -> None:
        if self.start_time is not None:
            self.finished_seconds = time.monotonic() - self.start_time
        if not lose and self.finished_seconds is not None:
            record = self.best.get(self.difficulty)
            if record is None or self.finished_seconds < record:
                self.best[self.difficulty] = self.finished_seconds
                save_best(self.best)
                self.hint_best()
                showinfo(
                    "Новый рекорд!",
                    f"{self.difficulty}: {fmt_time(self.finished_seconds)} — лучше всех!",
                )
        if lose:
            showinfo("Бум!", "Ты подорвался. Жми «Новая» — и ещё разок")

    def update_clock(self) -> None:
        if self.start_time is None:
            shown = 0.0
        elif self.finished_seconds is not None:
            shown = self.finished_seconds
        else:
            shown = time.monotonic() - self.start_time
            if self.game.won or self.game.lost and self.start_time is not None:
                shown = time.monotonic() - self.start_time
        self.time_label.configure(text=fmt_time(shown))
        self.after(100, self.update_clock)

    def render(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        cols, rows = self.game.cols, self.game.rows
        for rect_y in range(rows):
            for rect_x in range(cols):
                x0, y0 = rect_x * CELL, rect_y * CELL
                x1, y1 = x0 + CELL, y0 + CELL
                revealed = (rect_x, rect_y) in self.game.revealed
                flagged = (rect_x, rect_y) in self.game.flags
                if not revealed:
                    canvas.create_rectangle(
                        x0 + 1, y0 + 1, x1 - 1, y1 - 1,
                        fill=PALETTE["hidden"], outline=PALETTE["edge"], width=1,
                    )
                    if flagged:
                        canvas.create_text(
                            (x0 + x1) // 2, (y0 + y1) // 2,
                            text=FLAG, font=self.font_symbol, fill=PALETTE["text"],
                        )
                    continue
                canvas.create_rectangle(
                    x0 + 1, y0 + 1, x1 - 1, y1 - 1,
                    fill=PALETTE["open"], outline=PALETTE["grid"], width=1,
                )
                if self.game.is_mine(rect_x, rect_y):
                    canvas.create_rectangle(
                        x0 + 1, y0 + 1, x1 - 1, y1 - 1,
                        fill=PALETTE["mine"], outline=PALETTE["grid"], width=1,
                    )
                    canvas.create_text(
                        (x0 + x1) // 2, (y0 + y1) // 2,
                        text=MINE, font=self.font_symbol,
                    )
                    continue
                number = self.game.numbers[rect_y][rect_x]
                if number:
                    canvas.create_text(
                        (x0 + x1) // 2, (y0 + y1) // 2,
                        text=str(number),
                        font=self.font_num,
                        fill=NUMBER_COLORS.get(number, PALETTE["text"]),
                    )
        self.mines_label.configure(text=f"💣 {self.game.flags_left()}")
        self.canvas.configure(
            width=cols * CELL, height=rows * CELL,
        )


def main() -> None:
    app = MinesweeperApp()
    app.new_game()
    app.mainloop()


if __name__ == "__main__":
    main()
