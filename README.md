# Copilot Follow-up MCP Server

An MCP (Model Context Protocol) server that enables interactive follow-up questions for VSCode Copilot Chat. This solves the limitation where Copilot doesn't natively support asking follow-up questions during conversations.

## Features

- 🔄 **Interactive Follow-up Questions** - AI can ask users questions with multiple choice options
- ⌨️ **Rich CLI Interface** - Navigate with arrow keys, edit options, or type custom responses
- 🪟 **Cross-Platform** - Works on Windows, macOS, and Linux
- 🎯 **VSCode Integration** - Opens terminals in VSCode when available, falls back to system terminal
- 🔁 **Loop Support** - Designed to be used repeatedly until user explicitly says "finish"

## Installation

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- VSCode with Copilot Chat extension (recommended)

### Setup

1. **Clone or download this project:**
   ```bash
   cd "C:\Users\smitk\Desktop\copilot followup"
   ```

2. **Install dependencies using uv:**
   ```bash
   uv pip install -e .
   ```

   Or if you want to use a virtual environment:
   ```bash
   uv venv
   uv pip install -e .
   ```

3. **Configure VSCode to use this MCP server:**

   Create or edit your VSCode settings file (`.vscode/settings.json` in your workspace or user settings):

   ```json
   {
     "github.copilot.chat.mcp.servers": {
       "copilot-followup": {
         "command": "python",
         "args": [
           "-m",
           "copilot_followup_mcp.server"
         ],
         "cwd": "C:\\Users\\smitk\\Desktop\\copilot followup\\src"
       }
     }
   }
   ```

   Or use the full path to your Python executable:
   ```json
   {
     "github.copilot.chat.mcp.servers": {
       "copilot-followup": {
         "command": "C:\\path\\to\\python.exe",
         "args": [
           "-m",
           "copilot_followup_mcp.server"
         ],
         "cwd": "C:\\Users\\smitk\\Desktop\\copilot followup\\src"
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
  ↑/↓    : Navigate options
  Enter  : Select option or submit custom message
  Tab    : Switch between options and text box
  Ctrl+C : Cancel
```

### Interactive Controls

- **↑/↓ Arrow Keys** - Navigate through options
- **Enter** - Select the highlighted option (or submit custom message if in text box)
- **Shift+Enter** - Copy the selected option to the text box for editing
- **Tab** - Switch between option list and custom text box
- **Ctrl+C** - Cancel the prompt

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

## Terminal Fallback

The server tries to open terminals in this order:

### Windows
1. VSCode integrated terminal (if in VSCode)
2. Windows Terminal (`wt.exe`)
3. PowerShell
4. Command Prompt (cmd.exe)

### macOS
1. VSCode integrated terminal (if in VSCode)
2. Terminal.app
3. iTerm2 (if installed)

### Linux
1. VSCode integrated terminal (if in VSCode)
2. gnome-terminal
3. konsole
4. xfce4-terminal
5. xterm
6. terminator
7. x-terminal-emulator

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
- **Check VSCode settings** - Ensure MCP server is configured correctly
- **Try system terminal** - The tool falls back to system terminal if VSCode is unavailable

### "Missing dependencies" error

```bash
uv pip install prompt-toolkit psutil fastmcp
```

### Response timeout

- Default timeout is 5 minutes
- If you need more time, the timeout can be adjusted in `server.py`

### VSCode doesn't recognize the MCP server

1. Check that the path in settings.json is correct
2. Restart VSCode completely
3. Check the Output panel (View → Output) and select "Copilot Chat" to see errors

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