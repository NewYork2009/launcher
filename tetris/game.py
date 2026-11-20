"""Чистая игровая логика тетриса без зависимостей от GUI — тестируется headless."""
from __future__ import annotations

import json
import os
import random
from typing import Optional

CELL = 30
COLS = 10
ROWS = 20
PANEL_W = 130
WINDOW_W = COLS * CELL + PANEL_W
WINDOW_H = ROWS * CELL
TICK_DEFAULT = 800
TICK_MIN = 90
SPEEDUP_PER_LEVEL = 60

RECORD_PATH = os.path.join(os.path.expanduser("~"), ".tetris_record.json")

PALETTE = {
    "bg": "#0e1014",
    "board": "#131722",
    "grid": "#1c2231",
    "panel": "#12161f",
    "text": "#e8ecf4",
    "muted": "#8b95a7",
    "accent": "#22d3ee",
    "ghost": "#242c3d",
}

SHAPES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[0, 1, 0], [1, 1, 1]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "Z": [[1, 1, 0], [0, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
}

COLORS = {
    "I": "#22d3ee",
    "O": "#fbbf24",
    "T": "#c084fc",
    "S": "#34d399",
    "Z": "#f87171",
    "J": "#60a5fa",
    "L": "#fb923c",
}

SCORE_TABLE = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}


def rotate(shape: list[list[int]], times: int = 1) -> list[list[int]]:
    result = [row[:] for row in shape]
    for _ in range(times % 4):
        result = [list(row) for row in zip(*result)][::-1]
    return result


def load_record() -> int:
    try:
        with open(RECORD_PATH, encoding="utf-8") as fh:
            return int(json.load(fh).get("record", 0))
    except (OSError, ValueError, AttributeError):
        return 0


def save_record(value: int) -> None:
    try:
        with open(RECORD_PATH, "w", encoding="utf-8") as fh:
            json.dump({"record": value}, fh)
    except OSError:
        pass


class Piece:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.shape = [row[:] for row in SHAPES[kind]]
        self.x = (COLS - len(self.shape[0])) // 2
        self.y = 0
        self.color = COLORS[kind]

    def cells(self) -> list[tuple[int, int]]:
        return [
            (self.x + cx, self.y + cy)
            for cy, row in enumerate(self.shape)
            for cx, filled in enumerate(row)
            if filled
        ]


class Game:
    def __init__(self) -> None:
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.queue = random.sample(list(SHAPES), len(SHAPES))
        self.piece: Piece | None = None
        self.next: str = self._draw_from_queue()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.over = False
        self.spawn()

    def _draw_from_queue(self) -> str:
        if not self.queue:
            self.queue = random.sample(list(SHAPES), len(SHAPES))
        return self.queue.pop()

    def spawn(self) -> None:
        kind = self.next
        self.next = self._draw_from_queue()
        self.piece = Piece(kind)
        if self.collides(self.piece, 0, 0):
            self.over = True

    def collides(self, piece: Piece, dx: int, dy: int, shape=None) -> bool:
        shape = shape if shape is not None else piece.shape
        for cy, row in enumerate(shape):
            for cx, filled in enumerate(row):
                if not filled:
                    continue
                x, y = piece.x + cx + dx, piece.y + cy + dy
                if x < 0 or x >= COLS or y >= ROWS:
                    return True
                if y >= 0 and self.board[y][x] is not None:
                    return True
        return False

    def move(self, dx: int, dy: int) -> bool:
        if self.piece is None or self.over:
            return False
        if self.collides(self.piece, dx, dy):
            return False
        self.piece.x += dx
        self.piece.y += dy
        return True

    def rotate_piece(self, times: int = 1) -> None:
        if self.piece is None or self.over:
            return
        rotated = rotate(self.piece.shape, times)
        for kick in (0, -1, 1, -2, 2):
            if not self.collides(self.piece, kick, 0, rotated):
                self.piece.shape = rotated
                self.piece.x += kick
                return

    def hard_drop(self) -> None:
        while self.move(0, 1):
            self.score += 2

    def ghost_y(self) -> int:
        if self.piece is None:
            return 0
        offset = 0
        while not self.collides(self.piece, 0, offset + 1):
            offset += 1
        return self.piece.y + offset

    def lock(self) -> int:
        piece = self.piece
        cleared = 0
        if piece is not None:
            for x, y in piece.cells():
                if 0 <= y < ROWS:
                    self.board[y][x] = piece.color
            full_rows = [
                y for y in range(ROWS) if all(cell is not None for cell in self.board[y])
            ]
            for y in full_rows:
                del self.board[y]
                self.board.insert(0, [None] * COLS)
            cleared = len(full_rows)
            self.lines += cleared
            self.score += SCORE_TABLE.get(cleared, 200 * cleared)
            self.level = 1 + self.lines // 10
        self.spawn()
        return cleared

    def tick_delay(self) -> int:
        return max(TICK_MIN, TICK_DEFAULT - (self.level - 1) * SPEEDUP_PER_LEVEL)

    def next_shape_preview(self) -> list[list[int]]:
        return SHAPES[self.next]


