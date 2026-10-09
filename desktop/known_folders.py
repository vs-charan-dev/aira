"""Resolve redirected user folders through Windows, never by guessing a profile."""
import ctypes
import uuid

IDS={'desktop':'B4BFCC3A-DB2C-424C-B029-7FE99A87C641',
     'documents':'FDD39AD0-238F-46AF-ADB4-6C85480369C7',
     'downloads':'374DE290-123F-4565-9164-39C4925E467B'}

def resolve(name):
    buffer=(ctypes.c_ubyte*16).from_buffer_copy(uuid.UUID(IDS[name.lower()]).bytes_le)
    path=ctypes.c_void_p()
    shell=ctypes.WinDLL('shell32')
    shell.SHGetKnownFolderPath.argtypes=(ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p))
    shell.SHGetKnownFolderPath.restype=ctypes.c_long
    result=shell.SHGetKnownFolderPath(ctypes.byref(buffer),0,None,ctypes.byref(path))
    if result!=0: raise ValueError('Windows could not resolve that user folder.')
    try: return ctypes.wstring_at(path)
    finally:
        ole=ctypes.WinDLL('ole32')
        ole.CoTaskMemFree.argtypes=(ctypes.c_void_p,)
        ole.CoTaskMemFree(path)
