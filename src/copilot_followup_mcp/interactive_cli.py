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
from prompt_toolkit.layout.containers import ConditionalContainer, Container
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea


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
        self.result: Optional[str] = None
        self.text_area = TextArea(
            prompt="",
            multiline=False,
            focusable=True,
        )

    def _get_terminal_width(self) -> int:
        """Get the current terminal width."""
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80  # Default fallback

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

        # Display options
        if self.options:
            for idx, option in enumerate(self.options):
                is_selected = idx == self.selected_index and not self.focus_on_textbox
                prefix = "> " if is_selected else "  "
                style = "class:selected" if is_selected else "class:option"
                content.append((style, f"{prefix}- {option}\n"))

        content.append(("", "\n"))

        # Display custom input box
        box_width = min(terminal_width - 4, 80)
        is_textbox_selected = self.focus_on_textbox

        box_lines = self._create_box(
            "> Type your custom message"
            if not self.text_area.text
            else f"> {self.text_area.text}",
            box_width,
            selected=is_textbox_selected,
        )

        for line in box_lines:
            style = "class:textbox-selected" if is_textbox_selected else "class:textbox"
            content.append((style, line + "\n"))

        # Display hints
        content.append(("", "\n"))
        content.append(("class:hint", "💡 Hints:\n"))
        content.append(("class:hint", "  ↑/↓         : Navigate options\n"))
        content.append(
            ("class:hint", "  Enter       : Select option or submit custom message\n")
        )
        content.append(
            ("class:hint", "  Tab         : Switch to text input (pre-fill selected)\n")
        )
        content.append(
            ("class:hint", "  F2          : Edit selected option\n")
        )
        content.append(("class:hint", "  Ctrl+C      : Cancel\n"))

        return FormattedText(content)

    def _create_layout(self) -> Layout:
        """Create the application layout."""
        content_control = FormattedTextControl(
            text=self._render_content,
            focusable=False,
        )

        content_window = Window(
            content=content_control,
            wrap_lines=True,
        )

        # Hidden text input for actual text entry
        text_container = ConditionalContainer(
            self.text_area, filter=Condition(lambda: self.focus_on_textbox)
        )

        root_container = HSplit(
            [
                content_window,
                text_container,
            ]
        )

        return Layout(root_container)

    def _create_key_bindings(self) -> KeyBindings:
        """Create key bindings for the application."""
        kb = KeyBindings()

        @kb.add("up")
        def _up(event):
            """Move selection up."""
            if not self.focus_on_textbox and self.options:
                self.selected_index = (self.selected_index - 1) % len(self.options)

        @kb.add("down")
        def _down(event):
            """Move selection down."""
            if not self.focus_on_textbox and self.options:
                self.selected_index = (self.selected_index + 1) % len(self.options)

        @kb.add("tab")
        def _tab(event):
            """Switch to text input and pre-fill with selected option."""
            if not self.focus_on_textbox:
                if self.options and 0 <= self.selected_index < len(self.options):
                    # Pre-fill with selected option
                    self.text_area.text = self.options[self.selected_index]
                self.focus_on_textbox = True
                event.app.layout.focus(self.text_area)
            else:
                # If already in text mode, switch back to options
                self.focus_on_textbox = False
                event.app.layout.focus_previous()

        @kb.add("f2")
        def _edit_option(event):
            """Edit the selected option (F2)."""
            if not self.focus_on_textbox and self.options:
                if 0 <= self.selected_index < len(self.options):
                    # Pre-fill with selected option for editing
                    self.text_area.text = self.options[self.selected_index]
                    self.focus_on_textbox = True
                    event.app.layout.focus(self.text_area)

        @kb.add("enter")
        def _enter(event):
            """Select current option or submit custom message."""
            if self.focus_on_textbox:
                # Submit custom message
                self.result = self.text_area.text.strip()
                if self.result:
                    event.app.exit()
            else:
                # Select current option
                if self.options and 0 <= self.selected_index < len(self.options):
                    self.result = self.options[self.selected_index]
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
                "question": "bold #00aaff",
                "option": "#ffffff",
                "selected": "bold #00ff00",
                "textbox": "#888888",
                "textbox-selected": "bold #00ff00",
                "hint": "#888888 italic",
            }),
        )

        try:
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
