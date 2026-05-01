from __future__ import annotations

import pickle
from collections.abc import Iterable
from typing import cast

import numpy as np
from flwr.app import ArrayRecord, Message
from flwr.serverapp import Grid
from flwr.serverapp.strategy import FedAvg
from flwr.serverapp.strategy.strategy_utils import aggregate_metricrecords


def encode_ensemble_payload(model_payloads: list[bytes]) -> bytes:
    return pickle.dumps(model_payloads, protocol=pickle.HIGHEST_PROTOCOL)


def decode_ensemble_payload(payload: bytes) -> list[bytes]:
    return list(cast(list[bytes], pickle.loads(payload)))


def bytes_to_arrayrecord(payload: bytes) -> ArrayRecord:
    return ArrayRecord([np.frombuffer(payload, dtype=np.uint8)])


def arrayrecord_to_bytes(arrays: ArrayRecord) -> bytes:
    return arrays["0"].numpy().tobytes()


class SerializedEnsembleStrategy(FedAvg):
    """Aggregate client-local serialized models into a simple ensemble payload."""

    def configure_train(
        self, server_round: int, arrays: ArrayRecord, config, grid: Grid
    ) -> Iterable[Message]:
        empty_payload = bytes_to_arrayrecord(b"")
        return super().configure_train(server_round, empty_payload, config, grid)

    def aggregate_train(
        self,
        server_round: int,
        replies: Iterable[Message],
    ) -> tuple[ArrayRecord | None, object | None]:
        valid_replies, _ = self._check_and_log_replies(replies, is_train=True)
        if not valid_replies:
            return None, None

        reply_contents = [msg.content for msg in valid_replies]
        array_record_key = next(iter(reply_contents[0].array_records.keys()))
        model_payloads = [
            cast(ArrayRecord, content[array_record_key])["0"].numpy().tobytes()
            for content in reply_contents
        ]
        arrays = bytes_to_arrayrecord(encode_ensemble_payload(model_payloads))
        metrics = aggregate_metricrecords(reply_contents, self.weighted_by_key)
        return arrays, metrics
