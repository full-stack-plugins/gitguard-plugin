"""Bounded native XML policy, shared by all worktrees of a repository.

Dictionary fields are XML elements; explicit scalar types preserve nullable and
optional v2 fields without a second serialized policy hidden inside the XML.
"""
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import xml.etree.ElementTree as ET
from xml.parsers import expat

from .git import FlowError
from .storage import _lock_file

LIMIT = 256 * 1024
MAX_DEPTH = 16
MAX_NODES = 4096
MAX_TEXT = 16384


def _invalid(message='XML policy is invalid or exceeds its resource budget.'):
    return FlowError('policy_xml_invalid', message)


def _validate(value):
    from .policy import validate
    try:
        return validate(value)
    except (TypeError, ValueError, KeyError, RecursionError) as exc:
        raise _invalid() from exc


def _element(tag, value):
    if not isinstance(tag, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', tag):
        raise _invalid()
    types = {dict: 'object', list: 'list', str: 'string', int: 'int', bool: 'bool', type(None): 'null'}
    if type(value) not in types:
        raise _invalid()
    node = ET.Element(tag, {'type': types[type(value)]})
    if type(value) is dict:
        for key, item in value.items(): node.append(_element(key, item))
    elif type(value) is list:
        for item in value: node.append(_element('item', item))
    elif type(value) is bool: node.text = 'true' if value else 'false'
    elif value is not None: node.text = str(value)
    return node


def encode(policy):
    """Validate and serialize the complete policy as UTF-8 XML."""
    _validate(policy)
    try:
        root = _element('policy', policy)
        ET.indent(root, space='  ')
        data = ET.tostring(root, encoding='utf-8', xml_declaration=True).replace(b'\r', b'&#13;') + b'\n'
        if decode(data) != policy: raise _invalid('XML serialization changed policy values.')
        return data
    except (ValueError, RecursionError, UnicodeError) as exc:
        raise _invalid() from exc


def decode(data):
    """Parse XML without DTDs, entities, namespaces, or unbounded resources."""
    if type(data) is not bytes or len(data) > LIMIT:
        raise _invalid()
    builder = ET.TreeBuilder()
    depth = nodes = text_size = 0
    parser = expat.ParserCreate()
    def reject(*args): raise _invalid()
    def start(tag, attrs):
        nonlocal depth, nodes
        depth += 1; nodes += 1
        if depth > MAX_DEPTH or nodes > MAX_NODES or set(attrs) != {'type'} or len(tag) > 64 or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', tag) or len(attrs['type']) > 16:
            raise _invalid()
        builder.start(tag, attrs)
    def end(tag):
        nonlocal depth
        builder.end(tag); depth -= 1
    def characters(value):
        nonlocal text_size
        text_size += len(value)
        if text_size > 128 * 1024 or len(value) > MAX_TEXT: raise _invalid()
        builder.data(value)
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = characters
    parser.StartDoctypeDeclHandler = reject
    parser.EntityDeclHandler = reject
    parser.ExternalEntityRefHandler = reject
    parser.SkippedEntityHandler = reject
    parser.ProcessingInstructionHandler = reject
    parser.CommentHandler = reject
    def unpack(node):
        kind = node.attrib['type']; value = node.text or ''
        if len(value) > MAX_TEXT or (node.tail or '').strip(): raise _invalid()
        if kind in ('object', 'list'):
            if value.strip(): raise _invalid()
            if kind == 'list':
                if any(child.tag != 'item' for child in node): raise _invalid()
                return [unpack(child) for child in node]
            result = {}
            for child in node:
                if child.tag in result: raise _invalid()
                result[child.tag] = unpack(child)
            return result
        if len(node): raise _invalid()
        if kind == 'string': return value
        if kind == 'null' and not value: return None
        if kind == 'bool' and value in ('true', 'false'): return value == 'true'
        if kind == 'int' and re.fullmatch(r'-?(0|[1-9][0-9]{0,18})', value): return int(value)
        raise _invalid()
    try:
        parser.Parse(data, True)
        root = builder.close()
        if root.tag != 'policy' or root.attrib != {'type': 'object'}: raise _invalid()
        return _validate(unpack(root))
    except (expat.ExpatError, ValueError, UnicodeError, RecursionError) as exc:
        raise _invalid() from exc


def _redirected(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def _parents(path):
    for parent in reversed(path.parents):
        info = parent.lstat()
        if _redirected(info) or not stat.S_ISDIR(info.st_mode):
            raise FlowError('policy_path_invalid', 'Policy ancestors must be ordinary directories.')


def policy_path(facts):
    """Locate git-common-dir/gitflow.xml without resolving away redirects."""
    path = Path(os.path.abspath(facts['common_dir'])) / 'gitflow.xml'
    try: _parents(path)
    except OSError as exc: raise FlowError('policy_path_invalid', 'Policy directory is unavailable.') from exc
    return path


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, getattr(info, 'st_birthtime_ns', None))


def _same_file(path_signature, handle_signature):
    # CPython 3.12 Windows lstat uses creation time for ctime, whereas
    # fstat can expose ChangeTime. Only this cross-API comparison differs.
    # Each API's own before/after signature remains exact, including ctime.
    if sys.platform == 'win32':
        return path_signature[:4] + path_signature[5:] == handle_signature[:4] + handle_signature[5:]
    return path_signature == handle_signature


def _identity(path):
    try: info = path.lstat()
    except FileNotFoundError: return None
    if _redirected(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > LIMIT:
        raise FlowError('policy_file_invalid', 'Policy must be a bounded single-link ordinary file.')
    return _signature(info)


def read_policy(facts):
    path = policy_path(facts)
    try:
        before = _identity(path)
        if before is None: raise FlowError('policy_missing', 'No native XML policy is initialized.')
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            opened = _signature(info)
            if not _same_file(before, opened) or _redirected(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1: raise _invalid()
            raw = stream.read(LIMIT + 1)
            after = os.fstat(stream.fileno())
            if _signature(after) != opened or _redirected(after) or not stat.S_ISREG(after.st_mode) or after.st_nlink != 1: raise _invalid()
        if _identity(path) != before: raise _invalid()
        _parents(path)
        return decode(raw)
    except OSError as exc: raise FlowError('policy_file_invalid', 'Cannot safely read XML policy.') from exc


def write_policy(facts, policy):
    """Write validated XML under an independent lock and atomic replacement."""
    data = encode(policy)
    path = policy_path(facts)
    temporary = None
    try:
        with _lock_file(path.parent / 'gitflow.xml.lock'):
            _parents(path)
            parent = path.parent.stat()
            before = _identity(path)
            fd, temporary = tempfile.mkstemp(prefix='.gitflow-write-', dir=path.parent)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            _parents(path)
            now = path.parent.stat()
            if (parent.st_dev, parent.st_ino) != (now.st_dev, now.st_ino) or _identity(path) != before:
                raise FlowError('policy_changed', 'Policy identity changed during write.')
            os.replace(temporary, path)
            temporary = None
            if os.name != 'nt':
                directory = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
                try: os.fsync(directory)
                finally: os.close(directory)
    except OSError as exc: raise FlowError('policy_file_invalid', 'Cannot safely write XML policy.') from exc
    finally:
        if temporary is not None: Path(temporary).unlink(missing_ok=True)
