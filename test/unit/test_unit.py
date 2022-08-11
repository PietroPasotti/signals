# add here your unittests
import pytest
import yaml
from ops.charm import CharmBase, ActionEvent
from ops.testing import Harness

from signals import Signals, SignalEvent


@pytest.fixture
def emitter():
    class MyEmitterCharm(CharmBase):
        META = {"provides": {"signals": {"interface": "signals"}}}

        def __init__(self, fw, key=None):
            super().__init__(fw, key)
            self.signals = Signals(self, 'signals')
            self.framework.observe(self.signals.on.receive,
                                   self._on_signal_receive)

            self.pong = None

        def ping(self):
            self.signals.send('ping', 'ming!')

        def _on_signal_receive(self, event: SignalEvent):
            if event.name == 'pong':
                self.pong = event
            else:
                raise ValueError(event.name)

    return MyEmitterCharm


@pytest.fixture
def emitter_harness(emitter):
    return Harness(emitter,
                   meta=yaml.dump(emitter.META))


@pytest.fixture
def echo():
    class MyEchoCharm(CharmBase):
        META = {"requires": {"signals": {"interface": "signals"}}}

        def __init__(self, fw, key=None):
            super().__init__(fw, key)
            self.signals = Signals(self, 'signals')
            self.framework.observe(self.signals.on.receive,
                                   self._on_signal_receive)
            self.ping = None

        def _on_signal_receive(self, event: SignalEvent):
            if event.name == "ping":
                self.ping = event
                self.signals.send('pong', event.payload)
            else:
                raise ValueError(event.name)

    return MyEchoCharm


@pytest.fixture
def echo_harness(echo):
    return Harness(echo,
                   meta=yaml.dump(echo.META))


def test_emitter(emitter_harness):
    emitter_harness.begin()
    emitter_harness.set_leader(True)
    r_id = emitter_harness.add_relation("signals", "remote")
    emitter_harness.add_relation_unit(r_id, "remote/0")

    charm = emitter_harness.charm
    charm.ping()

    assert charm.signals.listeners[0].data[charm.app]['ping'] == 'ming!'

    charm.ping()
    assert charm.signals.listeners[0].data[charm.app][
               'ping'] == 'ming!' + charm.signals._padding


def test_echo_receive(echo_harness):
    echo_harness.begin()
    echo_harness.set_leader(True)

    r_id = echo_harness.add_relation("signals", "remote")
    echo_harness.add_relation_unit(r_id, "remote/0")

    charm = echo_harness.charm
    relation = charm.signals.listeners[0]

    echo_harness.update_relation_data(r_id, 'remote', {'ping': 'ming!'})
    assert charm.ping
    assert charm.ping.payload == 'ming!'
    assert charm.ping.leader
    assert charm.ping.relation is relation

    charm.ping = None
    echo_harness.update_relation_data(r_id, 'remote', {
        'ping': 'ming!' + charm.signals._padding})
    assert charm.ping
    assert charm.ping.payload == 'ming!'


def test_echo_bounce(echo_harness):
    echo_harness.set_leader(True)
    echo_harness.begin()
    r_id = echo_harness.add_relation("signals", "remote")
    echo_harness.add_relation_unit(r_id, "remote/0")

    charm = echo_harness.charm
    relation = charm.signals.listeners[0]

    echo_harness.update_relation_data(r_id, 'remote', {'ping': 'ming!'})
    assert relation.data[charm.app]['pong'] == 'ming!'
