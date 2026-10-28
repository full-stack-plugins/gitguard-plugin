"""Windows-only bounded argv runner; Job binding precedes first child instruction.

Uses only Python standard-library ctypes. Console interrupts are recorded while
resources are being acquired, then handled by the controller and bounded cleanup.
"""
import ctypes as c
from ctypes import wintypes as w
import os
import signal
import subprocess
import threading
import time

from .git import FlowError


class _BasicLimits(c.Structure):
    _fields_ = [('process_time', c.c_longlong), ('job_time', c.c_longlong),
                ('flags', w.DWORD), ('minimum', c.c_size_t), ('maximum', c.c_size_t),
                ('active_limit', w.DWORD), ('affinity', c.c_size_t),
                ('priority', w.DWORD), ('scheduling', w.DWORD)]


class _IoCounters(c.Structure):
    _fields_ = [(name, c.c_ulonglong) for name in ('read_ops', 'write_ops', 'other_ops',
                                                'read_bytes', 'write_bytes', 'other_bytes')]


class _ExtendedLimits(c.Structure):
    _fields_ = [('basic', _BasicLimits), ('io', _IoCounters),
                ('process_memory', c.c_size_t), ('job_memory', c.c_size_t),
                ('peak_process_memory', c.c_size_t), ('peak_job_memory', c.c_size_t)]


class _Accounting(c.Structure):
    _fields_ = [(name, c.c_longlong) for name in ('user', 'kernel', 'period_user', 'period_kernel')] + [
        (name, w.DWORD) for name in ('faults', 'total', 'active', 'terminated')]


class _ThreadEntry(c.Structure):
    _fields_ = [('size', w.DWORD), ('usage', w.DWORD), ('tid', w.DWORD),
                ('pid', w.DWORD), ('priority', w.LONG), ('delta', w.LONG), ('flags', w.DWORD)]


class _Api:
    def __init__(self):
        self.dll = c.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'CloseHandle': ([w.HANDLE], w.BOOL),
            'CreateJobObjectW': ([c.c_void_p, w.LPCWSTR], w.HANDLE),
            'SetInformationJobObject': ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD], w.BOOL),
            'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], w.BOOL),
            'TerminateJobObject': ([w.HANDLE, w.UINT], w.BOOL),
            'QueryInformationJobObject': ([w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p], w.BOOL),
            'OpenProcess': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            'CreateToolhelp32Snapshot': ([w.DWORD, w.DWORD], w.HANDLE),
            'Thread32First': ([w.HANDLE, c.POINTER(_ThreadEntry)], w.BOOL),
            'Thread32Next': ([w.HANDLE, c.POINTER(_ThreadEntry)], w.BOOL),
            'OpenThread': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            'GetProcessIdOfThread': ([w.HANDLE], w.DWORD),
            'ResumeThread': ([w.HANDLE], w.DWORD),
            'PeekNamedPipe': ([w.HANDLE, c.c_void_p, w.DWORD, c.c_void_p, c.POINTER(w.DWORD), c.c_void_p], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.dll, name)
            function.argtypes, function.restype = args, result
            setattr(self, name, function)

    def checked_handle(self, raw):
        if not raw or raw == c.c_void_p(-1).value:
            raise c.WinError(c.get_last_error())
        return raw

    def check(self, result):
        if not result:
            raise c.WinError(c.get_last_error())

    def active(self, job):
        state = _Accounting()
        self.check(self.QueryInformationJobObject(job, 1, c.byref(state), c.sizeof(state), None))
        return state.active

    def resume(self, pid):
        # Popen retains its process handle throughout, preventing PID reuse.
        snapshot = self.checked_handle(self.CreateToolhelp32Snapshot(4, 0))
        thread = None
        try:
            entry = _ThreadEntry()
            entry.size = c.sizeof(entry)
            self.check(self.Thread32First(snapshot, c.byref(entry)))
            found = []
            while True:
                if entry.pid == pid:
                    found.append(entry.tid)
                if not self.Thread32Next(snapshot, c.byref(entry)):
                    if c.get_last_error() != 18:  # ERROR_NO_MORE_FILES
                        raise c.WinError(c.get_last_error())
                    break
            if len(found) != 1:
                raise OSError('suspended process does not have exactly one initial thread')
            thread = self.checked_handle(self.OpenThread(0x0002 | 0x0800, False, found[0]))
            if self.GetProcessIdOfThread(thread) != pid:
                raise OSError('thread owner changed before resume')
            if self.ResumeThread(thread) != 1:
                raise OSError('unexpected initial thread suspension count')
        finally:
            close_error = None
            for handle in (thread, snapshot):
                if handle and not self.CloseHandle(handle):
                    close_error = c.WinError(c.get_last_error())
            if close_error is not None:
                raise close_error


