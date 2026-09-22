# -*- coding: utf-8 -*-
"""Banco SQLite (historico + estatisticas)."""

import sqlite3

from .paths import DATABASE_FILE


class NexusDB:
    def __init__(self, db_path=DATABASE_FILE):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            content_title TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS stats (
            service_name TEXT PRIMARY KEY,
            total_watches INTEGER DEFAULT 0,
            last_watched DATETIME
        )''')
        conn.commit()
        conn.close()

    def add_history(self, service_name, content_title="Home"):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO history (service_name, content_title) VALUES (?, ?)",
                  (service_name, content_title))
        c.execute("""INSERT INTO stats (service_name, total_watches, last_watched)
                     VALUES (?, 1, CURRENT_TIMESTAMP)
                     ON CONFLICT(service_name) DO UPDATE SET
                     total_watches = total_watches + 1,
                     last_watched = CURRENT_TIMESTAMP""",
                  (service_name,))
        conn.commit()
        conn.close()

    def get_recent_history(self, limit=10):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT service_name, content_title, timestamp FROM history ORDER BY id DESC LIMIT ?", (limit,))
        rows = [{"service": r[0], "title": r[1], "time": r[2]} for r in c.fetchall()]
        conn.close()
        return rows

    def get_top_services(self, limit=6):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT service_name, total_watches FROM stats ORDER BY total_watches DESC LIMIT ?", (limit,))
        rows = [{"service": r[0], "watches": r[1]} for r in c.fetchall()]
        conn.close()
        return rows
