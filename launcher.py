"""Diagnostic launcher for `main.py`.

Wraps module import and `main()` execution in a catch-all so that any exit
path (SystemExit, uncaught exception, import-time failure, C-level fault)
is written to a dedicated log file with a timestamp and full traceback
before the process terminates.

Used only for the Zo-hosted `gwmcp-auth` supervisord service while we are
diagnosing silent `exit status 1` restart storms. Not part of the upstream
startup path.
"""

from __future__ import annotations

import datetime
import faulthandler
import os
import sys
import traceback

LAUNCHER_LOG = os.environ.get(
    "GWMCP_LAUNCHER_LOG", "/dev/shm/gwmcp-auth-launcher.log"
)


def _log(line: str) -> None:
    stamp = datetime.datetime.now().isoformat(timespec="milliseconds")
    try:
        with open(LAUNCHER_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {line}\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        sys.stderr.write(f"[{stamp}] launcher log write failed\n")
        sys.stderr.flush()


def _emit(msg: str) -> None:
    _log(msg)
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def _dump_exception(prefix: str, exc: BaseException) -> None:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    _emit(f"{prefix} {type(exc).__name__}: {exc}")
    _emit("TRACEBACK:\n" + tb)


faulthandler.enable(all_threads=True)

_emit(
    f"=== launcher start pid={os.getpid()} "
    f"ppid={os.getppid()} argv={sys.argv!r} ==="
)

try:
    import main as _main
except BaseException as exc:
    _dump_exception("IMPORT-TIME FAILURE:", exc)
    sys.exit(1)

try:
    _main.main()
except SystemExit as exc:
    if exc.code not in (None, 0):
        tb = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        _emit(f"SystemExit code={exc.code}")
        _emit("TRACEBACK:\n" + tb)
    else:
        _emit(f"SystemExit code={exc.code}")
    raise
except BaseException as exc:
    _dump_exception("UNCAUGHT IN main():", exc)
    sys.exit(1)
else:
    _emit("main() returned normally")
