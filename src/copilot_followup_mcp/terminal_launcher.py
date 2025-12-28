"""Terminal launcher module for opening terminals in VSCode or OS fallback."""

import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


def create_terminal_script(python_code: str) -> Path:
    """
    Create a temporary script file that will run the interactive CLI.

    Args:
        python_code: The Python code to execute

    Returns:
        Path to the temporary script file
    """
    system = platform.system()

    if system == "Windows":
        # Create a .py file for Windows
        fd, temp_path = tempfile.mkstemp(suffix=".py", prefix="followup_", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(python_code)
            f.write("\n")
    else:
        # Create a .py file for Unix-like systems
        fd, temp_path = tempfile.mkstemp(suffix=".py", prefix="followup_", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(python_code)
            f.write("\n")

    return Path(temp_path)


def open_os_terminal(script_path: Path, title: str = "Follow-up Question", close_terminal: bool = True) -> Optional[subprocess.Popen]:
    """
    Open a new terminal in the OS and run the script.

    Args:
        script_path: Path to the script to run
        title: Title for the terminal

    Returns:
        Process handle if successful, None otherwise
    """
    system = platform.system()
    python_exe = sys.executable

    try:
        if system == "Windows":
            # Prefer launching PowerShell directly so we have a stable process handle
            try:
                ps_command = f"& '{python_exe}' '{script_path}'"
                if close_terminal:
                    proc = subprocess.Popen(
                        [
                            "powershell.exe",
                            "-Command",
                            ps_command,
                        ],
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )
                else:
                    proc = subprocess.Popen(
                        [
                            "powershell.exe",
                            "-NoExit",
                            "-Command",
                            ps_command,
                        ],
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )
                return proc
            except (FileNotFoundError, OSError):
                pass

            # Fallback to cmd
            # For cmd, we need to wrap the entire command in quotes and escape internal quotes
            if close_terminal:
                cmd_command = f'""{python_exe}" "{script_path}""'
                proc = subprocess.Popen(
                    [
                        "cmd.exe",
                        "/C",
                        cmd_command,
                    ],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                cmd_command = f'""{python_exe}" "{script_path}" && pause"'
                proc = subprocess.Popen(
                    [
                        "cmd.exe",
                        "/K",
                        cmd_command,
                    ],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            return proc

        elif system == "Darwin":  # macOS
            # Use AppleScript to open Terminal.app or iTerm2
            if close_terminal:
                script_content = f"""
tell application "Terminal"
    activate
    do script "cd '{script_path.parent}' && '{python_exe}' '{script_path}'"
end tell
"""
            else:
                script_content = f"""
tell application "Terminal"
    activate
    do script "cd '{script_path.parent}' && '{python_exe}' '{script_path}' && echo '\\nPress any key to close...' && read -n 1"
end tell
"""
            proc = subprocess.Popen(
                ["osascript", "-e", script_content],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return proc

        else:  # Linux and other Unix-like systems
            # Try various terminal emulators
            terminals = [
                [
                    "gnome-terminal",
                    "--",
                    "bash",
                    "-c",
                    f'"{python_exe}" "{script_path}"; echo "\nPress Enter to close..."; read',
                ],
                [
                    "konsole",
                    "-e",
                    "bash",
                    "-c",
                    f'"{python_exe}" "{script_path}"; echo "\nPress Enter to close..."; read',
                ],
                [
                    "xfce4-terminal",
                    "-e",
                    f'bash -c ""{python_exe}" "{script_path}"; echo \\"\\nPress Enter to close...\\"; read"',
                ],
                [
                    "xterm",
                    "-e",
                    f'bash -c ""{python_exe}" "{script_path}"; echo \\"\\nPress Enter to close...\\"; read"',
                ],
                [
                    "terminator",
                    "-e",
                    f'bash -c ""{python_exe}" "{script_path}"; echo \\"\\nPress Enter to close...\\"; read"',
                ],
            ]

            for terminal_cmd in terminals:
                try:
                    if close_terminal:
                        proc = subprocess.Popen(
                            [
                                terminal_cmd[0],
                                "-e",
                                f'bash -c ""{python_exe}" "{script_path}""',
                            ],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    else:
                        proc = subprocess.Popen(
                            [
                                terminal_cmd[0],
                                "-e",
                                f'bash -c ""{python_exe}" "{script_path}"; echo \\"\\nPress Enter to close...\\"; read"',
                            ],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    return proc
                except (FileNotFoundError, OSError):
                    continue

            # If no terminal emulator found, fall back to x-terminal-emulator
            try:
                proc = subprocess.Popen(
                    [
                        "x-terminal-emulator",
                        "-e",
                        f'bash -c ""{python_exe}" "{script_path}"; echo \\"\\nPress Enter to close...\\"; read"',
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return proc
            except (FileNotFoundError, OSError):
                pass

        return None

    except Exception as e:
        print(f"Failed to open OS terminal: {e}", file=sys.stderr)
        return None


def launch_terminal_prompt(
    question: str,
    options: list[str],
    output_file: Path,
    title: str = "Follow-up Question",
) -> Optional[subprocess.Popen]:
    """Launch OS terminal to display the interactive prompt."""
    close_terminal = os.getenv("CLOSE_TERMINAL", "true").lower() in ("true", "1", "yes")
    
    src_dir = Path(__file__).parent.parent
    python_code = f"""
import sys
import json
from pathlib import Path

sys.path.insert(0, {repr(str(src_dir))})

from copilot_followup_mcp.interactive_cli import run_interactive_prompt

try:
    result = run_interactive_prompt({repr(question)}, {repr(options)})
    with open({repr(str(output_file))}, 'w', encoding='utf-8') as f:
        json.dump({{'result': result}}, f)
except Exception as e:
    with open({repr(str(output_file))}, 'w', encoding='utf-8') as f:
        json.dump({{'error': str(e)}}, f)
"""
    
    script_path = create_terminal_script(python_code)
    
    try:
        return open_os_terminal(script_path, title, close_terminal)
    except Exception as e:
        try:
            script_path.unlink()
        except:
            pass
        return None


if __name__ == "__main__":
    # Test the terminal launcher
    import json
    import tempfile
    import time

    output_file = Path(tempfile.gettempdir()) / "test_followup_output.json"

    if output_file.exists():
        output_file.unlink()

    success = launch_terminal_prompt(
        question="What would you like to do next?",
        options=[
            "Continue with the current approach",
            "Try a different method",
            "Finish and conclude",
        ],
        output_file=output_file,
        title="Test Follow-up",
    )

    if success:
        print("Terminal launched successfully. Waiting for response...")

        # Wait for output file (with timeout)
        timeout = 60
        start_time = time.time()
        while not output_file.exists() and time.time() - start_time < timeout:
            time.sleep(0.5)

        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                result = json.load(f)
            print(f"Result: {result}")
        else:
            print("Timeout waiting for response")
    else:
        print("Failed to launch terminal")
