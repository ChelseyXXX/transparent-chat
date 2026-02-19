import os
import sqlite3
from passlib.context import CryptContext

# Use absolute path so DB is consistent no matter where uvicorn is started
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chatlog.db")

# Use pbkdf2_sha256 to avoid potential bcrypt binary issues in some environments
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def get_conn():
    return sqlite3.connect(DB_PATH)


def _migrate_users_table_if_needed():
    conn = get_conn()
    c = conn.cursor()
    c.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in c.fetchall()]
    if not cols or 'email' not in cols:
        conn.close()
        return

    c.execute("""
        CREATE TABLE IF NOT EXISTS users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        INSERT INTO users_new (id, username, password_hash, created_at)
        SELECT id, username, password_hash, created_at FROM users
    """)
    c.execute("DROP TABLE users")
    c.execute("ALTER TABLE users_new RENAME TO users")
    conn.commit()
    conn.close()


def get_or_create_default_user():
    """Ensure the legacy tester user exists and return its ID."""
    create_users_table()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ? LIMIT 1", ("tester",))
    row = c.fetchone()
    if row:
        conn.close()
        return row[0]

    hashed = pwd_context.hash("secret123")
    c.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        ("tester", hashed)
    )
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return user_id

def create_users_table():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    _migrate_users_table_if_needed()

def save_user(username, password_hash):
    create_users_table()
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                  (username, password_hash))
        conn.commit()
        user_id = c.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return None
    conn.close()
    return user_id

def get_user_by_username(username):
    create_users_table()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash FROM users WHERE username = ? LIMIT 1", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "password_hash": row[2]}
    return None


def _ensure_messages_schema(default_user_id=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("PRAGMA table_info(messages)")
    cols = [row[1] for row in c.fetchall()]
    if 'user_id' not in cols:
        c.execute("ALTER TABLE messages ADD COLUMN user_id INTEGER")
    if 'confidence_label' not in cols:
        c.execute("ALTER TABLE messages ADD COLUMN confidence_label TEXT")
    if 'confidence_score' not in cols:
        c.execute("ALTER TABLE messages ADD COLUMN confidence_score REAL")
    if 'reasoning' not in cols:
        c.execute("ALTER TABLE messages ADD COLUMN reasoning TEXT")
    if 'trust_analysis' not in cols:
        c.execute("ALTER TABLE messages ADD COLUMN trust_analysis TEXT")

    if default_user_id is not None:
        c.execute("UPDATE messages SET user_id = ? WHERE user_id IS NULL", (default_user_id,))

    conn.commit()
    conn.close()


def save_message(role, content, emotion, reasoning=None, trust_analysis=None, user_id=None):
    if user_id is None:
        user_id = get_or_create_default_user()

    _ensure_messages_schema(default_user_id=user_id)
    conn = get_conn()
    c = conn.cursor()

    # Serialize trust_analysis to JSON if provided
    trust_analysis_json = None
    if trust_analysis:
        import json
        trust_analysis_json = json.dumps(trust_analysis, ensure_ascii=False)

    # confidence may be None for user messages
    if not emotion:
        c.execute(
            "INSERT INTO messages (role, content, confidence_label, confidence_score, reasoning, trust_analysis, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (role, content, None, None, reasoning, trust_analysis_json, user_id)
        )
    else:
        c.execute(
            "INSERT INTO messages (role, content, confidence_label, confidence_score, reasoning, trust_analysis, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (role, content, emotion.get("label"), emotion.get("score"), reasoning, trust_analysis_json, user_id)
        )
    conn.commit()
    return c.lastrowid  # Return message ID for updates
    # if emotion includes a topic, persist it to topics table
    try:
        # create topics table if not exists with parent_id for hierarchy
        c.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                summary TEXT,
                parent_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(parent_id) REFERENCES topics(id)
            )
        """)
        conn.commit()
        # Ensure parent_id column exists (for backwards compatibility)
        c.execute("PRAGMA table_info(topics)")
        cols = [row[1] for row in c.fetchall()]
        if 'parent_id' not in cols:
            c.execute("ALTER TABLE topics ADD COLUMN parent_id INTEGER DEFAULT NULL")
            conn.commit()
        if emotion and isinstance(emotion, dict) and emotion.get('topic'):
            t = emotion.get('topic')
            s = emotion.get('reasoning') or None
            # Find similar parent topic
            try:
                parent_id = find_similar_topic_id(t)
            except Exception as e:
                print(f"[DEBUG] Error finding similar topic: {e}")
                parent_id = None
            c.execute("INSERT INTO topics (topic, summary, parent_id) VALUES (?, ?, ?)", (t, s, parent_id))
            conn.commit()
            print(f"[DEBUG] Saved topic: topic={t}, parent_id={parent_id}")
    except Exception as e:
        # non-fatal
        print(f"[DEBUG] Error saving topic: {e}")
    conn.close()

def get_conversation(user_id=None):
    import json
    if user_id is None:
        user_id = get_or_create_default_user()

    _ensure_messages_schema(default_user_id=user_id)
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT id, role, content, confidence_label, confidence_score, reasoning, trust_analysis, timestamp FROM messages WHERE user_id = ? ORDER BY id",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()
    result = []
    for (msg_id, r, ctext, conf_label, conf_score, reasoning, trust_analysis_json, t) in rows:
        conf = None
        if conf_label is not None or conf_score is not None:
            conf = {"label": conf_label, "score": conf_score}
        
        # Deserialize trust_analysis from JSON
        trust_analysis = None
        if trust_analysis_json:
            try:
                trust_analysis = json.loads(trust_analysis_json)
            except:
                trust_analysis = None
        
        result.append({
            "id": msg_id,
            "role": r,
            "content": ctext,
            "confidence": conf,
            "reasoning": reasoning,
            "trust_analysis": trust_analysis,
            "time": t
        })
    return result


def _ensure_topics_schema(default_user_id=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            summary TEXT,
            parent_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(parent_id) REFERENCES topics(id)
        )
    """)
    conn.commit()

    c.execute("PRAGMA table_info(topics)")
    cols = [row[1] for row in c.fetchall()]
    if 'parent_id' not in cols:
        c.execute("ALTER TABLE topics ADD COLUMN parent_id INTEGER DEFAULT NULL")
    if 'user_id' not in cols:
        c.execute("ALTER TABLE topics ADD COLUMN user_id INTEGER")

    if default_user_id is not None:
        c.execute("UPDATE topics SET user_id = ? WHERE user_id IS NULL", (default_user_id,))

    conn.commit()
    conn.close()


