"""Startup source fingerprint, allowing launchers to detect an older backend.

This module is also a standalone CLI; it imports no application configuration,
keys or provider clients. The value is captured once, not re-read per health call.
"""
import hashlib
from pathlib import Path


def backend_revision():
    backend = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    sources = sorted([backend / 'main.py', *backend.joinpath('app').rglob('*.py')])
    for source in sources:
        digest.update(source.relative_to(backend).as_posix().encode('utf-8') + b'\0')
        digest.update(source.read_bytes() + b'\0')
    return digest.hexdigest()


RUNTIME_REVISION = backend_revision()

if __name__ == '__main__':
    print(RUNTIME_REVISION)
