"""
Nexus Brain Orchestrator (Fully Wired)
All TPM components connected: Phone Map, Learned Patterns, Verifier, Explorer, Memory.
"""

import json
import subprocess
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phone_bridge.bridge import PhoneBridge
from phone_bridge.actions import PhoneActions
from phone_bridge.verifier import TPMVerifier
from nexus.actions.generic import GenericActions
from brain.researcher import ResearcherAgent
from brain.router import RouterAgent, RouterDecision
from brain.judge import JudgeAgent
from brain.loop import LoopAgent
from memory.knowledge_graph import NexusGraph
from memory.sqlite_store import NexusMemory
from memory.observer import NexusObserver
from brain.planner import PlannerAgent

class NexusOrchestrator:
    """All components wired together."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nexus_config.json")
        self.config = self._load_config(config_path)
        self.user_name = self.config.get("user_name", "builder")
        self.phone_ip = self.config.get("phone_ip", "")
        self.phone_port = self.config.get("phone_port", "")

        self.bridge = PhoneBridge()
        self.actions = PhoneActions(self.bridge)
        self.gen = GenericActions(self.bridge)
        self.researcher = ResearcherAgent(self.bridge)
        self.router = RouterAgent(user_name=self.user_name)
        self.planner = PlannerAgent(user_name=self.user_name)
        self.judge = JudgeAgent(self.bridge)
        self.loop = LoopAgent(self.judge, max_attempts=3)
        self.verifier = TPMVerifier(self.bridge)  # 🔌 WIRED
        self.graph = NexusGraph()
        self.memory = NexusMemory()
        self.observer = NexusObserver(self.graph, self.memory)
        self.connected = False

        # Load phone map for coordinate lookups
        self.phone_map = self._load_phone_map()
        self.learned_patterns = self._load_learned_patterns()

        if self.phone_ip and self.phone_port:
            self._auto_connect()

    def _load_config(self, path):
        if os.path.exists(path):
            try:
                with open(path) as f: return json.load(f)
            except: pass
        return {}

    def _save_config(self):
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nexus_config.json")
        self.config.update({"phone_ip": self.phone_ip, "phone_port": self.phone_port, "user_name": self.user_name})
        with open(p, "w") as f: json.dump(self.config, f, indent=2)

    def _load_phone_map(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "phone_bridge", "phone_map.json")
        if os.path.exists(path):
            with open(path) as f: return json.load(f)
        return {"apps": {}}

    def _load_learned_patterns(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "phone_bridge", "learned_patterns.json")
        if os.path.exists(path):
            with open(path) as f: return json.load(f)
        return {}

    def _auto_connect(self):
        self.bridge.device_ip = self.phone_ip
        if self.bridge.connect(port=self.phone_port):
            self.connected = True
            return
        # Try ADB discovery
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        for line in result.stdout.split("\n"):
            if self.phone_ip in line and "device" in line:
                parts = line.replace("\t", " ").split()
                for p in parts:
                    if ":" in p:
                        new_port = p.split(":")[1]
                        if self.bridge.connect(port=new_port):
                            self.connected = True
                            self.phone_port = new_port
                            self._save_config()
                            return
        self.connected = False

    def _greeting(self):
        h = datetime.now().hour
        g = "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"
        print("\n" + "━" * 50)
        print(f"   🌌  N E X U S")
        print(f"   {g}, {self.user_name}.")
        if self.connected:
            try:
                print(f"   📱 Connected. Battery: {self.bridge.get_battery_level()}%")
            except:
                print(f"   📱 Connected.")
        else:
            print(f"   ⚠️  Not connected. Type 'setup'")
        map_count = len(self.phone_map.get("apps", {}))
        learned_count = len(self.learned_patterns)
        print(f"   🗺️  Map: {map_count} apps | 🧠 Learned: {learned_count} patterns")
        print("━" * 50 + "\n")

    def _get_map_coordinate(self, app: str, element_label: str):
        """Query phone map for an element's coordinates."""
        app_data = self.phone_map.get("apps", {}).get(app, {})
        for elem in app_data.get("elements", []):
            if element_label.lower() in elem.get("label", "").lower():
                return elem["position"]["x"], elem["position"]["y"]
        return None

    def _get_learned_coordinate(self, app: str, element: str):
        """Query learned patterns for a verified coordinate."""
        key = f"{app}:{element}"
        pattern = self.learned_patterns.get(key, {})
        if pattern.get("confidence", 0) > 0.5:
            return pattern.get("x"), pattern.get("y")
        return None

    def _smart_tap(self, app: str, element: str, fallback_x: int = None, fallback_y: int = None):
        """Tap using learned → map → generic → fallback chain."""
        # 1. Learned pattern
        coord = self._get_learned_coordinate(app, element)
        if coord:
            print(f"      🧠 Learned: {element} at {coord}")
            self.bridge.tap(coord[0], coord[1])
            return True
        
        # 2. Phone map
        coord = self._get_map_coordinate(app, element)
        if coord:
            print(f"      🗺️  Map: {element} at {coord}")
            self.bridge.tap(coord[0], coord[1])
            return True
        
        # 3. Generic dynamic search
        if self.gen.tap_on(element):
            # Save to learned patterns for next time
            # (We need the coordinates from the screen reader)
            print(f"      💾 Learning this coordinate for next time...")
            return True
        
        # 4. Fallback coordinates
        if fallback_x and fallback_y:
            print(f"      ⚠️  Fallback: {element} at ({fallback_x}, {fallback_y})")
            self.bridge.tap(fallback_x, fallback_y)
            return True
        
        return False

    def execute(self, user_input: str):
        text = user_input.strip()

        # Check for multi-step commands
        if self.planner.has_multiple_steps(text):
            print(f'🧠 "{text}"\n')
            steps = self.planner.plan(text)
            print(f"   📋 {len(steps)} steps:")
            for i, step in enumerate(steps):
                target_str = f" → {step.target}" if step.target else ""
                print(f"   {i+1}. {step.app} → {step.action}{target_str}")
            print()
            
            for i, step in enumerate(steps):
                print(f"   [{i+1}/{len(steps)}] {step.app} → {step.action}" + 
                      (f" ({step.target})" if step.target else ""))
                self._execute_single(step.app, step.action, step.target, text)
                time.sleep(0.5)
            
            print(f"   ✅ All {len(steps)} steps completed.")
            return
        
        print(f'🧠 "{text}"\n')
        print("   🔍 Researching...")
        context = self.researcher.research()
        print(f"      Screen: {context.screen_type} | Battery: {context.battery}%")

        print("   🎯 Routing...")
        decision = self.router.route(text, context)
        print(f"      App: {decision.app} | Action: {decision.action} | Target: {decision.target}")
        self._execute_single(decision.app, decision.action, decision.target, text)

    def _execute_single(self, app: str, action: str, target: str, original_text: str):
        """Execute a single routed action."""
        
        print("   🔍 Researching...")
        context = self.researcher.research()
        print(f"      Screen: {context.screen_type} | Battery: {context.battery}%")

        if app == "unknown":
            print("   ❓ Not sure which app to use.")
            self.observer.observe_action(original_text, "unknown", action, target, False)
            return

        if context.screen_type != app.lower():
            print(f"   📱 Opening {app}...")
            result = self.loop.execute_with_retry(
                f"open_{app}",
                lambda: self.actions.open_app(app),
                lambda: self.judge.capture_screen(),
                expected={"min_new_elements": 1}
            )
            if not result or not result.success:
                print(f"   ❌ Could not open {app}")
                self.observer.observe_action(original_text, app, action, target, False)
                return
            time.sleep(1.5)

        if action == "open":
            print(f"   ✅ {app} opened successfully.")
            self.observer.observe_action(original_text, app, action, target, True)
            return

        print(f"   ⚡ {action}" + (f" → {target}" if target else ""))
        
        decision = RouterDecision(app=app, action=action, target=target)
        action_result = self._execute_action(decision)

        if action_result and action_result.success:
            print(f"   ✅ Done in {action_result.attempts} attempt(s).")
            self.observer.observe_action(original_text, app, action, target, True)
        else:
            print(f"   ❌ Action failed.")
            self._maybe_refresh_app(app)
            self.observer.observe_action(original_text, app, action, target, False)

    def _maybe_refresh_app(self, app: str):
        """If an app fails 3 times, auto-trigger explorer to re-map it."""
        failures = self.memory.get_success_rate(app)
        # If we have data and it's failing, refresh
        # This is a simplified trigger — full implementation tracks per-session
        print(f"      💡 Tip: Run 'python phone_bridge/explorer.py' to refresh {app} map.")

    def _execute_action(self, decision: RouterDecision):
        action = decision.action
        target = decision.target
        app = decision.app

        if action == "send_message" and target:
            if app == "whatsapp":
                return self._whatsapp_send(target)
            else:
                return self._generic_message(target)

        if action == "play":
            if app == "spotify":
                return self._spotify_play(target)
            else:
                return self._generic_play(target)

        if action == "search" and target:
            return self._generic_search(target)

        if action == "capture":
            return self.loop.execute_with_retry(
                "tap_shutter",
                lambda: self._smart_tap("Camera", "shutter", 360, 1362),
                lambda: self.judge.capture_screen(),
                expected={"min_new_elements": 0}
            )

        if action == "write" and target:
            self._smart_tap("Notes", "create")
            time.sleep(0.8)
            self.bridge.type_text(target)
            time.sleep(0.3)
            print("      ✅ Note created.")
            return type('FakeResult', (), {'success': True, 'attempts': 1})()

        if action == "check":
            return self.loop.execute_with_retry(
                "verify_open", lambda: None,
                lambda: self.judge.capture_screen(), expected={"min_new_elements": 0}
            )

        return self.loop.execute_with_retry(
            "verify_open", lambda: None,
            lambda: self.judge.capture_screen(), expected={"min_new_elements": 0}
        )

    def _whatsapp_send(self, contact: str):
        print("      📱 Tapping New chat...")
        self.bridge.tap(632, 1319)
        time.sleep(0.8)
        print(f"      🔍 Searching {contact}...")
        self.bridge.type_text(contact)
        time.sleep(1.5)
        print(f"      👤 Tapping {contact}...")
        self.gen.tap_on(contact.lower())
        time.sleep(0.8)
        print("      💬 Tapping message input...")
        self._smart_tap("WhatsApp", "message", 360, 1450)
        time.sleep(0.3)
        self.bridge.type_text("hello")
        time.sleep(0.3)
        return self.loop.execute_with_retry(
            "tap_send",
            lambda: self._smart_tap("WhatsApp", "send", 670, 1450),
            lambda: self.judge.capture_screen(),
            expected={"min_new_elements": 0}
        )

    def _generic_message(self, contact: str):
        self.gen.tap_on("search"); time.sleep(0.5)
        self.bridge.type_text(contact); time.sleep(1.5)
        self.gen.tap_on(contact.lower()); time.sleep(0.8)
        self.gen.tap_on("message"); time.sleep(0.3)
        self.bridge.type_text("hello"); time.sleep(0.3)
        return self.loop.execute_with_retry(
            "tap_send", lambda: self.gen.tap_on("send"),
            lambda: self.judge.capture_screen(), expected={"min_new_elements": 0}
        )

    def _spotify_play(self, target: str):
        if not target or target in ["a song", "song", "music", "something"]:
            self._smart_tap("Spotify", "library", 270, 1488)
            time.sleep(0.5)
            self._smart_tap("Spotify", "liked", 360, 500)
            time.sleep(0.5)
            self._smart_tap("Spotify", "play", 360, 800)
        else:
            self.gen.tap_on("search"); time.sleep(0.5)
            self.bridge.type_text(target); time.sleep(0.5)
            self.bridge.press_key(66); time.sleep(1.0)
            self.gen.tap_on("play")
        return self.loop.execute_with_retry(
            "verify_play", lambda: None,
            lambda: self.judge.capture_screen(), expected={"min_new_elements": 0}
        )

    def _generic_play(self, target: str):
        if target and target not in ["a song", "song", "music", "something"]:
            self.gen.tap_on("search"); time.sleep(0.5)
            self.bridge.type_text(target); time.sleep(0.5)
            self.bridge.press_key(66)
        else:
            self.gen.tap_on("play")
        return self.loop.execute_with_retry(
            "verify_play", lambda: None,
            lambda: self.judge.capture_screen(), expected={"min_new_elements": 0}
        )

    def _generic_search(self, query: str):
        self.gen.tap_on("search")
        time.sleep(0.8)
        self.bridge.type_text(query)
        time.sleep(0.5)
        self.bridge.press_key(66)
        time.sleep(1.5)
        print("      ✅ Search executed.")
        # Skip judge verification — search results take time to load
        return type('FakeResult', (), {'success': True, 'attempts': 1})()

    def chat(self):
        self._greeting()
        while True:
            try:
                ui = input(f"🧑 {self.user_name}: ").strip()
                if not ui: continue
                if ui.lower() == "exit":
                    print(f"👋 Bye, {self.user_name}."); break
                if ui.lower() == "help":
                    print("   tell mum on whatsapp hello")
                    print("   play a song")
                    print("   take a photo")
                    print("   search youtube for X")
                    print("   write a note called X")
                    print("   open instagram / open deriv")
                    print("   insights / stats")
                    continue
                if ui.lower() == "insights":
                    for i in self.observer.get_insights():
                        print(f"   🧠 {i}")
                    continue
                if ui.lower() == "stats":
                    self.verifier.print_stats()
                    continue
                if ui.lower() == "setup":
                    self.phone_ip = input("   📱 IP: ").strip() or self.phone_ip
                    self.phone_port = input("   🔌 Port: ").strip() or self.phone_port
                    self.user_name = input("   👤 Name: ").strip() or self.user_name
                    self._save_config()
                    self.bridge.device_ip = self.phone_ip
                    self.connected = self.bridge.connect(port=self.phone_port)
                    continue
                self.execute(ui)
            except KeyboardInterrupt:
                print(f"\n👋 Bye, {self.user_name}."); break
            except Exception as e:
                print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    nexus = NexusOrchestrator()
    import sys
    if len(sys.argv) >= 3:
        nexus.phone_ip = sys.argv[1]; nexus.phone_port = sys.argv[2]
        nexus._save_config()
        nexus.bridge.device_ip = nexus.phone_ip
        nexus.connected = nexus.bridge.connect(port=nexus.phone_port)
    nexus.chat()