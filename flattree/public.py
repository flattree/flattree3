from .settings import get_default_settings, get_symbols


class FlatTree:
    def __init__(self, xtree, settings=None):
        local_settings = settings or get_default_settings()
        self.settings = {}
        self.settings.update(local_settings)
