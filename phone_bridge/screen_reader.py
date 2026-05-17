"""
Nexus Screen Reader
Uses uiautomator to dump and parse the phone's UI tree.
Returns structured data about every interactive element on screen.
"""

import subprocess
import xml.etree.ElementTree as ET
import time
import os
import sys
import re
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ScreenElement:
    """Represents a single interactive element on the phone screen."""

    def __init__(self, xml_element):
        self.text = xml_element.get("text", "")
        self.content_desc = xml_element.get("content-desc", "")
        self.resource_id = xml_element.get("resource-id", "")
        self.class_name = xml_element.get("class", "")
        self.package = xml_element.get("package", "")
        self.bounds = xml_element.get("bounds", "0,0,0,0")
        self.clickable = xml_element.get("clickable") == "true"
        self.focusable = xml_element.get("focusable") == "true"
        self.scrollable = xml_element.get("scrollable") == "true"
        self.enabled = xml_element.get("enabled") == "true"
        self.selected = xml_element.get("selected") == "true"
        self.checkable = xml_element.get("checkable") == "true"
        self.checked = xml_element.get("checked") == "true"

        # Parse bounds into coordinates
        self._parse_bounds()

    def _parse_bounds(self):
        """Parse bounds like '[x1,y1][x2,y2]' into pixel coordinates."""
        try:
            match = re.findall(r'\d+', self.bounds)
            if len(match) >= 4:
                self.x1 = int(match[0])
                self.y1 = int(match[1])
                self.x2 = int(match[2])
                self.y2 = int(match[3])
                self.center_x = (self.x1 + self.x2) // 2
                self.center_y = (self.y1 + self.y2) // 2
                self.width = self.x2 - self.x1
                self.height = self.y2 - self.y1
            else:
                self.x1 = self.y1 = self.x2 = self.y2 = 0
                self.center_x = self.center_y = 0
                self.width = self.height = 0
        except Exception:
            self.x1 = self.y1 = self.x2 = self.y2 = 0
            self.center_x = self.center_y = 0
            self.width = self.height = 0

    @property
    def label(self) -> str:
        """Best human-readable label for this element."""
        return self.text or self.content_desc or self.resource_id or self.class_name

    @property
    def is_interactive(self) -> bool:
        """Is this element something a user would interact with?"""
        return self.clickable or self.focusable or self.scrollable or self.checkable

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "text": self.text,
            "content_desc": self.content_desc,
            "resource_id": self.resource_id,
            "class_name": self.class_name,
            "clickable": self.clickable,
            "focusable": self.focusable,
            "scrollable": self.scrollable,
            "enabled": self.enabled,
            "checked": self.checked,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "width": self.width,
            "height": self.height,
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
        }

    def __repr__(self):
        return f"<Element '{self.label}' @ ({self.center_x},{self.center_y}) clickable={self.clickable}>"


class ScreenReader:
    """Reads and parses the phone's current screen using uiautomator."""

    def __init__(self, device_serial: Optional[str] = None):
        self.device_serial = device_serial
        self._adb_prefix = ["adb"]
        if device_serial:
            self._adb_prefix += ["-s", device_serial]

    def _adb_shell(self, *args) -> str:
        """Run an ADB shell command and return stdout."""
        cmd = self._adb_prefix + ["shell"] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    def dump_ui(self) -> Optional[ET.Element]:
        """
        Dump the current UI tree from the phone.
        Returns the root XML element or None on failure.
        """
        # Dump UI tree
        self._adb_shell("uiautomator", "dump", "/sdcard/window_dump.xml")
        
        # Wait for dump to complete
        time.sleep(0.3)

        # Pull the XML content
        xml_content = self._adb_shell("cat", "/sdcard/window_dump.xml")

        if not xml_content:
            return None

        # Find where the XML actually starts
        xml_start = xml_content.find("<?xml")
        if xml_start == -1:
            return None
        
        # Take everything from <?xml onwards
        xml_content = xml_content[xml_start:]

        try:
            root = ET.fromstring(xml_content)
            return root
        except ET.ParseError as e:
            print(f"⚠️  Parse error: {e}")
            print(f"   XML snippet: {xml_content[:200]}...")
            return None

    def get_all_elements(self) -> list[ScreenElement]:
        """Get all elements from the current screen."""
        root = self.dump_ui()
        if root is None:
            return []

        elements = []
        for elem in root.iter("node"):
            se = ScreenElement(elem)
            elements.append(se)

        return elements

    def get_interactive_elements(self) -> list[ScreenElement]:
        """Get only interactive (clickable, focusable, scrollable, checkable) elements."""
        return [e for e in self.get_all_elements() if e.is_interactive]

    def get_clickable_elements(self) -> list[ScreenElement]:
        """Get only clickable elements."""
        return [e for e in self.get_all_elements() if e.clickable]

    def find_by_text(self, text: str, partial: bool = True) -> list[ScreenElement]:
        """
        Find elements by text content.
        If partial=True, matches if text contains the query.
        """
        elements = self.get_all_elements()
        results = []
        for elem in elements:
            target = (elem.text + " " + elem.content_desc).lower()
            query = text.lower()
            if partial and query in target:
                results.append(elem)
            elif not partial and query == target.strip():
                results.append(elem)
        return results

    def find_by_id(self, resource_id: str, partial: bool = True) -> list[ScreenElement]:
        """Find elements by resource ID."""
        elements = self.get_all_elements()
        results = []
        for elem in elements:
            if partial and resource_id in elem.resource_id:
                results.append(elem)
            elif not partial and resource_id == elem.resource_id:
                results.append(elem)
        return results

    def find_by_class(self, class_name: str) -> list[ScreenElement]:
        """Find elements by class name (e.g., 'android.widget.EditText', 'android.widget.Button')."""
        elements = self.get_all_elements()
        return [e for e in elements if class_name in e.class_name]

    def get_element_at(self, x: int, y: int) -> Optional[ScreenElement]:
        """Get the element at specific coordinates."""
        elements = self.get_all_elements()
        for elem in elements:
            if elem.x1 <= x <= elem.x2 and elem.y1 <= y <= elem.y2:
                return elem
        return None

    def summarize_screen(self) -> dict:
        """
        Return a summary of the current screen.
        Useful for the LLM to understand what's visible.
        """
        interactive = self.get_interactive_elements()

        return {
            "total_elements": len(self.get_all_elements()),
            "interactive_elements": len(interactive),
            "elements": [
                {
                    "label": e.label,
                    "position": f"({e.center_x},{e.center_y})",
                    "clickable": e.clickable,
                    "checked": e.checked,
                }
                for e in interactive[:25]
            ],
        }


# ─── Quick Test ────────────────────────────────────
if __name__ == "__main__":
    reader = ScreenReader()
    print("🔍 Reading phone screen...\n")

    # Get interactive elements
    interactive = reader.get_interactive_elements()
    print(f"Found {len(interactive)} interactive elements:\n")

    for elem in interactive[:20]:
        icon = "🖱️" if elem.clickable else "✅" if elem.checkable else "👁️"
        label = elem.label[:45] if elem.label else "(no label)"
        print(f"  {icon} {label:45s} @ ({elem.center_x:3d},{elem.center_y:3d})")

    if len(interactive) > 20:
        print(f"\n  ... and {len(interactive) - 20} more.")

    # Screen summary
    print(f"\n📊 Total elements on screen: {len(reader.get_all_elements())}")