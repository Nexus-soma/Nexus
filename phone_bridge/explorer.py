"""
Nexus Phone Explorer (TPM Layer 1)
Auto-maps apps on your phone using the screen reader.
Builds phone_map.json with exact coordinates for every interactive element.
Re-run anytime to refresh the map. Auto-detects installed apps.
"""

import json
import time
import os
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phone_bridge.bridge import PhoneBridge
from phone_bridge.screen_reader import ScreenReader


class PhoneExplorer:
    """
    Explores and maps apps on the phone.
    Builds a living coordinate map stored in phone_map.json.
    Auto-detects installed apps and maps them intelligently.
    """

    def __init__(self, bridge: PhoneBridge = None, map_path: str = None):
        self.bridge = bridge or PhoneBridge()
        self.reader = ScreenReader()
        self.map_path = map_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "phone_map.json"
        )
        self.map_data = self._load_map()
        self.installed_packages = self._detect_installed_apps()

    def _load_map(self) -> dict:
        """Load existing map or create new one."""
        if os.path.exists(self.map_path):
            try:
                with open(self.map_path, "r") as f:
                    print(f"   📂 Loaded existing map with {len(json.load(f).get('apps', {}))} apps")
                    f.seek(0)
                    return json.load(f)
            except json.JSONDecodeError:
                print("⚠️  Corrupted map file. Starting fresh.")
        return self._empty_map()

    def _empty_map(self) -> dict:
        """Create a fresh empty map structure."""
        return {
            "device": "unknown",
            "manufacturer": "unknown",
            "model": "unknown",
            "resolution": "unknown",
            "android_version": "unknown",
            "last_updated": None,
            "total_apps_mapped": 0,
            "apps": {},
        }

    def _save_map(self):
        """Save the map to disk."""
        self.map_data["last_updated"] = datetime.now().isoformat()
        self.map_data["total_apps_mapped"] = len(self.map_data["apps"])
        with open(self.map_path, "w") as f:
            json.dump(self.map_data, f, indent=2)
        print(f"   💾 Map saved ({self.map_data['total_apps_mapped']} apps)")

    def _detect_installed_apps(self) -> list:
        """Auto-discover all user-installed third-party packages."""
        result = self.bridge.run_raw("pm list packages -3")
        packages = []
        for line in result.split("\n"):
            if line.startswith("package:"):
                pkg = line.replace("package:", "").strip()
                packages.append(pkg)
        return packages

    def detect_device(self):
        """Detect full device info."""
        self.map_data["model"] = self.bridge.run_raw("getprop ro.product.model").strip()
        self.map_data["manufacturer"] = self.bridge.run_raw("getprop ro.product.manufacturer").strip()
        self.map_data["resolution"] = self.bridge.run_raw("wm size").strip().split(":")[-1].strip()
        self.map_data["android_version"] = self.bridge.run_raw("getprop ro.build.version.release").strip()

        print(f"   📱 {self.map_data['manufacturer']} {self.map_data['model']}")
        print(f"   📐 {self.map_data['resolution']} | Android {self.map_data['android_version']}")
        print(f"   📦 {len(self.installed_packages)} user apps installed")

    def explore_app(self, package_name: str, app_name: str) -> dict:
        """
        Open an app and map all its interactive elements.
        Returns the app's map entry.
        """
        # Check if app is installed
        if package_name not in self.installed_packages:
            print(f"   ⚠️  {app_name} ({package_name}) not installed. Skipping.")
            return {}

        print(f"   🔍 {app_name}...", end=" ", flush=True)

        # Open the app
        self.bridge.open_app(package_name)
        time.sleep(2.0)  # Wait for app to load

        # Read the screen
        elements = self.reader.get_interactive_elements()

        if not elements:
            print("(no elements)")
            self.bridge.press_key(3)  # Go home
            return {}

        # Build screen map
        screen_map = {
            "package": package_name,
            "last_explored": datetime.now().isoformat(),
            "total_elements": len(elements),
            "elements": [],
        }

        labeled_count = 0
        for elem in elements:
            if elem.label and elem.label.strip():
                screen_map["elements"].append({
                    "label": elem.label,
                    "position": {"x": elem.center_x, "y": elem.center_y},
                    "bounds": {"x1": elem.x1, "y1": elem.y1, "x2": elem.x2, "y2": elem.y2},
                    "clickable": elem.clickable,
                    "checkable": elem.checkable,
                    "class_name": elem.class_name,
                    "resource_id": elem.resource_id,
                })
                labeled_count += 1

        # Go home
        self.bridge.press_key(3)
        time.sleep(0.3)

        print(f"({labeled_count} labeled)")
        return screen_map

    def explore_all(self, app_list: dict = None):
        """
        Explore all apps in the provided list.
        If no list given, uses default apps for this device.
        """
        if app_list is None:
            app_list = self._default_apps()

        print("\n" + "=" * 50)
        print("   🗺️  TPM EXPLORER — Mapping Your Phone")
        print("=" * 50 + "\n")

        # Detect device info
        self.detect_device()
        print()

        # Explore each app
        mapped = 0
        for app_name, package_name in app_list.items():
            try:
                screen_map = self.explore_app(package_name, app_name)
                if screen_map:
                    self.map_data["apps"][app_name] = screen_map
                    mapped += 1
            except Exception as e:
                print(f"   ❌ {app_name}: {e}")
                try:
                    self.bridge.press_key(3)  # Try to go home
                except:
                    pass

        # Save
        self._save_map()
        self._print_summary()

    def _default_apps(self) -> dict:
        """
        Default apps to explore.
        Customized for this device based on installed packages.
        Only includes apps that are actually installed.
        """
        # Priority apps — always explore these if installed
        priority = {
            # Communication
            "WhatsApp": "com.whatsapp",
            "Telegram": "org.telegram.messenger",

            # Media (ReVanced versions)
            "YouTube": "app.revanced.android.youtube",
            "YouTube Music": "app.revanced.android.apps.youtube.music",
            "Spotify": "com.spotify.music",

            # Browser
            "Brave": "com.brave.browser",

            # Productivity
            "Notes": "com.miui.notes",
            "Calendar": "com.google.android.calendar",
            "Clock": "com.google.android.deskclock",
            "Calculator": "com.miui.calculator",
            "FileManager": "com.miui.android.fashiongallery",

            # System
            "Settings": "com.android.settings",
            "Dialer": "com.google.android.dialer",
            "Camera": "com.android.camera",
            "Messages": "com.google.android.apps.messaging",
        }

        # Filter to only installed apps
        installed_priority = {}
        for name, pkg in priority.items():
            if pkg in self.installed_packages:
                installed_priority[name] = pkg
            else:
                print(f"   ⏭️  Skipping {name} ({pkg}) — not installed")

        return installed_priority

    def explore_single(self, app_name: str, package_name: str):
        """Explore a single app and update its map entry."""
        screen_map = self.explore_app(package_name, app_name)
        if screen_map:
            self.map_data["apps"][app_name] = screen_map
            self._save_map()
            self._print_app_summary(app_name, screen_map)
        return screen_map

    def find_in_map(self, app_name: str, element_label: str) -> Optional[dict]:
        """
        Search the map for a specific element in an app.
        Returns the element dict with coordinates, or None.
        """
        app = self.map_data.get("apps", {}).get(app_name)
        if not app:
            return None

        # Try exact match first, then partial
        for elem in app.get("elements", []):
            if element_label.lower() == elem["label"].lower():
                return elem

        for elem in app.get("elements", []):
            if element_label.lower() in elem["label"].lower():
                return elem

        return None

    def refresh_app(self, app_name: str):
        """Re-explore an app that may have updated or moved."""
        # Try to find package in existing map
        app_data = self.map_data.get("apps", {}).get(app_name)
        if app_data:
            package = app_data.get("package")
        else:
            # Try default list
            package = self._default_apps().get(app_name)

        if package:
            print(f"   🔄 Refreshing {app_name}...")
            return self.explore_single(app_name, package)
        else:
            print(f"   ❌ Don't know package for '{app_name}'")
            print(f"   💡 Try: explorer.explore_single('{app_name}', 'com.example.app')")
            return None

    def refresh_all(self):
        """Re-explore all previously mapped apps."""
        apps = list(self.map_data.get("apps", {}).keys())
        if not apps:
            print("   No apps in map yet. Run explore_all() first.")
            return

        print(f"   🔄 Refreshing {len(apps)} apps...")
        for app_name in apps:
            self.refresh_app(app_name)

    def _print_summary(self):
        """Print a summary of all mapped apps."""
        print("\n" + "=" * 50)
        print("   📊 MAP SUMMARY")
        print("=" * 50)
        print(f"   Device: {self.map_data.get('manufacturer', '?')} {self.map_data.get('model', '?')}")
        print(f"   Resolution: {self.map_data.get('resolution', '?')}")
        print(f"   Apps mapped: {self.map_data.get('total_apps_mapped', 0)}")
        print()
        for app_name, app_data in self.map_data.get("apps", {}).items():
            total = app_data.get("total_elements", 0)
            labeled = len(app_data.get("elements", []))
            print(f"   📱 {app_name:20s}  {labeled} labeled / {total} total elements")
        print("=" * 50)

    def _print_app_summary(self, app_name: str, app_data: dict):
        """Print details for a single app."""
        print(f"\n   📱 {app_name}")
        print(f"   Package: {app_data.get('package')}")
        print(f"   Elements: {len(app_data.get('elements', []))} labeled")
        print("   Key elements:")
        for elem in app_data.get("elements", [])[:10]:
            pos = elem["position"]
            print(f"      {elem['label'][:40]:40s} @ ({pos['x']:3d},{pos['y']:3d})")
        if len(app_data.get("elements", [])) > 10:
            print(f"      ... and {len(app_data['elements']) - 10} more")


