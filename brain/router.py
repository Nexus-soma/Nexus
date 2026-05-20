"""
Nexus Router Agent (Phone Map Powered)
No hardcoded apps. Reads phone_map.json for all available apps.
Uses knowledge graph for relationship queries.
Router file stays static — phone_map.json is the dynamic part.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.knowledge_graph import NexusGraph


class RouterDecision:
    def __init__(self, app: str, action: str, target: str = None, confidence: float = 0.0):
        self.app = app
        self.action = action
        self.target = target
        self.confidence = confidence
    
    def to_dict(self) -> dict:
        return {"app": self.app, "action": self.action, "target": self.target, "confidence": self.confidence}
    
    def __repr__(self):
        return f"<Router: {self.app} → {self.action} ({self.target}) confidence={self.confidence:.0%}>"


class RouterAgent:
    """Routes commands using phone map + knowledge graph. File stays static."""
    
    def __init__(self, user_name: str = "Kip"):
        self.graph = NexusGraph()
        self.phone_map = self._load_phone_map()
        self.user_name = user_name
    
    def _load_phone_map(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                           "phone_bridge", "phone_map.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {"apps": {}}
    
    def route(self, user_command: str, screen_context=None) -> RouterDecision:
        text = user_command.lower().strip()
        
        app = self._find_app(text)
        action = self._find_action(text)
        
        # Default: if searching but no app found, use YouTube
        if action == "search" and app == "unknown":
            app = "YouTube"
        
        # Default: messaging → WhatsApp
        if action == "send_message" and app == "unknown":
            app = "WhatsApp"
        
        target = self._extract_target(text, app, action)
        
        # Resolve relationships via graph
        if target:
            for rel in ["brother", "sister", "mum", "mom", "dad", "friend"]:
                if target.lower() == f"my {rel}" or target.lower() == rel:
                    resolved = self.graph.who_is(self.user_name.capitalize(), rel)
                    if resolved:
                        target = resolved
                        break
        
        confidence = 0.8 if app != "unknown" else 0.0
        return RouterDecision(app=app, action=action, target=target, confidence=confidence)
    
    def _find_app(self, text: str) -> str:
        """Find app from aliases + phone map. No hardcoded app list."""
        text_lower = text.lower()
        
        # Aliases for common names that might not match phone map exactly
        ALIASES = {
            "calendar": "Calendar", "calender": "Calendar", "schedule": "Calendar",
            "picture": "Camera", "photo": "Camera", "selfie": "Camera",
            "note": "Notes", "notes": "Notes",
            "portfolio": "Deriv", "trade": "Deriv", "invest": "Deriv",
            "music": "Spotify", "song": "Spotify", "playlist": "Spotify",
            "video": "YouTube", "videos": "YouTube", "youtube": "YouTube",
            "whatsapp": "WhatsApp", "wp": "WhatsApp",
            "browser": "Brave", "internet": "Brave", "chrome": "Brave",
            "camera": "Camera", "deriv": "Deriv", "spotify": "Spotify",
            "brave": "Brave", "settings": "Settings", "clock": "Clock",
            "calculator": "Calculator", "gallery": "Gallery", "photos": "Gallery",
            "files": "FileManager", "messages": "Messages", "sms": "Messages",
            "dialer": "Dialer", "phone": "Dialer", "call": "Dialer",
            "instagram": "Instagram", "insta": "Instagram",
            "telegram": "Telegram", "tg": "Telegram",
            "tiktok": "TikTok", "discord": "Discord",
            "facebook": "Facebook", "fb": "Facebook",
            "snapchat": "Snapchat", "twitter": "Twitter", "x": "Twitter",
            "sim toolkit": "STK", "sim": "STK", "stk": "STK",
            
        }
        
        # Phone map check first (exact app names)
        for app_name in self.phone_map.get("apps", {}):
            if app_name.lower() in text_lower:
                return app_name
        
        # Aliases second (common names)
        for alias, app_name in ALIASES.items():
            if alias in text_lower:
                return app_name
        
        return "unknown"
    
    def _find_action(self, text: str) -> str:
        """Find action from keywords."""
        
        # Explicit "open" commands
        if text.startswith("open ") or text.startswith("launch ") or text.startswith("start "):
            return "open"
        
        # Action keywords
        ACTIONS = {
            "send_message": ["send", "text", "msg", "message", "tell", "say"],
            "play": ["play", "listen", "hear"],
            "search": ["search", "find", "look for", "google", "show me", "how to", "videos of"],
            "capture": ["take", "capture", "click", "shoot", "picture", "photo", "selfie"],
            "write": ["write", "create", "add", "new", "note"],
            "check": ["check", "show", "view", "see", "what is", "whats my", "portfolio", "balance"],
        }
        
        best_action = "open"
        best_score = 0
        for action, keywords in ACTIONS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_action = action
        
        return best_action
    
    def _extract_target(self, text: str, app: str, action: str) -> str:
        """Extract target from command."""
        
        if action == "send_message":
            skip = ["send", "text", "msg", "message", "tell", "a", "to", "on", "in",
                    "whatsapp", "wp", "saying", "that", "the", "my", "hello", "hi", "hey", "it"]
            for word in text.split():
                if word not in skip and not word.startswith("what"):
                    return word.capitalize()
        
        if action == "search":
            for prefix in ["search for ", "search ", "find ", "look for ", "show me ", "how to ", "videos of "]:
                if prefix in text:
                    rest = text.split(prefix, 1)[1].strip()
                    # Clean up app names from the target
                    for app_name in ["youtube", "brave", "chrome", "google"]:
                        if rest.startswith(app_name):
                            rest = rest[len(app_name):].strip()
                            if rest.startswith("for "):
                                rest = rest[4:].strip()
                    return rest if rest else None
            # If app name is in text, extract what comes after it
            app_lower = app.lower()
            if app_lower in text:
                parts = text.split(app_lower, 1)
                if len(parts) > 1:
                    rest = parts[1].strip()
                    for w in ["for ", "about ", "on "]:
                        if rest.startswith(w):
                            rest = rest[len(w):]
                    if rest and rest not in ["a", "an", "the"]:
                        return rest
        
        if action == "play":
            if "play " in text:
                rest = text.split("play ", 1)[1]
                for w in ["on spotify", "on youtube", "my ", "the ", "a "]:
                    rest = rest.replace(w, "")
                return rest.strip() if rest.strip() else None
        
        if action == "write":
            if "called " in text:
                return text.split("called ", 1)[1].strip()
            if "write " in text:
                rest = text.split("write ", 1)[1]
                for w in ["a ", "an ", "note "]:
                    if rest.startswith(w):
                        rest = rest[len(w):]
                return rest.strip() if rest.strip() else None
        
        return None


# ─── Test ──────────────────────────────────────────
if __name__ == "__main__":
    print("🎯 Router (Phone Map Powered)\n")
    router = RouterAgent()
    print(f"   📱 {len(router.phone_map.get('apps', {}))} apps in phone map\n")
    
    tests = [
        "open calendar",
        "search how to rebuild cars",
        "search youtube for AI",
        "open youtube and search for music",
        "take a picture",
        "write a note called ideas",
        "check my portfolio",
        "play music",
        "tell mum on whatsapp hello",
        "send message to my brother",
        "open camera",
        "search for cooking videos",
    ]
    
    for cmd in tests:
        d = router.route(cmd)
        print(f"   🧑: {cmd}")
        print(f"   🎯: {d}")
        print()