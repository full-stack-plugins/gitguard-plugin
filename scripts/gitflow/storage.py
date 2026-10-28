"""受管 JSON 读写：路径边界、原子替换与跨进程互斥。"""
from contextlib import contextmanager, ExitStack
import json
import os
from pathlib import Path
import tempfile
import stat
import sys

from .git import FlowError


def read_json(path):
    path = Path(path)
    if _redirected(path) or not path.is_file() or path.stat().st_size > 256 * 1024:
        raise FlowError('state_file_invalid', '配置或状态不是受限普通文件。')
    try:
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError('duplicate key')
                result[key] = value
            return result
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs)
    except (OSError, ValueError, UnicodeError) as exc:
        raise FlowError('state_json_invalid', '配置或状态 JSON 损坏。') from exc


def safe_dir(base, relative):
    base = Path(base).resolve()
    target = base / relative
    if not target.resolve().is_relative_to(base):
        raise FlowError('state_path_escape', '受管路径越出仓库或 Git 目录。')
    current = base
    for piece in Path(relative).parts:
        current = current / piece
        if _redirected(current):
            raise FlowError('state_symlink', '受管目录不能通过符号链接写入。')
    return target


def atomic_json(path, value):
    path = Path(path)
    if _redirected(path):
        raise FlowError('state_symlink', '不能替换符号链接状态文件。')
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    fd, name = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)



def _redirected(path):
    """Reject POSIX links and every Windows reparse point (including junctions)."""
    try:
        info = Path(path).lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def _check_lock_path(path):
    for parent in reversed(path.parents):
        if _redirected(parent):
            raise FlowError('state_symlink', '锁目录不能通过重解析点访问。')
    if _redirected(path):
        raise FlowError('state_symlink', '锁文件不能是符号链接或重解析点。')


@contextmanager
def _lock_file(path, *, movable=False):
    """Nonblocking kernel exclusion; process exit releases both backends."""
    path = Path(path).absolute()
    _check_lock_path(path)
    if sys.platform == 'win32':
        with _windows_lock(path, movable=movable):
            yield
        return
    import fcntl
    try:
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise FlowError('state_lock_unavailable', '无法安全打开状态锁。') from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise FlowError('state_file_invalid', '锁必须是单链接普通文件。')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise FlowError('operation_busy', '另一 GitFlow 操作占用此仓库，请稍后复核。') from exc
        yield
    finally:
        os.close(fd)


@contextmanager
def _windows_lock(path, *, movable=False):
    # A nonblocking byte-range kernel lock matches POSIX flock's cooperative
    # contract. DELETE sharing permits legacy-directory migration while the
    # original file remains locked. This is not an adversarial same-user sandbox.
    import ctypes
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE]
    create.restype = w.HANDLE
    close = kernel.CloseHandle
    close.argtypes = [w.HANDLE]
    close.restype = w.BOOL

    class FileInfo(ctypes.Structure):
        _fields_ = [('attributes', w.DWORD), ('created', w.FILETIME),
                    ('accessed', w.FILETIME), ('written', w.FILETIME),
                    ('volume', w.DWORD), ('size_high', w.DWORD), ('size_low', w.DWORD),
                    ('links', w.DWORD), ('index_high', w.DWORD), ('index_low', w.DWORD)]

    query = kernel.GetFileInformationByHandle
    query.argtypes = [w.HANDLE, ctypes.POINTER(FileInfo)]
    query.restype = w.BOOL
    class Overlapped(ctypes.Structure):
        _fields_ = [('internal', ctypes.c_size_t), ('internal_high', ctypes.c_size_t),
                    ('offset', w.DWORD), ('offset_high', w.DWORD), ('event', w.HANDLE)]

    lock_range = kernel.LockFileEx
    lock_range.argtypes = [w.HANDLE, w.DWORD, w.DWORD, w.DWORD, w.DWORD, ctypes.POINTER(Overlapped)]
    lock_range.restype = w.BOOL
    unlock = kernel.UnlockFileEx
    unlock.argtypes = [w.HANDLE, w.DWORD, w.DWORD, w.DWORD, ctypes.POINTER(Overlapped)]
    unlock.restype = w.BOOL
    pins = []
    handle = None
    acquired = False
    overlap = Overlapped()
    try:
        # Pin ordinary ancestors against rename/deletion; never deny WRITE on
        # directories (that blocks legitimate child namespace operations).
        parents = list(reversed(path.parents))
        if movable:
            parents = parents[:-1]  # the locked legacy directory is moved by prepare()
        for parent in parents:
            pin = create(str(parent), 0x1 | 0x80, 0x1 | 0x2, None, 3,
                         0x00200000 | 0x02000000, None)
            if pin == ctypes.c_void_p(-1).value:
                raise FlowError('state_lock_unavailable', '无法固定状态锁目录。') from ctypes.WinError(ctypes.get_last_error())
            pins.append(pin)
            info = FileInfo()
            if not query(pin, ctypes.byref(info)) or info.attributes & 0x400 or not info.attributes & 0x10:
                raise FlowError('state_symlink', '状态锁祖先必须为普通目录。')
        handle = create(str(path), 0x80000000 | 0x40000000 | 0x80, 0x1 | 0x2 | 0x4,
                        None, 4, 0x00200000, None)
        if handle == ctypes.c_void_p(-1).value:
            handle = None
            raise FlowError('state_lock_unavailable', '无法安全打开 Windows 状态锁。') from ctypes.WinError(ctypes.get_last_error())
        info = FileInfo()
        if not query(handle, ctypes.byref(info)):
            raise FlowError('state_lock_unavailable', '无法验证 Windows 状态锁身份。') from ctypes.WinError(ctypes.get_last_error())
        if info.attributes & (0x400 | 0x10) or info.links != 1:
            raise FlowError('state_file_invalid', '锁必须是无重解析点的单链接普通文件。')
        if not lock_range(handle, 0x1 | 0x2, 0, 1, 0, ctypes.byref(overlap)):
            code = ctypes.get_last_error()
            if code in (32, 33):
                raise FlowError('operation_busy', '另一 GitFlow 操作占用此仓库，请稍后复核。')
            raise FlowError('state_lock_unavailable', '无法取得 Windows 状态锁。') from ctypes.WinError(code)
        acquired = True
        _check_lock_path(path)
        yield
    finally:
        failed = False
        if acquired and not unlock(handle, 0, 1, 0, ctypes.byref(overlap)):
            failed = True
        if handle is not None and not close(handle):
            failed = True
        for pin in reversed(pins):
            if not close(pin):
                failed = True
        if failed:
            raise FlowError('state_lock_release_failed', '状态锁释放结果不确定，必须复核后继续。')


@contextmanager
def locked(facts):
    """只在显式变更时创建锁；迁移同时持有新旧布局的内核锁。"""
    from .layout import migration_plan, prepare, state_dir
    directory = state_dir(facts)
    migration_plan(facts, directory)
    directory.mkdir(parents=True, exist_ok=True)
    with ExitStack() as locks:
        locks.enter_context(_lock_file(directory / 'state.lock'))
        plan = migration_plan(facts, directory)
        for old, _ in plan[0]:
            locks.enter_context(_lock_file(old / 'state.lock', movable=True))
        prepare(facts, directory, migration_plan(facts, directory))
        yield
