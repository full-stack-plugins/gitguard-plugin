"""Python entry point for the existing GitGuard command and install modules."""
import sys
from pathlib import Path


def main(arguments):
    if arguments and arguments[0] in ('install', 'uninstall', 'upgrade', 'completion'):
        from install_cli import main as install
        return install(arguments)
    sys.argv[0] = str(Path(__file__).with_name("gitflow.py"))
    from gitflow.cli import main as gitflow
    return gitflow(arguments)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
