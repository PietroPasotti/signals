#!/usr/bin/env python3
# Copyright 2022 pietro
# See LICENSE file for licensing details.


import logging

from charms.signals.v0.signals import Signals, SignalEvent
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus

logger = logging.getLogger(__name__)


class MyPingCharm(CharmBase):
    def __init__(self, fw, key=None):
        super().__init__(fw, key)
        self.signals = Signals(self, 'signals')
        self.unit.status = ActiveStatus('ready')
        self.framework.observe(self.signals.on.receive,
                               self._on_signal_receive)
        self.framework.observe(self.on.ping_action,
                               self.ping)

    def ping(self, _):
        self.signals.send('ping', 'ming!')

    def _on_signal_receive(self, event: SignalEvent):
        if event.name == 'pong':
            print('got ponged!')
        else:
            raise ValueError(event.name)


if __name__ == "__main__":
    main(MyPingCharm)
