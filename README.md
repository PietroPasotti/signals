# Signals

When a unit is awakened by juju and given a chance to do something, we call that an Event.
When a unit is awakened by juju and decides to notify **another unit** of some state change, we call that a Signal.
Signals are therefore analogous to Events, but for remote observers.

## Usage

The API mimics largely that of Events.
The main difference is that for signals to work between two applications, there needs to be a relation between them, which by default we call `channel`.

So the first step to implementing a signal observer/emitter is to add to `metadata.yaml` in both charms you wish to connect by means of signals:
```yaml
provides:
  channel: 
    interface: signal
```

(the provides/requires divide is largely semantic, and in this case it does not matter at all)

Next you add to your `charm.py`, on both sides (or write a library to share this code more easily):
```python
from signals import Signal, SignalSource, ObjectSignals
from ops import CharmBase


class Ready(Signal):
    pass
    

class Bork(Signal):
    def __init__(self, reason: str):
        self.reason = reason
    def snapshot(self):
        return {'reason': self.reason}
    def restore(self, snapshot):
        self.reason = snapshot['reason']
    
        
class MySignals(ObjectSignals):
    ready = SignalSource(Ready)
    bork = SignalSource(Bork)

    
class MyCharm(CharmBase):
    remote = MySignals()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.framework.observe(self.remote.ready, self._on_remote_ready)
        self.framework.observe(self.remote.bork, self._on_remote_bork)
        self.framework.observe(self.on.install, self._on_install)
        
    def _on_install(self, _):
        try:
            pass  # do installation
        except Exception as e:
            # this is how we notify the remote end that WE are bork
            self.remote.bork.emit(str(e))
        
    def _on_remote_ready(self, event: Ready):
        print('remote is ready')
        
    def _on_remote_bork(self, event: Bork):
        # the remote end just notified us that THEY are bork.
        print(f'remote is bork because {event.reason}')        
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

