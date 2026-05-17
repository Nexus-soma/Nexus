"""
Nexus Device Registry
Central manager for all connected devices.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nexus.devices.base import NexusDevice
from nexus.devices.phone_device import PhoneDevice
from nexus.devices.laptop_device import LaptopDevice

class NexusRegistry:
    def __init__(self):
        self.devices = {}
    def add_device(self, device):
        if device.connect():
            self.devices[device.name] = device
            print(f"   ✅ {device.name} ({device.device_type}) ready")
            return True
        print(f"   ❌ {device.name} failed"); return False
    def get(self, name):
        return self.devices.get(name)
    def list_devices(self):
        return [{"name":d.name,"type":d.device_type,"connected":d.connected} for d in self.devices.values()]
    def perceive_all(self):
        state = {}
        for name, device in self.devices.items():
            try: state[name] = device.read()
            except Exception as e: state[name] = {"error":str(e)}
        return state
    def act(self, device_name, action, params=None):
        device = self.devices.get(device_name)
        if device: return device.act(action, params or {})
        print(f"   ❌ Device '{device_name}' not found"); return False

if __name__ == "__main__":
    registry = NexusRegistry()
    laptop = LaptopDevice("laptop")
    registry.add_device(laptop)
    phone_ip = input("📱 Phone IP: ").strip()
    phone_port = input("📱 Port: ").strip()
    phone = PhoneDevice("phone", phone_ip, phone_port)
    registry.add_device(phone)
    print("\n" + "="*50)
    print("   🌌 NEXUS DEVICE REGISTRY")
    print("="*50)
    print("\n   📋 Connected:")
    for d in registry.list_devices():
        print(f"   {'✅' if d['connected'] else '❌'} {d['name']} ({d['type']})")
    if registry.get("laptop"):
        print("\n   💻 Laptop:")
        for k,v in registry.get("laptop").read().items():
            print(f"      {k}: {v}")
    if registry.get("phone") and registry.get("phone").connected:
        print("\n   📱 Phone:")
        state = registry.get("phone").read()
        print(f"      Battery: {state.get('battery')}%")
        print(f"      Elements: {state.get('clickable_elements')}")
