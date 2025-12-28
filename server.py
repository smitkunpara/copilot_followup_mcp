"""Main MCP server with interactive follow-up question tool."""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("copilot-followup")


@mcp.tool()
async def ask_followup_question(question: str, options: list[str]) -> str:
    """
    Ask a follow-up question to the user with interactive options.

    **CRITICAL: This tool MUST be used in the following scenarios:**

    1. **Before concluding ANY task** - Always ask if the user wants to make changes or add something
    2. **After completing each step** - Check if the user is satisfied or wants modifications
    3. **When you're about to finish** - Give the user a chance to request additional work
    4. **Throughout the conversation** - Use this tool in a loop until the user explicitly says "finish" or "done"
    5. **Whenever you need to ask ANY question** - STRICTLY use this tool for ALL questions, never ask in plain text

    **Usage Pattern:**
    - Complete a task → use ask_followup_question
    - User provides feedback → make changes → use ask_followup_question again
    - Repeat until user says they're done
    - NEVER ask questions in plain text; ALWAYS use this tool

    **Important Notes:**
    - This tool opens an interactive terminal where users can:
      * Navigate options with ↑/↓ keys
      * Select an option with Enter
      * Edit an option with Shift+Enter
      * Switch to custom input with Tab
      * Type a custom response
    - The terminal will open in VSCode (if available) or the system's default terminal
    - Do NOT conclude or finish ANY work without using this tool first
    - Keep using this tool in a loop until the user explicitly requests to finish

    Args:
        question: The follow-up question to ask the user (e.g., "What would you like to do next?",
                 "Are you satisfied with these changes?", "Would you like me to add anything else?")
        options: List of suggested options (e.g., ["Add more features", "Make changes", "Finish"])
                Provide 3-5 clear, actionable options. Always include an option to finish/conclude.

    Returns:
        str: The user's response - either a selected option or custom input

    Example:
        ```python
        response = await ask_followup_question(
            question="I've completed the initial implementation. What would you like to do next?",
            options=[
                "Add error handling",
                "Improve performance",
                "Add more tests",
                "Make styling changes",
                "Finish - this looks good"
            ]
        )
        ```
    """
    try:
        # Import here to avoid issues if not installed
        from copilot_followup_mcp.terminal_launcher import launch_terminal_prompt

        # Create temporary output file
        output_file = (
            Path(tempfile.gettempdir())
            / f"followup_output_{os.getpid()}_{time.time()}.json"
        )

        # Remove old output file if it exists
        if output_file.exists():
            output_file.unlink()

        # Ensure we have valid options
        if not options:
            options = ["Continue", "Make changes", "Finish"]

        # Configure timeout from environment (minutes). <1 means wait forever.
        raw_timeout = os.getenv("FOLLOWUP_TIMEOUT_MINUTES")
        timeout_minutes: Optional[float]
        if raw_timeout is None:
            timeout_minutes = 5.0
        else:
            try:
                parsed = float(raw_timeout)
                if parsed < 1:
                    timeout_minutes = None
                else:
                    timeout_minutes = min(parsed, 1440.0)
            except ValueError:
                timeout_minutes = 5.0

        timeout_seconds = None if timeout_minutes is None else timeout_minutes * 60

        # Launch terminal
        terminal_process = launch_terminal_prompt(
            question=question,
            options=options,
            output_file=output_file,
            title="Follow-up Question",
        )

        if not terminal_process:
            return json.dumps(
                {
                    "error": "Failed to launch terminal. Please ensure you have terminal access.",
                    "fallback_message": "Unable to get user input. Assuming 'Continue' as default response.",
                }
            )

        # Wait for user response with process monitoring
        start_time = time.time()
        check_interval = 0.5  # Check every 0.5 seconds
        grace_period = 3  # Allow 3 seconds for process to stabilize

        while not output_file.exists() and (
            timeout_seconds is None or time.time() - start_time < timeout_seconds
        ):
            # Check if the terminal process has ended after grace period
            if time.time() - start_time > grace_period:
                if terminal_process.poll() is not None:
                    # Process has ended, wait a bit for the file to be written
                    time.sleep(1)
                    if output_file.exists():
                        break

                    # Process ended without producing a response
                    return json.dumps(
                        {
                            "error": "Terminal closed without response",
                            "message": "The terminal window was closed before a response was provided. You can skip this follow-up question and continue with the task, or ask again if needed.",
                            "suggestion": "Skip this follow-up and proceed with the current task.",
                        }
                    )

            time.sleep(check_interval)

        if not output_file.exists():
            # Timeout reached
            # Try to terminate the process gracefully
            if terminal_process and terminal_process.poll() is None:
                try:
                    terminal_process.terminate()
                except Exception:
                    pass
                
            configured_timeout = (
                "infinite"
                if timeout_minutes is None
                else f"{timeout_minutes:g} minute(s)"
            )
            return json.dumps(
                {
                    "error": "User did not respond",
                    "message": "No response was received within the configured timeout. The user may have closed the terminal window or not responded. You can either skip this question and continue, or ask the question again if needed.",
                    "timeout": configured_timeout,
                    "suggestion": "Skip this follow-up and continue with the task, or rephrase and retry the question.",
                }
            )

        # Read result
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                result = json.load(f)

            # Check if script reported an error
            if "error" in result:
                return json.dumps(
                    {
                        "error": "Script execution failed",
                        "message": f"The interactive prompt encountered an error: {result['error']}",
                        "suggestion": "Try again or check the terminal for more details.",
                    }
                )

            user_response = result.get("result")

            # Clean up output file
            try:
                output_file.unlink()
            except Exception:
                pass

            if user_response is None:
                return json.dumps(
                    {
                        "error": "cancelled",
                        "message": "User cancelled the follow-up question by closing the terminal or not selecting an option. You can skip this follow-up and continue with the task.",
                    }
                )

            # On success, return the raw string only (no JSON wrapper)
            return str(user_response)

        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "error": f"Failed to parse response: {str(e)}",
                    "message": "Invalid response format",
                }
            )

    except ImportError as e:
        return json.dumps(
            {
                "error": f"Missing dependencies: {str(e)}",
                "message": "Please install required packages: pip install prompt-toolkit psutil",
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "error": f"Unexpected error: {str(e)}",
                "message": "An error occurred while processing the follow-up question",
            }
        )


@mcp.tool()
async def confirm_completion(task_summary: str) -> str:
    """
    Confirm task completion with the user before finishing.

    This is a specialized follow-up tool that MUST be used before concluding any work.
    It automatically asks if the user wants to make any final changes.

    **CRITICAL: This tool MUST be used before winding up ANY session or task.**
    - ALWAYS use this tool before finishing
    - NEVER conclude without confirmation

    Args:
        task_summary: Brief summary of what was accomplished

    Returns:
        str: User's response indicating if they want changes or are satisfied
    """
    question = (
        f"I've completed the following:\n\n{task_summary}\n\nWhat would you like to do?"
    )
    options = [
        "This looks perfect - finish",
        "Make some changes",
        "Add more features",
        "Start over with a different approach",
    ]

    return await ask_followup_question(question, options)


def main():
    """Main entry point for the MCP server."""
    # Run the MCP server
    mcp.run()


if __name__ == "__main__":
    main()
