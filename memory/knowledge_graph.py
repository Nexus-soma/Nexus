"""
Nexus Knowledge Graph
NetworkX-based graph for people, apps, routines, preferences.
Enables multi-hop reasoning: "Who is my brother?" → Derick
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import networkx as nx
except ImportError:
    print("Installing networkx...")
    os.system("pip install networkx")
    import networkx as nx


class NexusGraph:
    """Knowledge graph for Nexus — relationships, preferences, routines."""
    
    def __init__(self, graph_path: str = None):
        if graph_path is None:
            graph_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nexus_graph.json")
        self.graph_path = graph_path
        self.G = nx.DiGraph()
        self._load()
    
    def _load(self):
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path) as f:
                    data = json.load(f)
                self.G = nx.node_link_graph(data)
            except:
                pass
    
    def _save(self):
        data = nx.node_link_data(self.G)
        with open(self.graph_path, "w") as f:
            json.dump(data, f, indent=2)
    
    # ─── PEOPLE ────────────────────────────────
    
    def add_person(self, name: str, **attrs):
        self.G.add_node(name, type="person", **attrs)
        self._save()
    
    def add_relationship(self, person1: str, person2: str, relation: str):
        self.G.add_edge(person1, person2, relation=relation)
        self._save()
    
    def find_by_relationship(self, person: str, relation: str) -> list:
        """Find people connected by a specific relationship."""
        results = []
        for neighbor in self.G.neighbors(person):
            edge = self.G.edges[person, neighbor]
            if edge.get("relation") == relation:
                results.append(neighbor)
        return results
    
    def who_is(self, person: str, relationship: str) -> str | None:
        """Who is my brother? → Derick"""
        results = self.find_by_relationship(person, relationship)
        return results[0] if results else None
    
    # ─── APPS ──────────────────────────────────
    
    def add_app_usage(self, person: str, app: str, **attrs):
        self.G.add_edge(person, app, relation="uses", **attrs)
        self._save()
    
    def get_preferred_app(self, person: str, category: str = None) -> str | None:
        """Get preferred app by category."""
        for neighbor in self.G.neighbors(person):
            edge = self.G.edges[person, neighbor]
            if edge.get("relation") == "uses":
                if category and edge.get("category") == category:
                    return neighbor
                elif not category:
                    return neighbor
        return None
    
    # ─── ROUTINES ──────────────────────────────
    
    def add_routine(self, person: str, routine_name: str, **attrs):
        self.G.add_edge(person, routine_name, relation="has_routine", **attrs)
        self._save()
    
    def get_routines(self, person: str, day: str = None) -> list:
        routines = []
        for neighbor in self.G.neighbors(person):
            edge = self.G.edges[person, neighbor]
            if edge.get("relation") == "has_routine":
                if day and edge.get("day") == day:
                    routines.append({"name": neighbor, **edge})
                elif not day:
                    routines.append({"name": neighbor, **edge})
        return routines
    
    # ─── PREFERENCES ───────────────────────────
    
    def add_preference(self, person: str, key: str, value: str):
        node_name = f"pref_{key}"
        self.G.add_edge(person, node_name, relation="prefers", key=key, value=value)
        self._save()
    
    def get_preference(self, person: str, key: str) -> str | None:
        for neighbor in self.G.neighbors(person):
            edge = self.G.edges[person, neighbor]
            if edge.get("relation") == "prefers" and edge.get("key") == key:
                return edge.get("value")
        return None
    
    # ─── QUERIES ───────────────────────────────
    
    def query(self, question: str) -> str | None:
        """Simple natural language graph queries."""
        q = question.lower()
        
        # "Who is my brother?"
        if "who is my" in q or "who's my" in q:
            for rel in ["brother", "sister", "mum", "dad", "friend"]:
                if rel in q:
                    return self.who_is("Kip", rel)
        
        # "What app for music?"
        if "app for" in q:
            for cat in ["music", "messaging", "browser", "trading"]:
                if cat in q:
                    return self.get_preferred_app("Kip", cat)
        
        # "What's my routine on Tuesday?"
        if "routine" in q:
            for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                if day in q:
                    routines = self.get_routines("Kip", day)
                    return [r["name"] for r in routines] if routines else None
        
        return None
    
    # ─── STATS ─────────────────────────────────
    
    def stats(self) -> dict:
        return {
            "nodes": self.G.number_of_nodes(),
            "edges": self.G.number_of_edges(),
            "people": len([n for n in self.G.nodes if self.G.nodes[n].get("type") == "person"]),
        }
    
    def print_graph(self):
        print("\n   🕸️  KNOWLEDGE GRAPH")
        print(f"   Nodes: {self.G.number_of_nodes()}")
        print(f"   Edges: {self.G.number_of_edges()}")
        for u, v, data in self.G.edges(data=True):
            print(f"   {u} --[{data.get('relation', '?')}]--> {v}")


# ─── Test ──────────────────────────────────────────
if __name__ == "__main__":
    graph = NexusGraph()
    
    # Add people
    graph.add_person("Kip", age=22)
    graph.add_person("Mum")
    graph.add_person("Derick")
    graph.add_person("Ak")
    
    # Add relationships
    graph.add_relationship("Kip", "Mum", "family")
    graph.add_relationship("Kip", "Derick", "brother")
    graph.add_relationship("Kip", "Ak", "friend")
    
    # Add app preferences
    graph.add_app_usage("Kip", "Spotify", category="music", frequency="daily")
    graph.add_app_usage("Kip", "WhatsApp", category="messaging", frequency="daily")
    graph.add_app_usage("Kip", "Brave", category="browser", frequency="daily")
    graph.add_app_usage("Kip", "Deriv", category="trading", frequency="weekdays")
    
    # Add routines
    graph.add_routine("Kip", "Gym", day="Tuesday", time="18:00")
    graph.add_routine("Kip", "Trading", day="Weekdays", time="09:00")
    
    # Add preferences
    graph.add_preference("Kip", "browser", "Brave")
    graph.add_preference("Kip", "music", "Spotify")
    
    graph.print_graph()
    
    # Queries
    print(f"\n   Who is my brother? → {graph.query('Who is my brother?')}")
    print(f"   What app for music? → {graph.query('What app for music?')}")
    print(f"   Tuesday routine? → {graph.query('What is my routine on Tuesday?')}")