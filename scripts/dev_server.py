#!/usr/bin/env python3

"""
Reliable dev server with file watching and proper process management.

This script ensures that the Flask dev server is properly stopped before
restarting, preventing multiple instances from running simultaneously.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import NoReturn

import psutil
import watchdog.events
import watchdog.observers


class DevServerManager:
    """Manages the Flask dev server with reliable process control."""
    
    def __init__(self, port: int = 5500):
        self.port = port
        self.server_process: subprocess.Popen | None = None
        self.observer: watchdog.observers.Observer | None = None
        self.running = False
        
    def find_server_processes(self) -> list[psutil.Process]:
        """Find all Flask server processes running on the specified port."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if f'flask --app cnc.main:app run --host=0.0.0.0 --port={self.port}' in cmdline:
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
                proc.terminate()
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                print(f"Force killing process {proc.pid}")
                proc.kill()
            except psutil.NoSuchProcess:
                pass
    
    def start_server(self) -> None:
        """Start the Flask development server."""
        if self.server_process and self.server_process.poll() is None:
            print("Server is already running")
            return
            
        print("Starting Flask development server...")
        self.server_process = subprocess.Popen([
            "uv", "run", "flask", "--app", "cnc.main:app", "run",
            "--host=0.0.0.0", f"--port={self.port}"
        ])
        print(f"Server started with PID {self.server_process.pid}")
    
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
        time.sleep(0.5)  # Brief pause to ensure cleanup
        self.start_server()
    
    def setup_file_watcher(self, watch_paths: list[str]) -> None:
        """Set up file watching for the specified paths."""
        class FileChangeHandler(watchdog.events.FileSystemEventHandler):
            def __init__(self, manager: DevServerManager):
                self.manager = manager
                self.last_restart = 0
                self.debounce_delay = 0.5  # Debounce rapid changes
                
            def on_modified(self, event):
                if event.is_directory:
                    return
                    
                # Skip cache files and other non-essential files
                src_path = str(event.src_path)
                if any(skip in src_path for skip in ['__pycache__', '.pyc', '.pyo', '.git', '.DS_Store']):
                    return
                    
                # Debounce rapid file changes
                current_time = time.time()
                if current_time - self.last_restart < self.debounce_delay:
                    return
                    
                self.last_restart = current_time
                print(f"File changed: {event.src_path}")
                self.manager.restart_server()
        
        self.observer = watchdog.observers.Observer()
        handler = FileChangeHandler(self)
        
        for path in watch_paths:
            if os.path.exists(path):
                print(f"Watching: {path}")
                self.observer.schedule(handler, path, recursive=True)
        
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


def main():
    """Main entry point."""
    # Default paths to watch
    watch_paths = [
        "src/",
        "templates/",
        "static/",
    ]
    
    # Check if we're in the right directory
    if not os.path.exists("src/cnc/main.py"):
        print("Error: Must be run from the project root directory")
        print("Current directory:", os.getcwd())
        sys.exit(1)
    
    manager = DevServerManager(port=5500)
    manager.run(watch_paths)


if __name__ == "__main__":
    main()
