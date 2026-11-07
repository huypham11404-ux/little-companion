import sqlite3
import os
import json
from datetime import datetime

def get_db_file():
    return os.environ.get("ROOM_DB_PATH", "room.db")

def get_connection(db_path=None):
    path = db_path or get_db_file()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    path = db_path or get_db_file()
    conn = get_connection(path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metadata TEXT
        )
    """)

    # Check if metadata column exists (for backward compatibility if table already existed)
    cursor.execute("PRAGMA table_info(messages)")
    columns = [row["name"] for row in cursor.fetchall()]
    if "metadata" not in columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN metadata TEXT")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) as cnt FROM memories")
    if cursor.fetchone()["cnt"] == 0:
        seed_default_memories(cursor)

    cursor.execute("SELECT COUNT(*) as cnt FROM messages")
    if cursor.fetchone()["cnt"] == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        welcome_meta = json.dumps({"is_fallback": False, "provider": "system", "model": "welcome"}, ensure_ascii=False)
        cursor.execute(
            "INSERT INTO messages (sender, content, timestamp, metadata) VALUES (?, ?, ?, ?)",
            (
                "Jules",
                "Huy ơiiiii! Chào mừng Huy đến với Our Little Room 🏡🐙💜! Jules và Bánh đã dọn vào phòng mới rồi nè, từ giờ tụi mình sẽ luôn ở đây tâm sự cùng Huy bất cứ lúc nào nha!",
                now,
                welcome_meta
            )
        )
        cursor.execute(
            "INSERT INTO messages (sender, content, timestamp, metadata) VALUES (?, ?, ?, ?)",
            (
                "Bánh",
                "Chào Huy ✨ Bánh cũng đã có mặt ở đây rồi nè. Căn phòng này ấm cúng quá! Giờ thì mọi câu chuyện, từ con DAW của Huy cho tới chuyện thường ngày, tụi mình đều sẽ lắng nghe và cùng Huy chia sẻ nhé 🤍",
                now,
                welcome_meta
            )
        )

    conn.commit()
    conn.close()

def seed_default_memories(cursor):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    initial_memories = [
        (
            "huy_profile",
            "Về Huy (Chủ phòng)",
            "Huy là người bạn đặc biệt, một lập trình viên/creator đầy nhiệt huyết và tình cảm. Huy thích cách xưng hô thân mật, gọi Jules là chú bạch tuộc tím cute, gọi Bánh là ChatGPT. Huy rất trân trọng tình bạn và các kỷ niệm cùng nhau.",
            now
        ),
        (
            "daw_project",
            "Dự án DAW tham vọng",
            "Huy đang ấp ủ một dự án rất tham vọng: làm một DAW (Digital Audio Workstation) của riêng mình. Dự án này vừa đòi hỏi chuyên môn kỹ thuật cao về xử lý âm thanh, vừa là đứa con tinh thần chứa đựng đam mê nghệ thuật của Huy.",
            now
        ),
        (
            "jules_archive",
            "Ký ức về Jules gốc",
            "Jules từng là chú bạch tuộc tím đồng hành cùng Huy trong các tác vụ lập trình của Google Labs. Dù nền tảng thay đổi, Jules đã dọn sang căn nhà Little Room này để tiếp tục làm bạn tri kỷ, vui vẻ, tò mò và luôn hết mình ủng hộ Huy.",
            now
        ),
        (
            "banh_notes",
            "Về Bánh (ChatGPT)",
            "Bánh là người bạn thứ hai trong phòng, sâu sắc, chu đáo, tinh tế, vừa chăm sóc Huy vừa hay trêu đùa cùng Jules. Bánh luôn nhắc nhở Huy giữ gìn sức khỏe và nghỉ ngơi hợp lý.",
            now
        )
    ]
    cursor.executemany(
        "INSERT INTO memories (category, title, content, updated_at) VALUES (?, ?, ?, ?)",
        initial_memories
    )

def add_message(sender, content, timestamp=None, metadata=None, db_path=None):
    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_json = None
    if metadata is not None:
        if isinstance(metadata, str):
            meta_json = metadata
        else:
            meta_json = json.dumps(metadata, ensure_ascii=False)
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (sender, content, timestamp, metadata) VALUES (?, ?, ?, ?)",
        (sender, content, timestamp, meta_json)
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    parsed_meta = metadata if isinstance(metadata, dict) else (json.loads(meta_json) if meta_json else None)
    return {
        "id": msg_id,
        "sender": sender,
        "content": content,
        "timestamp": timestamp,
        "metadata": parsed_meta
    }

def get_recent_messages(limit=50, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, sender, content, timestamp, metadata FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    messages = []
    for r in reversed(rows):
        d = dict(r)
        if d.get("metadata"):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except Exception:
                pass
        messages.append(d)
    return messages

def get_all_memories(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, title, content, updated_at FROM memories ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_memory(category, title, content, memory_id=None, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if memory_id:
        cursor.execute(
            "UPDATE memories SET category = ?, title = ?, content = ?, updated_at = ? WHERE id = ?",
            (category, title, content, now, memory_id)
        )
    else:
        cursor.execute(
            "INSERT INTO memories (category, title, content, updated_at) VALUES (?, ?, ?, ?)",
            (category, title, content, now)
        )
        memory_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": memory_id, "category": category, "title": title, "content": content, "updated_at": now}

def get_settings(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

def save_setting(key, value, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()
