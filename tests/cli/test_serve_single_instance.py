"""Server startup must reject duplicates before background services start."""

from __future__ import annotations

import socket

from openjarvis.cli.serve import _bind_address_available


def test_bind_preflight_detects_an_existing_server() -> None:
    owner = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    owner.bind(("127.0.0.1", 0))
    host, port = owner.getsockname()
    try:
        available, error = _bind_address_available(host, port)
    finally:
        owner.close()

    assert available is False
    assert error


def test_bind_preflight_accepts_a_free_port() -> None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    host, port = probe.getsockname()
    probe.close()

    available, error = _bind_address_available(host, port)

    assert available is True
    assert error == ""
