# Copilot Follow-up MCP Server

An MCP (Model Context Protocol) server that lets Copilot Chat keep asking you questions inside the same request, so you do not burn through the 300 monthly messages on student accounts.

## Why this exists

- Preserve Copilot quota: tool calls stay inside one request and do not consume new messages.
- Keep conversations on-rails: AI must confirm next steps, completion, and clarifications through the tool.
- Cross-platform and resilient: falls back through multiple terminal launchers so you still get the prompt.

## Features at a glance

- 🔄 Interactive follow-up prompts with multiple choice and free-form input
- ⌨️ Prompt-toolkit UI: arrow navigation, edit options, or type immediately
- 🪟 Works on Windows, macOS, and Linux with sensible fallbacks
- 🔁 Loop-friendly: ask after each step until you explicitly say "finish"
- 💰 No extra Copilot requests consumed while interacting

## Installation

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

1. **Clone or download this project.**

2. **Install dependencies using uv:**
  ```bash
  uv sync
  ```

3. **Configure your MCP client to use this server:**

   Add the following to your MCP configuration:

   ```jsonc
   {
     "servers": {
       "copilot-followup": {
         "command": "uv",
         "args": [
           "run",
           "server.py"
         ],
         "cwd": "C:\\Users\\smitk\\Desktop\\copilot followup"
       }
     }
   }
   ```

4. **Restart VSCode** to load the MCP server.

## Usage

### In VSCode Copilot Chat

Once configured, Copilot automatically has access to the tools. The AI will use `ask_followup_question` to:

1. **Ask questions before finishing tasks** - "I've completed X, what would you like to do next?"
2. **Get clarification during work** - "Which approach would you prefer?"
3. **Confirm completion** - "Are you satisfied with these changes?"

### Tools

The server exposes two tools that Copilot is required to use when interacting with you:

#### 1) `ask_followup_question`

The primary prompt loop for clarifying next steps.

```python
ask_followup_question(
    question="What would you like to do next?",
    options=[
        "Add more features",
        "Make changes", 
        "Finish - looks good"
    ]
)
```

**Usage rules for AI:**
- ✅ Ask before finishing any task
- ✅ Ask after each step to confirm direction
- ✅ Keep asking until you say "finish"/"done"
- ✅ Use for clarifications instead of plain questions
- ❌ Do not conclude without calling this tool

#### 2) `confirm_completion`

Shortcut that summarizes work and runs a final confirmation prompt before finishing.

```python
confirm_completion(
    task_summary="Created web scraper with error handling and CSV export"
)
```

## How it works

1. Copilot decides to ask a follow-up and calls `ask_followup_question` with options.
2. The server launches an interactive terminal window (VSCode terminal when available; OS fallback otherwise).
3. You pick an option or type your own response with prompt-toolkit UI controls.
4. The response is written to a temporary file; the server reads it and returns the raw text to Copilot.
5. Copilot continues in the same request, keeping your Copilot quota untouched.

## Behavior and defaults

- Default options: if none are provided, you will see `Continue`, `Make changes`, `Finish`.
- Timeout: set with `FOLLOWUP_TIMEOUT_MINUTES` (default 5; <1 means wait indefinitely; max 1440).
- Terminal closing: `CLOSE_TERMINAL=true` closes the window after submission; set to `false` to keep it open.
- CLI controls: ↑/↓ to navigate, Enter to select, Tab to toggle focus, F2 to edit an option, typing switches to free input, Ctrl+C cancels.
- Error handling: if the terminal closes without a response or times out, the tool returns a structured JSON error that Copilot can surface.

## Architecture

- server.py — FastMCP server and tool definitions
- src/copilot_followup_mcp/interactive_cli.py — prompt-toolkit UI
- src/copilot_followup_mcp/terminal_launcher.py — terminal launcher with platform fallbacks

## Configuration

### Environment variables

- `FOLLOWUP_TIMEOUT_MINUTES`: User-response timeout in minutes (1-1440, default 5; <1 waits forever).
- `CLOSE_TERMINAL`: Close the terminal after completion (`true`/`false`, default `true`).

### Terminal fallback order

- Windows: PowerShell, then Command Prompt
- macOS: Terminal.app (via AppleScript)
- Linux: gnome-terminal → konsole → xfce4-terminal → xterm → terminator → x-terminal-emulator
