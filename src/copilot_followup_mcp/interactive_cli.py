"""Interactive CLI module for follow-up questions with dynamic UI."""

import os
import shutil
import sys
from typing import List, Optional, Tuple

from prompt_toolkit import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import FormattedTextControl, HSplit, Layout, VSplit, Window
from prompt_toolkit.layout.containers import ConditionalContainer, Container, DynamicContainer
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea, Frame
from prompt_toolkit.cursor_shapes import CursorShape


class InteractiveFollowUpCLI:
    """Interactive CLI for follow-up questions with options and custom input."""

    def __init__(self, question: str, options: List[str]):
        """
        Initialize the interactive CLI.

        Args:
            question: The question to display
            options: List of option strings
        """
        self.question = question
        self.options = options if options else []
        self.selected_index = 0
        self.focus_on_textbox = False
        self.highlight_options = True  # Start highlighted; disable once user types
        self.result: Optional[str] = None
        self.submitted = False
        self.submission_type: Optional[str] = None  # 'option' or 'custom'
        self.text_area = TextArea(
            prompt="",
            multiline=True,
            wrap_lines=True,
            scrollbar=False,
            focusable=True,
            height=Dimension(min=1, max=20),
        )
        # If user types directly, stop highlighting options
        self.text_area.buffer.on_text_insert += self._handle_text_insert

    def _handle_text_insert(self, _event=None) -> None:
        """When user types, remove option highlighting and focus text box."""
        self.highlight_options = False
        self.focus_on_textbox = True

    def _get_text_area_height(self) -> int:
        """Calculate dynamic height based on content (1-5 lines)."""
        text = self.text_area.text
        if not text:
            return 1
        line_count = text.count('\n') + 1
        return min(max(1, line_count), 5)

    def _get_terminal_width(self) -> int:
        """Get the current terminal width."""
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80  # Default fallback

    def _create_success_box(self, text: str) -> List[Tuple[str, str]]:
        """Create a success box with the selected/submitted text."""
        terminal_width = self._get_terminal_width()
        box_width = min(terminal_width - 4, max(len(text) + 6, 40))
        inner_width = box_width - 4
        
        lines = []
        for line in text.split('\n'):
            while len(line) > inner_width:
                lines.append(line[:inner_width])
                line = line[inner_width:]
            lines.append(line)
        
        result = []
        result.append(("class:success-box", "\n"))
        result.append(("class:success-box", "  ╭" + "─" * (box_width - 2) + "╮\n"))
        result.append(("class:success-box", "  │" + " ✓ Selected ".center(box_width - 2) + "│\n"))
        result.append(("class:success-box", "  ├" + "─" * (box_width - 2) + "┤\n"))
        
        for line in lines:
            padded = f" {line}".ljust(box_width - 2)
            result.append(("class:success-box", f"  │{padded}│\n"))
        
        result.append(("class:success-box", "  ╰" + "─" * (box_width - 2) + "╯\n"))
        
        return result

    def _create_box(self, text: str, width: int, selected: bool = False) -> List[str]:
        """Create a text box with borders."""
        if width < 10:
            width = 10

        inner_width = width - 4  # Account for borders and padding

        # Wrap text if it's too long
        wrapped_lines = []
        words = text.split()
        current_line = ""

        for word in words:
            if len(current_line) + len(word) + 1 <= inner_width:
                current_line += (" " if current_line else "") + word
            else:
                if current_line:
                    wrapped_lines.append(current_line)
                current_line = word

        if current_line:
            wrapped_lines.append(current_line)

        if not wrapped_lines:
            wrapped_lines = [""]

        # Create box
        top_left = "╭" if not selected else "┏"
        top_right = "╮" if not selected else "┓"
        bottom_left = "╰" if not selected else "┗"
        bottom_right = "╯" if not selected else "┛"
        horizontal = "─" if not selected else "━"
        vertical = "│" if not selected else "┃"

        lines = []
        lines.append(top_left + horizontal * (width - 2) + top_right)

        for line in wrapped_lines:
            padded_line = line.ljust(inner_width)
            lines.append(f"{vertical} {padded_line} {vertical}")

        lines.append(bottom_left + horizontal * (width - 2) + bottom_right)

        return lines

    def _render_content(self) -> FormattedText:
        """Render the main content."""
        terminal_width = self._get_terminal_width()
        content = []

        # Display question
        content.append(("class:question", f"\n{self.question}\n\n"))

        # Display options with rounded appearance
        if self.options:
            for idx, option in enumerate(self.options):
                is_selected = idx == self.selected_index and self.highlight_options
                if is_selected:
                    # Selected option with arrow and color
                    content.append(("class:option", "  "))
                    content.append(("class:arrow", "➤ "))
                    content.append(("class:selected", f"{option}\n"))
                else:
                    # Normal option
                    content.append(("class:option", f"    {option}\n"))

        content.append(("", "\n"))

        # Display hints
        hints = "↑↓ Navigate  •  Enter Select  •  Tab Toggle  •  F2 Edit  •  Ctrl+C Cancel"
        content.append(("class:hint", f"  {hints}\n"))

        content.append(("", "\n"))

        return FormattedText(content)

    def _render_submitted_content(self) -> FormattedText:
        """Render the submitted state with green success box."""
        content = []
        content.append(("class:question", f"\n{self.question}\n\n"))
        content.extend(self._create_success_box(self.result or ""))
        return FormattedText(content)

    def _create_layout(self) -> Layout:
        """Create the application layout."""
        def get_content():
            if self.submitted:
                return self._render_submitted_content()
            return self._render_content()

        content_control = FormattedTextControl(
            text=get_content,
            focusable=False,
        )

        content_window = Window(
            content=content_control,
            wrap_lines=True,
        )

        # Always render the text input inside a frame so the box stays visible and full-width
        def get_text_frame():
            if self.submitted:
                return Window(height=0)
            style = "class:textbox-active" if self.focus_on_textbox else "class:textbox-frame"
            return Frame(
                body=self.text_area,
                style=style,
            )

        text_frame = DynamicContainer(get_text_frame)

        root_container = HSplit(
            [
                content_window,
                text_frame,
            ]
        )

        return Layout(root_container)

    def _create_key_bindings(self) -> KeyBindings:
        """Create key bindings for the application."""
        kb = KeyBindings()

        @kb.add("up")
        def _up(event):
            """Move selection up or navigate text."""
            if self.submitted:
                return
            if self.focus_on_textbox:
                event.app.current_buffer.cursor_up()
            elif self.options and self.highlight_options:
                self.selected_index = (self.selected_index - 1) % len(self.options)
                event.app.invalidate()

        @kb.add("down")
        def _down(event):
            """Move selection down or navigate text."""
            if self.submitted:
                return
            if self.focus_on_textbox:
                event.app.current_buffer.cursor_down()
            elif self.options and self.highlight_options:
                self.selected_index = (self.selected_index + 1) % len(self.options)
                event.app.invalidate()

        @kb.add("tab")
        def _tab(event):
            """Switch focus between options and text input."""
            if self.submitted:
                return
            if not self.focus_on_textbox:
                self.focus_on_textbox = True
                self.highlight_options = False
                event.app.layout.focus(self.text_area)
            else:
                self.focus_on_textbox = False
                self.highlight_options = True
                # Focus away from text area to hide cursor
                event.app.layout.focus(event.app.layout.container)

        @kb.add("f2")
        def _edit_option(event):
            """Edit the selected option (F2)."""
            if not self.focus_on_textbox and self.options:
                if 0 <= self.selected_index < len(self.options):
                    # Pre-fill with selected option for editing
                    self.text_area.text = self.options[self.selected_index]
                    self.focus_on_textbox = True
                    self.highlight_options = False
                    event.app.layout.focus(self.text_area)

        @kb.add("enter")
        def _enter(event):
            if self.submitted:
                event.app.exit()
                return
                
            if self.focus_on_textbox and self.text_area.text.strip():
                self.result = self.text_area.text.strip()
                self.submission_type = 'custom'
                self.submitted = True
                event.app.invalidate()
                import time
                time.sleep(0.3)
                event.app.exit()
            elif not self.focus_on_textbox and self.options:
                if 0 <= self.selected_index < len(self.options):
                    self.result = self.options[self.selected_index]
                    self.submission_type = 'option'
                    self.submitted = True
                    event.app.invalidate()
                    import time
                    time.sleep(0.3)
                    event.app.exit()

        @kb.add("c-c")
        def _cancel(event):
            """Cancel and exit."""
            self.result = None
            event.app.exit()

        return kb

    def run(self) -> Optional[str]:
        """Run the interactive CLI and return the user's choice."""
        # Create application
        app = Application(
            layout=self._create_layout(),
            key_bindings=self._create_key_bindings(),
            full_screen=False,
            mouse_support=False,
            style=Style.from_dict({
                "question": "bold #61afef",           # Softer blue
                "option": "#abb2bf",                   # Light gray
                "selected": "bold #98c379",            # Green
                "arrow": "bold #e5c07b",               # Gold arrow
                "textbox-frame": "#5c6370",
                "textbox-active": "#98c379 bold",
                "hint": "#5c6370 italic",              # Muted gray
                "success-box": "bold #98c379",
                "input-label": "#5c6370",
                "input-label-active": "bold #98c379",
                "input-active": "bold #98c379",
            }),
        )

        try:
            # Start with focus on options, not text area
            self.focus_on_textbox = False
            self.highlight_options = True
            # Run application
            app.run()
            return self.result
        except KeyboardInterrupt:
            return None
        except Exception as e:
            print(f"Error running interactive CLI: {e}", file=sys.stderr)
            return None


def run_interactive_prompt(question: str, options: List[str]) -> Optional[str]:
    """
    Run an interactive prompt with the given question and options.

    Args:
        question: The question to ask
        options: List of option strings

    Returns:
        The user's selection or custom input, or None if cancelled
    """
    cli = InteractiveFollowUpCLI(question, options)
    return cli.run()


if __name__ == "__main__":
    # Test the interactive CLI
    test_question = "What would you like to do next?"
    test_options = [
        "Continue with the current approach",
        "Try a different method",
        "Add more features",
        "Finish and conclude",
    ]

    result = run_interactive_prompt(test_question, test_options)
    if result:
        print(f"\nYou selected: {result}")
    else:
        print("\nCancelled")
