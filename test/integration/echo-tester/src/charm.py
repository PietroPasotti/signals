#!/usr/bin/env python3
# Copyright 2022 pietro
# See LICENSE file for licensing details.


import logging

from charms.signals.v0.signals import Signals, SignalEvent
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus

logger = logging.getLogger(__name__)


class MyEchoCharm(CharmBase):
    def __init__(self, fw, key=None):
        super().__init__(fw, key)
        print('hey!')
        self.signals = Signals(self, 'signals')
        self.unit.status = ActiveStatus('ready')
        self.framework.observe(self.signals.on.receive,
                               self._on_signal_receive)

    def _on_signal_receive(self, event: SignalEvent):
        if event.name == "ping":
            self.signals.send('pong', event.payload)
        else:
            print(f'unrecognized signal: {event.name}')


if __name__ == "__main__":
    main(MyEchoCharm)
