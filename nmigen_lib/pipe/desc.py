#!/usr/bin/env nmigen

from enum import Enum, auto
from typing import NamedTuple, Union

from nmigen import Shape
from nmigen.hdl.rec import Layout

class SignalDirection(Enum):
    UPSTREAM = auto()
    DOWNSTREAM = auto()


class SignalDesc(NamedTuple):
    name: str
    shape: Union[Layout, Shape]
    direction: SignalDirection = SignalDirection.DOWNSTREAM
