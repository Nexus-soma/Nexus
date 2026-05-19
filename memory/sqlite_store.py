"""
Nexus SQLite Memory Store
Stores contacts, apps, action history, routines, preferences.
Single file. Zero setup. Always local.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional


class NexusMemory:
    """Local SQLite memory for Nexus."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nexus_memory.db")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                relationship TEXT,
                app TEXT DEFAULT 'whatsapp',
                frequency INTEGER DEFAULT 0,
                last_contacted TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                package TEXT NOT NULL,
                category TEXT,
                home_screen_page INTEGER,
                home_x INTEGER,
                home_y INTEGER,
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS action_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                command TEXT,
                app TEXT,
                action TEXT,
                target TEXT,
                success BOOLEAN,
                response_time_ms INTEGER,
                attempt_count INTEGER DEFAULT 1
            );
            
            CREATE TABLE IF NOT EXISTS routines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                trigger_time TEXT,
                trigger_day TEXT,
                app TEXT,
                action TEXT,
                target TEXT,
                confidence REAL DEFAULT 0.0,
                last_triggered TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS learned_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app TEXT,
                element TEXT,
                x INTEGER,
                y INTEGER,
                successes INTEGER DEFAULT 0,
                failures INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        self.conn.commit()
    
    # ─── CONTACTS ──────────────────────────────
    
    def add_contact(self, name: str, phone: str = None, relationship: str = None, app: str = "whatsapp"):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO contacts (name, phone, relationship, app, last_contacted)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET frequency = frequency + 1, last_contacted = ?
        """, (name, phone, relationship, app, datetime.now(), datetime.now()))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_contact(self, name: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM contacts WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_contacts_by_relationship(self, relationship: str) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM contacts WHERE relationship = ? ORDER BY frequency DESC", (relationship,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_frequent_contacts(self, limit: int = 10) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM contacts ORDER BY frequency DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def update_contact_relationship(self, name: str, relationship: str):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE contacts SET relationship = ? WHERE name = ?", (relationship, name))
        self.conn.commit()
    
    # ─── APPS ──────────────────────────────────
    
    def add_app(self, name: str, package: str, category: str = None):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO apps (name, package, category, last_used)
            VALUES (?, ?, ?, ?)
        """, (name, package, category, datetime.now()))
        self.conn.commit()
    
    def get_app(self, name: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM apps WHERE name = ? OR package = ?", (name, name))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_apps_by_category(self, category: str) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM apps WHERE category = ?", (category,))
        return [dict(row) for row in cursor.fetchall()]
    
    def record_app_usage(self, app_name: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE apps SET usage_count = usage_count + 1, last_used = ?
            WHERE name = ? OR package = ?
        """, (datetime.now(), app_name, app_name))
        self.conn.commit()
    
    # ─── ACTION HISTORY ────────────────────────
    
    def log_action(self, command: str, app: str, action: str, target: str = None, 
                   success: bool = True, response_time_ms: int = 0, attempt_count: int = 1):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO action_history (command, app, action, target, success, response_time_ms, attempt_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (command, app, action, target, success, response_time_ms, attempt_count))
        self.conn.commit()
    
    def get_recent_actions(self, limit: int = 20) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM action_history ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_success_rate(self, app: str = None) -> float:
        cursor = self.conn.cursor()
        if app:
            cursor.execute("""
                SELECT SUM(CASE WHEN success THEN 1 ELSE 0 END) * 1.0 / COUNT(*) 
                FROM action_history WHERE app = ?
            """, (app,))
        else:
            cursor.execute("""
                SELECT SUM(CASE WHEN success THEN 1 ELSE 0 END) * 1.0 / COUNT(*) 
                FROM action_history
            """)
        row = cursor.fetchone()
        return row[0] if row and row[0] else 0.0
    
    # ─── ROUTINES ──────────────────────────────
    
    def add_routine(self, name: str, trigger_time: str = None, trigger_day: str = None,
                    app: str = None, action: str = None, target: str = None):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO routines (name, trigger_time, trigger_day, app, action, target)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, trigger_time, trigger_day, app, action, target))
        self.conn.commit()
    
    def get_routines(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM routines ORDER BY confidence DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    def update_routine_confidence(self, routine_id: int, success: bool):
        cursor = self.conn.cursor()
        cursor.execute("SELECT successes, failures FROM routines WHERE id = ?", (routine_id,))
        row = cursor.fetchone()
        if row:
            successes = row["successes"] + (1 if success else 0)
            failures = row["failures"] + (0 if success else 1)
            confidence = successes / (successes + failures) if (successes + failures) > 0 else 0.0
            cursor.execute("""
                UPDATE routines SET successes = ?, failures = ?, confidence = ?, last_triggered = ?
                WHERE id = ?
            """, (successes, failures, confidence, datetime.now(), routine_id))
            self.conn.commit()
    
    # ─── PREFERENCES ───────────────────────────
    
    def set_preference(self, key: str, value: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO preferences (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
        """, (key, value, datetime.now(), value, datetime.now()))
        self.conn.commit()
    
    def get_preference(self, key: str) -> Optional[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None
    
    # ─── LEARNED ACTIONS ───────────────────────
    
    def update_learned_coordinate(self, app: str, element: str, x: int, y: int, success: bool):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM learned_actions WHERE app = ? AND element = ?", (app, element))
        row = cursor.fetchone()
        
        if row:
            successes = row["successes"] + (1 if success else 0)
            failures = row["failures"] + (0 if success else 1)
            confidence = successes / (successes + failures) if (successes + failures) > 0 else 0.0
            cursor.execute("""
                UPDATE learned_actions 
                SET x = ?, y = ?, successes = ?, failures = ?, confidence = ?, updated_at = ?
                WHERE app = ? AND element = ?
            """, (x, y, successes, failures, confidence, datetime.now(), app, element))
        else:
            confidence = 1.0 if success else 0.0
            cursor.execute("""
                INSERT INTO learned_actions (app, element, x, y, successes, failures, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (app, element, x, y, 1 if success else 0, 0 if success else 1, confidence))
        
        self.conn.commit()
    
    def get_learned_coordinate(self, app: str, element: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM learned_actions 
            WHERE app = ? AND element = ? AND confidence > 0.5
            ORDER BY confidence DESC LIMIT 1
        """, (app, element))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ─── STATS ─────────────────────────────────
    
    def get_stats(self) -> dict:
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM contacts")
        contact_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM action_history")
        action_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM learned_actions WHERE confidence > 0.5")
        learned_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM routines WHERE confidence > 0.5")
        routine_count = cursor.fetchone()[0]
        
        return {
            "contacts": contact_count,
            "actions_logged": action_count,
            "learned_coordinates": learned_count,
            "routines": routine_count,
            "success_rate": self.get_success_rate(),
        }
    
    def print_stats(self):
        stats = self.get_stats()
        print("\n   💾 NEXUS MEMORY")
        print(f"   Contacts: {stats['contacts']}")
        print(f"   Actions: {stats['actions_logged']}")
        print(f"   Learned: {stats['learned_coordinates']}")
        print(f"   Routines: {stats['routines']}")
        print(f"   Success rate: {stats['success_rate']:.0%}")


# ─── Test ──────────────────────────────────────────
if __name__ == "__main__":
    memory = NexusMemory()
    
    # Add some contacts
    memory.add_contact("Mum", relationship="family")
    memory.add_contact("Derick", relationship="brother")
    memory.add_contact("Ak", relationship="friend")
    
    # Log some actions
    memory.log_action("tell mum on whatsapp hello", "whatsapp", "send_message", "Mum", True)
    memory.log_action("play a song", "spotify", "play", None, False)
    
    # Set preferences
    memory.set_preference("default_browser", "brave")
    memory.set_preference("preferred_music_app", "spotify")
    
    # Show stats
    memory.print_stats()
    
    # Query
    print(f"\n   Frequent contacts: {[c['name'] for c in memory.get_frequent_contacts()]}")
    print(f"   Default browser: {memory.get_preference('default_browser')}")