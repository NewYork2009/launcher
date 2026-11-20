"""Launcher — быстрый лаунчер по хоткею.

Запуск:       python main.py
Хоткей:       Ctrl+Alt+Space  (нужен пакет keyboard:  pip install keyboard)
Без хоткея:   окно открыто, Esc закрывает приложение.
Ввод:         ptys — поиск приложения · «2+2*10» — калькулятор · «g котики» — Google · «yt трек» — YouTube · «gh repo» — GitHub · «w запрос» — Википедия
Клавиши:      ↑/↓ выбор · Enter открыть · Esc скрыть/выход
"""
from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional

sys.path.insert(0, str(os.path.dirname(os.path.abspath(__file__))))

from engine import Index, Item, build_index, open_item, plan_results

HISTORY_PATH = os.path.join(os.path.expanduser("~"), ".syslauncher.json")
HOTKEY = "ctrl+alt+space"

PALETTE = {
    "bg": "#0f1115",
    "card": "#191d26",
    "edge": "#252b38",
    "text": "#e8ecf4",
    "muted": "#8b95a7",
    "accent": "#22d3ee",
    "select": "#123a4a",
}


class LauncherApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Launcher")
        self.configure(bg=PALETTE["bg"])
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.index: Index = Index(apps=[])
        self.history: list[str] = self.load_history()
        self.hotkey_ready = False
        self.results: list[Item] = []
        self.font_big = tkfont.Font(size=16)
        self.font_list = tkfont.Font(size=11)
        self.font_hint = tkfont.Font(size=9)
        self.build_ui()
        self.bind_keys()
        self.geometry(f"+{(self.winfo_screenwidth() - 640) // 2}+{self.winfo_screenheight() // 5}")
        self.after(50, self.load_index_async)

    def load_index_async(self) -> None:
        self.index = build_index()
        self.update_results()

    def load_history(self) -> list[str]:
        try:
            with open(HISTORY_PATH, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def save_history(self) -> None:
        try:
            with open(HISTORY_PATH, "w", encoding="utf-8") as fh:
                json.dump(self.history[-20:], fh, ensure_ascii=False)
        except OSError:
            pass

    def build_ui(self) -> None:
        wrapper = tk.Frame(self, bg=PALETTE["edge"], padx=1, pady=1)
        wrapper.pack(fill="both", expand=True)
        inner = tk.Frame(wrapper, bg=PALETTE["bg"])
        inner.pack(fill="both", expand=True)

        self.entry = tk.Entry(
            inner,
            font=self.font_big,
            bg=PALETTE["bg"],
            fg=PALETTE["text"],
            insertbackground=PALETTE["accent"],
            relief="flat",
        )
        self.entry.pack(fill="x", padx=16, pady=(14, 8))
        self.entry.insert(0, "")
        self.entry.icursor("end")

        self.listbox = tk.Listbox(
            inner,
            font=self.font_list,
            bg=PALETTE["card"],
            fg=PALETTE["text"],
            selectbackground=PALETTE["select"],
            selectforeground=PALETTE["text"],
            activestyle="none",
            relief="flat",
            highlightthickness=0,
            bd=0,
        )
        self.listbox.pack(fill="both", expand=True, padx=8, pady=(0, 12))
        self.hint = tk.Label(
            inner,
            text="",
            font=self.font_hint,
            bg=PALETTE["bg"],
            fg=PALETTE["muted"],
            anchor="w",
        )
        self.hint.pack(fill="x", padx=16, pady=(0, 10))
        self.entry.focus_force()

    def bind_keys(self) -> None:
        self.entry.bind("<KeyRelease>", lambda e: self.update_results() if e.keysym not in ("Up", "Down", "Return") else None)
        self.entry.bind("<Return>", lambda e: self.launch())
        self.entry.bind("<Escape>", lambda e: self.on_escape())
        self.entry.bind("<Down>", lambda e: self.move(1))
        self.entry.bind("<Up>", lambda e: self.move(-1))
        self.listbox.bind("<Double-Button-1>", lambda e: self.launch())
        self.bind("<FocusOut>", self.on_focus_out)
        try:
            import keyboard

            keyboard.add_hotkey(HOTKEY, self.schedule_toggle)
            self.hotkey_ready = True
        except Exception:
            self.hotkey_ready = False

    def schedule_toggle(self) -> None:
        self.after(0, self.toggle)

    def toggle(self) -> None:
        if self.state() == "withdrawn":
            self.deiconify()
            self.entry.focus_force()
            self.entry.icursor("end")
        else:
            self.withdraw()

    def on_escape(self) -> None:
        if self.hotkey_ready:
            self.withdraw()
        else:
            self.save_history()
            self.destroy()

    def on_focus_out(self, _event: Optional[tk.Event] = None) -> None:
        if not self.hotkey_ready:
            return
        self.after(150, self._withdraw_if_unfocused)

    def _withdraw_if_unfocused(self) -> None:
        try:
            if self.focus_get() is None:
                self.withdraw()
        except KeyError:
            self.withdraw()

    def move(self, delta: int) -> None:
        size = self.listbox.size()
        if not size:
            return
        current = self.listbox.curselection()[0] if self.listbox.curselection() else 0
        nxt = max(0, min(current + delta, size - 1))
        self.listbox.selection_clear(0, size)
        self.listbox.selection_set(nxt)
        self.listbox.activate(nxt)
        self.listbox.see(nxt)

    def update_results(self) -> None:
        query = self.entry.get()
        self.results = plan_results(query, self.index, self.history)
        self.listbox.delete(0, "end")
        for i, item in enumerate(self.results):
            mark = "  " if item.hint == "" else ""
            self.listbox.insert("end", f"{mark}{item.name}")
            if item.hint:
                self.listbox.itemconfig(i, fg=PALETTE["text"] if i else PALETTE["accent"])
        if self.results:
            self.listbox.selection_set(0)
            self.listbox.activate(0)
        selected = self.results[0] if self.results else None
        hints = []
        if selected:
            hints.append(selected.hint)
        if not self.index.apps and not self.results:
            hints.append("индексирую приложения…")
        self.hint.configure(text=" · ".join(hints))

    def launch(self) -> None:
        if not self.results:
            return
        selection = self.listbox.curselection()
        idx = selection[0] if selection else 0
        item = self.results[idx]
        if item.kind == "app":
            if item.name in self.history:
                self.history.remove(item.name)
            self.history.append(item.name)
            self.save_history()
        open_item(item)
        self.entry.delete(0, "end")
        self.update_results()
        if self.hotkey_ready:
            self.withdraw()


def main() -> None:
    app = LauncherApp()
    if not app.hotkey_ready:
        app.hint.configure(
            text="хоткей Ctrl+Alt+Space не активен (установи: pip install keyboard) · Esc — выход"
        )
    app.mainloop()


if __name__ == "__main__":
    main()
