from .private import FlatTreeBase


class FlatTree (FlatTreeBase):
    def __init__(self, xtree, settings=None):
        super().__init__(xtree, settings)
