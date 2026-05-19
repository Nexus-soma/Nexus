"""
Nexus Graph Queries
Multi-hop reasoning: "What should I cook?" → exclude allergens
Inspired by the Knowledge Graph demo's Cypher queries.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.knowledge_graph import NexusGraph


class GraphQueries:
    """Multi-hop reasoning queries for the Nexus Knowledge Graph."""
    
    def __init__(self, graph: NexusGraph = None):
        self.graph = graph or NexusGraph()
    
    def suggest_place(self, person: str) -> list:
        """Suggest places based on preferences."""
        places = []
        for neighbor in self.graph.G.neighbors(person):
            edge = self.graph.G.edges[person, neighbor]
            if edge.get("relation") == "likes" and edge.get("category"):
                places.append({
                    "name": neighbor,
                    "category": edge.get("category"),
                    "confidence": edge.get("confidence", 0.5)
                })
        return sorted(places, key=lambda p: p["confidence"], reverse=True)
    
    def suggest_app(self, person: str, category: str) -> str | None:
        """Suggest an app by category."""
        return self.graph.get_preferred_app(person, category)
    
    def who_to_message(self, person: str) -> list:
        """Who does this person message most?"""
        contacts = []
        for neighbor in self.graph.G.neighbors(person):
            edge = self.graph.G.edges[person, neighbor]
            if edge.get("relation") == "messages":
                contacts.append({
                    "name": neighbor,
                    "frequency": edge.get("frequency", 0),
                    "app": edge.get("app", "whatsapp")
                })
        return sorted(contacts, key=lambda c: c["frequency"], reverse=True)
    
    def what_to_do(self, person: str, day: str = None, time: str = None) -> list:
        """Suggest activities based on routines."""
        routines = self.graph.get_routines(person, day)
        return routines
    
    def find_relationship(self, person: str, target: str) -> str | None:
        """Find how two people are connected."""
        for neighbor in self.graph.G.neighbors(person):
            edge = self.graph.G.edges[person, neighbor]
            if neighbor == target:
                return edge.get("relation")
        return None


# ─── Test ──────────────────────────────────────────
if __name__ == "__main__":
    queries = GraphQueries()
    
    # Add some places
    queries.graph.add_place = lambda name, **attrs: queries.graph.G.add_node(name, type="place", **attrs)
    queries.graph.add_edge = queries.graph.G.add_edge
    
    queries.graph.add_place("Java House", category="coffee", location="CBD")
    queries.graph.add_place("Artcaffe", category="coffee", location="Westlands")
    queries.graph.G.add_edge("Kip", "Java House", relation="likes", category="coffee", confidence=0.9)
    queries.graph.G.add_edge("Kip", "Artcaffe", relation="likes", category="coffee", confidence=0.5)
    
    print("☕ Coffee places:", queries.suggest_place("Kip"))
    print("🎵 Music app:", queries.suggest_app("Kip", "music"))
    print("💬 Frequent contacts:", queries.who_to_message("Kip"))