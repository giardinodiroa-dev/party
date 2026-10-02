"""Root-window capture on X11 through MIT-SHM, via ctypes. One grab ≈ a few ms.

Returns a numpy view (H, W, 4) in BGRA over shared memory that X fills in place —
no copy on the Python side. Falls back to plain XGetImage (copy) if SHM fails.
"""
from __future__ import annotations

import ctypes
import ctypes.util

import numpy as np

ZPIXMAP = 2
ALL_PLANES = 0xFFFFFFFF
IPC_PRIVATE = 0
IPC_CREAT = 0o1000
IPC_RMID = 0


class _XImage(ctypes.Structure):
    _fields_ = [("width", ctypes.c_int), ("height", ctypes.c_int),
                ("xoffset", ctypes.c_int), ("format", ctypes.c_int),
                ("data", ctypes.c_void_p), ("byte_order", ctypes.c_int),
                ("bitmap_unit", ctypes.c_int), ("bitmap_bit_order", ctypes.c_int),
                ("bitmap_pad", ctypes.c_int), ("depth", ctypes.c_int),
                ("bytes_per_line", ctypes.c_int), ("bits_per_pixel", ctypes.c_int),
                ("red_mask", ctypes.c_ulong), ("green_mask", ctypes.c_ulong),
                ("blue_mask", ctypes.c_ulong), ("obdata", ctypes.c_void_p),
                ("f", ctypes.c_void_p * 6)]


class _XShmSegmentInfo(ctypes.Structure):
    _fields_ = [("shmseg", ctypes.c_ulong), ("shmid", ctypes.c_int),
                ("shmaddr", ctypes.c_void_p), ("readOnly", ctypes.c_int)]


def _lib(name: str) -> ctypes.CDLL:
    path = ctypes.util.find_library(name)
    if not path:
        raise OSError(f"lib{name} not found")
    return ctypes.CDLL(path)


class ScreenGrab:
    def __init__(self, display: str | None = None) -> None:
        self.x = _lib("X11")
        self.ext = _lib("Xext")
        self.c = _lib("c")
        self.x.XOpenDisplay.restype = ctypes.c_void_p
        self.x.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.d = self.x.XOpenDisplay(display.encode() if display else None)
        if not self.d:
            raise OSError("cannot open X display")
        for fn in ("XDefaultScreen", "XDisplayWidth", "XDisplayHeight", "XDefaultDepth"):
            getattr(self.x, fn).restype = ctypes.c_int
        self.x.XDefaultScreen.argtypes = [ctypes.c_void_p]
        self.x.XRootWindow.restype = ctypes.c_ulong
        self.x.XRootWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.x.XDefaultVisual.restype = ctypes.c_void_p
        self.x.XDefaultVisual.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.x.XDisplayWidth.argtypes = self.x.XDisplayHeight.argtypes = \
            self.x.XDefaultDepth.argtypes = [ctypes.c_void_p, ctypes.c_int]
        s = self.x.XDefaultScreen(self.d)
        self.root = self.x.XRootWindow(self.d, s)
        self.width = self.x.XDisplayWidth(self.d, s)
        self.height = self.x.XDisplayHeight(self.d, s)
        self.depth = self.x.XDefaultDepth(self.d, s)
        self.visual = self.x.XDefaultVisual(self.d, s)
        self.shm = False
        self.frame: np.ndarray | None = None
        try:
            self._init_shm()
            self.shm = True
        except Exception as exc:                 # noqa: BLE001 — fall back, say why
            self.shm_error = str(exc)
            self._init_plain()

    # -- MIT-SHM path ----------------------------------------------------------
    def _init_shm(self) -> None:
        ext, c = self.ext, self.c
        ext.XShmCreateImage.restype = ctypes.POINTER(_XImage)
        ext.XShmCreateImage.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
                                        ctypes.c_int, ctypes.c_void_p,
                                        ctypes.POINTER(_XShmSegmentInfo),
                                        ctypes.c_uint, ctypes.c_uint]
        ext.XShmAttach.argtypes = [ctypes.c_void_p, ctypes.POINTER(_XShmSegmentInfo)]
        ext.XShmGetImage.restype = ctypes.c_int
        ext.XShmGetImage.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_XImage),
                                     ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
        c.shmget.restype = ctypes.c_int
        c.shmget.argtypes = [ctypes.c_int, ctypes.c_size_t, ctypes.c_int]
        c.shmat.restype = ctypes.c_void_p
        c.shmat.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        c.shmctl.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
        self.x.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.info = _XShmSegmentInfo()
        img = ext.XShmCreateImage(self.d, self.visual, self.depth, ZPIXMAP, None,
                                  ctypes.byref(self.info), self.width, self.height)
        if not img:
            raise OSError("XShmCreateImage failed")
        self.img = img
        size = img.contents.bytes_per_line * img.contents.height
        shmid = c.shmget(IPC_PRIVATE, size, IPC_CREAT | 0o777)
        if shmid < 0:
            raise OSError("shmget failed")
        addr = c.shmat(shmid, None, 0)
        if addr in (None, ctypes.c_void_p(-1).value):
            raise OSError("shmat failed")
        self.info.shmid = shmid
        self.info.shmaddr = addr
        self.info.readOnly = 0
        img.contents.data = addr
        if not ext.XShmAttach(self.d, ctypes.byref(self.info)):
            raise OSError("XShmAttach refused")
        self.x.XSync(self.d, 0)
        c.shmctl(shmid, IPC_RMID, None)          # segment goes away with the process
        buf = (ctypes.c_ubyte * size).from_address(addr)
        stride = img.contents.bytes_per_line // 4
        self.frame = np.frombuffer(buf, dtype=np.uint8).reshape(self.height, stride, 4)[:, :self.width, :]

    # -- plain XGetImage path --------------------------------------------------
    def _init_plain(self) -> None:
        self.x.XGetImage.restype = ctypes.POINTER(_XImage)
        self.x.XGetImage.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong, ctypes.c_int]
        self.x.XDestroyImage = None
        self.frame = np.zeros((self.height, self.width, 4), dtype=np.uint8)

    def grab(self) -> np.ndarray:
        """Fill and return the BGRA frame (H, W, 4)."""
        if self.shm:
            if not self.ext.XShmGetImage(self.d, self.root, self.img, 0, 0, ALL_PLANES):
                raise OSError("XShmGetImage failed")
            return self.frame
        img = self.x.XGetImage(self.d, self.root, 0, 0, self.width, self.height, ALL_PLANES, ZPIXMAP)
        if not img:
            raise OSError("XGetImage failed")
        size = img.contents.bytes_per_line * img.contents.height
        buf = (ctypes.c_ubyte * size).from_address(img.contents.data)
        stride = img.contents.bytes_per_line // 4
        self.frame[:] = np.frombuffer(buf, dtype=np.uint8).reshape(self.height, stride, 4)[:, :self.width, :]
        # XDestroyImage is a macro: call the destroy_image function pointer in f[0]
        destroy = ctypes.cast(img.contents.f[0], ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(_XImage)))
        destroy(img)
        return self.frame
