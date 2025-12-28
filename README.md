# Copilot Follow-up MCP Server

An MCP (Model Context Protocol) server that enables interactive follow-up questions for VSCode Copilot Chat. This solves the limitation where Copilot doesn't natively support asking follow-up questions during conversations.

## Features

- 🔄 **Interactive Follow-up Questions** - AI can ask users questions with multiple choice options
- ⌨️ **Rich CLI Interface** - Navigate with arrow keys, edit options, or type custom responses
- ✍️ **Typing-First UX** - Start typing immediately for custom responses without navigation
- 🪟 **Cross-Platform** - Works on Windows, macOS, and Linux
- 🔁 **Loop Support** - Designed to be used repeatedly until user explicitly says "finish"

## Installation

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

1. **Clone or download this project:**
   ```bash
   cd "C:\Users\smitk\Desktop\copilot followup"
   ```

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

Once configured, Copilot will automatically have access to the `ask_followup_question` tool. The AI will use this tool to:

1. **Ask questions before finishing tasks** - "I've completed X, what would you like to do next?"
2. **Get clarification during work** - "Which approach would you prefer?"
3. **Confirm completion** - "Are you satisfied with these changes?"

### Example Conversation Flow

```
You: "Create a Python web scraper"

Copilot: *creates the scraper code*

Copilot: *uses ask_followup_question tool*
```

At this point, a new terminal opens with an interactive interface:

```
I've created a basic web scraper. What would you like to do next?

  - Add error handling
  - Add rate limiting
  - Support multiple pages
> - Add data export to CSV
  - Finish - this looks good

╭───────────────────────────────────────╮
│ >   Type your custom message          │
╰───────────────────────────────────────╯

💡 Hints:
  ↑/↓         : Navigate options
  Enter       : Select option or submit custom message
  Tab         : Toggle between options and text input
  F2          : Edit selected option
  Ctrl+C      : Cancel
```

### Interactive Controls

- **↑/↓ Arrow Keys** - Navigate through options (when options are highlighted)
- **Enter** - Select the highlighted option or submit custom message
- **Tab** - Toggle focus between options and text input
- **F2** - Edit selected option (copies it to text box for modification)
- **Ctrl+C** - Cancel the prompt
- **Typing directly** - Start typing immediately to enter custom response (disables option highlighting)

### Tool Description

The MCP server provides two main tools:

#### 1. `ask_followup_question`

The primary tool for asking follow-up questions.

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

**Important Usage Rules for AI:**
- ✅ MUST use before concluding any task
- ✅ MUST use after completing each step
- ✅ MUST use in a loop until user says "finish"
- ✅ CAN use during work for clarifications
- ❌ DO NOT finish without using this tool

#### 2. `confirm_completion`

A specialized tool for confirming task completion.

```python
confirm_completion(
    task_summary="Created web scraper with error handling and CSV export"
)
```

## Architecture

The MCP server consists of several components:

- **`server.py`** - Main FastMCP server with tool definitions
- **`interactive_cli.py`** - Rich terminal UI using prompt-toolkit
- **`terminal_launcher.py`** - Cross-platform terminal launcher

## How It Works

1. **AI makes decision** - Copilot decides to ask a follow-up question
2. **Tool invocation** - Calls `ask_followup_question` with question and options
3. **Terminal launch** - Opens a new terminal (VSCode or system terminal)
4. **User interaction** - User selects/edits/types their response
5. **Response capture** - Result is written to a temporary file
6. **AI receives response** - Copilot gets the user's choice and continues

## Configuration

### Environment Variables

- `FOLLOWUP_TIMEOUT_MINUTES`: Timeout in minutes for waiting user response (1-1440, <1 = infinite, default 5)
- `CLOSE_TERMINAL`: Whether to close terminal after question completion (true/false, default true)

## Terminal Fallback

### Windows
1. PowerShell
2. Command Prompt (cmd.exe)

### macOS
1. Terminal.app

### Linux
1. gnome-terminal
2. konsole
3. xfce4-terminal
4. xterm
5. terminator
6. x-terminal-emulator

## Testing

### Test the Interactive CLI

```bash
cd "C:\Users\smitk\Desktop\copilot followup"
python -m copilot_followup_mcp.interactive_cli
```

### Test the Terminal Launcher

```bash
python -m copilot_followup_mcp.terminal_launcher
```

### Test the Full MCP Server

```bash
python -m copilot_followup_mcp.server
```

## Troubleshooting

### Terminal doesn't open

- **Check if Python is in PATH** - Run `python --version`
- **Check MCP client configuration** - Ensure the server is configured correctly

### "Missing dependencies" error

```bash
uv pip install prompt-toolkit psutil fastmcp
```

### Response timeout

- Default timeout is 5 minutes
- If you need more time, the timeout can be adjusted in `server.py`

## Development

### Project Structure

```
copilot followup/
├── src/
│   └── copilot_followup_mcp/
│       ├── __init__.py
│       ├── server.py              # Main MCP server
│       ├── interactive_cli.py     # Interactive terminal UI
│       └── terminal_launcher.py   # Terminal launcher
├── pyproject.toml                 # Project configuration
└── README.md                      # This file
```

### Adding New Features

1. Edit the relevant module in `src/copilot_followup_mcp/`
2. Test your changes
3. Restart the MCP server (restart VSCode)

## Best Practices for AI Usage

When using this MCP server, the AI should:

1. **Always provide clear options** - Give 3-5 specific, actionable choices
2. **Always include a "finish" option** - Let users exit the loop
3. **Use descriptive questions** - Be specific about what you're asking
4. **Loop until done** - Keep asking until user selects "finish" or equivalent
5. **Handle cancellations gracefully** - User might press Ctrl+C

## License

MIT License - Feel free to use and modify as needed.

## Credits

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - Interactive CLI
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager