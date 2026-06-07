import time
from datetime import datetime

class ApprovalGate:
    def __init__(self, auto_timeout: int = 30):
        self.auto_timeout = auto_timeout
        self.history = []
    
    def ask(self, action_description: str, timeout: int = None) -> bool:
        timeout = timeout or self.auto_timeout
        print(f"\n   ╔══════════════════════════════════╗")
        print(f"   ║  NEXUS NEEDS APPROVAL           ║")
        print(f"   ╠══════════════════════════════════╣")
        print(f"   ║  {action_description[:35]:<32s} ║")
        print(f"   ║  Auto-deny in {timeout}s              ║")
        print(f"   ╚══════════════════════════════════╝")
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = input("   Approve? (y/n): ").strip().lower()
            if response in ["y", "yes"]:
                self._log(action_description, True)
                print("   Approved.")
                return True
            if response in ["n", "no"]:
                self._log(action_description, False)
                print("   Denied.")
                return False
        self._log(action_description, False, timed_out=True)
        print("   Timed out. Auto-denied.")
        return False
    
    def _log(self, action: str, approved: bool, timed_out: bool = False):
        self.history.append({"timestamp": datetime.now().isoformat(), "action": action, "approved": approved, "timed_out": timed_out})
    
    def get_history(self, limit: int = 10) -> list:
        return self.history[-limit:]
