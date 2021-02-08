from typing import List
from itertools import cycle
from collections import deque, UserDict
from collections.abc import Hashable
from .settings import get_symbols


class Leaf:
    def __init__(self, value):
        self.value = value

    def render(self):
        return self.value


class Key:
    def __init__(self, key):
        self.key = key


class ListKey(Key):
    def __init__(self, key):
        try:
            super().__init__(int(key))
        except ValueError:
            super().__init__(key)

    def is_valid(self):
        return isinstance(self.key, int)

    def __repr__(self):
        return f"ListKey({repr(self.key)})"


class DictKey(Key):
    def is_valid(self):
        return isinstance(self.key, Hashable)

    def __repr__(self):
        return f"DictKey({repr(self.key)})"


class Branch(UserDict):
    _allowed_key_type = None

    def render(self):
        return self.data

    @classmethod
    def key_type_matches(cls, key):
        return (
                cls._allowed_key_type is None
                or isinstance(key, cls._allowed_key_type) and key.is_valid()
        )


class DictBranch(Branch):
    _allowed_key_type = DictKey

    def render(self):
        result = {}
        for key, value in self.data.items():
            try:
                result[key] = value.render()
            except AttributeError:
                result[key] = value
        return result


class ListBranch(Branch):
    _allowed_key_type = ListKey

    def render(self):
        result = []
        for key in sorted(self.data.keys()):
            value = self.data[key]
            try:
                result.append(value.render())
            except AttributeError:
                result.append(value)
        return result


def gen_leaf_tuples(xtree, preface=None):
    if preface is None:
        preface = []
    if isinstance(xtree, dict) and xtree:
        for key, value in xtree.items():
            yield from gen_leaf_tuples(xtree[key], preface + [DictKey(key)])
    elif isinstance(xtree, list) and xtree:
        for i, el in enumerate(xtree):
            yield from gen_leaf_tuples(el, preface + [ListKey(i)])
    else:
        yield preface, xtree


def encode_step(step: Key, settings) -> str:
    sep, lbr, rbr, lquo, rquo = get_symbols(settings)
    if isinstance(step, ListKey):
        return f"{lbr}{step.key}{rbr}"
    special = set(f"{sep}{lbr}{rbr}{lquo}{rquo}")
    if isinstance(step.key, str):
        key_str = step.key
        if (
                key_str.isdigit()
                or key_str in ('None', 'False', 'True')
                or set(key_str) & special
        ):
            replaced = key_str.replace(lquo, lquo * 2)
            if lquo != rquo:
                replaced = replaced.replace(rquo, rquo * 2)
            return f"{lquo}{replaced}{rquo}"
        else:
            return key_str
    return str(step.key)


def gen_crown(xtree, settings, preface=None):
    sep, lbr, *_ = get_symbols(settings)
    for path, value in gen_leaf_tuples(xtree, preface=preface):
        if path:
            leafkey = encode_step(path[0], settings=settings)
            for step in path[1:]:
                key_str = encode_step(step, settings=settings)
                if not key_str.startswith(lbr):
                    key_str = sep + key_str
                leafkey += key_str
        else:
            leafkey = None
        yield leafkey, value


def build_crown(xtree, settings, preface=None):
    return dict(gen_crown(xtree=xtree, settings=settings, preface=preface))


def split_leafkey(leafkey, settings) -> List[str]:
    if not isinstance(leafkey, str):  # non-strings treated as None
        return []
    sep, lbr, _, lquo, rquo = get_symbols(settings)
    result = []
    buffer = ''
    quoted = False
    for c in leafkey:
        flush, append = False, True
        quoted = (quoted or c == lquo) and not (quoted and c == rquo)
        if not quoted:
            if c == sep:
                flush, append = True, False
            elif c == lbr:
                # Don't append buffer in front of the leading left bracket
                flush, append = bool(result), True
        if flush:
            result.append(buffer)
            buffer = ''
        if append:
            buffer += c
    result.append(buffer)
    return result


def decode_key_str(key_str, settings):
    if key_str.isdigit():
        return DictKey(int(key_str))
    sep, lbr, rbr, lquo, rquo = get_symbols(settings)
    if len(key_str) > 2 and key_str[0] == lbr and key_str[-1] == rbr:
        return ListKey(key_str[1:-1])
    key = key_str
    if len(key_str) > 2 and key_str[0] == lquo and key_str[-1] == rquo:
        key = key_str[1:-1].replace(lquo * 2, rquo)
        if lquo != rquo:
            key = key.replace(lquo * 2, lquo)
    elif key_str in ('None', 'False', 'True'):
        key = eval(key_str)
    return DictKey(key)


def _gen_leafstream(crown, settings):
    for leafkey, value in crown.items():
        key_parts = split_leafkey(leafkey, settings)
        leafpath = list(map(decode_key_str, key_parts, cycle((settings,))))
        yield leafpath, value


def _new_branch(key=None):
    if isinstance(key, ListKey):
        return ListBranch()
    return DictBranch()


def _from_leafstream(stream):
    istream = iter(stream)
    root = {}
    shadow = []
    try:
        # Set up root or return early
        leafpath, value = next(istream)
        if not leafpath:
            return value, list(istream)
        root = _new_branch(leafpath[0])
        # Build xtree and shadow
        while True:
            try:
                if not leafpath:
                    raise KeyError
                path = deque(leafpath)
                branch = root
                while path:
                    step = path.popleft()
                    if not branch.key_type_matches(step):
                        raise KeyError
                    if path:  # step is a branch
                        if step.key not in branch:
                            branch[step.key] = _new_branch(path[0])
                        branch = branch[step.key]
                    else:
                        if step.key in branch:
                            raise KeyError
                        branch[step.key] = value
            except KeyError:
                shadow.append((leafpath, value))
            leafpath, value = next(istream)
    except StopIteration:
        xtree = root.render() if isinstance(root, Branch) else root
        return xtree, shadow
