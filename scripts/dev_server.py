"""
Reliable dev server with file watching and proper process management.

This script ensures that the Flask dev server is properly stopped before
restarting, preventing multiple instances from running simultaneously.
It properly respects .gitignore files using the pathspec library.
"""

import argparse
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import NoReturn

import psutil
import watchdog.events
from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern
from watchdog.observers.polling import PollingObserver


class DevServerManager:
    """Manages the Flask dev server with reliable process control."""

    def __init__(self, port: int, build_command: list[str]):
        self.port = port
        self.build_command = build_command
        self.server_process = None
        self.observer = None
        self.running = False
        self.gitignore_spec = None
        self._load_gitignore()

    def _load_gitignore(self) -> None:
        """Load and parse .gitignore files from the project root."""
        try:
            gitignore_path = Path(".gitignore")
            if gitignore_path.exists():
                with open(gitignore_path, "r") as f:
                    patterns = f.readlines()
                # Parse gitignore patterns using pathspec
                self.gitignore_spec = PathSpec.from_lines(GitWildMatchPattern, patterns)
                print("Loaded .gitignore patterns")
            else:
                print("No .gitignore found, watching all files")
        except Exception as e:
            print(f"Warning: Could not load .gitignore: {e}")
            self.gitignore_spec = None

    def _is_gitignored(self, file_path: str) -> bool:
        """Check if a file should be ignored based on .gitignore patterns."""
        if not self.gitignore_spec:
            return False

        # Convert to relative path from project root for gitignore matching
        try:
            rel_path = os.path.relpath(file_path, ".")
            return self.gitignore_spec.match_file(rel_path)
        except ValueError:
            # If we can't get relative path, assume it's not ignored
            return False

    def find_server_processes(self) -> list[psutil.Process]:
        """Find all Flask server processes running on the specified port."""
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["cmdline"]:
                    cmdline = " ".join(proc.info["cmdline"])
                    if (
                        f"flask --app cnc.main:app run --host=0.0.0.0 --port={self.port}"
                        in cmdline
                    ):
                        processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes

    def kill_server_processes(self) -> None:
        """Forcefully kill all Flask server processes."""
        processes = self.find_server_processes()
        for proc in processes:
            try:
                print(f"Killing Flask server process {proc.pid}")
                # Try to kill the entire process group
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=5)
                except (OSError, AttributeError):
                    # Fallback to individual process termination
                    proc.terminate()
                    proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                print(f"Force killing process {proc.pid}")
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (OSError, AttributeError):
                    proc.kill()
                proc.wait()
            except psutil.NoSuchProcess:
                pass

    def start_server(self) -> None:
        """Start the Flask development server."""
        if self.server_process and self.server_process.poll() is None:
            print("Server is already running")
            return

        # Run the build process before starting
        print(f"Running build: {shlex.join(self.build_command)}")
        try:
            subprocess.run(
                self.build_command, check=True, capture_output=True, text=True
            )
            print("Build completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Build failed: {e}")
            print(f"Build stderr: {e.stderr}")
            return  # Don't start if build fails

        print("Starting Flask development server...")
        try:
            self.server_process = subprocess.Popen(
                [
                    "uv",
                    "run",
                    "flask",
                    "--app",
                    "cnc.main:app",
                    "run",
                    "--host=0.0.0.0",
                    f"--port={self.port}",
                ],
                start_new_session=True,  # Run in new session to avoid signal interference
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            print(f"Server started with PID {self.server_process.pid}")

            # Give the server a moment to start up and check if it's still running
            time.sleep(2)
            if self.server_process.poll() is not None:
                print("Flask server failed to start")
                stdout, stderr = self.server_process.communicate()
                if stdout:
                    print("Server stdout:", stdout)
                if stderr:
                    print("Server stderr:", stderr)
                return

        except Exception as e:
            print(f"Failed to start Flask server: {e}")
            return

    def stop_server(self) -> None:
        """Stop the Flask development server."""
        if self.server_process:
            print("Stopping Flask development server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
                print("Server stopped gracefully")
            except subprocess.TimeoutExpired:
                print("Force killing server")
                self.server_process.kill()
                self.server_process.wait()
            self.server_process = None

        # Also kill any other Flask processes that might be running
        self.kill_server_processes()

    def restart_server(self) -> None:
        """Restart the Flask development server."""
        print("Restarting server...")
        self.stop_server()

        # Run the build process before restarting
        print(f"Running build: {shlex.join(self.build_command)}")
        try:
            subprocess.run(
                self.build_command, check=True, capture_output=True, text=True
            )
            print("Build completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Build failed: {e}")
            print(f"Build stderr: {e.stderr}")
            return  # Don't restart if build fails

        time.sleep(0.5)  # Brief pause to ensure cleanup
        self.start_server()

    def setup_file_watcher(self, watch_paths: list[str]) -> None:
        """Set up file watching for the specified paths with proper gitignore support."""

        class FileChangeHandler(watchdog.events.FileSystemEventHandler):
            def __init__(self, manager: DevServerManager):
                self.manager = manager
                self.last_restart = 0
                self.debounce_delay = 0.5  # Debounce rapid changes

            def on_modified(self, event):
                if event.is_directory:
                    return

                # Check if the file should be ignored based on gitignore
                if self.manager._is_gitignored(str(event.src_path)):
                    return

                # Debounce rapid file changes
                current_time = time.time()
                if current_time - self.last_restart < self.debounce_delay:
                    return

                self.last_restart = current_time
                print(f"File changed: {event.src_path}")
                self.manager.restart_server()

        # Use PollingObserver for better cross-platform support
        self.observer = PollingObserver()
        handler = FileChangeHandler(self)

        for path in watch_paths:
            if os.path.exists(path):
                print(f"Watching: {path}")
                if self.observer:
                    self.observer.schedule(handler, path, recursive=True)

        if self.observer:
            self.observer.start()

    def run(self, watch_paths: list[str]) -> NoReturn:
        """Run the dev server with file watching."""
        try:
            # Start the server initially
            self.start_server()

            # Set up file watching
            self.setup_file_watcher(watch_paths)

            print(f"Dev server running on port {self.port}")
            print("Watching for file changes...")
            print("Git ignored files are automatically excluded")
            print("Press Ctrl+C to stop")

            # Keep the main thread alive
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.stop_server()
            if self.observer:
                self.observer.stop()
                self.observer.join()
            print("Dev server stopped")
            sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Development server with file watching and build integration"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5500,
        help="Port to run the server on (default: 5500)",
    )
    parser.add_argument(
        "--build-command",
        help="Build command to run before starting/restarting",
    )

    args = parser.parse_args()

    watch_paths = ["."]

    # Check if we're in the right directory
    if not os.path.exists("src/cnc/main.py"):
        print("Error: Must be run from the project root directory")
        print("Current directory:", os.getcwd())
        sys.exit(1)

    manager = DevServerManager(
        port=args.port, build_command=shlex.split(args.build_command)
    )
    manager.run(watch_paths)


if __name__ == "__main__":
    main()
