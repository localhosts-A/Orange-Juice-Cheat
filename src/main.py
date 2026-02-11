from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .config import AppConfig
from .memory import ProcessMemory


APP = QApplication.instance() or QApplication(sys.argv)


def main() -> int:

    from .ui import MainWindow

    config = AppConfig.load()
    memory = ProcessMemory(config.process_name, config.module_name)
    window = MainWindow(config, memory)

    # No hotkeys

    window.show()
    return APP.exec()


if __name__ == "__main__":
    raise SystemExit(main())
