"""
Nexus Phone Device
Wraps phone bridge in NexusDevice interface.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nexus.devices.base import NexusDevice
from phone_bridge.bridge import PhoneBridge
from phone_bridge.screen_reader import ScreenReader
from phone_bridge.actions import PhoneActions

class PhoneDevice(NexusDevice):
    def __init__(self, name="phone", ip=None, port=None):
        super().__init__(name, "phone")
        self.ip, self.port = ip, port
        self.bridge = PhoneBridge()
        self.reader = ScreenReader()
        self.actions = None
        self.capabilities = ["screen_read","tap","type","swipe","screenshot","open_app","call","whatsapp","youtube","notes"]
    def connect(self):
        if not self.ip or not self.port: return False
        self.bridge.device_ip = self.ip
        if self.bridge.connect(port=self.port):
            self.connected = True
            self.actions = PhoneActions(self.bridge)
            return True
        return False
    def read(self):
        if not self.connected: return {"error":"Not connected"}
        elements = self.reader.get_clickable_elements()
        return {"battery": self.bridge.get_battery_level(), "clickable_elements": len(elements), "screen_summary": [{"label": e.label[:50], "position": (e.center_x, e.center_y)} for e in elements[:20]]}
    def act(self, action, params=None):
        if not self.connected: return False
        params = params or {}
        try:
            if action == "tap": return self.bridge.tap(params["x"], params["y"])
            elif action == "type": return self.bridge.type_text(params.get("text",""))
            elif action == "screenshot": return self.bridge.screenshot(params.get("path","screenshot.png"))
            elif action == "open_app": return self.actions.open_app(params["app_name"])
            elif action == "home": return self.bridge.press_key(3)
            elif action == "back": return self.bridge.press_key(4)
            elif action == "send_whatsapp": return self.actions.send_whatsapp(params["contact"], params.get("message",""))
            elif action == "write_note": return self.actions.write_note(params.get("title",""), params.get("content",""))
            elif action == "search_youtube": return self.actions.search_youtube(params.get("query",""))
            elif action == "call": return self.actions.call_number(params["number"])
            else: print(f"   ❌ Unknown: {action}"); return False
        except Exception as e:
            print(f"   ❌ Failed: {e}"); return False
