import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_test_patches = pytest.MonkeyPatch()


def _deny_network(*args, **kwargs):
    raise AssertionError("Network access is disabled during tests")


def pytest_configure(config):
    _test_patches.setenv("GM_USE_STUB", "1")
    _test_patches.setattr(socket, "getaddrinfo", _deny_network)
    _test_patches.setattr(socket, "create_connection", _deny_network)
    _test_patches.setattr(socket.socket, "connect", _deny_network)
    _test_patches.setattr(socket.socket, "connect_ex", _deny_network)


def pytest_unconfigure(config):
    _test_patches.undo()
