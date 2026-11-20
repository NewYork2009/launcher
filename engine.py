"""Search engine for Launcher: apps index, ranking, math, web shortcuts.

No GUI here — everything is testable headless."""
from __future__ import annotations

import ast
import operator
import os
import re
import shlex
import subprocess
import sys
import webbrowser
from dataclasses import dataclass, field

WEB_PREFIXES = {
    "g ": "https://www.google.com/search?q=",
    "yt ": "https://www.youtube.com/results?search_query=",
    "gh ": "https://github.com/search?q=",
    "w ": "https://ru.wikipedia.org/w/index.php?search=",
}

CALC_RE = re.compile(r"^[\d\s.+\-*/()%^,]+$")


@dataclass
class Item:
    name: str
    kind: str            # app | web | calc | search | shell
    action: str = ""
    hint: str = ""
    score: int = 0


@dataclass
class Index:
    apps: list[Item] = field(default_factory=list)


# ---------------------------------------------------------------- apps index

def _iter_desktop_files() -> list[str]:
    roots = [
        "/usr/share/applications",
        os.path.expanduser("~/.local/share/applications"),
    ]
    found: list[str] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.endswith(".desktop"):
                    found.append(os.path.join(dirpath, fn))
    return found


def _parse_desktop(path: str) -> Item | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = [
                ln.strip()
                for ln in fh.read().splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]
    except OSError:
        return None
    if lines and lines[0] != "[Desktop Entry]":
        return None
    values: dict[str, str] = {}
    for ln in lines[1:]:
        if ln.startswith("["):
            break
        key, _, val = ln.partition("=")
        key = key.strip()
        if not key.endswith("[ru]") and not key.endswith("[en]"):
            values.setdefault(key.strip(), val.strip())
    if values.get("NoDisplay", "false").lower() == "true":
        return None
    if values.get("Terminal", "false").lower() == "true":
        return None
    name = values.get("Name")
    exec_cmd = values.get("Exec")
    if not name or not exec_cmd:
        return None
    return Item(name=name, kind="app", action=path, hint="приложение")


def _iter_windows_shortcuts() -> list[tuple[str, str]]:
    roots = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
    ]
    found: list[tuple[str, str]] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith((".lnk", ".url")):
                    found.append((os.path.splitext(fn)[0], os.path.join(dirpath, fn)))
    return found


def build_index() -> Index:
    apps: list[Item] = []
    if sys.platform.startswith("win"):
        for name, path in _iter_windows_shortcuts():
            apps.append(Item(name=name, kind="app", action=path, hint="приложение"))
    elif sys.platform == "darwin":
        apps_dir = "/Applications"
        if os.path.isdir(apps_dir):
            for fn in sorted(os.listdir(apps_dir)):
                if fn.endswith(".app"):
                    apps.append(
                        Item(
                            name=fn[:-4],
                            kind="app",
                            action=fn[:-4],
                            hint="приложение",
                        )
                    )
    else:
        for path in _iter_desktop_files():
            item = _parse_desktop(path)
            if item:
                apps.append(item)
    seen: set[str] = set()
    unique: list[Item] = []
    for app in apps:
        key = (app.name, app.action).lower()
        if key not in seen:
            seen.add(key)
            unique.append(app)
    return Index(apps=unique)


# ------------------------------------------------------------------ ranking

def rank_score(query: str, name: str) -> int:
    q = query.lower().strip()
    n = name.lower()
    if not q:
        return 0
    if n == q:
        return 100
    if n.startswith(q):
        return 80
    if any(word.startswith(q) for word in n.split()):
        return 60
    if q in n:
        return 40
    pos = 0
    for ch in q:
        pos = n.find(ch, pos)
        if pos == -1:
            return 0
        pos += 1
    return 10


def boost_history(query: str, item: Item, history: list[str]) -> int:
    bonus = 0
    for offset, name in enumerate(reversed(history[-20:])):
        if name == item.name:
            bonus = max(bonus, max(0, 15 - offset))
    return bonus


# --------------------------------------------------------------------- math

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def safe_calc(expr: str) -> float | None:
    expr = expr.strip().replace(",", ".").replace("^", "**").strip()
    if not expr or not CALC_RE.match(expr):
        return None
    try:
        tree = ast.parse(expr, mode="eval")
    except (SyntaxError, ValueError, MemoryError):
        return None
    try:
        value = _eval_node(tree.body)
    except (ZeroDivisionError, OverflowError, ValueError, TypeError):
        return None
    if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
        return None
    return value


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_node(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    raise TypeError("unsupported expression")


def fmt_calc(value: float) -> str:
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.6g}"


# --------------------------------------------------------------- planning

def looks_like_url(query: str) -> bool:
    if " " in query:
        return False
    return bool(re.match(r"^(https?://)?[\w-]+(\.[\w-]+)+(/.*)?$", query, re.I))


def plan_results(query: str, index: Index, history: list[str]) -> list[Item]:
    query = query.strip()
    if not query:
        return top_history(index, history)
    results: list[Item] = []
    lowered = query.lower()
    for prefix, url in WEB_PREFIXES.items():
        if lowered.startswith(prefix):
            from urllib.parse import quote_plus

            results.append(
                Item(
                    name=query[len(prefix):],
                    kind="web",
                    action=url + quote_plus(query[len(prefix):]),
                    hint="открыть в браузере",
                    score=120,
                )
            )
            return results
    if looks_like_url(query):
        url = query if query.startswith("http") else f"https://{query}"
        results.append(Item(name=query, kind="web", action=url, hint="открыть сайт", score=120))
        return results
    value = safe_calc(query)
    if value is not None:
        results.append(
            Item(name=f"= {fmt_calc(value)}", kind="calc", action=fmt_calc(value), hint="калькулятор", score=110)
        )
    scored: list[tuple[int, Item]] = []
    for app in index.apps:
        score = rank_score(query, app.name)
        if score:
            scored.append((score + boost_history(query, app, history), app))
    scored.sort(key=lambda pair: (-pair[0], pair[1].name.lower()))
    results.extend(item for _s, item in scored[:9])
    if not scored and value is None:
        from urllib.parse import quote_plus

        results.append(
            Item(
                name=f"Искать «{query}» в Google",
                kind="web",
                action="https://www.google.com/search?q=" + quote_plus(query),
                hint="поиск в интернете",
                score=5,
            )
        )
    if results and results[0].kind in ("web", "calc"):
        return results
    return results


def top_history(index: Index, history: list[str]) -> list[Item]:
    by_name = {app.name: app for app in index.apps}
    items = [by_name[n] for n in history if n in by_name]
    if not items:
        items = index.apps[:6]
    return items[:6]


# ----------------------------------------------------------------- actions

def open_item(item: Item) -> None:
    if item.kind == "web":
        webbrowser.open(item.action)
    elif item.kind == "calc":
        pass
    elif item.kind == "app":
        if sys.platform.startswith("win"):
            os.startfile(item.action)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", item.action])
        else:
            cmd = _desktop_exec(item.action)
            if cmd:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _desktop_exec(path: str) -> list[str] | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                if ln.strip().startswith("Exec="):
                    parts = shlex.split(ln.strip()[5:])
                    return [p for p in parts if not p.startswith("%")]
    except OSError:
        return None
    return None
