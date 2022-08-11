# Signals

When a unit is awakened by juju and given a chance to do something, we call that an Event.
When a unit is awakened by juju and decides to notify **another unit** of some state change, we call that a Signal.
Signals are therefore analogous to Events, but for remote observers.

## Usage

Signals are meant to work seamlessly with Events.

The first step to implementing a signal observer/emitter is to add to `metadata.yaml` in both charms you wish to connect by means of signals:
```yaml
provides:  # or requires, it does not quite matter
  signal:  # or any name you like 
    interface: signal
```

Now you can send and receive signals.
Both charms will need a Signals instance to wrap the endpoint you prepared:

```python
from charms.signals.v0.signals import Signals

class MyCharm(CharmBase):
    def __init__(...):
         self.signals = Signals(endpoint='signals')
```

## Sending a signal
You send a signal by:

```python
self.signals.send(name='ping', payload='hello signals')
```

By default this will send the signal on all available channels for the `signals` endpoint. So if multiple charms are related to the emitter, they will all receive the 'ping' signal (with the same payload).
To target a specific relation instead, you can pass a `Relation` instance to the `send` method:

```python
relation: Relation = self.get_relation()
self.signals.send(name='ping', payload='hello signals', relation=relation)
```

This means only the remote units belonging to that relation will receive the signal.

## Receiving a signal
You receive a signal by observing the `Signals.on.receive` event.

You do so by adding to your charm's `__init__`:
```python
self.framework.observe(self.signals.on.receive, 
                       self._on_signal_receive)
```



## Publishing
Don't forget to open a PR with the version bumped. If you wish to bump the version (requires typer):

    export PYTHONPATH=$PYTHONPATH:$(pwd)
    python ./scripts/bump-version.py [minor=True] [major=False]

To inline (embed) the stub file in the library code:

    export PYTHONPATH=$PYTHONPATH:$(pwd)
    python ./scripts/inline-lib.py

After you've done that, you can use `sh ./scripts/publish` to publish to charmcraft.

Now you're ready to use the lib in your charms: `charmcraft fetch-lib charms.signals.v0.signals`

