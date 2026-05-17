"""
Nexus Brain Orchestrator (Hybrid Mode)
Fast keyword matching for common commands + Qwen2.5 LLM fallback.
Dynamic TPM reads the phone screen in real-time.
Instant for known patterns, smart for variations.
"""

import json
import subprocess
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phone_bridge.bridge import PhoneBridge
from phone_bridge.actions import PhoneActions


class NexusOrchestrator:
    """Hybrid command executor with LLM fallback."""

    def __init__(self, phone_ip: str = None, phone_port: str = None, user_name: str = "builder"):
        self.user_name = user_name
        self.bridge = PhoneBridge()
        self.actions = PhoneActions(self.bridge)
        self.connected = False
        self.llm_model = "qwen2.5:0.5b"

        if phone_ip and phone_port:
            self.bridge.device_ip = phone_ip
            if self.bridge.connect(port=phone_port):
                self.connected = True

    def _startup_greeting(self):
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        print("\n" + "━" * 50)
        print(f"   🌌  N E X U S")
        print(f"   {greeting}, {self.user_name}.")
        if self.connected:
            battery = self.bridge.get_battery_level()
            print(f"   📱 Phone connected. Battery: {battery}%")
        print(f"   ⚡ Hybrid mode — fast + smart")
        print(f"   Type 'help' for commands, 'exit' to leave.")
        print("━" * 50)
        print(f"   I'm here. What do you need?\n")

    def _llm_think(self, user_input: str) -> dict | None:
        """Use Qwen2.5 to understand the command. Returns tool call dict or None."""
        prompt = f"""You are a phone agent. You have these tools:
- send_whatsapp(contact, message)
- write_note(title, content)
- search_youtube(query)
- open_app(app_name)
- go_home()
- go_back()
- call_number(number)
- screenshot()

User says: "{user_input}"

Respond with ONLY JSON. No other text.
Format: {{"tool": "tool_name", "params": {{"param_name": "value"}}}}"""

        try:
            result = subprocess.run(
                ["ollama", "run", self.llm_model, prompt],
                capture_output=True, text=True, timeout=15
            )
            response = result.stdout.strip()

            if not response.startswith("{"):
                start = response.find("{")
                if start != -1:
                    response = response[start:]
            if response.endswith("}}"):
                response = response[:-1]

            return json.loads(response)
        except Exception:
            return None

    def _llm_execute(self, tool_call: dict):
        """Execute a tool call from the LLM."""
        tool = tool_call.get("tool", "")
        params = tool_call.get("params", {})

        print(f"   🤖 LLM: {tool}({params})")

        if tool == "send_whatsapp":
            return self.actions.send_whatsapp(params.get("contact", ""), params.get("message", ""))
        elif tool == "write_note":
            return self.actions.write_note(params.get("title", ""), params.get("content", ""))
        elif tool == "search_youtube":
            return self.actions.search_youtube(params.get("query", ""))
        elif tool == "open_app":
            return self.actions.open_app(params.get("app_name", ""))
        elif tool == "go_home":
            return self.actions.go_home()
        elif tool == "go_back":
            return self.actions.go_back()
        elif tool == "call_number":
            return self.actions.call_number(params.get("number", ""))
        elif tool == "screenshot":
            self.bridge.screenshot("nexus_screenshot.png")
            print("   📸 Screenshot saved.")
            return True
        return False

    def execute(self, user_input: str):
        """Parse and execute user command. Fast path first, LLM fallback."""
        text = user_input.lower().strip()

        # ─── FAST PATH: Keyword Matching ────────────
        result = self._fast_match(text)
        if result is True:
            return

        # ─── SLOW PATH: LLM Fallback ────────────────
        print("   🤔 Thinking...")
        tool_call = self._llm_think(user_input)

        if tool_call and tool_call.get("tool"):
            self._llm_execute(tool_call)
            print("   ✅ Done.")
        else:
            print(f"   ❓ Not sure what you mean.")
            print(f"   💡 Try: send mum a whatsapp saying hello")
            print(f"   💡 Try: open spotify")
            print(f"   💡 Try: search youtube for arch linux")

    def _fast_match(self, text: str):
        """Try fast keyword matching. Returns True if handled, None if no match."""

        # ─── WHATSAPP ──────────────────────────
        if any(w in text for w in ["whatsapp", "wp"]):
            send_words = ["send", "text", "msg", "message", "tell"]
            if any(s in text for s in send_words):
                words = text.split()
                contact = None
                message = None
                
                filler = ["send", "text", "msg", "message", "tell", "a", "to", "on", "in", "the"]
                
                for i, word in enumerate(words):
                    if word in send_words:
                        for j in range(i+1, len(words)):
                            if words[j] not in filler and words[j] not in ["whatsapp", "wp", "saying", "that"]:
                                contact = words[j].capitalize()
                                rest = " ".join(words[j+1:])
                                for sep in ["saying", "that"]:
                                    if sep in rest:
                                        message = rest.split(sep, 1)[1].strip()
                                        break
                                if not message:
                                    message = rest
                                break
                        break
                
                if contact:
                    print(f"   📱 WhatsApp → {contact}: \"{message or 'hello'}\"")
                    self.actions.send_whatsapp(contact, message or "hello")
                    return True

        # ─── NOTES ─────────────────────────────
        if any(w in text for w in ["note", "notes"]) and any(w in text for w in ["write", "create", "new", "add", "take"]):
            title = None
            content = ""
            
            if "called" in text:
                parts = text.split("called", 1)[1]
                if "with" in parts:
                    title_part, content = parts.split("with", 1)
                    title = title_part.strip()
                    content = content.strip()
                elif "saying" in parts:
                    title_part, content = parts.split("saying", 1)
                    title = title_part.strip()
                    content = content.strip()
                else:
                    title = parts.strip()
            
            if title:
                print(f"   📝 Note: '{title}'")
                self.actions.write_note(title, content)
                return True

        # ─── YOUTUBE ────────────────────────────
        if any(w in text for w in ["youtube", "play", "search", "find", "video"]) and \
           not any(w in text for w in ["whatsapp", "note", "call"]):
            query = text
            prefixes = ["search youtube for", "youtube", "play", "search for", 
                       "find", "earch youtube for", "earch", "video of", "play on youtube"]
            for prefix in prefixes:
                if prefix in text:
                    query = text.split(prefix, 1)[1].strip()
                    break
            
            if query and query != text:
                print(f"   ▶️  YouTube: '{query}'")
                self.actions.search_youtube(query)
                return True

        # ─── NAVIGATION ─────────────────────────
        if text in ["home", "go home", "home screen", "go to home"]:
            self.actions.go_home()
            return True

        if text in ["back", "go back", "press back", "previous"]:
            self.actions.go_back()
            return True

        if "notification" in text:
            self.actions.open_notifications()
            return True

        # ─── CALLING ────────────────────────────
        if text.startswith("call ") or text.startswith("dial "):
            number = text.replace("call ", "").replace("dial ", "").strip()
            print(f"   📞 Dialing {number}")
            self.actions.call_number(number)
            return True

        # ─── OPEN APPS ──────────────────────────
        open_prefixes = ["open ", "pen ", "opn ", "launch ", "start "]
        for prefix in open_prefixes:
            if text.startswith(prefix):
                app = text.replace(prefix, "").strip()
                print(f"   📱 Opening {app}")
                self.actions.open_app(app)
                return True

        # ─── SCREENSHOT ─────────────────────────
        if "screenshot" in text or "screen shot" in text:
            self.bridge.screenshot("nexus_screenshot.png")
            print("   📸 Screenshot saved.")
            return True

        # ─── NO FAST MATCH ──────────────────────
        return None

    def chat(self):
        """Interactive chat loop."""
        self._startup_greeting()

        while True:
            try:
                user_input = input(f"🧑 {self.user_name}: ").strip()
                if not user_input:
                    continue
                if user_input.lower() == "exit":
                    print(f"👋 See you soon, {self.user_name}.")
                    break
                if user_input.lower() == "help":
                    print("""
   ┌──────────────────────────────────────────────┐
   │  ⚡ HYBRID COMMANDS:                         │
   │                                              │
   │  💬 WHATSAPP:                                │
   │  send mum a whatsapp saying hello            │
   │  tell dad on whatsapp I'm coming             │
   │  message John on whatsapp hey                │
   │                                              │
   │  📝 NOTES:                                   │
   │  write a note called shopping list           │
   │  create a note called ideas with content AI  │
   │                                              │
   │  ▶️  YOUTUBE:                                │
   │  search youtube for arch linux               │
   │  find nexus ai on youtube                    │
   │                                              │
   │  🏠 NAVIGATION:                              │
   │  home / back / notifications                 │
   │                                              │
   │  📱 APPS:                                    │
   │  open spotify / launch youtube               │
   │  start brave / pen chrome                    │
   │                                              │
   │  📞 CALLING:                                 │
   │  call 0790969643                             │
   │                                              │
   │  📸 OTHER:                                   │
   │  screenshot                                  │
   │                                              │
   │  🧠 Smart fallback for unknown commands      │
   └──────────────────────────────────────────────┘
                    """)
                    continue

                self.execute(user_input)

            except KeyboardInterrupt:
                print(f"\n👋 Catch you later, {self.user_name}.")
                break
            except Exception as e:
                print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3:
        phone_ip = sys.argv[1]
        phone_port = sys.argv[2]
    else:
        phone_ip = input("📱 Enter phone IP: ").strip()
        phone_port = input("📱 Enter phone port: ").strip()

    user_name = input("👤 What should I call you? ").strip()
    if not user_name:
        user_name = "builder"

    nexus = NexusOrchestrator(phone_ip, phone_port, user_name)
    nexus.chat()