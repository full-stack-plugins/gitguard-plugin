#!/usr/bin/env python3
"""Keep exact test exit status and bounded diagnostics for candidate CI."""
import pathlib
import subprocess
import sys

# GitHub annotations and captured Rust diagnostics are UTF-8 even when the
# Windows console defaults to a legacy code page. Do not mask the test status.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if len(sys.argv) < 3 or not sys.argv[1].replace('-', '').isalnum():
    raise SystemExit('usage: candidate-test.py evidence-name command [args...]')
evidence = pathlib.Path('candidate-evidence')
evidence.mkdir(exist_ok=True)
log_path = evidence / (sys.argv[1] + '.log')
with log_path.open('wb') as log:
    result = subprocess.run(sys.argv[2:], stdout=log, stderr=subprocess.STDOUT, check=False)
print(f'Test exit {result.returncode}; log: {log_path}', flush=True)
with log_path.open('rb') as log:
    log.seek(0, 2)
    log.seek(max(0, log.tell() - 4096))
    tail = log.read().decode('utf-8', errors='replace')
print(tail, flush=True)
if result.returncode:
    escaped = tail.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::error title=Candidate ' + sys.argv[1] + ' failed::' + escaped, flush=True)
sys.exit(result.returncode)
