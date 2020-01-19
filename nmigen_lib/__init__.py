import sys

if sys.argv[:1] == ['-m']:
    __all__ = []
else:
    from . import pipe, seven_segment
    from .blinker import Blinker
    from .buzzer import Buzzer
    from .counter import Counter
    from .i2s import I2SOut
    from .mul import Mul
    from .oneshot import OneShot
    from .pll import PLL
    from .timer import Timer
    from .uart import UART, UARTTx, UARTRx
    from .seven_segment.hex_display import HexDisplay
    from .seven_segment.driver import Seg7Record

    __all__ = [
        'Blinker',
        'Buzzer',
        'Counter',
        'HexDisplay',
        'I2SOut',
        'Mul',
        'OneShot',
        'PLL',
        'Seg7Record',
        'Timer',
        'UART',
        'UARTTx',
        'UARTRx',
        'pipe',
        'seven_segment',
    ]
