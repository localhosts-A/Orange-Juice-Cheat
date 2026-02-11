from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


@dataclass
class AppConfig:
    process_name: str
    module_name: str
    base_offset: int
    fields: Dict[str, int]
    module_fields: Dict[str, int]
    pointer_chains: Dict[str, List[int]]
    name_ranges: Dict[str, Dict[str, object]]
    double_write: Dict[str, List[int]]
    double_write_fields: Dict[str, List[int]]
    hp_stride: int
    win_stride: int
    star_stride: int
    poll_interval_ms: int

    @staticmethod
    def load() -> "AppConfig":
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return AppConfig(
            process_name=data.get("process_name", "100orange.exe"),
            module_name=data.get("module_name", "100orange.exe"),
            base_offset=int(str(data.get("base_offset", "0x0")), 16),
            fields={k: int(str(v), 16) for k, v in data.get("fields", {}).items()},
            module_fields={
                k: int(str(v), 16) for k, v in data.get("module_fields", {}).items()
            },
            pointer_chains={
                k: [int(str(item), 16) for item in v]
                for k, v in data.get("pointer_chains", {}).items()
            },
            name_ranges={
                k: {
                    "chain": [int(str(item), 16) for item in v.get("chain", [])],
                    "start": int(str(v.get("start", "0x0")), 16),
                    "end": int(str(v.get("end", "0x0")), 16),
                }
                for k, v in data.get("name_ranges", {}).items()
            },
            double_write={
                k: [int(str(item), 16) for item in v]
                for k, v in data.get("double_write", {}).items()
            },
            double_write_fields={
                k: [int(str(item), 16) for item in v]
                for k, v in data.get("double_write_fields", {}).items()
            },
            hp_stride=int(str(data.get("hp_stride", "0x0")), 16),
            win_stride=int(str(data.get("win_stride", "0x0")), 16),
            star_stride=int(str(data.get("star_stride", "0x0")), 16),
            poll_interval_ms=int(data.get("poll_interval_ms", 300)),
        )

    def save(self) -> None:
        data = {
            "process_name": self.process_name,
            "module_name": self.module_name,
            "base_offset": hex(self.base_offset),
            "fields": {k: hex(v) for k, v in self.fields.items()},
            "module_fields": {k: hex(v) for k, v in self.module_fields.items()},
            "pointer_chains": {
                k: [hex(item) for item in v] for k, v in self.pointer_chains.items()
            },
            "name_ranges": {
                k: {
                    "chain": [hex(item) for item in v.get("chain", [])],
                    "start": hex(int(v.get("start", 0))),
                    "end": hex(int(v.get("end", 0))),
                }
                for k, v in self.name_ranges.items()
            },
            "double_write": {
                k: [hex(item) for item in v] for k, v in self.double_write.items()
            },
            "double_write_fields": {
                k: [hex(item) for item in v] for k, v in self.double_write_fields.items()
            },
            "hp_stride": hex(self.hp_stride),
            "win_stride": hex(self.win_stride),
            "star_stride": hex(self.star_stride),
            "poll_interval_ms": self.poll_interval_ms,
        }
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
