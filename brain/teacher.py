"""
Nexus Teacher Agent
Watches actions, detects failures, analyzes why, and teaches the system to improve.
Uses LLM for screen analysis and self-correction.
"""

import sys
import os
import json
import time
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TeacherAgent:
    """
    Watches actions, detects failures, teaches the system.
    - Analyzes before/after screen states
    - Uses LLM to understand what went wrong
    - Updates phone_map.json with corrected roles
    - Updates learned_patterns.json with verified coordinates
    """

    def __init__(self, llm_model: str = "qwen2.5:0.5b"):
        self.llm_model = llm_model
        self.lessons_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "phone_bridge", "teacher_lessons.json"
        )
        self.lessons = self._load_lessons()

    def _load_lessons(self) -> list:
        if os.path.exists(self.lessons_path):
            try:
                with open(self.lessons_path) as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_lessons(self):
        with open(self.lessons_path, "w") as f:
            json.dump(self.lessons, f, indent=2)

    def analyze_failure(self, action_name: str, app: str, 
                        before_elements: list, after_elements: list,
                        expected: str, actual: str) -> dict:
        """
        Analyze WHY an action failed and suggest a fix.
        
        Returns:
            {"diagnosis": "...", "fix_type": "role_update|coordinate_update|new_element",
             "details": {...}}
        """
        
        # Quick analysis without LLM (fast path)
        diagnosis = self._quick_analyze(action_name, before_elements, after_elements, expected)
        if diagnosis:
            return diagnosis

        # Deep analysis with LLM (slow path)
        return self._llm_analyze(action_name, before_elements, after_elements, expected, actual)

    def _quick_analyze(self, action_name, before_elements, after_elements, expected) -> dict | None:
        """Fast analysis without LLM."""
        
        # Check 1: Wrong element with same role
        before_labels = [e.get("label", "") for e in before_elements[:20]]
        after_labels = [e.get("label", "") for e in after_elements[:20]]
        
        if expected in before_labels and expected in after_labels:
            return {
                "diagnosis": f"Element '{expected}' was present but action didn't change screen. May need different approach.",
                "fix_type": "alternative_action",
                "confidence": 0.7
            }

        # Check 2: Element not found at all
        if expected not in before_labels and expected not in after_labels:
            return {
                "diagnosis": f"Element '{expected}' not found on screen. App may have updated.",
                "fix_type": "re_explore",
                "confidence": 0.9
            }

        return None

    def _llm_analyze(self, action_name, before_elements, after_elements, expected, actual) -> dict:
        """Deep analysis using LLM."""
        
        prompt = f"""An AI agent tried to '{action_name}' on an Android app but failed.

EXPECTED: {expected}
ACTUAL RESULT: {actual}

BEFORE elements (first 10): {before_elements[:10]}
AFTER elements (first 10): {after_elements[:10]}

What went wrong? What should the agent do differently next time?
Respond with JSON:
{{"diagnosis": "brief explanation", "fix_type": "role_update|coordinate_update|re_explore|alternative_action", "suggestion": "what to do instead"}}"""

        try:
            result = subprocess.run(
                ["ollama", "run", self.llm_model, prompt],
                capture_output=True, text=True, timeout=15
            )
            response = result.stdout.strip()
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except:
            pass

        return {
            "diagnosis": "LLM analysis failed. Defaulting to re-explore.",
            "fix_type": "re_explore",
            "confidence": 0.5
        }

    def teach(self, app: str, action_name: str, analysis: dict, 
              correct_element: dict = None):
        """
        Apply the fix based on analysis.
        Updates phone map, learned patterns, and lessons log.
        """
        lesson = {
            "timestamp": datetime.now().isoformat(),
            "app": app,
            "action": action_name,
            "analysis": analysis,
            "applied_fix": None,
        }

        fix_type = analysis.get("fix_type", "re_explore")

        if fix_type == "re_explore":
            print(f"   📚 Teacher: {app} needs re-exploration. Triggering auto-mapping...")
            lesson["applied_fix"] = "triggered_explorer"
            # The orchestrator's _maybe_refresh_app will handle this

        elif fix_type == "role_update" and correct_element:
            print(f"   📚 Teacher: Updating role for {correct_element.get('label')}...")
            self._update_element_role(app, correct_element)
            lesson["applied_fix"] = "role_updated"

        elif fix_type == "coordinate_update" and correct_element:
            print(f"   📚 Teacher: Updating coordinates for {correct_element.get('label')}...")
            self._update_learned_coordinate(app, action_name, correct_element)
            lesson["applied_fix"] = "coordinate_updated"

        elif fix_type == "alternative_action":
            print(f"   📚 Teacher: Recording alternative approach for {action_name}...")
            lesson["applied_fix"] = "alternative_recorded"

        self.lessons.append(lesson)
        self._save_lessons()
        print(f"   ✅ Teacher: Lesson learned and saved.")

    def _update_element_role(self, app: str, correct_element: dict):
        """Update an element's role in phone_map.json."""
        map_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "phone_bridge", "phone_map.json"
        )
        with open(map_path) as f:
            data = json.load(f)

        app_data = data.get("apps", {}).get(app, {})
        for elem in app_data.get("elements", []):
            if (elem.get("position", {}).get("x") == correct_element.get("x") and
                elem.get("position", {}).get("y") == correct_element.get("y")):
                elem["role"] = correct_element.get("role", elem.get("role"))
                break

        with open(map_path, "w") as f:
            json.dump(data, f, indent=2)

    def _update_learned_coordinate(self, app: str, element: str, correct_element: dict):
        """Update learned coordinate in learned_patterns.json."""
        learned_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "phone_bridge", "learned_patterns.json"
        )
        with open(learned_path) as f:
            data = json.load(f)

        key = f"{app}:{element}"
        data[key] = {
            "successes": 5,
            "failures": 0,
            "x": correct_element.get("x"),
            "y": correct_element.get("y"),
            "confidence": 1.0
        }

        with open(learned_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_lessons_learned(self, limit: int = 10) -> list:
        """Get recent lessons the Teacher has learned."""
        return self.lessons[-limit:]

    def print_lessons(self):
        """Print all lessons learned."""
        if not self.lessons:
            print("   📚 No lessons learned yet.")
            return

        print(f"\n   📚 TEACHER LESSONS ({len(self.lessons)} total)")
        print("   " + "=" * 40)
        for lesson in self.lessons[-5:]:
            ts = lesson["timestamp"][:19]
            app = lesson["app"]
            action = lesson["action"]
            fix = lesson.get("applied_fix", "none")
            diag = lesson.get("analysis", {}).get("diagnosis", "")[:50]
            print(f"   {ts} | {app}:{action} → {fix}")
            if diag:
                print(f"   {diag}")
        print()


# ─── Quick Test ────────────────────────────────────
if __name__ == "__main__":
    teacher = TeacherAgent()
    
    # Simulate a failure
    analysis = teacher.analyze_failure(
        "send_whatsapp",
        "WhatsApp",
        [{"label": "Ask Meta AI or Search"}, {"label": "New chat"}],
        [{"label": "Meta AI chat"}, {"label": "Type a message"}],
        expected="contact_search",
        actual="Meta AI chat opened instead of contact selector"
    )
    
    print("Analysis:", analysis)
    teacher.print_lessons()