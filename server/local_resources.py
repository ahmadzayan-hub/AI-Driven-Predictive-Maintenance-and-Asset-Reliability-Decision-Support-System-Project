"""Fail-closed physical-memory policy for local inference."""
import os

MIN_FREE_BYTES = 3 * 1024 ** 3


def free_memory_bytes():
    """Read available physical RAM. Unknown is a refusal, never permission."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class Memory(ctypes.Structure):
                _fields_ = [("length", wintypes.DWORD), ("load", wintypes.DWORD)] + [
                    (name, ctypes.c_ulonglong) for name in
                    ("total", "available", "page_total", "page_available", "virtual_total",
                     "virtual_available", "extended")]

            memory = Memory()
            memory.length = ctypes.sizeof(memory)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
                return memory.available
        # This increment is local Windows only; other hosts fail closed.
    except (AttributeError, OSError, ValueError):
        pass
    return None


