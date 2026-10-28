"""Use UTF-8 for CLI and JSON-RPC streams, independently of pipe codepages."""
import sys


def configure_stdio():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if callable(reconfigure):
            reconfigure(encoding='utf-8', errors='strict')
