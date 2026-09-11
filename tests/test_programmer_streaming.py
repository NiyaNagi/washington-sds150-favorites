"""Streaming subprocess runs for the fleet wizard."""
from __future__ import annotations

import sys
import time

from wasds150.radios.programmer import run_streaming


def test_lines_arrive_in_order_and_stderr_is_merged(tmp_path):
    seen = []
    code = "import sys; print('one'); print('two', file=sys.stderr); print('three')"
    run = run_streaming([sys.executable, "-c", code], seen.append, root=tmp_path)
    assert run.ok and run.returncode == 0
    assert seen == ["one", "two", "three"]
    assert run.stdout.splitlines() == seen


def test_a_failing_child_is_not_ok(tmp_path):
    run = run_streaming([sys.executable, "-c", "raise SystemExit(3)"], lambda line: None, root=tmp_path)
    assert not run.ok and run.returncode == 3 and not run.cancelled


def test_cancel_terminates_the_child(tmp_path):
    seen = []
    code = "import time; print('started', flush=True); time.sleep(60)"
    started = time.monotonic()
    run = run_streaming([sys.executable, "-c", code], seen.append, should_cancel=lambda: bool(seen), root=tmp_path)
    assert run.cancelled and not run.ok
    assert time.monotonic() - started < 30
    assert seen == ["started"]


def test_timeout_terminates_the_child(tmp_path):
    run = run_streaming([sys.executable, "-c", "import time; time.sleep(60)"], lambda line: None, root=tmp_path, timeout=1)
    assert run.timed_out and not run.ok