def _fully_qualified_windows_path(value):
    # Python 3.11 ntpath.isabs accepts root-relative \foo; that still depends
    # on the current drive. Require an explicit drive or UNC share as well.
    import ntpath
    drive, tail = ntpath.splitdrive(value)
    return bool(drive) and (tail.startswith(('\\', '/')) or
                            (drive.startswith('\\\\') and not tail))


def _resolve_native(executable, env):
    """Search only explicit absolute PATH directories, never process cwd/PATHEXT.

    PATH remains the configured tool trust boundary. Empty/relative components
    cannot authorize execution from whichever repository happens to be current.
    """
    import ntpath
    value = os.fspath(executable)
    if _fully_qualified_windows_path(value):
        candidates = [value]
    elif ntpath.dirname(value):
        raise OSError('relative executable paths are not authorized')
    else:
        name = value if value.lower().endswith('.exe') else value + '.exe'
        search = next((v for k, v in env.items() if k.upper() == 'PATH'), '')
        directories = (part.strip().strip('"') for part in search.split(';'))
        candidates = [ntpath.join(directory, name) for directory in directories
                      if directory and _fully_qualified_windows_path(directory)]
    for candidate in candidates:
        if candidate.lower().endswith('.exe') and os.path.isfile(candidate):
            return os.path.abspath(candidate)
    raise FileNotFoundError('native executable was not found in absolute configured PATH directories')


