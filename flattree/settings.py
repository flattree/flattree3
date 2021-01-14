_default_settings = {
    'separator': '.',
    'brackets': '[]',
    'quotes': "'"
}


def get_default_settings():
    return _default_settings


def get_symbols(settings):
    sep, bra, quo = (settings[x] for x in ('separator', 'brackets', 'quotes'))
    return sep, bra[0], bra[-1], quo[0], quo[-1]
