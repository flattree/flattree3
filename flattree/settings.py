from typing import Dict, Tuple

_default_settings = {
    'separator': '.',
    'brackets': '[]',
    'quotes': "'"
}


def get_default_settings() -> Dict:
    return _default_settings


def get_symbols(settings) -> Tuple[str, str, str, str, str]:
    sep: str
    bra: str
    quo: str
    sep, bra, quo = (settings[x] for x in ('separator', 'brackets', 'quotes'))
    return sep, bra[0], bra[-1], quo[0], quo[-1]
