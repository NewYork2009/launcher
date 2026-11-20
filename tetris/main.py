"""Tetris — классический тетрис на Tkinter.

Запуск:  python main.py
Клавиши: ← → двигать · ↓ ускорить · ↑ / X повернуть · Z поворот назад ·
         Space мгновенно вниз · P пауза · R заново · Esc выход
"""
from __future__ import annotations

import json
import os
import random
import tkinter as tk

from game import (
    COLS,
    COLORS,
    Game,
    ROWS,
    SHAPES,
    load_record,
    save_record,
)

class TetrisApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tetris")
        self.configure(bg=PALETTE["bg"])
        self.resizable(False, False)
        self.game = Game()
        self.paused = False
        self.record = max(load_record(), 0)
        from tkinter import font as tkfont

        family = next(
            (
                f
                for f in ("Segoe UI", "SF Pro Text", "Ubuntu", "DejaVu Sans")
                if f in tkfont.families()
            ),
            "TkDefaultFont",
        )
        self.font_title = tkfont.Font(family=family, size=13, weight="bold")
        self.font_body = tkfont.Font(family=family, size=11)
        self.font_small = tkfont.Font(family=family, size=9)
        self.canvas = tk.Canvas(
            self, width=WINDOW_W, height=WINDOW_H, bg=PALETTE["bg"],
            bd=0, highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.bind("<Key>", self.on_key)
        self.after(self.game.tick_delay(), self.on_tick)
        self.render()

    def on_key(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key == "escape":
            self.destroy()
            return
        if self.game.over and key == "r":
            self.game = Game()
            self.paused = False
            self.render()
            return
        if key == "r":
            self.game = Game()
            self.render()
            return
        if key == "p":
            self.paused = not self.paused
            self.render()
            return
        if self.paused or self.game.over:
            return
        if key == "left":
            self.game.move(-1, 0)
        elif key == "right":
            self.game.move(1, 0)
        elif key == "down":
            if self.game.move(0, 1):
                self.game.score += 1
        elif key == "up" or key == "x":
            self.game.rotate_piece(1)
        elif key == "z":
            self.game.rotate_piece(3)
        elif key == "space":
            self.game.hard_drop()
        else:
            return
        self.render()

    def on_tick(self) -> None:
        if not self.paused and not self.game.over:
            landed = not self.game.move(0, 1)
            if landed:
                self.game.lock()
                new_record = self.game.score > self.record
                if new_record:
                    self.record = self.game.score
                    save_record(self.record)
        self.render()
        self.after(self.game.tick_delay(), self.on_tick)

    def render(self) -> None:
        canvas = self.canvas
        canvas.delete("all")

        canvas.create_rectangle(
            0, 0, COLS * CELL, ROWS * CELL,
            fill=PALETTE["board"], outline=PALETTE["grid"],
        )
        for x in range(1, COLS):
            canvas.create_line(x * CELL, 0, x * CELL, ROWS * CELL, fill=PALETTE["grid"])
        for y in range(1, ROWS):
            canvas.create_line(0, y * CELL, COLS * CELL, y * CELL, fill=PALETTE["grid"])

        for y in range(ROWS):
            for x in range(COLS):
                color = self.game.board[y][x]
                if color:
                    self._cell(canvas, x, y, color)

        piece = self.game.piece
        if piece is not None:
            ghost_offset = self.game.ghost_y() - piece.y
            gx, gy = piece.x, self.game.ghost_y()
            for cy, row in enumerate(piece.shape):
                for cx, filled in enumerate(row):
                    if filled and gy + cy < ROWS:
                        canvas.create_rectangle(
                            (gx + cx) * CELL + 3, (gy + cy) * CELL + 3,
                            (gx + cx + 1) * CELL - 3, (gy + cy + 1) * CELL - 3,
                            outline=PALETTE["ghost"], width=2,
                        )
            for x, y in piece.cells():
                if y >= 0:
                    self._cell(canvas, x, y, piece.color)

        px = COLS * CELL
        canvas.create_rectangle(
            px, 0, WINDOW_W, WINDOW_H, fill=PALETTE["panel"], outline=PALETTE["grid"]
        )
        canvas.create_text(px + PANEL_W // 2, 24, text="TETRIS", fill=PALETTE["accent"],
                           font=self.font_title)
        rows = [
            ("Счёт", str(self.game.score), PALETTE["text"]),
            ("Рекорд", str(self.record), PALETTE["accent"] if self.record <= self.game.score else PALETTE["muted"]),
            ("Линии", str(self.game.lines), PALETTE["text"]),
            ("Уровень", str(self.game.level), PALETTE["text"]),
        ]
        for i, (label, value, color) in enumerate(rows):
            y = 70 + i * 44
            canvas.create_text(px + 14, y, text=label, anchor="w",
                               fill=PALETTE["muted"], font=self.font_small)
            canvas.create_text(px + PANEL_W - 14, y, text=value, anchor="e",
                               fill=color, font=self.font_body)

        canvas.create_text(px + 14, 260, text="Следующая", anchor="w",
                           fill=PALETTE["muted"], font=self.font_small)
        shape = self.game.next_shape_preview()
        offset_x = px + (PANEL_W - len(shape[0]) * 22) // 2
        for cy, row in enumerate(shape):
            for cx, filled in enumerate(row):
                if filled:
                    canvas.create_rectangle(
                        offset_x + cx * 22 + 2, 280 + cy * 22 + 2,
                        offset_x + (cx + 1) * 22 - 2, 280 + (cy + 1) * 22 - 2,
                        fill=COLORS[self.game.next],
                    )

        hint_font = self.font_small
        hint_font = self.font_small
        hints = [
            "← → двигать",
            "↓ ускорить",
            "↑ / X поворот",
            "Z — назад",
            "Space — вниз",
            "P — пауза",
            "R — заново",
            "Esc — выход",
        ]
        for i, line in enumerate(hints):
            canvas.create_text(px + 14, 380 + i * 20, text=line, anchor="w",
                               fill=PALETTE["muted"], font=hint_font)

        if self.game.over:
            overlay = canvas.create_rectangle(
                0, ROWS * CELL / 2 - 70, COLS * CELL, ROWS * CELL / 2 + 70,
                fill="#000000", stipple="gray50",
            )
            canvas.create_text(
                COLS * CELL / 2, ROWS * CELL / 2 - 20,
                text="Игра окончена", fill="#f87171", font=self.font_title,
            )
            canvas.create_text(
                COLS * CELL / 2, ROWS * CELL / 2 + 12,
                text=f"Счёт: {self.game.score} · Рекорд: {self.record}",
                fill=PALETTE["text"], font=self.font_body,
            )
            canvas.create_text(
                COLS * CELL / 2, ROWS * CELL / 2 + 40,
                text="R — сыграть ещё", fill=PALETTE["muted"], font=self.font_small,
            )
        elif self.paused:
            canvas.create_rectangle(
                0, ROWS * CELL / 2 - 40, COLS * CELL, ROWS * CELL / 2 + 40,
                fill="#000000", stipple="gray50",
            )
            canvas.create_text(
                COLS * CELL / 2, ROWS * CELL / 2,
                text="Пауза (P)", fill=PALETTE["accent"], font=self.font_title,
            )

    def _cell(self, canvas: tk.Canvas, x: int, y: int, color: str) -> None:
        canvas.create_rectangle(
            x * CELL + 1, y * CELL + 1,
            (x + 1) * CELL - 1, (y + 1) * CELL - 1,
            fill=color, outline="",
        )
        canvas.create_rectangle(
            x * CELL + 5, y * CELL + 5,
            (x + 1) * CELL - 5, y * CELL + CELL // 2,
            fill="#ffffff", outline="", stipple="gray12",
        )


def main() -> None:
    app = TetrisApp()
    app.mainloop()


if __name__ == "__main__":
    main()
