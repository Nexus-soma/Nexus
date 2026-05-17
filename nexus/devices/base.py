"""
Nexus Generic Device Protocol
Any device can become part of Nexus by implementing:
- connect(): Establish connection
- read(): Return current state
- act(action, params): Perform an action
- disconnect(): Close connection
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class NexusDevice(ABC):
    """
    Base class for any device that joins the Nexus ecosystem.
    Phone, laptop, watch, fridge, camera, drone, TV — anything.
    """

    def __init__(self, name: str, device_type: str):
        self.name = name
        self.device_type = device_type
        self.connected = False
        self.capabilities = []

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the device. Return True if successful."""
        pass

    @abstractmethod
    def read(self) -> Dict[str, Any]:
        """Read the current state of the device."""
        pass

    @abstractmethod
    def act(self, action: str, params: Optional[Dict] = None) -> bool:
        """Perform an action on the device."""
        pass

    def disconnect(self) -> bool:
        """Close connection to the device."""
        self.connected = False
        return True

    def is_available(self) -> bool:
        """Check if device is currently reachable."""
        return self.connected

    def get_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "name": self.name,
            "type": self.device_type,
            "connected": self.connected,
            "capabilities": self.capabilities,
        }

    def __repr__(self):
        status = "✅" if self.connected else "❌"
        return f"<{status} {self.name} ({self.device_type})>"


class DeviceRegistry:
    """
    Central registry for all devices in the Nexus ecosystem.
    The brain queries this to know what's available.
    """

    def __init__(self):
        self.devices: Dict[str, NexusDevice] = {}

    def register(self, device: NexusDevice) -> bool:
        """Add a device to the registry."""
        if device.connect():
            self.devices[device.name] = device
            print(f"   ✅ {device.name} ({device.device_type}) connected")
            return True
        print(f"   ❌ {device.name} failed to connect")
        return False

    def unregister(self, name: str) -> bool:
        """Remove a device."""
        if name in self.devices:
            self.devices[name].disconnect()
            del self.devices[name]
            return True
        return False

    def get(self, name: str) -> Optional[NexusDevice]:
        """Get a device by name."""
        return self.devices.get(name)

    def get_by_type(self, device_type: str) -> list[NexusDevice]:
        """Get all devices of a specific type."""
        return [d for d in self.devices.values() if d.device_type == device_type]

    def list_all(self) -> list[str]:
        """List all connected device names."""
        return list(self.devices.keys())

    def perceive_all(self) -> Dict[str, Any]:
        """Read state from ALL connected devices."""
        state = {}
        for name, device in self.devices.items():
            try:
                state[name] = {
                    "info": device.get_info(),
                    "state": device.read(),
                }
            except Exception as e:
                state[name] = {"error": str(e)}
        return state

    def act_on(self, device_name: str, action: str, params: Optional[Dict] = None) -> bool:
        """Perform an action on a specific device."""
        device = self.devices.get(device_name)
        if device:
            return device.act(action, params or {})
        return False