# ─── Quick Run ─────────────────────────────────────
if __name__ == "__main__":
    explorer = PhoneExplorer()

    print("\n📱 TPM Explorer — Ready")
    print("   [1] Explore ALL installed priority apps")
    print("   [2] Explore SINGLE app (by name & package)")
    print("   [3] Refresh a previously mapped app")
    print("   [4] Refresh ALL mapped apps")
    print("   [5] Show current map summary")

    choice = input("\n   Choice: ").strip()

    if choice == "1":
        explorer.explore_all()

    elif choice == "2":
        print("\n   Some installed apps:")
        # Show a sample of installed packages
        for pkg in explorer.installed_packages[:15]:
            print(f"   - {pkg}")
        if len(explorer.installed_packages) > 15:
            print(f"   ... and {len(explorer.installed_packages) - 15} more")
        name = input("\n   App name (e.g., WhatsApp): ").strip()
        pkg = input("   Package name: ").strip()
        if name and pkg:
            explorer.explore_single(name, pkg)

    elif choice == "3":
        name = input("   App name to refresh: ").strip()
        if name:
            explorer.refresh_app(name)

    elif choice == "4":
        explorer.refresh_all()

    elif choice == "5":
        explorer._print_summary()

    else:
        print("   Running full exploration...")
        explorer.explore_all()