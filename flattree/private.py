from typing import List
from collections import deque, UserDict
from collections.abc import Hashable
from .settings import get_default_settings, get_symbols


class Tag:
    def __init__(self, key):
        self.key = key


class ListTag(Tag):
    def __init__(self, key):
        try:
            super().__init__(int(key))
        except ValueError:
            super().__init__(key)

    def is_valid(self):
        return isinstance(self.key, int)

    def __repr__(self):
        return f"ListKey({repr(self.key)})"


class DictTag(Tag):
    def is_valid(self):
        return isinstance(self.key, Hashable)

    def __repr__(self):
        return f"DictKey({repr(self.key)})"


class Branch(UserDict):
    _allowed_tag_type = None

    def render(self):
        return self.data

    @classmethod
    def tag_matches(cls, tag):
        return (
                cls._allowed_tag_type is None
                or isinstance(tag, cls._allowed_tag_type) and tag.is_valid()
        )


class DictBranch(Branch):
    _allowed_tag_type = DictTag

    def render(self):
        result = {}
        for key, value in self.data.items():
            try:
                result[key] = value.render()
            except AttributeError:
                result[key] = value
        return result


class ListBranch(Branch):
    _allowed_tag_type = ListTag

    def render(self):
        result = []
        for key in sorted(self.data.keys()):
            value = self.data[key]
            try:
                result.append(value.render())
            except AttributeError:
                result.append(value)
        return result


def gen_leaves(xtree, preface=None):
    if preface is None:
        preface = []
    if isinstance(xtree, dict) and xtree:
        for key, value in xtree.items():
            yield from gen_leaves(xtree[key], preface + [DictTag(key)])
    elif isinstance(xtree, list) and xtree:
        for i, el in enumerate(xtree):
            yield from gen_leaves(el, preface + [ListTag(i)])
    else:
        yield Leaf(preface, xtree)


def encode_tag(tag: Tag, symbols) -> str:
    sep, lbr, rbr, lquo, rquo = symbols
    if isinstance(tag, ListTag):
        return f"{lbr}{tag.key}{rbr}"
    special = set(f"{sep}{lbr}{rbr}{lquo}{rquo}")
    if isinstance(tag.key, str):
        enctag = tag.key
        if (
                enctag.isdigit()
                or enctag in ('None', 'False', 'True')
                or set(enctag) & special
        ):
            replaced = enctag.replace(lquo, lquo * 2)
            if lquo != rquo:
                replaced = replaced.replace(rquo, rquo * 2)
            return f"{lquo}{replaced}{rquo}"
        else:
            return enctag
    return str(tag.key)


def decode_tag(enctag, symbols):
    if enctag.isdigit():
        return DictTag(int(enctag))
    sep, lbr, rbr, lquo, rquo = symbols
    if len(enctag) > 2 and enctag[0] == lbr and enctag[-1] == rbr:
        return ListTag(enctag[1:-1])
    key = enctag
    if len(enctag) > 2 and enctag[0] == lquo and enctag[-1] == rquo:
        key = enctag[1:-1].replace(rquo * 2, rquo)
        if lquo != rquo:
            key = key.replace(lquo * 2, lquo)
    elif enctag in ('None', 'False', 'True'):
        key = eval(enctag)
    return DictTag(key)


def get_path(route, symbols):
    sep, lbr, *_ = symbols
    if route:
        path = encode_tag(route[0], symbols=symbols)
        for tag in route[1:]:
            enctag = encode_tag(tag, symbols=symbols)
            if not enctag.startswith(lbr):
                enctag = f"{sep}{enctag}"
            path += enctag
    else:
        path = None
    return path


def get_route(path, symbols) -> List:
    if not isinstance(path, str):  # non-strings treated as None
        return []
    sep, lbr, _, lquo, rquo = symbols
    route = []
    buffer = ''
    quoted = False
    for c in path:
        flush, append = False, True
        quoted = (quoted or c == lquo) and not (quoted and c == rquo)
        if not quoted:
            if c == sep:
                flush, append = True, False
            elif c == lbr:
                # Don't append buffer in front of the leading left bracket:
                flush, append = bool(route), True
        if flush:
            route.append(decode_tag(buffer, symbols))
            buffer = ''
        if append:
            buffer += c
    route.append(decode_tag(buffer, symbols))
    return route


class Leaf:
    def __init__(self, route, value):
        self.route = route
        self.value = value

    def __repr__(self):
        return f"Leaf({repr(self.route)}, {repr(self.value)})"


class FlatTreeBase:
    def __init__(self, xtree, settings=None):
        local_settings = settings or get_default_settings()
        self.settings = {}
        self.settings.update(local_settings)
        self._stn_symbols = get_symbols(self.settings)
        self.crown = list(gen_leaves(xtree))
        self.crown_idx = dict(self._gen_crown_idx())
        self.shadow = []

    def _gen_crown_idx(self):
        for idx, leaf in enumerate(self.crown):
            yield get_path(leaf.route, self._stn_symbols), idx


def _from_leaves(leaves):
    leafstream = iter(leaves)
    root = {}
    crown = []
    shadow = []
    try:
        # Set up root or return early
        leaf = next(leafstream)
        if not leaf.route:
            return leaf.value, [leaf], list(leafstream)
        if isinstance(leaf.route[0], ListTag):
            root = ListBranch()
        else:
            root = DictBranch()
        # Build xtree, crown and shadow
        while True:
            try:
                if not leaf.route:
                    raise KeyError
                route = deque(leaf.route)
                branch = root
                while route:
                    tag = route.popleft()
                    if not branch.tag_matches(tag):
                        raise KeyError
                    if route:  # key is a branch
                        if tag.key not in branch:
                            if isinstance(route[0], ListTag):
                                branch[tag.key] = ListBranch()
                            else:
                                branch[tag.key] = DictBranch()
                        branch = branch[tag.key]
                    else:
                        if tag.key in branch:
                            raise KeyError
                        branch[tag.key] = leaf.value
                crown.append(leaf)
            except KeyError:
                shadow.append(leaf)
            leaf = next(leafstream)
    except StopIteration:
        xtree = root.render() if isinstance(root, Branch) else root
        return xtree, crown, shadow
