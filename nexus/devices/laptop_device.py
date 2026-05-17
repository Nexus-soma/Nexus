"""
Nexus Laptop Device
Basic laptop control through shell commands.
"""
import subprocess, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nexus.devices.base import NexusDevice

class LaptopDevice(NexusDevice):
    def __init__(self, name="laptop"):
        super().__init__(name, "laptop")
        self.capabilities = ["shell","open_app","open_file","create_file","read_file","system_info","notifications"]
    def connect(self):
        self.connected = True
        return True
    def read(self):
        try:
            mem = subprocess.run(["free","-h"], capture_output=True, text=True).stdout
            disk = subprocess.run(["df","-h","/"], capture_output=True, text=True).stdout
            up = subprocess.run(["uptime","-p"], capture_output=True, text=True).stdout.strip()
            return {"hostname": os.uname().nodename, "uptime": up, "memory": mem.strip().split("\n")[1] if mem else "?", "disk": disk.strip().split("\n")[1] if disk else "?", "user": os.getenv("USER")}
        except Exception as e:
            return {"error": str(e)}
    def act(self, action, params=None):
        params = params or {}
        try:
            if action == "shell":
                print(subprocess.run(params["command"], shell=True, capture_output=True, text=True).stdout)
            elif action == "open_app":
                subprocess.Popen([params["app_name"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"   💻 Opened {params['app_name']}")
            elif action == "notify":
                subprocess.run(["notify-send", params.get("title","Nexus"), params.get("message","")])
            elif action == "create_file":
                os.makedirs(os.path.dirname(params["path"]) or ".", exist_ok=True)
                with open(params["path"],"w") as f: f.write(params.get("content",""))
                print(f"   📝 Created {params['path']}")
            elif action == "system_info":
                for k,v in self.read().items(): print(f"   {k}: {v}")
            else:
                print(f"   ❌ Unknown: {action}")
                return False
            return True
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False
