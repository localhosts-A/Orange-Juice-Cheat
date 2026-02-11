from __future__ import annotations

from dataclasses import dataclass
import ctypes
from typing import Optional

import pymem
import pymem.process


@dataclass
class MemoryValue:
    address: int
    value: int


class ProcessMemory:
    def __init__(self, process_name: str, module_name: str) -> None:
        self.process_name = process_name
        self.module_name = module_name
        self._pm: Optional[pymem.Pymem] = None
        self._base_address: Optional[int] = None

    @property
    def attached(self) -> bool:
        return self._pm is not None and self._base_address is not None

    def attach(self) -> None:
        self._pm = pymem.Pymem(self.process_name)
        module = pymem.process.module_from_name(self._pm.process_handle, self.module_name)
        self._base_address = module.lpBaseOfDll

    def detach(self) -> None:
        if self._pm is not None:
            try:
                self._pm.close_process()
            finally:
                self._pm = None
                self._base_address = None

    def terminate(self) -> None:
        if self._pm is None:
            return
        try:
            handle = self._pm.process_handle
            if not handle:
                return
            ctypes.windll.kernel32.TerminateProcess(handle, 1)
        finally:
            self.detach()

    def get_address(self, base_offset: int, field_offset: int) -> int:
        if not self.attached:
            raise RuntimeError("Process not attached")
        base_ptr_addr = self._base_address + base_offset
        ptr_value = self.read_pointer(base_ptr_addr)
        return ptr_value + field_offset

    def get_address_from_chain(self, base_offset: int, offsets: list[int]) -> int:
        if not self.attached:
            raise RuntimeError("Process not attached")
        if not offsets:
            raise ValueError("Offsets chain cannot be empty")

        base_ptr_addr = self._base_address + base_offset
        ptr_value = self.read_pointer(base_ptr_addr)

        for index, offset in enumerate(offsets):
            addr = ptr_value + offset
            if index < len(offsets) - 1:
                ptr_value = self.read_pointer(addr)
            else:
                return addr

        raise RuntimeError("Failed to resolve pointer chain")

    def get_module_address(self, module_offset: int) -> int:
        if not self.attached:
            raise RuntimeError("Process not attached")
        return self._base_address + module_offset

    def read_pointer(self, address: int) -> int:
        if not self.attached:
            raise RuntimeError("Process not attached")
        if self._pm.is_64_bit:
            return self._pm.read_ulonglong(address)
        return self._pm.read_uint(address)

    def read_int(self, address: int) -> int:
        if not self.attached:
            raise RuntimeError("Process not attached")
        return self._pm.read_int(address)

    def write_int(self, address: int, value: int) -> None:
        if not self.attached:
            raise RuntimeError("Process not attached")
        self._pm.write_int(address, int(value))

    def read_bytes(self, address: int, size: int) -> bytes:
        if not self.attached:
            raise RuntimeError("Process not attached")
        return self._pm.read_bytes(address, size)
