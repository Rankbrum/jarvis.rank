import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class UiContractTests(unittest.TestCase):
    def test_shell_exposes_the_regions_and_controls_used_by_other_ui_modules(self):
        """Removing an integration anchor would disconnect graph or voice modules from the shell."""
        html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")

        for marker in (
            'id="inspector"',
            'id="graph-canvas"',
            'id="filters"',
            'id="reactor"',
            'id="conversation"',
            'id="messages"',
            'id="response-card"',
            'id="ask-form"',
            'id="ask-input"',
            'id="mic-button"',
            'id="mute-button"',
            'data-panel-open="inspector"',
            'data-panel-open="filters"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)

    def test_reactor_exports_the_complete_assistant_state_contract(self):
        """Dropping a supported state or its state event would leave the visual shell out of sync."""
        source = (ROOT / "ui" / "reactor.js").read_text(encoding="utf-8")

        for state in ("IDLE", "LISTENING", "THINKING", "SPEAKING", "ERROR"):
            with self.subTest(state=state):
                self.assertIn(f'{state}: "{state}"', source)
        self.assertIn("export function setAssistantState", source)
        self.assertIn("export function getAssistantState", source)
        self.assertIn('"jarvis:state"', source)

    def test_client_exports_text_submission_card_rendering_and_api_boundary(self):
        """Removing a UI API boundary would make shell actions bypass standard error handling."""
        source = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")

        for marker in (
            "export async function api",
            "export async function submitText",
            "export function renderCard",
            '"/api/chat"',
            '"/api/remember"',
            "confirmed: true",
            "addMessage(\"user\"",
            "addMessage(\"assistant\"",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
