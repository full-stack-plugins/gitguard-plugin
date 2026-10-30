#!/usr/bin/env python3
"""Run the unchanged unittest suite only in a genuinely unmanaged temp tree.

This harness neither changes GitGuard discovery nor masks ancestor metadata.
A contaminated base is an explicit environment error, never a skipped test.
"""
import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def contaminated_ancestors(path):
    path=Path(path).resolve(strict=True)
    return [item/'.git' for item in (path,*path.parents)
            if (item/'.git').exists() or (item/'.git').is_symlink()]


@contextmanager
def isolated_environment(parent):
    parent=Path(parent).resolve(strict=True)
    markers=contaminated_ancestors(parent)
    if markers:
        raise RuntimeError('Test fixture has ancestor Git metadata: '+', '.join(map(str,markers)))
    with tempfile.TemporaryDirectory(prefix='gitguard-suite-',dir=parent) as raw:
        root=Path(raw).resolve(strict=True)
        markers=contaminated_ancestors(root)
        if markers:
            raise RuntimeError('Test fixture has ancestor Git metadata: '+', '.join(map(str,markers)))
        env={**os.environ,'TMPDIR':str(root),'TEMP':str(root),'TMP':str(root)}
        yield root,env


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temp-root',type=Path,default=Path(tempfile.gettempdir()))
    args=parser.parse_args()
    try:
        with isolated_environment(args.temp_root) as (root,env):
            print('Verified clean temporary root: '+str(root),flush=True)
            # Full native macOS discovery can exceed 180s while individual cases
            # keep progressing. Bound the whole suite below the 10-minute CI job;
            # per-operation timeouts and all assertions remain unchanged.
            result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py','-v'],cwd=ROOT,env=env,timeout=480)
            return result.returncode
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
        print('Test environment incomplete: '+str(exc),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
