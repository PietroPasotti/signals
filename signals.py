import logging
from typing import Any, Dict, List, Optional, Tuple

from ops.charm import CharmBase, RelationChangedEvent
from ops.framework import EventBase, EventSource, Object, ObjectEvents, StoredState
from ops.model import Model, Relation, RelationDataContent

_relation_dunder = "__relation__"

logger = logging.getLogger()


def _serialize_relation(relation: Relation) -> str:
    return f"{_relation_dunder}:{relation.name}/{relation.id}"


def _deserialize_relation(model: Model, obj: str) -> Relation:
    rel_name, rel_id = obj[len(f"{_relation_dunder}:") :].split("/")  # noqa: E203
    if relation := model.get_relation(rel_name, int(rel_id)):
        return relation
    raise RuntimeError(f"cannot deserialize {obj} as relation; not found.")


class _Event(EventBase):
    __args__ = ()  # type: Tuple[str, ...]
    __optional_kwargs__ = {}  # type: Dict[str, Any]

    serializers = {Relation: _serialize_relation}
    deserializers = {
        lambda s: (
            isinstance(s, str) and s.startswith(f"{_relation_dunder}:")
        ): _deserialize_relation
    }

    @classmethod
    def __attrs__(cls):
        return cls.__args__ + tuple(cls.__optional_kwargs__.keys())

    def __init__(self, handle, *args, **kwargs):
        super().__init__(handle)

        if not len(self.__args__) == len(args):
            raise TypeError(
                "expected {} args, got {}".format(len(self.__args__), len(args))
            )

        for attr, obj in zip(self.__args__, args):
            setattr(self, attr, obj)
        for attr, default in self.__optional_kwargs__.items():
            obj = kwargs.get(attr, default)
            setattr(self, attr, obj)

    def snapshot(self) -> dict:
        dct = super().snapshot() or {}
        for attr in self.__attrs__():
            obj = getattr(self, attr)
            if serializer := self.serializers.get(type(obj), None):
                obj = serializer(obj)

            try:
                dct[attr] = obj
            except ValueError as e:
                raise ValueError(
                    "cannot automagically serialize {}: "
                    "override this method and do it "
                    "manually.".format(obj)
                ) from e

        return dct

    def restore(self, snapshot: dict) -> None:
        super().restore(snapshot)
        for attr, obj in snapshot.items():
            for can_apply, deserializer in self.deserializers.items():
                if can_apply(obj):
                    obj = deserializer(self.framework.model, obj)
                    break
            setattr(self, attr, obj)


class SignalEvent(_Event):
    """Event emitted when a signal is received."""

    __args__ = ("name", "payload", "leader", "relation")

    name: str  # name of the signal
    payload: str  # payload of the signal
    leader: bool  # whether the source of the signal is the leader of the remote app
    relation: Relation  # the relation which emitted this signal


class SignalEvents(ObjectEvents):
    """Events emitted by the Signals endpoint."""

    receive = EventSource(SignalEvent)


class Signals(Object):
    """Endpoint for a signal emitter/receiver."""

    on = SignalEvents()
    _stored = StoredState()
    IGNORED_KEYS = {"egress-subnets", "ingress-address", "private-address"}

    def __init__(
        self, charm: CharmBase, endpoint: str, padding: str = "※", ignore_keys=None
    ):
        super().__init__(charm, endpoint)
        self._charm = charm
        self._ignored_keys = ignore_keys or type(self).IGNORED_KEYS
        self._endpoint = endpoint
        self._padding = padding
        self.framework.observe(
            self._charm.on[endpoint].relation_changed, self._on_relation_changed
        )
        self._stored.set_default(signals={})  # type:ignore

    @property
    def channels(self) -> List[Relation]:
        """Return all relations that this endpoint is connected to."""
        return self.model.relations.get(self._endpoint, [])

    def _broadcast(self, name: str, payload: str, relation: Optional[Relation] = None):
        relations = [relation] if relation else self.channels
        if self._charm.unit.is_leader():
            target = self.model.app
        else:
            target = self._charm.unit

        for r in relations:
            if r.data[target].get(name, None) == payload:  # identical payload exists
                payload += self._padding  # pad to ensure there's a diff
            r.data[target][name] = payload
        logger.debug(f"Emitting signal {name} via channel {self._endpoint}")

    # todo: on leadership change, move app to unit and viceversa

    def _check_seen(self, signal_name: str, payload: str, relation: Relation):
        rel_id = relation.id
        if previous := self._stored.signals.get(  # type:ignore
            (signal_name, rel_id), None
        ):
            if previous == payload:
                return True

        self._stored.signals[(signal_name, rel_id)] = payload  # type:ignore
        return False

    def _emit_unseen(
        self, signal_name: str, payload: str, leader: bool, relation: Relation
    ):
        if self._check_seen(signal_name, payload, relation):
            # seen this before: do nothing
            return

        # strip padding:
        payload = payload.strip(self._padding)
        logger.debug(
            f"Received {'leader ' if leader else ''}signal {signal_name} "
            f"via channel {self._endpoint}"
        )
        self.on.receive.emit(signal_name, payload, leader, relation)  # type:ignore

    def _check_for_signals(
        self, databag: RelationDataContent, relation: Relation, leader: bool = False
    ):
        for key, value in databag.items():
            if key in self._ignored_keys:
                continue
            self._emit_unseen(key, value, leader=True, relation=relation)

    def _on_relation_changed(self, event: RelationChangedEvent):
        relation = event.relation

        # type guards
        assert isinstance(relation, Relation)
        assert relation.app

        leader_data = relation.data[relation.app]
        self._check_for_signals(leader_data, relation, leader=True)
        for unit_data in (
            relation.data[unit] for unit in relation.units if not unit._is_our_unit
        ):
            self._check_for_signals(unit_data, relation, leader=False)

    def send(self, name: str, payload: str, relation: Optional[Relation] = None):
        """Send a signal to all channels (default) or a specific one."""
        self._broadcast(name, payload, relation)
