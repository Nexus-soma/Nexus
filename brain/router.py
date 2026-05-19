"""
Nexus Router Agent
Decides which app and action based on user command + knowledge graph.
Uses graph for relationship queries: "message my brother" → Derick
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.knowledge_graph import NexusGraph


class RouterDecision:
    def __init__(self, app: str, action: str, target: str = None, confidence: float = 0.0):
        self.app = app
        self.action = action
        self.target = target
        self.confidence = confidence
    
    def to_dict(self) -> dict:
        return {
            "app": self.app, "action": self.action,
            "target": self.target, "confidence": self.confidence
        }
    
    def __repr__(self):
        return f"<Router: {self.app} → {self.action} ({self.target}) confidence={self.confidence:.0%}>"


class RouterAgent:
    """Routes commands using keywords + knowledge graph."""
    
    def __init__(self):
        self.graph = NexusGraph()
        
        self.APP_KEYWORDS = {
            "whatsapp": ["whatsapp", "wp", "message", "text", "send", "tell", "chat"],
            "spotify": ["spotify", "music", "song", "play", "playlist", "liked"],
            "youtube": ["youtube", "video", "watch"],
            "camera": ["camera", "photo", "picture", "selfie", "capture"],
            "brave": ["brave", "browser", "search for", "google", "internet", "web"],
            "notes": ["note", "notes", "write", "create note", "add note"],
            "deriv": ["deriv", "portfolio", "trade", "invest", "balance"],
            "settings": ["settings", "wifi", "bluetooth", "battery saver"],
            "calculator": ["calculator", "calc", "calculate", "math"],
            "clock": ["clock", "alarm", "timer", "time"],
            "instagram": ["instagram", "insta", "ig", "reels"],
            "tiktok": ["tiktok", "tik tok"],
            "telegram": ["telegram", "tg"],
        }
        
        self.ACTION_KEYWORDS = {
            "send_message": ["send", "text", "msg", "message", "tell", "say"],
            "play": ["play", "listen", "start"],
            "search": ["search", "find", "look for", "google"],
            "capture": ["take", "capture", "click", "shoot"],
            "open": ["open", "launch", "start", "go to"],
            "write": ["write", "create", "add", "new"],
            "check": ["check", "show", "view", "see", "what is"],
        }
    
    def route(self, user_command: str, screen_context=None) -> RouterDecision:
        text = user_command.lower().strip()
        
        # Find matching app
        best_app = None
        best_app_score = 0
        for app, keywords in self.APP_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_app_score:
                best_app_score = score
                best_app = app
        
        # Find matching action
        best_action = "open"
        best_action_score = 0
        for action, keywords in self.ACTION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_action_score:
                best_action_score = score
                best_action = action
        
        # Extract target with GRAPH QUERY
        target = self._extract_target(text, best_app, best_action)
        
        # Confidence
        confidence = min(best_app_score / 3.0, 1.0) if best_app else 0.0
        
        return RouterDecision(
            app=best_app or "unknown",
            action=best_action,
            target=target,
            confidence=confidence
        )
    
    def _extract_target(self, text: str, app: str, action: str) -> str:
        """Extract target using graph for relationship queries."""
        words = text.split()
        
        # TRY GRAPH: "my brother" → query graph → "Derick"
        relationship_words = ["brother", "sister", "mum", "mom", "dad", "friend", "family"]
        for i, word in enumerate(words):
            if word in relationship_words:
                if i > 0 and words[i-1] == "my":
                    rel = word
                    result = self.graph.who_is("Kip", rel)
                    if result:
                        return result
        
        # TRY GRAPH: "my mum" → query graph → "Mum"
        if "my" in words:
            for i, word in enumerate(words):
                if word == "my" and i+1 < len(words):
                    potential_rel = words[i+1]
                    result = self.graph.who_is("Kip", potential_rel)
                    if result:
                        return result
        
        # Extract from text (original logic)
        if app == "whatsapp" and action == "send_message":
            skip = ["send", "text", "msg", "message", "tell", "a", "to", "on", "in",
                    "whatsapp", "wp", "saying", "that", "the", "my", "hello", "hi", "hey"]
            for word in words:
                if word not in skip and word not in relationship_words:
                    return word.capitalize()
        
        if action == "search":
            for prefix in ["search for ", "find ", "google ", "search youtube for "]:
                if prefix in text:
                    return text.split(prefix, 1)[1].strip()
        
        if action == "play":
            if "play " in text:
                rest = text.split("play ", 1)[1]
                for w in ["on spotify", "on youtube", "my ", "the "]:
                    rest = rest.replace(w, "")
                return rest.strip()
        
        return None


# ─── Test ──────────────────────────────────────────
if __name__ == "__main__":
    print("🎯 Router + Knowledge Graph Test\n")
    
    router = RouterAgent()
    
    tests = [
        "message my brother",
        "tell my mum hello on whatsapp",
        "message my friend",
        "play a song",
        "search youtube for AI",
        "open instagram",
    ]
    
    for cmd in tests:
        decision = router.route(cmd)
        print(f"   🧑: {cmd}")
        print(f"   🎯: {decision}")
        print()