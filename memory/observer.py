"""
Nexus Observer
Watches what you do and auto-updates the knowledge graph.
Learns preferences, routines, and relationships over time.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.knowledge_graph import NexusGraph
from memory.sqlite_store import NexusMemory


class NexusObserver:
    """Watches actions and learns patterns automatically."""
    
    def __init__(self, graph: NexusGraph = None, memory: NexusMemory = None):
        self.graph = graph or NexusGraph()
        self.memory = memory or NexusMemory()
    
    def observe_action(self, command: str, app: str, action: str, target: str = None, success: bool = True):
        """Observe an action and update graph + memory."""
        
        # Log to SQLite
        self.memory.log_action(command, app, action, target, success)
        
        # Update graph based on action
        if app == "whatsapp" and action == "send_message" and target:
            self._learn_contact(target, "whatsapp")
        
        if app in ["spotify", "youtube"] and action == "play":
            self._learn_app_preference(app, "music")
        
        if app == "brave" and action == "search":
            self._learn_app_preference(app, "browser")
    
    def _learn_contact(self, name: str, app: str):
        """Learn a contact relationship."""
        if name not in self.graph.G.nodes:
            self.graph.add_person(name)
        
        if not self.graph.G.has_edge("Kip", name):
            self.graph.G.add_edge("Kip", name, relation="messages", app=app, frequency=1)
        else:
            edge = self.graph.G.edges["Kip", name]
            edge["frequency"] = edge.get("frequency", 0) + 1
        
        self.graph._save()
    
    def _learn_app_preference(self, app: str, category: str):
        """Learn an app preference."""
        existing = self.graph.get_preferred_app("Kip", category)
        if not existing or existing != app:
            # Remove old preference
            for neighbor in list(self.graph.G.neighbors("Kip")):
                edge = self.graph.G.edges["Kip", neighbor]
                if edge.get("relation") == "uses" and edge.get("category") == category:
                    self.graph.G.remove_edge("Kip", neighbor)
            
            # Add new preference
            self.graph.add_app_usage("Kip", app, category=category, frequency="daily")
            self.graph._save()
    
    def get_insights(self) -> list:
        """Get insights about what Nexus has learned."""
        insights = []
        
        # Frequent contacts
        contacts = self.memory.get_frequent_contacts(3)
        if contacts:
            names = [c["name"] for c in contacts]
            insights.append(f"You message {', '.join(names)} most often.")
        
        # Preferred apps
        for cat in ["music", "browser", "messaging"]:
            app = self.graph.get_preferred_app("Kip", cat)
            if app:
                insights.append(f"Your preferred {cat} app is {app}.")
        
        # Success rate
        rate = self.memory.get_success_rate()
        insights.append(f"My success rate is {rate:.0%}.")
        
        return insights


# ─── Test ──────────────────────────────────────────
if __name__ == "__main__":
    observer = NexusObserver()
    
    # Simulate some actions
    observer.observe_action("tell mum on whatsapp hello", "whatsapp", "send_message", "Mum", True)
    observer.observe_action("play a song", "spotify", "play", None, True)
    observer.observe_action("search youtube for AI", "youtube", "search", "AI", True)
    observer.observe_action("tell Derick on whatsapp hey", "whatsapp", "send_message", "Derick", True)
    
    print("🧠 Nexus Insights:")
    for insight in observer.get_insights():
        print(f"   {insight}")