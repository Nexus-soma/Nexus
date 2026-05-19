"""
Nexus Thinker
Context-aware reasoning layer. Reads the screen, understands where it is,
plans actions, verifies before executing, and stops if something is wrong.
No more blind execution.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phone_bridge.screen_reader import ScreenReader
from phone_bridge.bridge import PhoneBridge


class ScreenContext:
    """Understands what screen the phone is currently on."""

    def __init__(self, elements: list):
        self.elements = elements
        self.labels = []
        for e in elements:
            if e.label:
                self.labels.append(e.label.lower())
            if e.content_desc and e.content_desc != e.label:
                self.labels.append(e.content_desc.lower())
        self.all_text = " ".join(self.labels)

    def is_lock_screen(self) -> bool:
        return any("emergency" in t for t in self.labels) or any("locked" in t for t in self.labels)

    def is_home_screen(self) -> bool:
        home_indicators = ["folder", "clock", "calendar", "camera", "settings", "chrome", "brave"]
        return sum(1 for t in self.labels if any(ind in t for ind in home_indicators)) >= 3

    def is_app_drawer(self) -> bool:
        return any("drawer" in t for t in self.labels)

    def is_inside_app(self, app_name: str) -> bool:
        APP_MARKERS = {
            "whatsapp": ["chat", "update", "community", "call", "meta ai", "search", "camera", "more options", "new chat"],
            "youtube": ["home", "shorts", "subscriptions", "library", "search", "create"],
            "settings": ["wireless", "bluetooth", "battery", "display", "sound", "debugging"],
            "notes": ["note", "checklist", "drawing", "audio", "create"],
            "brave": ["bookmark", "history", "download", "setting", "tab"],
            "spotify": ["home", "search", "library", "premium", "play"],
            "playstore": ["game", "app", "offer", "install"],
            "camera": ["photo", "video", "portrait", "night", "capture"],
            "calculator": ["equals", "plus", "minus", "multiply", "divide"],
        }
        markers = APP_MARKERS.get(app_name.lower(), [app_name.lower()])
        found = sum(1 for label in self.labels if any(marker in label for marker in markers))
        return found >= 2

    def has_element(self, label: str) -> bool:
        return any(label.lower() in t for t in self.labels)

    def get_summary(self) -> str:
        if self.is_lock_screen():
            return "lock_screen"
        elif self.is_home_screen():
            return "home_screen"
        elif self.is_app_drawer():
            return "app_drawer"
        else:
            for app in ["whatsapp", "youtube", "settings", "notes", "brave", "spotify"]:
                if self.is_inside_app(app):
                    return f"inside_{app}"
            return "unknown_screen"


class NexusThinker:
    """Thinks before acting. Reads context, plans, verifies."""

    def __init__(self, bridge: PhoneBridge = None):
        self.bridge = bridge or PhoneBridge()
        self.reader = ScreenReader()

    def read_context(self) -> ScreenContext:
        elements = self.reader.get_all_elements()
        return ScreenContext(elements)

    def ensure_awake(self) -> bool:
        """Make sure the screen is ON before trying to read it."""
        result = self.bridge.run_raw("dumpsys power | grep 'mWakefulness'")
        if "Asleep" in result or "Dozing" in result:
            print("   💤 Screen is asleep. Waking up...")
            self.bridge.press_key(26)
            time.sleep(1.0)
            result = self.bridge.run_raw("dumpsys power | grep 'mWakefulness'")
            if "Awake" in result:
                print("   ✅ Screen awake")
                return True
            else:
                print("   ❌ Screen still asleep. Please wake your phone.")
                return False
        print("   ✅ Screen is awake")
        return True

    def ensure_unlocked(self) -> bool:
        ctx = self.read_context()
        if ctx.is_lock_screen():
            print("   🔓 Phone is locked. Swiping to unlock...")
            self.bridge.swipe(360, 1500, 360, 500, 200)
            time.sleep(0.5)
            ctx = self.read_context()
            if ctx.is_lock_screen():
                print("   ❌ Still locked. I need your help to unlock.")
                return False
        return True

    def ensure_on_home_screen(self) -> bool:
        ctx = self.read_context()
        if ctx.get_summary() != "home_screen":
            print("   🏠 Going to home screen...")
            self.bridge.press_key(3)
            time.sleep(0.5)
        return True

    def ensure_app_open(self, app_name: str, package: str) -> bool:
        ctx = self.read_context()
        if ctx.is_inside_app(app_name):
            print(f"   ✅ Already in {app_name}")
            return True
        self.ensure_on_home_screen()
        time.sleep(0.3)
        print(f"   📱 Opening {app_name}...")
        self.bridge.open_app(package)
        for attempt in range(5):
            time.sleep(1.0)
            ctx = self.read_context()
            if ctx.is_inside_app(app_name):
                print(f"   ✅ {app_name} opened")
                return True
        print(f"   ⚠️ {app_name} may not have opened correctly")
        return True

    def verify_target_exists(self, target_name: str) -> bool:
        ctx = self.read_context()
        found = ctx.has_element(target_name)
        if found:
            print(f"   ✅ Found '{target_name}' on screen")
            return True
        else:
            print(f"   ⚠️ '{target_name}' NOT found on screen")
            print(f"   🛑 Stopping — I won't send to the wrong person.")
            return False

    def think_through(self, task_description: str) -> dict:
        ctx = self.read_context()
        current_screen = ctx.get_summary()
        print(f"   🧠 Thinking...")
        print(f"   📍 Current screen: {current_screen}")
        plan = {"current_screen": current_screen, "steps": [], "warnings": []}
        if ctx.is_lock_screen():
            plan["steps"].append("unlock_phone")
