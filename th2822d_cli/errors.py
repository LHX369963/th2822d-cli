"""Public error types used by the TH2822D client."""


class TH2822DError(Exception):
    """Base error for expected CLI failures."""


class TransportError(TH2822DError):
    """Serial discovery, access, timeout, or I/O failure."""


class TransportTimeout(TransportError):
    """No complete response arrived before the serial deadline."""


class ProtocolError(TH2822DError):
    """Invalid SCPI operation or malformed instrument response."""
