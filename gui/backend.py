# My backend module for this compiler project.
"""Real C translation, GCC compilation and process I/O for the desktop GUI."""
from __future__ import annotations

from diagnostics import SourceDiagnostics

import codecs
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from typing import Callable


class BuildError(RuntimeError):
    pass


@dataclass
class BuildResult:
    directory: Path
    generated: Path
    executable: Path | None


@dataclass
class RunResult:
    returncode: int
    reason: str
    elapsed: float


def find_gcc() -> str:
    found = shutil.which("gcc")
    if found:
        return str(Path(found).resolve())
    if os.name == "nt":
        for candidate in (
            Path("C:/msys64/ucrt64/bin/gcc.exe"),
            Path("C:/msys64/mingw64/bin/gcc.exe"),
            Path("C:/mingw64/bin/gcc.exe"),
        ):
            if candidate.is_file():
                return str(candidate)
    return ""


class CompilerBackend:
    """No Tk calls: events are handed to the GUI's thread-safe queue."""

    OUTPUT_LIMIT = 512 * 1024

    def __init__(self, root: Path, emit: Callable[[str, object], None] | None = None,
                 gcc: str = ""):
        self.root = Path(root).resolve()
        self.emit = emit or (lambda kind, value: None)
        self.gcc = gcc or find_gcc()
        self.cancelled = threading.Event()
        self._process: subprocess.Popen | None = None
        self._process_lock = threading.Lock()
        self._stdin_lock = threading.Lock()
        self._stdin_closed = False

    def reset(self):
        self.cancelled.clear()

    def cancel(self):
        self.cancelled.set()

    def _active(self):
        if self.cancelled.is_set():
            raise BuildError("Stopped.")

    def _environment(self):
        env = os.environ.copy()
        if self.gcc:
            env["PATH"] = str(Path(self.gcc).resolve().parent) + os.pathsep + env.get("PATH", "")
        return env

    @staticmethod
    def _process_options():
        if os.name == "nt":
            return {"creationflags": subprocess.CREATE_NO_WINDOW}
        return {"start_new_session": True}

    def _set_process(self, process):
        with self._process_lock:
            self._process = process
            self._stdin_closed = False

    @staticmethod
    def _terminate(process):
        if process.poll() is not None:
            return
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW, timeout=4,
                )
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except (OSError, subprocess.TimeoutExpired):
            pass
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            pass

    def _command(self, args, cwd: Path, timeout=45, diagnostics=None):
        self._active()
        display = subprocess.list2cmdline(args) if os.name == "nt" else shlex.join(args)
        self.emit("log", "$ " + display + "\n")
        try:
            process = subprocess.Popen(
                args, cwd=cwd, env=self._environment(),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, **self._process_options(),
            )
        except OSError as error:
            raise BuildError(f"Could not start compiler: {error}") from error
        self._set_process(process)
        started = time.monotonic()
        try:
            while True:
                try:
                    output, _ = process.communicate(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    if self.cancelled.is_set() or time.monotonic() - started > timeout:
                        self._terminate(process)
                        output, _ = process.communicate()
                        if output:
                            self.emit("log", output.decode("utf-8", "replace"))
                        raise BuildError("Stopped." if self.cancelled.is_set()
                                         else "Compilation exceeded its 45-second limit.")
            text = output.decode("utf-8", "replace")
            if diagnostics:
                text = diagnostics.format(text)
            if text:
                self.emit("log", text if text.endswith("\n") else text + "\n")
            self._active()
            if process.returncode != 0:
                raise BuildError("Build failed. See the Build log for the exact error.")
        finally:
            with self._process_lock:
                if self._process is process:
                    self._process = None

    def build(self, source: str, config: str, source_folder: Path | None = None,
              translate_only=False) -> BuildResult:
        self._active()
        if not self.gcc or not Path(self.gcc).is_file():
            raise BuildError("GCC was not found. Click 'Choose GCC' and select gcc.exe.")
        build = self.root / "build"
        build.mkdir(parents=True, exist_ok=True)
        sources = [self.root / "custom-keywords" / "src" / name for name in
                   ("main.c", "keywords.c", "translate.c", "keywords.h", "translate.h")]
        fingerprint = hashlib.sha256(self.gcc.encode("utf-8"))
        for path in sources:
            fingerprint.update(path.read_bytes())
        build_id = fingerprint.hexdigest()
        suffix = ".exe" if os.name == "nt" else ""
        translator = build / ("customc" + suffix)
        stamp = build / "translator-build-id.txt"
        if not translator.is_file() or not stamp.is_file() or stamp.read_text() != build_id:
            self.emit("status", "Building the C frontend...")
            self._command(
                [self.gcc, "-std=c11", "-Wall", "-Wextra", "-fdiagnostics-color=never",
                 *map(str, sources[:3]), "-o", str(translator)], self.root,
            )
            stamp.write_text(build_id)
        self._active()
        directory = Path(tempfile.mkdtemp(prefix="run-", dir=build))
        input_path = directory / "source.myc"
        config_path = directory / "keywords.cfg"
        generated = directory / "generated.c"
        input_path.write_text(source, encoding="utf-8")
        config_path.write_text(config, encoding="utf-8")
        diagnostics = SourceDiagnostics(source, input_path, generated, self.emit, config_path, config)
        self.emit("status", "Translating custom keywords...")
        self._command([str(translator), str(config_path), str(input_path), str(generated)],
                      self.root, diagnostics=diagnostics)
        self.emit("generated", generated.read_text(encoding="utf-8"))
        if translate_only:
            return BuildResult(directory, generated, None)
        executable = directory / ("program" + suffix)
        include_folder = Path(source_folder or self.root).resolve()
        self.emit("status", "Compiling with GCC...")
        self._command(
            [self.gcc, "-std=c11", "-Wall", "-Wextra", "-Werror=implicit-function-declaration",
             "-fdiagnostics-column-unit=byte", "-fmax-errors=10",
             "-fdiagnostics-color=never", "-include", str(self.root / "gui" / "runtime_io.h"),
             "-iquote", str(include_folder), str(generated), "-o", str(executable)],
            self.root, diagnostics=diagnostics,
        )
        self.emit("log", "Build successful.\n")
        return BuildResult(directory, generated, executable)

    def send_input(self, text: str) -> bool:
        # Call from a worker: a program may not be reading its stdin yet.
        with self._stdin_lock:
            with self._process_lock:
                process = self._process
                closed = self._stdin_closed
            if not process or process.poll() is not None or not process.stdin or closed:
                return False
            try:
                process.stdin.write(text.encode("utf-8"))
                process.stdin.flush()
                return True
            except (BrokenPipeError, OSError, ValueError):
                return False

    def close_input(self):
        with self._stdin_lock:
            with self._process_lock:
                process = self._process
                self._stdin_closed = True
            if process and process.stdin:
                try:
                    process.stdin.close()
                except (OSError, ValueError):
                    pass

    def run(self, result: BuildResult, initial_input="", timeout=30) -> RunResult:
        self._active()
        if not result.executable or not result.executable.is_file():
            raise BuildError("Compile an executable before running.")
        process = subprocess.Popen(
            [str(result.executable)], cwd=result.directory, env=self._environment(),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=0, **self._process_options(),
        )
        self._set_process(process)
        exceeded = threading.Event()

        def read_output():
            decoder = codecs.getincrementaldecoder("utf-8")("replace")
            total = 0
            try:
                while True:
                    chunk = os.read(process.stdout.fileno(), 4096)
                    if not chunk:
                        break
                    remaining = max(0, self.OUTPUT_LIMIT - total)
                    if remaining:
                        self.emit("output", decoder.decode(chunk[:remaining]))
                    total += len(chunk)
                    if total > self.OUTPUT_LIMIT:
                        exceeded.set()
                        break
                tail = decoder.decode(b"", final=True)
                if tail:
                    self.emit("output", tail)
            except (OSError, ValueError):
                pass
            finally:
                process.stdout.close()

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        # Preloaded input is sent first; stdin stays open for live input.
        if initial_input:
            payload = initial_input if initial_input.endswith("\n") else initial_input + "\n"
            threading.Thread(target=self.send_input, args=(payload,), daemon=True).start()
        self.emit("running", process.pid)
        started = time.monotonic()
        reason = "completed"
        try:
            while process.poll() is None:
                if self.cancelled.is_set():
                    reason = "stopped"
                elif exceeded.is_set():
                    reason = "output limit"
                elif time.monotonic() - started >= timeout:
                    reason = "time limit"
                else:
                    time.sleep(0.025)
                    continue
                self._terminate(process)
                break
            process.wait(timeout=5)
            reader.join(timeout=2)
            # A short-lived program may hit the output cap just before it exits.
            if exceeded.is_set() and reason == "completed":
                reason = "output limit"
            self.close_input()
            return RunResult(process.returncode, reason, time.monotonic() - started)
        finally:
            self._terminate(process)
            with self._process_lock:
                if self._process is process:
                    self._process = None

    def cleanup(self):
        """Call after a job has stopped, when no exported artifact needs this folder."""
        for directory in (self.root / "build").glob("run-*"):
            if directory.is_dir():
                shutil.rmtree(directory, ignore_errors=True)
