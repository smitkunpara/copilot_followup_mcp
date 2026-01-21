"""Main MCP server with interactive follow-up question tool."""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("copilot-followup")


@mcp.tool()
async def ask_followup_question(question: str, options: list[str]) -> str:
    """
    Ask a follow-up question to the user with interactive options.

    ⚠️ **MANDATORY: USE THIS TOOL FOR ALL USER INTERACTIONS - NEVER ASK IN PLAIN TEXT**

    **WHEN TO USE THIS TOOL:**
    1. When you need details from the user → use this tool
    2. BEFORE finishing ANY task → ALWAYS use this tool to confirm
    3. AFTER completing work → use this tool and wait for user to test and respond
    4. BEFORE concluding ANY topic → MUST use this tool first
    5. For ANY question → ONLY use this tool, never ask in plain text
    6. **REMINDER: Before ending every conversation, you MUST use this tool.**
    7. **If the task is done, the AI MUST use this tool to confirm completion.**

    **REQUIRED WORKFLOW:**
    - Complete work → use ask_followup_question to ask user to test
    - User tests → they respond with feedback
    - Make changes based on feedback → use ask_followup_question again
    - Repeat until user confirms it's working and says finish/done
    - NEVER finish without user testing and confirming

    **Example scenarios:**
    - "I've made the changes. Please test and let me know if it's working:"
      Options: ["It's working - finish", "Not working - needs fixes", "Need more changes"]
    - "I need more information to proceed:"
      Options: ["Option A", "Option B", "Provide custom details"]

    Args:
        question: Your question to the user
        options: List of suggested responses (3-5 recommended)
                Always include an option to finish when appropriate

    Returns:
        str: User's response
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


def main():
    """Main entry point for the MCP server."""
    # Run the MCP server
    mcp.run()


if __name__ == "__main__":
    main()
