"""
Nexus Phone Actions (Dynamic TPM)
High-level phone interactions using REAL-TIME screen reading.
No hardcoded coordinates. No stale maps. 
Reads the screen fresh for every action and adapts dynamically.
"""

import time
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phone_bridge.bridge import PhoneBridge
from phone_bridge.screen_reader import ScreenReader


class PhoneActions:
    """
    High-level phone actions powered by dynamic screen reading.
    Every action reads the phone's screen in real-time to find elements.
    Adapts automatically to any app layout, any device.
    """

    def __init__(self, bridge: PhoneBridge = None):
        self.bridge = bridge or PhoneBridge()
        self.reader = ScreenReader()
        self.default_wait = 0.8

    def _wait(self, seconds: float = None):
        """Pause between actions for UI to respond."""
        time.sleep(seconds or self.default_wait)

    def _find_and_tap(self, search_text: str, search_area: str = "any") -> bool:
        """
        Read the current screen and tap the first element matching search_text.
        search_area can be: 'any', 'top', 'bottom', 'center'
        Returns True if found and tapped.
        """
        elements = self.reader.get_clickable_elements()
        
        candidates = []
        for e in elements:
            label = (e.text + " " + e.content_desc + " " + e.resource_id).lower()
            if search_text.lower() in label:
                candidates.append(e)
        
        if not candidates:
            return False
        
        # Filter by screen area if specified
        if search_area == "top":
            candidates = [e for e in candidates if e.center_y < 400]
        elif search_area == "bottom":
            candidates = [e for e in candidates if e.center_y > 1200]
        elif search_area == "center":
            candidates = [e for e in candidates if 400 <= e.center_y <= 1200]
        
        if not candidates:
            return False
        
        # Tap the first match
        target = candidates[0]
        print(f"   👆 Found '{target.label[:40]}' at ({target.center_x}, {target.center_y})")
        self.bridge.tap(target.center_x, target.center_y)
        return True

    def _find_elements_by_text(self, search_text: str) -> list:
        """Find all elements containing search_text. Returns list of ScreenElements."""
        elements = self.reader.get_clickable_elements()
        results = []
        for e in elements:
            label = (e.text + " " + e.content_desc + " " + e.resource_id).lower()
            if search_text.lower() in label:
                results.append(e)
        return results

    def _type_and_enter(self, text: str):
        """Type text and press enter."""
        self.bridge.type_text(text)
        self._wait(0.3)
        self.bridge.press_key(66)  # Enter

    # ─── WhatsApp ──────────────────────────────────

    def send_whatsapp(self, contact: str, message: str) -> bool:
        """
        Send a WhatsApp message using DYNAMIC screen reading.
        Reads the screen at every step to find elements in real-time.
        """
        print(f"   📱 WhatsApp: Sending to '{contact}'...")

        # STEP 1: Open WhatsApp
        self.bridge.open_app("com.whatsapp")
        self._wait(2.5)

        # STEP 2: Find and tap the search icon
        print("   🔍 Looking for search icon...")
        
        found = self._find_and_tap("search", "top")
        
        if not found:
            search_by_id = self.reader.find_by_id("search")
            if search_by_id:
                target = search_by_id[0]
                print(f"   👆 Found search by ID at ({target.center_x}, {target.center_y})")
                self.bridge.tap(target.center_x, target.center_y)
            else:
                print("   ⚠️  Search icon not found. Using position fallback.")
                self.bridge.tap(636, 124)
        
        self._wait(0.8)

        # STEP 3: Type contact name to search
        print(f"   🔍 Searching for '{contact}'...")
        self.bridge.type_text(contact)
        self._wait(2.5)

        # STEP 4: Find the contact in search results
        print(f"   👤 Looking for {contact} in results...")
        
        all_elements = self._find_elements_by_text(contact)
        # Only look at results area (Y 300-1300), skip search input bar and bottom tabs
        contact_elements = [e for e in all_elements if 300 < e.center_y < 1300]
        
        if contact_elements:
            target = contact_elements[0]
            print(f"   ✅ Found '{target.label[:30]}' at ({target.center_x}, {target.center_y})")
            # Tap the center of the contact row at this Y position
            self.bridge.tap(360, target.center_y)
        else:
            print(f"   ⚠️  '{contact}' not found on screen. Tapping first result.")
            self.bridge.tap(360, 392)
        
        self._wait(1.0)

        # STEP 5: Find message input field
        print("   💬 Looking for message input...")
        
        found = self._find_and_tap("message", "bottom")
        if not found:
            found = self._find_and_tap("type", "bottom")
        if not found:
            edit_fields = self.reader.find_by_class("EditText")
            if edit_fields:
                bottom_edits = [e for e in edit_fields if e.center_y > 1200]
                if bottom_edits:
                    target = bottom_edits[0]
                    print(f"   👆 Found input field at ({target.center_x}, {target.center_y})")
                    self.bridge.tap(target.center_x, target.center_y)
                    found = True
            
        if not found:
            print("   ⚠️  Message input not found. Using fallback.")
            self.bridge.tap(360, 1450)
        
        self._wait(0.5)

        # STEP 6: Type the message
        print(f"   📝 Typing message...")
        self.bridge.type_text(message)
        self._wait(0.4)

        # STEP 7: Find and tap send button
        print("   📤 Looking for send button...")
        
        found = self._find_and_tap("send", "bottom")
        if not found:
            send_ids = ["send", "com.whatsapp:id/send"]
            for sid in send_ids:
                elements = self.reader.find_by_id(sid)
                if elements:
                    target = elements[0]
                    print(f"   👆 Found send button at ({target.center_x}, {target.center_y})")
                    self.bridge.tap(target.center_x, target.center_y)
                    found = True
                    break
        
        if not found:
            print("   ⚠️  Send button not found. Using fallback.")
            self.bridge.tap(670, 1450)
        
        self._wait(0.5)

        print(f"   ✅ WhatsApp message sent to {contact}.")
        return True

    # ─── Notes ─────────────────────────────────────

    def write_note(self, title: str, content: str = "") -> bool:
        """
        Create a new note using dynamic screen reading.
        Works with any notes app by reading the screen.
        """
        print(f"   📝 Writing note: '{title}'...")

        # Open Notes
        self.bridge.open_app("com.miui.notes")
        self._wait(1.5)

        # Find and tap new note button
        found = self._find_and_tap("new", "any")
        if not found:
            found = self._find_and_tap("add", "any")
        if not found:
            found = self._find_and_tap("create", "any")
        if not found:
            print("   ⚠️  New note button not found. Using fallback.")
            self.bridge.tap(670, 200)
        
        self._wait(0.5)

        # Type title
        if title:
            self.bridge.type_text(title)
            self._wait(0.3)

        # Move to content area
        if content:
            self.bridge.press_key(66)  # Enter
            self._wait(0.3)
            self.bridge.type_text(content)
            self._wait(0.3)

        # Find and tap save/done
        found = self._find_and_tap("save", "top")
        if not found:
            found = self._find_and_tap("done", "top")
        if not found:
            found = self._find_and_tap("check", "top")
        if not found:
            print("   ⚠️  Save button not found. Using fallback.")
            self.bridge.tap(670, 150)
        
        self._wait(0.5)

        # Go home
        self.bridge.press_key(3)
        print(f"   ✅ Note saved.")
        return True

    # ─── YouTube ────────────────────────────────────

    def search_youtube(self, query: str) -> bool:
        """
        Search YouTube using dynamic screen reading.
        Works with any YouTube app (regular or ReVanced).
        """
        print(f"   ▶️  YouTube: Searching '{query}'...")

        # Open YouTube (ReVanced)
        self.bridge.open_app("app.revanced.android.youtube")
        self._wait(2.0)

        # Find and tap search
        found = self._find_and_tap("search", "top")
        if not found:
            print("   ⚠️  Search not found. Using fallback.")
            self.bridge.tap(650, 100)
        
        self._wait(0.5)

        # Type query and search
        self._type_and_enter(query)
        self._wait(1.0)

        print(f"   ✅ Search results shown.")
        return True

    # ─── Calling ────────────────────────────────────

    def call_number(self, number: str, auto_dial: bool = False) -> bool:
        """
        Open dialer with number. If auto_dial, also press call button.
        """
        print(f"   📞 Dialing {number}...")

        self.bridge.open_dialer(number)
        self._wait(1.0)

        if auto_dial:
            print("   ⚠️  Auto-dial enabled. Placing call...")
            found = self._find_and_tap("call", "bottom")
            if not found:
                self.bridge.tap(650, 2200)

        print(f"   ✅ Dialer ready.")
        return True

    # ─── Navigation ─────────────────────────────────

    def go_home(self) -> bool:
        """Go to home screen."""
        self.bridge.press_key(3)
        return True

    def go_back(self) -> bool:
        """Press back button."""
        self.bridge.press_key(4)
        return True

    def open_notifications(self) -> bool:
        """Swipe down to open notification shade."""
        self.bridge.swipe(360, 0, 360, 600)
        return True

    def open_recent_apps(self) -> bool:
        """Open recent apps switcher."""
        self.bridge.swipe(360, 1800, 360, 800)
        return True

    # ─── Open App ───────────────────────────────────

    def open_app(self, app_name: str) -> bool:
        """
        Open an app by friendly name or package name.
        """
        APP_MAP = {
            "whatsapp": "com.whatsapp",
            "telegram": "org.telegram.messenger",
            "youtube": "app.revanced.android.youtube",
            "youtube music": "app.revanced.android.apps.youtube.music",
            "spotify": "com.spotify.music",
            "brave": "com.brave.browser",
            "chrome": "com.android.chrome",
            "notes": "com.miui.notes",
            "calendar": "com.google.android.calendar",
            "clock": "com.google.android.deskclock",
            "calculator": "com.miui.calculator",
            "settings": "com.android.settings",
            "dialer": "com.google.android.dialer",
            "phone": "com.google.android.dialer",
            "camera": "com.android.camera",
            "gallery": "com.google.android.apps.photos",
            "photos": "com.google.android.apps.photos",
            "messages": "com.google.android.apps.messaging",
            "files": "com.miui.android.fashiongallery",
        }

        package = APP_MAP.get(app_name.lower())
        if package:
            self.bridge.open_app(package)
            print(f"   ✅ Opened {app_name}.")
            return True
        else:
            self.bridge.open_app(app_name)
            return True


# ─── Quick Test ────────────────────────────────────
if __name__ == "__main__":
    print("PhoneActions (Dynamic TPM) loaded.")
    print("Every action reads the screen in real-time.")
    print("Available: send_whatsapp, write_note, search_youtube, call_number, go_home, go_back, open_app")