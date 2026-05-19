"""
Nexus Researcher Agent
Single-purpose: Read the phone screen and return structured context.
No LLM. Pure Python + screen reader. One job. Easy to debug.
"""

import sys
import os
import time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phone_bridge.bridge import PhoneBridge
from phone_bridge.screen_reader import ScreenReader


class ScreenContext:
    """Structured output from the Researcher."""
    
    def __init__(self, data: dict):
        self.screen_type = data.get("screen_type", "unknown")
        self.elements = data.get("elements", [])
        self.element_count = data.get("element_count", 0)
        self.is_locked = data.get("is_locked", False)
        self.is_asleep = data.get("is_asleep", False)
        self.battery = data.get("battery")
        self.resolution = data.get("resolution")
    
    def to_dict(self) -> dict:
        return {
            "screen_type": self.screen_type,
            "element_count": self.element_count,
            "is_locked": self.is_locked,
            "is_asleep": self.is_asleep,
            "battery": self.battery,
            "resolution": self.resolution,
            "elements": self.elements[:10],  # Top 10 for summary
        }
    
    def __repr__(self):
        return f"<ScreenContext: {self.screen_type} | {self.element_count} elements | battery={self.battery}%>"


class ResearcherAgent:
    """
    Reads the phone screen and returns structured context.
    One job. No LLM. Pure Python.
    
    Usage:
        researcher = ResearcherAgent(bridge)
        context = researcher.research()
        print(context.screen_type)  # "home_screen", "whatsapp", etc.
    """
    
    def __init__(self, bridge: PhoneBridge = None):
        self.bridge = bridge or PhoneBridge()
        self.reader = ScreenReader()
    
    def _ensure_awake(self) -> bool:
        """Wake the screen if asleep."""
        result = self.bridge.run_raw("dumpsys power | grep 'mWakefulness'")
        if "Asleep" in result or "Dozing" in result:
            self.bridge.press_key(26)
            time.sleep(1.0)
            result = self.bridge.run_raw("dumpsys power | grep 'mWakefulness'")
            return "Awake" in result
        return True
    
    def _get_battery(self) -> Optional[int]:
        """Get battery percentage."""
        return self.bridge.get_battery_level()
    
    def _get_resolution(self) -> str:
        """Get screen resolution."""
        try:
            result = self.bridge.run_raw("wm size")
            return result.strip().split(":")[-1].strip()
        except:
            return "unknown"
    
    def _classify_screen(self, elements: list) -> str:
        """Classify what screen we're on based on visible elements."""
        labels = []
        for e in elements:
            if e.label:
                labels.append(e.label.lower())
            if e.content_desc:
                labels.append(e.content_desc.lower())
        all_text = " ".join(labels)
        
        # Lock screen check
        if any(w in all_text for w in ["emergency", "keyguard", "locked"]):
            return "lock_screen"
        
        # App-specific markers
        APP_MARKERS = {
            "whatsapp": ["chat", "update", "community", "call", "meta ai", "new chat"],
            "youtube": ["home", "shorts", "subscriptions", "library"],
            "settings": ["wireless", "bluetooth", "battery", "display", "sound"],
            "notes": ["note", "checklist", "create"],
            "brave": ["bookmark", "history", "tab"],
            "spotify": ["home", "search", "library", "premium"],
            "camera": ["photo", "video", "portrait", "shutter"],
            "calculator": ["equals", "plus", "minus", "divide"],
            "deriv": ["trade", "portfolio", "balance"],
        }
        
        for app, markers in APP_MARKERS.items():
            if sum(1 for m in markers if m in all_text) >= 2:
                return app
        
        # Home screen check
        home_markers = ["folder", "clock", "calendar", "camera", "settings", "chrome", "brave"]
        if sum(1 for m in home_markers if m in all_text) >= 3:
            return "home_screen"
        
        return "unknown"
    
    def research(self) -> ScreenContext:
        """
        Read the phone screen and return structured context.
        This is the ONE job of the Researcher Agent.
        """
        # Wake screen
        is_asleep = not self._ensure_awake()
        
        # Read UI tree
        elements = self.reader.get_all_elements()
        clickable = self.reader.get_clickable_elements()
        
        # Build element summaries
        element_list = []
        for e in clickable:
            label = e.label if e.label else e.content_desc if e.content_desc else "(no label)"
            element_list.append({
                "label": label[:50],
                "x": e.center_x,
                "y": e.center_y,
                "clickable": e.clickable,
            })
        
        # Classify screen
        screen_type = self._classify_screen(elements)
        
        # Check if locked
        is_locked = (screen_type == "lock_screen")
        
        # Build structured output
        data = {
            "screen_type": screen_type,
            "elements": element_list,
            "element_count": len(clickable),
            "is_locked": is_locked,
            "is_asleep": is_asleep,
            "battery": self._get_battery(),
            "resolution": self._get_resolution(),
        }
        
        return ScreenContext(data)


# ─── Independent Test (like Google's curl test) ───
if __name__ == "__main__":
    print("🔍 Researcher Agent - Independent Test\n")
    
    bridge = PhoneBridge()
    bridge.device_ip = "192.168.100.10"
    bridge.connect(port="35543")
    
    researcher = ResearcherAgent(bridge)
    context = researcher.research()
    
    print(f"📱 Screen Type: {context.screen_type}")
    print(f"🔒 Locked: {context.is_locked}")
    print(f"💤 Asleep: {context.is_asleep}")
    print(f"🔋 Battery: {context.battery}%")
    print(f"📐 Resolution: {context.resolution}")
    print(f"📋 Elements: {context.element_count}")
    print(f"\nFirst 5 elements:")
    for e in context.elements[:5]:
        print(f"   [{e['x']:3d},{e['y']:3d}] {e['label'][:40]}")
