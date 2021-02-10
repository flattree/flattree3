from .settings import get_default_settings, get_symbols
from .private import Leaf, DictTag, ListTag, get_path, build_tree


def _gen_leaves(*trees, preface=None):
    for tree in trees:
        if isinstance(tree, FlatTree):
            if tree.crown:
                yield from tree.crown
            if tree.shadow:
                yield from tree.shadow
        else:
            if preface is None:
                preface = []
            if isinstance(tree, dict) and tree:
                for key, value in tree.items():
                    yield from _gen_leaves(tree[key],
                                           preface=preface + [DictTag(key)])
            elif isinstance(tree, list) and tree:
                for i, el in enumerate(tree):
                    yield from _gen_leaves(el, preface=preface + [ListTag(i)])
            else:
                yield Leaf(preface, tree)


def merge(*trees, settings=None):
    _, crown, shadow = build_tree(_gen_leaves(*trees))
    return FlatTree.from_leaves(crown, shadow, settings)


class FlatTree:
    @classmethod
    def from_leaves(cls, crown=None, shadow=None, settings=None):
        new_ft = cls.__new__(cls)
        new_ft._init_settings(settings=settings)
        new_ft._init_leaves(crown=crown, shadow=shadow)
        return new_ft

    def __init__(self, tree, settings=None):
        self._init_settings(settings)
        if isinstance(tree, FlatTree):
            crown = tree.crown[:]
        else:
            crown = list(_gen_leaves(tree))
        self._init_leaves(crown)

    def _init_settings(self, settings=None):
        self.settings = {}
        self.settings.update(settings or get_default_settings())
        self._stn_symbols = get_symbols(self.settings)

    def _init_leaves(self, crown=None, shadow=None):
        self.shadow = shadow or []
        self.crown = crown or []
        self.crown_idx = dict(self._gen_crown_idx())

    def _gen_crown_idx(self):
        for idx, leaf in enumerate(self.crown):
            yield get_path(leaf.route, self._stn_symbols), idx

    def get_xtree(self):
        xtree, *_ = build_tree(self.crown)
        return xtree
