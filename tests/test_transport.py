from __future__ import annotations

import os
import pty
import termios

import pytest

import th2822d_cli.transport as transport
from th2822d_cli.errors import ProtocolError, TransportError, TransportTimeout
from th2822d_cli.transport import SerialTransport


class FakeSerial:
    def __init__(self, response=b"OK\r\n"):
        self.response = response
        self.writes = []
        self.flushed = False
        self.closed = False

    def write(self, data):
        self.writes.append(data)
        return len(data)

    def flush(self):
        self.flushed = True

    def readline(self):
        return self.response

    def close(self):
        self.closed = True


def transport_with(fake):
    value = SerialTransport("/dev/fake", command_delay=0, query_retries=0)
    value._serial = fake
    return value


def test_query_uses_ascii_lf_and_strips_crlf():
    fake = FakeSerial(b"100Hz\r\n")
    value = transport_with(fake)
    assert value.query("FREQuency?") == "100Hz"
    assert fake.writes == [b"FREQuency?\n"]
    assert fake.flushed


@pytest.mark.parametrize("command", ["", "A\nB", "电压?"])
def test_reject_invalid_commands(command):
    with pytest.raises(ProtocolError):
        SerialTransport.encode(command)


def test_timeout_and_non_ascii():
    with pytest.raises(TransportTimeout):
        transport_with(FakeSerial(b"")).read_line()
    with pytest.raises(ProtocolError):
        transport_with(FakeSerial(b"\xff\n")).read_line()


def test_timeout_must_be_positive():
    with pytest.raises(TransportError):
        SerialTransport("/dev/fake", 0)
    with pytest.raises(TransportError):
        SerialTransport("/dev/fake", command_delay=-1)
    with pytest.raises(TransportError):
        SerialTransport("/dev/fake", query_retries=-1)


def test_query_retries_timeout_once():
    class RetrySerial(FakeSerial):
        def __init__(self):
            super().__init__()
            self.responses = [b"", b"answer\r\n"]

        def readline(self):
            return self.responses.pop(0)

        def reset_input_buffer(self):
            pass

    fake = RetrySerial()
    value = SerialTransport("/dev/fake", command_delay=0, query_retries=1)
    value._serial = fake
    assert value.query("FETCh?") == "answer"
    assert fake.writes == [b"FETCh?\n", b"FETCh?\n"]


def test_open_disables_hangup_on_close():
    master_fd, slave_fd = pty.openpty()
    try:
        path = os.ttyname(slave_fd)
        with SerialTransport(path, command_delay=0) as value:
            attributes = termios.tcgetattr(value.serial.fileno())
            assert not attributes[2] & termios.HUPCL
    finally:
        os.close(master_fd)
        os.close(slave_fd)


def test_explicit_port_does_not_enumerate_serial_devices(monkeypatch):
    class FakeTransport:
        def __init__(self, port, timeout):
            assert (port, timeout) == ("/dev/ttyUSB7", 1.0)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def query(self, command):
            assert command == "*IDN?"
            return "TH2822D Handheld LCR Meter,VER4.5.2307,SNTEST"

    monkeypatch.setattr(transport, "serial_ports", lambda: pytest.fail("enumerated ports"))
    port, identity = transport.choose_port("/dev/ttyUSB7", 1.0, FakeTransport)
    assert port == "/dev/ttyUSB7"
    assert identity.model == "TH2822D Handheld LCR Meter"
