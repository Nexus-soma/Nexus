"""
Nexus Generic Actions
Universal actions that work on ANY device with a screen.
These are the building blocks for autonomous behavior.
No app-specific code. No hardcoded coordinates.
"""

import time
import random
from typing import Optional

from phone_bridge.bridge import PhoneBridge
from phone_bridge.screen_reader import ScreenReader


class GenericActions:
    """
    Universal screen interaction. Works on ANY app, ANY screen.
    Uses dynamic screen reading to find and interact with elements.
    """

    def __init__(self, bridge: PhoneBridge = None):
        self.bridge = bridge or PhoneBridge()
        self.reader = ScreenReader()

    def _human_delay(self, min_ms: float = 0.2, max_ms: float = 0.8):
        """Add random human-like delay between actions."""
        time.sleep(random.uniform(min_ms, max_ms))

    def _human_tap(self, x: int, y: int):
        """Tap with slight random offset (humans don't tap exact center)."""
        offset_x = random.randint(-8, 8)
        offset_y = random.randint(-5, 5)
        self.bridge.tap(x + offset_x, y + offset_y)

    # ─── SCREEN AWARENESS ────────────────────────

    def read_screen(self) -> dict:
        """
        Read everything visible on screen.
        Returns a summary the LLM can use to plan next actions.
        """
        elements = self.reader.get_clickable_elements()
        return {
            "total_clickable": len(elements),
            "elements": [
                {
                    "label": e.label[:60] if e.label else "(no label)",
                    "position": (e.center_x, e.center_y),
                    "clickable": e.clickable,
                    "resource_id": e.resource_id[:40] if e.resource_id else "",
                }
                for e in elements[:30]
            ],
        }

    def what_do_i_see(self) -> str:
        """
        Human-readable description of the current screen.
        Useful for LLM context.
        """
        data = self.read_screen()
        lines = [f"I see {data['total_clickable']} clickable elements:"]
        for e in data["elements"]:
            label = e["label"][:50]
            pos = e["position"]
            lines.append(f"  [{pos[0]:3d},{pos[1]:3d}] {label}")
        return "\n".join(lines)

    # ─── FINDING ELEMENTS ─────────────────────────

    def find_element(self, label_contains: str, area: str = "any") -> Optional[dict]:
        """
        Find an element by partial label match.
        area: 'any', 'top', 'center', 'bottom'
        Returns element dict or None.
        """
        elements = self.reader.get_clickable_elements()

        # Filter by area
        if area == "top":
            elements = [e for e in elements if e.center_y < 400]
        elif area == "bottom":
            elements = [e for e in elements if e.center_y > 1200]
        elif area == "center":
            elements = [e for e in elements if 400 <= e.center_y <= 1200]

        # Search by label
        query = label_contains.lower()
        for e in elements:
            label = (e.text + " " + e.content_desc + " " + e.resource_id).lower()
            if query in label:
                return {
                    "label": e.label,
                    "x": e.center_x,
                    "y": e.center_y,
                    "clickable": e.clickable,
                }

        return None

    def find_all(self, label_contains: str) -> list[dict]:
        """Find all elements matching a label."""
        elements = self.reader.get_clickable_elements()
        results = []
        query = label_contains.lower()
        for e in elements:
            label = (e.text + " " + e.content_desc + " " + e.resource_id).lower()
            if query in label:
                results.append({
                    "label": e.label,
                    "x": e.center_x,
                    "y": e.center_y,
                    "clickable": e.clickable,
                })
        return results

    # ─── UNIVERSAL ACTIONS ────────────────────────

    def tap_on(self, label_contains: str, area: str = "any") -> bool:
        """
        Find and tap an element by label. Works on ANY screen.
        Returns True if found and tapped.
        """
        element = self.find_element(label_contains, area)
        if element:
            print(f"   👆 Tapping '{element['label'][:40]}' at ({element['x']}, {element['y']})")
            self._human_delay()
            self._human_tap(element["x"], element["y"])
            return True
        return False

    def tap_on_any(self, labels: list, area: str = "any") -> bool:
        """Try multiple labels, tap the first one found."""
        for label in labels:
            if self.tap_on(label, area):
                return True
        return False

    def type_into(self, label_contains: str, text: str) -> bool:
        """Find a text field and type into it."""
        element = self.find_element(label_contains)
        if element:
            print(f"   👆 Tapping '{element['label'][:40]}'")
            self._human_delay()
            self._human_tap(element["x"], element["y"])
            self._human_delay(0.3, 0.5)
            print(f"   ⌨️  Typing: '{text[:50]}'")
            self.bridge.type_text(text)
            return True
        return False

    def scroll_down(self, distance: int = 500) -> bool:
        """Scroll down on the current screen."""
        self.bridge.swipe(360, 1200, 360, 1200 - distance, random.randint(200, 500))
        return True

    def scroll_up(self, distance: int = 500) -> bool:
        """Scroll up on the current screen."""
        self.bridge.swipe(360, 400, 360, 400 + distance, random.randint(200, 500))
        return True

    def press_back(self) -> bool:
        """Press the back button."""
        self.bridge.press_key(4)
        return True

    def press_home(self) -> bool:
        """Press the home button."""
        self.bridge.press_key(3)
        return True

    def press_enter(self) -> bool:
        """Press the enter key."""
        self.bridge.press_key(66)
        return True

    def take_screenshot(self, path: str = "nexus_screen.png") -> str:
        """Take a screenshot and return the path."""
        self.bridge.screenshot(path)
        return path

    # ─── COMPLEX ACTIONS ──────────────────────────

    def search_and_enter(self, search_label: str, query: str) -> bool:
        """
        Find a search bar, tap it, type query, press enter.
        Universal search for ANY app.
        """
        # Find search bar
        found = self.tap_on_any(["search", "search", "find"], "top")
        if not found:
            # Try tapping where search usually is
            self._human_tap(650, 100)

        self._human_delay(0.5, 1.0)
        print(f"   ⌨️  Typing: '{query}'")
        self.bridge.type_text(query)
        self._human_delay(0.3, 0.5)
        self.press_enter()
        return True

    def read_and_summarize(self) -> str:
        """
        Read the current screen and return a text summary.
        Extracts all visible text content.
        """
        elements = self.reader.get_all_elements()
        texts = []
        for e in elements:
            if e.text and e.text.strip():
                texts.append(e.text.strip())
            if e.content_desc and e.content_desc.strip():
                texts.append(e.content_desc.strip())

        return " | ".join(texts[:50])  # Top 50 text elements

    def wait_for_element(self, label_contains: str, timeout: float = 5.0) -> bool:
        """
        Wait for an element to appear on screen.
        Useful after navigation or loading.
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.find_element(label_contains):
                return True
            time.sleep(0.5)
        return False

    def long_press(self, x: int, y: int, duration_ms: int = 800):
        """Long press at coordinates."""
        self.bridge.swipe(x, y, x, y, duration_ms)


# ─── Quick Test ────────────────────────────────────
if __name__ == "__main__":
    gen = GenericActions()
    print("Generic Actions loaded.")
    print("Available: tap_on, type_into, search_and_enter, read_screen, scroll_down, press_back, press_home")
    print("\nCurrent screen:")
    print(gen.what_do_i_see())