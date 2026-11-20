"""Игровая логика «Сапёра» без GUI — тестируется headless."""
from __future__ import annotations

import random

DIFFICULTIES = {
    "Легко": (9, 9, 10),
    "Средне": (16, 16, 40),
    "Сложно": (16, 30, 99),
}


class Game:
    def __init__(self, cols: int, rows: int, mines: int) -> None:
        self.cols, self.rows, self.mines_total = cols, rows, mines
        self.mines: set[tuple[int, int]] = set()
        self.revealed: set[tuple[int, int]] = set()
        self.flags: set[tuple[int, int]] = set()
        self.numbers = [[0] * cols for _ in range(rows)]
        self.planted = False
        self.won = False
        self.lost = False
        self.hit_mine: tuple[int, int] | None = None

    def neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        result = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.cols and 0 <= ny < self.rows:
                    result.append((nx, ny))
        return result

    def plant(self, safe_x: int, safe_y: int) -> None:
        forbidden = {(safe_x, safe_y), *self.neighbors(safe_x, safe_y)}
        free = [
            (x, y)
            for y in range(self.rows)
            for x in range(self.cols)
            if (x, y) not in forbidden
        ]
        self.mines = set(random.sample(free, self.mines_total))
        for (mx, my) in self.mines:
            for nx, ny in self.neighbors(mx, my):
                self.numbers[ny][nx] += 1
        self.planted = True

    def is_mine(self, x: int, y: int) -> bool:
        return (x, y) in self.mines

    def reveal(self, x: int, y: int) -> bool:
        if self.won or self.lost:
            return False
        if not 0 <= x < self.cols or not 0 <= y < self.rows:
            return False
        if (x, y) in self.flags or (x, y) in self.revealed:
            return False
        if not self.planted:
            self.plant(x, y)
        if self.is_mine(x, y):
            self.lost = True
            self.hit_mine = (x, y)
            return True
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in self.revealed or self.is_mine(cx, cy):
                continue
            self.revealed.add((cx, cy))
            if self.numbers[cy][cx] == 0:
                stack.extend(self.neighbors(cx, cy))
        self._check_win()
        return False

    def chord(self, x: int, y: int) -> bool:
        if self.lost or self.won or not self.planted:
            return False
        if (x, y) not in self.revealed or self.numbers[y][x] == 0:
            return False
        flagged = sum(1 for n in self.neighbors(x, y) if n in self.flags)
        if flagged != self.numbers[y][x]:
            return False
        for nx, ny in self.neighbors(x, y):
            if (nx, ny) not in self.flags and (nx, ny) not in self.revealed:
                if self.reveal(nx, ny):
                    return True
        return False

    def toggle_flag(self, x: int, y: int) -> None:
        if self.won or self.lost or (x, y) in self.revealed:
            return
        if (x, y) in self.flags:
            self.flags.discard((x, y))
        else:
            self.flags.add((x, y))

    def flags_left(self) -> int:
        return self.mines_total - len(self.flags)

    def _check_win(self) -> None:
        if len(self.revealed) == self.cols * self.rows - len(self.mines):
            self.won = True
            for mine in self.mines:
                self.flags.add(mine)

    def mistakes_in_flags(self) -> list[tuple[int, int]]:
        return [f for f in self.flags if f not in self.mines]
