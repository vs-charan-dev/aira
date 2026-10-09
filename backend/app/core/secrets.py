"""User-bound Windows DPAPI, with encrypted files on E."""
import ctypes
import os
from ctypes import wintypes
from app.config import settings

class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

def _crypt(data: bytes, decrypt=False):
    if os.name != 'nt':
        raise RuntimeError('AIRA secret storage requires Windows DPAPI')
    buf = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)

def path():
    return settings.aira_data_dir / 'secrets' / 'gemini.dpapi'

def save_key(key):
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    if not key:
        target.unlink(missing_ok=True)
        return
    temp = target.with_suffix('.tmp')
    temp.write_bytes(_crypt(key.strip().encode()))
    temp.replace(target)

def read_key():
    target = path()
    return _crypt(target.read_bytes(), decrypt=True).decode() if target.exists() else None
