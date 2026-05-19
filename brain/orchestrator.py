"""
Nexus Brain Orchestrator (Multi-Agent + Memory)
Researcher → Router → Loop(Judge) → Observer
Works on ANY app. Learns from every action.
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
from nexus.actions.generic import GenericActions
from brain.researcher import ResearcherAgent
from brain.router import RouterAgent, RouterDecision
from brain.judge import JudgeAgent
from brain.loop import LoopAgent
from memory.knowledge_graph import NexusGraph
from memory.sqlite_store import NexusMemory
from memory.observer import NexusObserver


class NexusOrchestrator:
    """Coordinates all agents. Learns from every action."""

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
        self.router = RouterAgent()
        self.judge = JudgeAgent(self.bridge)
        self.loop = LoopAgent(self.judge, max_attempts=3)
        self.graph = NexusGraph()
        self.memory = NexusMemory()
        self.observer = NexusObserver(self.graph, self.memory)
        self.connected = False

        if self.phone_ip and self.phone_port:
            self.bridge.device_ip = self.phone_ip
            if self.bridge.connect(port=self.phone_port):
                self.connected = True

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
            print(f"   ⚠️  Not connected. Type 'setup' then enter IP & port.")
        print(f"   🧠 Works on ANY app | Learns from you")
        print("━" * 50 + "\n")

    def execute(self, user_input: str):
        text = user_input.strip()
        print(f'🧠 "{text}"\n')

        print("   🔍 Researching...")
        context = self.researcher.research()
        print(f"      Screen: {context.screen_type} | Battery: {context.battery}%")

        print("   🎯 Routing...")
        decision = self.router.route(text, context)
        print(f"      App: {decision.app} | Action: {decision.action} | Target: {decision.target}")

        if decision.app == "unknown":
            print("\n   ❓ Not sure which app to use. Try rephrasing.")
            self.observer.observe_action(text, "unknown", "unknown", None, False)
            return

        if context.screen_type != decision.app:
            print(f"   📱 Opening {decision.app}...")
            result = self.loop.execute_with_retry(
                f"open_{decision.app}",
                lambda: self.actions.open_app(decision.app),
                lambda: self.judge.capture_screen(),
                expected={"min_new_elements": 3}
            )
            if not result or not result.success:
                print(f"   ❌ Could not open {decision.app}")
                self.observer.observe_action(text, decision.app, decision.action, decision.target, False)
                return
            time.sleep(0.5)

        print(f"   ⚡ {decision.action}" + (f" → {decision.target}" if decision.target else ""))
        action_result = self._execute_action(decision)

        if action_result and action_result.success:
            print(f"   ✅ Done in {action_result.attempts} attempt(s).")
            self.observer.observe_action(text, decision.app, decision.action, decision.target, True)
        else:
            print(f"   ❌ Action failed.")
            self.observer.observe_action(text, decision.app, decision.action, decision.target, False)

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
                "tap_shutter", lambda: self.gen.tap_on("shutter"),
                lambda: self.judge.capture_screen(), expected={"min_new_elements": 0}
            )

        if action == "write" and target:
            self.gen.tap_on("new")
            time.sleep(0.5)
            self.bridge.type_text(target)
            return self.loop.execute_with_retry(
                "verify_note", lambda: None,
                lambda: self.judge.capture_screen(), expected={"min_new_elements": 0}
            )

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
        self.gen.tap_on("message")
        time.sleep(0.3)
        self.bridge.type_text("hello")
        time.sleep(0.3)
        return self.loop.execute_with_retry(
            "tap_send", lambda: self.gen.tap_on("send"),
            lambda: self.judge.capture_screen(), expected={"min_new_elements": 0}
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
            self.gen.tap_on("library"); time.sleep(0.5)
            self.gen.tap_on("liked"); time.sleep(0.5)
            self.gen.tap_on("play")
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
        self.gen.tap_on("search"); time.sleep(0.5)
        self.bridge.type_text(query); time.sleep(0.3)
        self.bridge.press_key(66); time.sleep(1.0)
        return self.loop.execute_with_retry(
            "verify_search", lambda: None,
            lambda: self.judge.capture_screen(), expected={"min_new_elements": 0}
        )

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
                    print("   insights")
                    continue
                if ui.lower() == "insights":
                    for i in self.observer.get_insights():
                        print(f"   🧠 {i}")
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