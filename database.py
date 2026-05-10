import sqlite3
import json
import os
from datetime import datetime
from models import Tournament
from tournament_io import _tournament_to_dict, _dict_to_tournament

DB_PATH = os.path.join(os.path.expanduser("~"), "SCTM_Data", "tournaments.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id TEXT PRIMARY KEY,
                name TEXT,
                date TEXT,
                last_modified DATETIME,
                data TEXT
            )
        """)

def save_tournament_to_db(tournament: Tournament):
    """Save or update a tournament in the database."""
    data_dict = _tournament_to_dict(tournament)
    data_str = json.dumps(data_dict, ensure_ascii=False)
    now = datetime.now()
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO tournaments (id, name, date, last_modified, data)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                date=excluded.date,
                last_modified=excluded.last_modified,
                data=excluded.data
        """, (tournament.id, tournament.name, tournament.date, now, data_str))

def load_tournament_from_db(tournament_id: str) -> Tournament:
    """Load a specific tournament by ID."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT data FROM tournaments WHERE id=?", (tournament_id,))
        row = cursor.fetchone()
        if row:
            data_dict = json.loads(row[0])
            return _dict_to_tournament(data_dict)
    raise ValueError(f"Tournament {tournament_id} not found in database.")

def get_all_tournaments_info() -> list[dict]:
    """Get basic info of all saved tournaments for the dashboard."""
    info_list = []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT id, name, date, last_modified FROM tournaments ORDER BY last_modified DESC")
        for row in cursor.fetchall():
            info_list.append({
                "id": row[0],
                "name": row[1],
                "date": row[2],
                "last_modified": row[3]
            })
    return info_list

def delete_tournament_from_db(tournament_id: str):
    """Delete a tournament from the database."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM tournaments WHERE id=?", (tournament_id,))
