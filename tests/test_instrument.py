from th2822d_cli.instrument import TH2822D


class FakeTransport:
    def __init__(self, responses):
        self.responses = {key: list(value) for key, value in responses.items()}
        self.writes = []
        self.opened = False
        self.closed = False

    def open(self):
        self.opened = True
        return self

    def close(self):
        self.closed = True

    def write(self, command):
        self.writes.append(command)

    def query(self, command):
        self.writes.append(command)
        return self.responses[command].pop(0)


def test_configuration_and_go_local():
    transport = FakeTransport({
        "CALCulate:TOLerance:RANGe?": ["BIN2"],
        "FREQuency?": ["10kHz"],
        "VOLTage?": ["0.6V"],
        "FUNCtion:IMPA?": ["C"],
        "FUNCtion:IMPB?": ["D"],
        "FUNCtion:EQUivalent?": ["PAL"],
        "CALCulate:TOLerance:STATe?": ["ON"],
        "CALCulate:RECording:STATe?": ["OFF"],
    })
    with TH2822D(transport) as meter:
        config = meter.configuration()
    assert config.frequency_hz == 10000
    assert config.voltage_v == 0.6
    assert config.tolerance_range == 5
    assert transport.writes[-1] == "*GTL"
    assert transport.closed


def test_measurement_reads_active_parameters():
    transport = FakeTransport({
        "FUNCtion:IMPA?": ["C"],
        "FUNCtion:IMPB?": ["ESR"],
        "FETCh?": ["+6.8e-4,+1.5e-2,N"],
    })
    meter = TH2822D(transport)
    result = meter.measurement()
    assert result.primary_value == 0.00068
    assert result.secondary == "ESR"
    assert result.secondary_unit == "ohm"


def test_dcr_does_not_query_secondary():
    transport = FakeTransport({
        "FUNCtion:IMPA?": ["DCR"],
        "FETCh?": ["+1.0e+1,N"],
    })
    meter = TH2822D(transport)
    assert meter.measurement().primary == "DCR"
    assert "FUNCtion:IMPB?" not in transport.writes


def test_measurement_can_reuse_known_parameters():
    transport = FakeTransport({"FETCh?": ["+6.8e-4,+1.5e-2,N"]})
    meter = TH2822D(transport)
    result = meter.measurement("C", "ESR")
    assert result.secondary_value == 0.015
    assert transport.writes == ["FETCh?"]
