"""Standalone launcher: runs the app as a child process, periodically pulls
the latest commit from GitHub, and restarts the child when it changes.

Deliberately stdlib-only and never imports the `app` package, so a broken
push (bad import, missing dependency) can only kill the child - this
launcher keeps polling and recovers once a fix is pushed.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent.parent

GIT_BRANCH = os.environ.get("QUOTEBOOK_GIT_BRANCH", "master")
CHECK_INTERVAL_SECONDS = int(os.environ.get("QUOTEBOOK_UPDATE_INTERVAL", "300"))

GIT_ENV = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}


def log(message: str) -> None:
    print(f"quotebook-launcher: {message}", flush=True)


def run_git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        env=GIT_ENV,
    )


def working_tree_is_clean() -> bool:
    result = run_git("status", "--porcelain", "--untracked-files=no")
    return result.returncode == 0 and result.stdout.strip() == ""


def check_for_update() -> bool:
    """Fetches origin/<branch> and, if it moved, hard-resets to it.

    Returns True if an update was applied. Never raises: any failure
    (git missing, no network, dirty tree, etc.) is logged and treated as
    "no update this tick" so the launcher itself never dies.
    """
    try:
        if not working_tree_is_clean():
            log("working tree has uncommitted changes, skipping update check")
            return False

        fetch = run_git("fetch", "origin", GIT_BRANCH)
        if fetch.returncode != 0:
            log(f"git fetch failed, skipping: {fetch.stderr.strip()}")
            return False

        local = run_git("rev-parse", "HEAD")
        remote = run_git("rev-parse", f"origin/{GIT_BRANCH}")
        if local.returncode != 0 or remote.returncode != 0:
            log("git rev-parse failed, skipping update check")
            return False

        local_sha, remote_sha = local.stdout.strip(), remote.stdout.strip()
        if local_sha == remote_sha:
            return False

        log(f"new commit on origin/{GIT_BRANCH} ({local_sha[:8]} -> {remote_sha[:8]}), updating")

        requirements_path = BACKEND_DIR / "requirements.txt"
        old_requirements = requirements_path.read_text(encoding="utf-8")

        reset = run_git("reset", "--hard", f"origin/{GIT_BRANCH}")
        if reset.returncode != 0:
            log(f"git reset --hard failed: {reset.stderr.strip()}")
            return False

        new_requirements = requirements_path.read_text(encoding="utf-8")
        if new_requirements != old_requirements:
            log("requirements.txt changed, reinstalling dependencies")
            pip_result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=BACKEND_DIR,
            )
            if pip_result.returncode != 0:
                log("pip install failed; restarting anyway with whatever is installed")

        return True
    except subprocess.TimeoutExpired:
        log("git command timed out, skipping this check")
        return False
    except FileNotFoundError:
        log("git not found on PATH; auto-update is disabled until it is")
        return False
    except Exception as exc:  # the launcher must never die
        log(f"unexpected error during update check: {exc!r}")
        return False


def start_child() -> subprocess.Popen:
    log("starting server")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", *sys.argv[1:]],
        cwd=BACKEND_DIR,
    )


def stop_child(child: subprocess.Popen) -> None:
    child.terminate()
    try:
        child.wait(timeout=30)
    except subprocess.TimeoutExpired:
        log("server did not stop in time, killing it")
        child.kill()
        child.wait()


def main() -> None:
    check_for_update()  # always start on the latest commit
    child = start_child()

    try:
        while True:
            time.sleep(CHECK_INTERVAL_SECONDS)
            try:
                # Checking for an update first, every tick, regardless of
                # whether the child is currently alive or crashed, matters:
                # if a bad push crashed the child, it keeps crashing on
                # every retry until a *newer* commit is pulled. Checking
                # git unconditionally is what lets a pushed fix actually
                # get noticed, instead of the crash-restart branch below
                # forever respawning the same broken code.
                if check_for_update():
                    log("restarting server to apply update")
                    stop_child(child)
                    child = start_child()
                elif child.poll() is not None:
                    log(f"server exited with code {child.returncode}; restarting")
                    child = start_child()
            except Exception as exc:  # never let the supervisor loop die
                log(f"unexpected error in launcher loop: {exc!r}")
    except KeyboardInterrupt:
        log("shutting down")
        stop_child(child)


if __name__ == "__main__":
    main()
