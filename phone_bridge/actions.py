"""
Nexus Phone Actions (Self-Learning TPM)
Checks learned patterns first. Falls back to dynamic screen reading.
Updates phone_map.json with verified coordinates on every success.
Gets smarter every time you use it.
"""

import json
import time
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phone_bridge.bridge import PhoneBridge
from phone_bridge.screen_reader import ScreenReader


class PhoneActions:
    """Self-learning phone actions powered by TPM."""

    def __init__(self, bridge: PhoneBridge = None):
        self.bridge = bridge or PhoneBridge()
        self.reader = ScreenReader()
        self.default_wait = 0.8
        self.map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phone_map.json")
        self.learned_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learned_patterns.json")
        self.map_data = self._load_json(self.map_path, {"apps": {}})
        self.learned = self._load_json(self.learned_path, {})

    def _load_json(self, path: str, default: dict) -> dict:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return default

    def _save_json(self, path: str, data: dict):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _wait(self, seconds: float = None):
        time.sleep(seconds or self.default_wait)

    # ─── LEARNED COORDINATE SYSTEM ──────────────

    def _get_learned_coordinate(self, app: str, element: str) -> Optional[dict]:
        """Get best-known coordinate for an element. Returns {x, y, confidence} or None."""
        key = f"{app}:{element}"
        entry = self.learned.get(key)
        if entry and entry.get("confidence", 0) > 0.5:
            return entry
        return None

    def _update_learned(self, app: str, element: str, x: int, y: int, success: bool):
        """Update learned coordinates after an action."""
        key = f"{app}:{element}"
        if key not in self.learned:
            self.learned[key] = {"successes": 0, "failures": 0, "x": x, "y": y, "confidence": 0.0}

        entry = self.learned[key]
        if success:
            entry["successes"] += 1
            entry["x"] = x  # Update with latest successful position
            entry["y"] = y
        else:
            entry["failures"] += 1

        total = entry["successes"] + entry["failures"]
        entry["confidence"] = entry["successes"] / total if total > 0 else 0.0
        self._save_json(self.learned_path, self.learned)

    # ─── SMART TAP (LEARNED FIRST, DYNAMIC FALLBACK) ──

    def _smart_tap(self, app: str, element_label: str, area: str = "any") -> bool:
        """
        Tap an element using learned coordinates first, dynamic search as fallback.
        Updates learned coordinates on success.
        """
        # TRY 1: Learned coordinate
        learned = self._get_learned_coordinate(app, element_label)
        if learned:
            print(f"   🧠 Using learned {element_label} at ({learned['x']}, {learned['y']}) (confidence: {learned['confidence']:.0%})")
            self.bridge.tap(learned["x"], learned["y"])
            self._wait(0.3)
            # Quick verify — did the screen change?
            after = len(self.reader.get_clickable_elements())
            if after > 5:  # Screen has content
                self._update_learned(app, element_label, learned["x"], learned["y"], True)
                return True
            else:
                print(f"   ⚠️ Learned coordinate failed. Trying dynamic search...")
                self._update_learned(app, element_label, learned["x"], learned["y"], False)

        # TRY 2: Dynamic search by label
        elements = self.reader.get_clickable_elements()
        if area == "top":
            elements = [e for e in elements if e.center_y < 400]
        elif area == "bottom":
            elements = [e for e in elements if e.center_y > 1200]
        elif area == "center":
            elements = [e for e in elements if 400 <= e.center_y <= 1200]

        for e in elements:
            label = (e.text + " " + e.content_desc + " " + e.resource_id).lower()
            if element_label.lower() in label:
                print(f"   👆 Found '{e.label[:40]}' at ({e.center_x}, {e.center_y}) [dynamic]")
                self.bridge.tap(e.center_x, e.center_y)
                self._update_learned(app, element_label, e.center_x, e.center_y, True)
                return True

        return False

    def _smart_find(self, app: str, label_contains: str, area: str = "any") -> Optional[dict]:
        """Find element with learned-first, dynamic-fallback approach."""
        learned = self._get_learned_coordinate(app, label_contains)
        if learned:
            return {"label": label_contains, "x": learned["x"], "y": learned["y"]}

        elements = self.reader.get_clickable_elements()
        if area == "top":
            elements = [e for e in elements if e.center_y < 400]
        elif area == "bottom":
            elements = [e for e in elements if e.center_y > 1200]

        for e in elements:
            label = (e.text + " " + e.content_desc + " " + e.resource_id).lower()
            if label_contains.lower() in label:
                return {"label": e.label, "x": e.center_x, "y": e.center_y}

        return None

    # ─── WHATSAPP (SELF-LEARNING) ────────────────

    def send_whatsapp(self, contact: str, message: str) -> bool:
        print(f"   📱 WhatsApp → {contact}: \"{message}\"")

        self.bridge.open_app("com.whatsapp")
        self._wait(2.0)

        # Search — learned first, dynamic fallback
        if not self._smart_tap("WhatsApp", "search", "top"):
            self._smart_tap("WhatsApp", "meta ai", "top")
        self._wait(0.5)

        # Type contact
        self.bridge.type_text(contact)
        self._wait(2.5)

        # Find contact in results (Y > 300 to skip search input)
        all_el = self.reader.get_clickable_elements()
        contact_el = [e for e in all_el if contact.lower() in (e.text + e.content_desc).lower() and e.center_y > 300]

        if contact_el:
            target = contact_el[0]
            print(f"   ✅ Found '{target.label[:30]}' at ({target.center_x}, {target.center_y})")
            self.bridge.tap(360, target.center_y)
        else:
            self.bridge.tap(360, 392)
        self._wait(1.5)

        # Message input — learned first
        if not self._smart_tap("WhatsApp", "message", "bottom"):
            self.bridge.tap(360, 1450)
        self._wait(0.5)

        # Type message
        self.bridge.type_text(message)
        self._wait(0.4)

        # Send button — learned first
        if not self._smart_tap("WhatsApp", "send", "bottom"):
            self.bridge.tap(670, 1450)
        self._wait(0.3)

        print(f"   ✅ Sent.")
        return True

    # ─── NOTES ─────────────────────────────────────

    def write_note(self, title: str, content: str = "") -> bool:
        print(f"   📝 Note: '{title}'")
        self.bridge.open_app("com.miui.notes")
        self._wait(1.5)

        if not self._smart_tap("Notes", "new") and not self._smart_tap("Notes", "create"):
            self.bridge.tap(670, 200)
        self._wait(0.5)

        if title:
            self.bridge.type_text(title)
            self._wait(0.3)

        if content:
            self.bridge.press_key(66)
            self._wait(0.3)
            self.bridge.type_text(content)
            self._wait(0.3)

        if not self._smart_tap("Notes", "save") and not self._smart_tap("Notes", "done"):
            self.bridge.tap(670, 150)
        self._wait(0.5)

        self.bridge.press_key(3)
        print(f"   ✅ Saved.")
        return True

    # ─── YOUTUBE ────────────────────────────────────

    def search_youtube(self, query: str) -> bool:
        print(f"   ▶️  YouTube: '{query}'")
        self.bridge.open_app("app.revanced.android.youtube")
        self._wait(2.0)

        if not self._smart_tap("YouTube", "search", "top"):
            self.bridge.tap(650, 100)
        self._wait(0.5)

        self.bridge.type_text(query)
        self._wait(0.3)
        self.bridge.press_key(66)
        self._wait(1.0)

        print(f"   ✅ Done.")
        return True

    # ─── CALLING ────────────────────────────────────

    def call_number(self, number: str, auto_dial: bool = False) -> bool:
        print(f"   📞 {number}")
        self.bridge.open_dialer(number)
        self._wait(1.0)
        if auto_dial:
            if not self._smart_tap("Dialer", "call", "bottom"):
                self.bridge.tap(650, 2200)
        return True

    # ─── NAVIGATION ─────────────────────────────────

    def go_home(self): self.bridge.press_key(3)
    def go_back(self): self.bridge.press_key(4)
    def open_notifications(self): self.bridge.swipe(360, 0, 360, 600)
    def open_recent_apps(self): self.bridge.swipe(360, 1800, 360, 800)

    # ─── OPEN APP ───────────────────────────────────

    def open_app(self, app_name: str) -> bool:
        APP_MAP = {
            "whatsapp": "com.whatsapp", "telegram": "org.telegram.messenger",
            "youtube": "app.revanced.android.youtube", "spotify": "com.spotify.music",
            "brave": "com.brave.browser", "chrome": "com.android.chrome",
            "notes": "com.miui.notes", "calendar": "com.google.android.calendar",
            "clock": "com.google.android.deskclock", "calculator": "com.miui.calculator",
            "settings": "com.android.settings", "dialer": "com.google.android.dialer",
            "camera": "com.android.camera", "gallery": "com.google.android.apps.photos",
            "messages": "com.google.android.apps.messaging",
            "playstore": "com.android.vending",
        }
        package = APP_MAP.get(app_name.lower(), app_name)
        self.bridge.open_app(package)
        print(f"   ✅ Opened {app_name}.")
        return True


# ─── Quick Stats ────────────────────────────────────
if __name__ == "__main__":
    actions = PhoneActions()
    print("PhoneActions (Self-Learning TPM) loaded.")
    print(f"Learned patterns: {len(actions.learned)}")
    for key, entry in actions.learned.items():
        print(f"   {key}: confidence={entry.get('confidence', 0):.0%} at ({entry.get('x')},{entry.get('y')})")