"""Install the gitguard launcher into a user bin directory."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "bin" / "gitguard"
DEFAULT_BIN = Path.home() / ".local" / "bin"


def target(argv):
    directory = None
    index = 1
    while index < len(argv):
        option = argv[index]
        if option in ("--dry-run", "--json"):
            index += 1
            continue
        if option != "--bin-dir":
            raise ValueError("unknown option: " + option)
        if directory is not None:
            raise ValueError("--bin-dir may only be provided once")
        index += 1
        if index >= len(argv) or not argv[index] or argv[index].startswith("-"):
            raise ValueError("--bin-dir requires a directory path")
        directory = argv[index]
        index += 1
    return (Path(directory).expanduser().resolve() if directory is not None else DEFAULT_BIN) / ("gitguard.cmd" if sys.platform == "win32" else "gitguard")


def payload(command, decision, **extra):
    code = {"allow": 0, "deny": 1, "error": 2, "unverified": 3}.get(decision, 4)
    return {"schemaVersion": "partme.guard/v1", "tool": "gitguard", "command": "gitguard." + command,
            "decision": decision, "exitCode": code, "findings": [], "evidence": {}, **extra}


def windows_launcher(path):
    entry = ROOT / "scripts" / "cli_entry.py"
    # Avoid cmd expansion/quoting ambiguity instead of trying to escape arbitrary
    # batch metacharacters. Ordinary paths containing spaces remain supported.
    for value in (str(path), sys.executable, str(entry)):
        if not value.isascii():
            raise ValueError("Windows batch launcher paths must be ASCII until codepage support is verified")
        if not value or any(character in value for character in '%!&^\r\n"<>|()'):
            raise ValueError("Windows launcher paths must not contain batch metacharacters")
    return ("@echo off\r\nsetlocal DisableDelayedExpansion\r\n"
            f'"{sys.executable}" "{entry}" %*\r\nexit /b %errorlevel%\r\n').encode()


def windows_action(command, path, argv):
    content = windows_launcher(path)
    exists = path.exists() or path.is_symlink()
    managed = (exists and not path.is_symlink() and path.is_file()
               and path.stat().st_size == len(content) and path.read_bytes() == content)
    if (command == "uninstall" and not managed) or (exists and not managed):
        print(json.dumps(payload(command, "deny", error="not_managed", path=str(path)), ensure_ascii=False))
        return 1
    if "--dry-run" in argv:
        print(json.dumps(payload(command, "allow", dryRun=True, path=str(path)), ensure_ascii=False))
        return 0
    if command == "uninstall":
        path.unlink()
        result = payload(command, "allow", removed=str(path))
    else:
        if not managed:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as output:
                output.write(content)
        result = payload(command, "allow", installed=True, target=str(path))
    print(json.dumps(result, ensure_ascii=False))
    return 0


def main(argv):
    from gitflow.stdio import configure_stdio
    configure_stdio()
    command = argv[0] if argv else "install"
    if command == "completion":
        shell = argv[1] if len(argv) > 1 else "bash"
        commands = "version discover init audit gate policy branch sync release recovery context hooks organization doctor check status report"
        if shell not in ("bash", "zsh", "fish"):
            print("usage: gitguard completion bash|zsh|fish", file=sys.stderr)
            return 2
        if shell == "fish":
            print("complete -c gitguard -f -a '" + commands + "'")
        else:
            print("complete -W '" + commands + "' gitguard")
        return 0
    if command not in ("install", "uninstall", "upgrade"):
        print("usage: gitguard install|uninstall|upgrade [--bin-dir DIR] [--dry-run]", file=sys.stderr)
        return 2
    try:
        path = target(argv)
        if sys.platform == "win32":
            return windows_action(command, path, argv)
    except ValueError as exc:
        print(json.dumps(payload(command, "error", error="invalid_arguments", message=str(exc)), ensure_ascii=False))
        return 2
    except OSError as exc:
        print(json.dumps(payload(command, "error", error="installation_io_error", message=str(exc)), ensure_ascii=False))
        return 2
    if command == "uninstall":
        if not path.is_symlink() or path.resolve() != SOURCE.resolve():
            print(json.dumps(payload("uninstall", "deny", error="not_managed", path=str(path)), ensure_ascii=False))
            return 1
        if "--dry-run" in argv:
            print(json.dumps(payload("uninstall", "allow", dryRun=True, target=str(path)), ensure_ascii=False))
            return 0
        path.unlink()
        print(json.dumps(payload("uninstall", "allow", removed=str(path)), ensure_ascii=False))
        return 0
    if path.exists() and not path.is_symlink():
        print(json.dumps(payload(command, "deny", error="target_exists", path=str(path)), ensure_ascii=False))
        return 1
    if path.is_symlink() and path.resolve() != SOURCE.resolve():
        print(json.dumps(payload(command, "deny", error="target_is_other_symlink", path=str(path)), ensure_ascii=False))
        return 1
    if "--dry-run" in argv:
        print(json.dumps(payload(command, "allow", dryRun=True, source=str(SOURCE), target=str(path)), ensure_ascii=False))
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        path.unlink()
    os.symlink(SOURCE, path)
    print(json.dumps(payload(command, "allow", installed=True, source=str(SOURCE), target=str(path)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
