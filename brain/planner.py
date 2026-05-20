"""
Nexus Planner Agent
Splits multi-step commands into individual actions.
"open youtube and search for AI" → [open YouTube, search AI]
Reuses existing Router for each step.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.router import RouterAgent, RouterDecision


class PlannerAgent:
    """
    Breaks compound commands into sequential steps.
    Works with ANY app — no hardcoding.
    """
    
    def __init__(self, user_name: str = "Kip"):
        self.router = RouterAgent(user_name=user_name)
    
    def plan(self, command: str) -> list[RouterDecision]:
        """
        Split a command into individual steps.
        
        Args:
            command: Full user command
        
        Returns:
            List of RouterDecision objects, one per step
        """
        text = command.lower().strip()

        # Split on common connectors
        separators = [" and ", " then ", " after that ", " afterwards "]
        parts = [text]

        for sep in separators:
            new_parts = []
            for part in parts:
                new_parts.extend(part.split(sep))
            parts = new_parts

        # Clean up each part
        parts = [p.strip() for p in parts if p.strip()]

        # Route each part individually, carry forward last opened app
        steps = []
        last_app = None

        for part in parts:
            decision = self.router.route(part)

            # If this step has no app but the previous step opened one, use it
            if decision.app == "unknown" and last_app:
                decision.app = last_app

            if decision.app != "unknown":
                steps.append(decision)
                last_app = decision.app

        return steps
    
    def has_multiple_steps(self, command: str) -> bool:
        """Check if a command has multiple steps."""
        connectors = [" and ", " then ", " after that "]
        return any(conn in command.lower() for conn in connectors)


# ─── Test ──────────────────────────────────────────
if __name__ == "__main__":
    print("📋 Planner Agent Test\n")
    
    planner = PlannerAgent(user_name="kip")
    
    tests = [
        "open youtube and search for AI",
        "write a note called shopping and send it to mum",
        "take a photo and open gallery",
        "open calendar",
        "search youtube for cooking videos then open notes",
    ]
    
    for cmd in tests:
        print(f"🧑: {cmd}")
        if planner.has_multiple_steps(cmd):
            steps = planner.plan(cmd)
            print(f"   📋 {len(steps)} steps:")
            for i, step in enumerate(steps):
                print(f"   {i+1}. {step.app} → {step.action}" + 
                      (f" ({step.target})" if step.target else ""))
        else:
            decision = planner.router.route(cmd)
            print(f"   🎯 Single: {decision.app} → {decision.action}")
        print()
