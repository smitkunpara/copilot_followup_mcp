"""Terminal launcher module for opening terminals in VSCode or OS fallback."""

import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


def is_vscode_terminal() -> bool:
    """Check if running inside a VSCode terminal."""
    return (
        os.environ.get("TERM_PROGRAM") == "vscode"
        or os.environ.get("VSCODE_INJECTION") == "1"
        or os.environ.get("VSCODE_GIT_ASKPASS_NODE") is not None
        or os.environ.get("VSCODE_GIT_IPC_HANDLE") is not None
    )


def get_vscode_executable() -> Optional[str]:
    """Get the VSCode executable path."""
    system = platform.system()

    # Try common VSCode executable names
    vscode_commands = ["code", "code-insiders"]

    for cmd in vscode_commands:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            if result.returncode == 0:
                return cmd
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            continue

    return None


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


def open_vscode_terminal(script_path: Path, title: str = "Follow-up Question") -> Optional[subprocess.Popen]:
    """
    Open a new terminal in VSCode and run the script.

    Args:
        script_path: Path to the script to run
        title: Title for the terminal

    Returns:
        Process handle if successful, None otherwise
    """
    try:
        # When running inside VSCode, use Windows Terminal or PowerShell
        # VSCode's integrated terminal API is not directly accessible from MCP server
        # So we fall back to OS terminal which the user will see
        python_exe = sys.executable
        system = platform.system()
        
        if system == "Windows":
            # Use PowerShell directly when in VSCode
            # Don't use pause - NoExit keeps window open
            ps_command = f"& '{python_exe}' '{script_path}'"
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
        
        return None
    except Exception as e:
        print(f"Failed to open VSCode terminal: {e}", file=sys.stderr)
        return None


def open_os_terminal(script_path: Path, title: str = "Follow-up Question") -> Optional[subprocess.Popen]:
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
                    proc = subprocess.Popen(
                        terminal_cmd,
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
    """
    Launch a terminal (VSCode or OS) to display the interactive prompt.

    Args:
        question: The question to ask
        options: List of options
        output_file: Path to write the result
        title: Title for the terminal

    Returns:
        Process handle if terminal launched successfully, None otherwise
    """
    # Create Python script that will run in the new terminal
    # Get the src directory path to add to Python path
    src_dir = Path(__file__).parent.parent
    
    python_code = f"""
import sys
import json
from pathlib import Path

# Add the src directory to Python path
src_dir = Path({repr(str(src_dir))})
sys.path.insert(0, str(src_dir))

from copilot_followup_mcp.interactive_cli import run_interactive_prompt

question = {repr(question)}
options = {repr(options)}
output_file = Path({repr(str(output_file))})

result = run_interactive_prompt(question, options)

# Write result to output file
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({{'result': result}}, f)
"""

    # Create temporary script
    script_path = create_terminal_script(python_code)

    try:
        # Try VSCode terminal first (when running inside VSCode)
        if is_vscode_terminal():
            proc = open_vscode_terminal(script_path, title)
            if proc:
                return proc

        # Fallback to OS terminal
        return open_os_terminal(script_path, title)

    except Exception as e:
        print(f"Failed to launch terminal: {e}", file=sys.stderr)
        # Clean up script file
        try:
            script_path.unlink()
        except Exception:
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