def run_windows(argv, env, timeout, *, cancelled=None, _before_resume=None):
    """Return complete bytes, or a structured unverified error; no shell.

    ``_before_resume`` is a private test seam, never exposed through CLI/env.
    A fresh unnamed Job denies breakaway and kills remaining descendants even
    after normal leader exit. Existing unrelated ancestor jobs are not changed.
    """
    if os.name != 'nt':
        raise FlowError('windows_process_control_unverified', 'Windows 原生进程监管不可用；未启动命令。')
    if not argv or str(argv[0]).lower().endswith(('.bat', '.cmd')):
        raise FlowError('git_io_error', '需要原生可执行文件；不隐式调用命令解释器。')
    import msvcrt
    deadline = time.monotonic() + timeout
    try:
        api = _Api()
    except (OSError, AttributeError) as exc:
        raise FlowError('windows_process_control_unverified', 'Windows 原生进程监管不可用；未启动命令。') from exc
    handles = []
    proc = None
    job = None
    assigned = False
    started = False
    interrupted = False
    previous = {}
    buffers = [bytearray(), bytearray()]
    eof = [False, False]
    cleanup_error = None

    def mark_interrupt(_number, _frame):
        nonlocal interrupted
        interrupted = True

    # Avoid KeyboardInterrupt between native handle acquisition and ownership.
    if threading.current_thread() is threading.main_thread():
        for number in (signal.SIGINT, signal.SIGBREAK):
            previous[number] = signal.signal(number, mark_interrupt)

    def check_budget():
        if interrupted or (cancelled is not None and cancelled()):
            raise FlowError('git_cancelled', 'Git 操作已取消；实际写入结果未知，必须复核状态。')
        if time.monotonic() >= deadline:
            raise FlowError('git_timeout', 'Git 操作超时；需要重新读取目标状态。')

    def drain():
        # Sole reader; never ask os.read for bytes not already reported present.
        for index, stream in enumerate((proc.stdout, proc.stderr)):
            if eof[index]:
                continue
            available = w.DWORD()
            if not api.PeekNamedPipe(msvcrt.get_osfhandle(stream.fileno()), None, 0,
                                     None, c.byref(available), None):
                error = c.get_last_error()
                if error == 109:  # ERROR_BROKEN_PIPE
                    eof[index] = True
                    continue
                raise c.WinError(error)
            if available.value:
                data = os.read(stream.fileno(), min(available.value, 65536))
                if not data:
                    eof[index] = True
                buffers[index].extend(data)
                if sum(map(len, buffers)) > 4 * 1024 * 1024:
                    raise FlowError('git_output_limit', 'Git 输出超过预算，不采用截断结果。')

    try:
        check_budget()
        argv = [_resolve_native(argv[0], env), *argv[1:]]
        job = api.checked_handle(api.CreateJobObjectW(None, None))
        handles.append(job)
        limits = _ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway.
        api.check(api.SetInformationJobObject(job, 9, c.byref(limits), c.sizeof(limits)))
        proc = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                creationflags=0x00000004 | 0x00000200, close_fds=True)
        process_handle = api.checked_handle(api.OpenProcess(0x0100 | 0x0001, False, proc.pid))
        handles.append(process_handle)
        api.check(api.AssignProcessToJobObject(job, process_handle))
        assigned = True
        if _before_resume is not None:
            _before_resume()
        check_budget()
        # ResumeThread may execute the child even if subsequent bookkeeping
        # fails. From this point any uncertainty must journal as unknown.
        started = True
        api.resume(proc.pid)
        while True:
            check_budget()
            drain()
            code = proc.poll()
            if code is not None:
                # A normally exited leader can leave descendants holding pipes.
                api.check(api.TerminateJobObject(job, 1))
                break
            time.sleep(0.002)
        # Final drain remains bounded by the original request deadline.
        while not all(eof):
            check_budget()
            drain()
            if not all(eof):
                time.sleep(0.002)
        return subprocess.CompletedProcess(argv, code, bytes(buffers[0]), bytes(buffers[1]))
    except KeyboardInterrupt as exc:
        raise FlowError('git_cancelled', 'Git 操作已取消；实际写入结果未知，必须复核状态。') from exc
    except FileNotFoundError as exc:
        raise FlowError('git_unavailable', 'Git 命令不可用，请先恢复已有工具。') from exc
    except OSError as exc:
        # A command that ran may already have changed the repository. Preserve
        # unknown-journal semantics, not the pre-launch incomplete classification.
        error = FlowError('git_cleanup_failed' if started else 'git_io_error',
                          'Windows Git 进程监管失败；必须复核状态。')
        error.os_error = getattr(exc, 'winerror', None) or getattr(exc, 'errno', None)
        raise error from exc
    finally:
        try:
            if proc is not None:
                cleanup_deadline = time.monotonic() + 1
                try:
                    if assigned:
                        api.check(api.TerminateJobObject(job, 1))
                    else:
                        proc.kill()  # still suspended; job assignment did not succeed.
                    while proc.poll() is None or (assigned and api.active(job)):
                        if time.monotonic() >= cleanup_deadline:
                            raise OSError('process tree cleanup deadline expired')
                        time.sleep(0.002)
                except OSError as exc:
                    cleanup_error = exc
                for stream in (proc.stdout, proc.stderr):
                    try:
                        stream.close()
                    except OSError as exc:
                        cleanup_error = exc
                # CPython's process handle normally closes at Popen destruction;
                # closing explicitly makes ownership independent of GC timing.
                if getattr(proc, '_handle', None) is not None:
                    try:
                        proc._handle.Close()
                    except OSError as exc:
                        cleanup_error = exc
            for handle in reversed(handles):
                if not api.CloseHandle(handle):
                    cleanup_error = c.WinError(c.get_last_error())
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)
        if cleanup_error is not None:
            error = FlowError('git_cleanup_failed', 'Git 进程树清理未确认；结果未知，必须复核进程与仓库状态。')
            error.os_error = getattr(cleanup_error, 'winerror', None) or getattr(cleanup_error, 'errno', None)
            raise error from cleanup_error