def get_recent_topics(limit=7, user_id=None):
    if user_id is None:
        user_id = get_or_create_default_user()

    _ensure_topics_schema(default_user_id=user_id)
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute(
            "SELECT id, topic, summary, parent_id, timestamp FROM topics WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
        rows = c.fetchall()
    except Exception as e:
        print(f"[DEBUG] Error getting topics: {e}")
        rows = []
    conn.close()
    return [{"id": r[0], "topic": r[1], "summary": r[2], "parent_id": r[3], "time": r[4]} for r in rows]

def get_all_topic_names():
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("SELECT id, topic FROM topics")
        rows = c.fetchall()
    except Exception:
        rows = []
    conn.close()
    return rows

def find_similar_topic_id(new_topic, threshold=0.5):
    """Find a similar topic ID to use as parent for the new topic using simple keyword overlap."""
    all_topics = get_all_topic_names()
    if not all_topics:
        return None
    
    # Simple keyword overlap similarity
    new_words = set(new_topic.lower().split())
    best_match_id = None
    best_score = 0
    
    for topic_id, topic_name in all_topics:
        existing_words = set(topic_name.lower().split())
        if not new_words or not existing_words:
            continue
        overlap = len(new_words & existing_words) / max(len(new_words), len(existing_words))
        if overlap > best_score and overlap >= threshold:
            best_score = overlap
            best_match_id = topic_id
    
    return best_match_id

def update_message_trust_analysis(message_content: str, trust_analysis: dict, user_id=None, message_id: int | None = None):
    """Update trust_analysis for an assistant message, preferring message_id when provided."""
    import json
    if user_id is None:
        user_id = get_or_create_default_user()

    _ensure_messages_schema(default_user_id=user_id)
    conn = get_conn()
    c = conn.cursor()

    trust_analysis_json = json.dumps(trust_analysis, ensure_ascii=False)

    if message_id is not None:
        c.execute(
            "UPDATE messages SET trust_analysis = ? WHERE id = ? AND user_id = ?",
            (trust_analysis_json, message_id, user_id)
        )
        conn.commit()
        updated = c.rowcount
        conn.close()
        return updated > 0

    # Find the most recent assistant message with matching content
    c.execute("""
        SELECT id FROM messages 
        WHERE role = 'assistant' AND content = ? AND user_id = ?
        ORDER BY id DESC LIMIT 1
    """, (message_content, user_id))
    
    row = c.fetchone()
    if row:
        message_id = row[0]
        c.execute("UPDATE messages SET trust_analysis = ? WHERE id = ?", (trust_analysis_json, message_id))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False
