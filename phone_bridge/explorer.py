"""
Nexus Phone Explorer (TPM Layer 1)
Auto-maps ALL apps on your phone using the screen reader.
Builds phone_map.json with exact coordinates AND element roles.
Auto-detects installed apps and maps them intelligently.
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
    """Explores and maps apps with role detection."""

    def __init__(self, bridge: PhoneBridge = None, map_path: str = None):
        self.bridge = bridge or PhoneBridge()
        self.reader = ScreenReader()
        self.map_path = map_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "phone_map.json"
        )
        self.map_data = self._load_map()
        self.installed_packages = self._detect_installed_apps()

    def _load_map(self) -> dict:
        if os.path.exists(self.map_path):
            try:
                with open(self.map_path, "r") as f:
                    data = json.load(f)
                    print(f"   📂 Loaded map with {len(data.get('apps', {}))} apps")
                    return data
            except json.JSONDecodeError:
                print("⚠️  Corrupted map file. Starting fresh.")
        return self._empty_map()

    def _empty_map(self) -> dict:
        return {
            "device": "unknown", "manufacturer": "unknown", "model": "unknown",
            "resolution": "unknown", "android_version": "unknown",
            "last_updated": None, "total_apps_mapped": 0, "apps": {},
        }

    def _save_map(self):
        self.map_data["last_updated"] = datetime.now().isoformat()
        self.map_data["total_apps_mapped"] = len(self.map_data["apps"])
        with open(self.map_path, "w") as f:
            json.dump(self.map_data, f, indent=2)
        print(f"   💾 Map saved ({self.map_data['total_apps_mapped']} apps)")

    def _detect_installed_apps(self) -> list:
        result = self.bridge.run_raw("pm list packages -3")
        packages = []
        for line in result.split("\n"):
            if line.startswith("package:"):
                packages.append(line.replace("package:", "").strip())
        return packages

    def detect_device(self):
        self.map_data["model"] = self.bridge.run_raw("getprop ro.product.model").strip()
        self.map_data["manufacturer"] = self.bridge.run_raw("getprop ro.product.manufacturer").strip()
        self.map_data["resolution"] = self.bridge.run_raw("wm size").strip().split(":")[-1].strip()
        self.map_data["android_version"] = self.bridge.run_raw("getprop ro.build.version.release").strip()
        print(f"   📱 {self.map_data['manufacturer']} {self.map_data['model']}")
        print(f"   📐 {self.map_data['resolution']} | Android {self.map_data['android_version']}")
        print(f"   📦 {len(self.installed_packages)} user apps installed")

    def _detect_role(self, label: str, resource_id: str) -> str:
        text = (label + " " + resource_id).lower()
        patterns = {
            "create": ["create", "add", "new"],
            "save": ["save", "done", "confirm", "check"],
            "share": ["share", "send to"],
            "delete": ["delete", "remove", "trash"],
            "search": ["search", "find", "look"],
            "back": ["back", "arrow", "up", "close"],
            "menu": ["menu", "more", "overflow", "options", "settings"],
            "camera": ["camera", "photo", "picture", "capture", "shoot", "shutter"],
            "media": ["play", "pause", "stop", "music"],
        }
        for role, keywords in patterns.items():
            if any(kw in text for kw in keywords):
                return role
        return "unknown"

    def explore_app(self, package_name: str, app_name: str) -> dict:
        if package_name not in self.installed_packages:
            print(f"   ⚠️  {app_name} ({package_name}) not installed. Skipping.")
            return {}
        print(f"   🔍 {app_name}...", end=" ", flush=True)
        self.bridge.open_app(package_name)
        time.sleep(2.0)
        elements = self.reader.get_interactive_elements()
        if not elements:
            print("(no elements)")
            self.bridge.press_key(3)
            return {}
        screen_map = {
            "package": package_name,
            "last_explored": datetime.now().isoformat(),
            "total_elements": len(elements),
            "elements": [],
        }
        labeled_count = 0
        for elem in elements:
            if elem.label and elem.label.strip():
                role = self._detect_role(elem.label, elem.resource_id)
                screen_map["elements"].append({
                    "label": elem.label,
                    "position": {"x": elem.center_x, "y": elem.center_y},
                    "bounds": {"x1": elem.x1, "y1": elem.y1, "x2": elem.x2, "y2": elem.y2},
                    "clickable": elem.clickable, "checkable": elem.checkable,
                    "class_name": elem.class_name, "resource_id": elem.resource_id,
                    "role": role,
                })
                labeled_count += 1
        self.bridge.press_key(3)
        time.sleep(0.3)
        print(f"({labeled_count} labeled)")
        return screen_map

    def _all_installed_apps(self) -> dict:
        apps = {}
        skip_keywords = ["google", "xiaomi", "miui", "qualcomm", "mediatek",
                        "android", "overlay", "factory", "service"]
        for package in self.installed_packages:
            if any(s in package for s in skip_keywords):
                continue
            parts = package.split(".")
            name = parts[-1].replace("_", " ").replace("-", " ").title()
            if name.lower() in ["app", "android", "main", "lifestyle"]:
                name = parts[-2].replace("_", " ").replace("-", " ").title() if len(parts) > 1 else name
            apps[name] = package
        return apps

    def explore_all(self, app_list: dict = None):
        if app_list is None:
            app_list = self._all_installed_apps()
        print("\n" + "=" * 50)
        print("   🗺️  TPM EXPLORER — Mapping ALL Apps")
        print("=" * 50 + "\n")
        self.detect_device()
        print()
        mapped = 0
        for app_name, package_name in app_list.items():
            try:
                screen_map = self.explore_app(package_name, app_name)
                if screen_map:
                    self.map_data["apps"][app_name] = screen_map
                    mapped += 1
            except Exception as e:
                print(f"   ❌ {app_name}: {e}")
                try: self.bridge.press_key(3)
                except: pass
        self._save_map()
        self._print_summary()

    def explore_single(self, app_name: str, package_name: str):
        screen_map = self.explore_app(package_name, app_name)
        if screen_map:
            self.map_data["apps"][app_name] = screen_map
            self._save_map()
            self._print_app_summary(app_name, screen_map)
        return screen_map

    def find_in_map(self, app_name: str, element_label: str) -> Optional[dict]:
        app = self.map_data.get("apps", {}).get(app_name)
        if not app: return None
        for elem in app.get("elements", []):
            if element_label.lower() == elem["label"].lower(): return elem
        for elem in app.get("elements", []):
            if element_label.lower() in elem["label"].lower(): return elem
        return None

    def refresh_app(self, app_name: str):
        app_data = self.map_data.get("apps", {}).get(app_name)
        if app_data:
            package = app_data.get("package")
        else:
            package = self._all_installed_apps().get(app_name)
        if package:
            print(f"   🔄 Refreshing {app_name}...")
            return self.explore_single(app_name, package)
        else:
            print(f"   ❌ Don't know package for '{app_name}'")
            return None

    def refresh_all(self):
        apps = list(self.map_data.get("apps", {}).keys())
        if not apps:
            print("   No apps in map yet. Run explore_all() first.")
            return
        print(f"   🔄 Refreshing {len(apps)} apps...")
        for app_name in apps:
            self.refresh_app(app_name)

    def _print_summary(self):
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
            roles = set(e.get("role", "?") for e in app_data.get("elements", []))
            print(f"   📱 {app_name:20s}  {labeled} elements | roles: {', '.join(roles)}")
        print("=" * 50)

    def _print_app_summary(self, app_name: str, app_data: dict):
        print(f"\n   📱 {app_name}")
        print(f"   Package: {app_data.get('package')}")
        print(f"   Elements: {len(app_data.get('elements', []))} labeled")
        print("   Key elements:")
        for elem in app_data.get("elements", [])[:10]:
            pos = elem["position"]
            role = elem.get("role", "?")
            print(f"      [{role:8s}] {elem['label'][:35]:35s} @ ({pos['x']:3d},{pos['y']:3d})")
        if len(app_data.get("elements", [])) > 10:
            print(f"      ... and {len(app_data['elements']) - 10} more")


if __name__ == "__main__":
    explorer = PhoneExplorer()
    print("\n📱 TPM Explorer — Ready")
    print("   [1] Explore ALL installed apps")
    print("   [2] Explore SINGLE app")
    print("   [3] Refresh a mapped app")
    print("   [4] Refresh ALL mapped apps")
    print("   [5] Show map summary")
    choice = input("\n   Choice: ").strip()
    if choice == "1": explorer.explore_all()
    elif choice == "2":
        for pkg in explorer.installed_packages[:15]: print(f"   - {pkg}")
        name = input("\n   App name: ").strip()
        pkg = input("   Package: ").strip()
        if name and pkg: explorer.explore_single(name, pkg)
    elif choice == "3":
        name = input("   App to refresh: ").strip()
        if name: explorer.refresh_app(name)
    elif choice == "4": explorer.refresh_all()
    elif choice == "5": explorer._print_summary()
    else: explorer.explore_all()
