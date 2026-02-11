from __future__ import annotations

from typing import Callable, Dict

from pynput import keyboard


class GlobalHotkeys:
    def __init__(self) -> None:
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self, hotkey_map: Dict[str, Callable[[], None]]) -> None:
        self.stop()
        self._listener = keyboard.GlobalHotKeys(hotkey_map)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
