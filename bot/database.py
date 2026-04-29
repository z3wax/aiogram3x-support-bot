import aiosqlite
import logging
from datetime import datetime

DB_NAME = "luxraqamlar.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Users table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                role TEXT DEFAULT 'client', -- client, operator, superadmin
                is_banned BOOLEAN DEFAULT 0,
                is_online BOOLEAN DEFAULT 1,
                permissions TEXT DEFAULT 'all', -- For operators: chat, accept, rate, etc.
                rating_score INTEGER DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                phone TEXT DEFAULT NULL
            )
        ''')
        
        # Backward compatibility for phone column
        try:
            await db.execute('ALTER TABLE users ADD COLUMN phone TEXT DEFAULT NULL')
        except:
            pass
        
        # Tickets table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                operator_id INTEGER,
                status TEXT DEFAULT 'open', -- open, in_progress, pending, closed
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP
            )
        ''')

        # Messages table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                sender_id INTEGER,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Ratings table (One per ticket)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                ticket_id INTEGER PRIMARY KEY,
                client_id INTEGER,
                operator_id INTEGER,
                score INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Templates (Quick replies)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_id INTEGER,
                text TEXT
            )
        ''')
        
        # Audit Logs
        await db.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Bot Settings
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Favorite Operators table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS favorite_operators (
                client_id INTEGER,
                operator_id INTEGER,
                PRIMARY KEY (client_id, operator_id)
            )
        ''')
        
        # Default settings
        await db.execute('INSERT OR IGNORE INTO bot_settings (key, value) VALUES ("welcome_msg", "Assalomu alaykum! luxRaqamlar support botiga xush kelibsiz. Savolingizni yozib qoldiring.")')
        
        # Migrations (if fields don't exist in existing db)
        try:
            await db.execute('ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0')
            await db.execute('ALTER TABLE users ADD COLUMN is_online BOOLEAN DEFAULT 1')
            await db.execute('ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT "all"')
            await db.execute('ALTER TABLE tickets ADD COLUMN closed_at TIMESTAMP')
        except:
            pass # Already exists
            
        await db.commit()
        logging.info("Database initialized with CRM features.")

async def log_action(user_id: int, action: str, details: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO audit_logs (user_id, action, details) VALUES (?, ?, ?)', (user_id, action, details))
        await db.commit()

async def get_setting(key: str):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT value FROM bot_settings WHERE key = ?', (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)', (key, value))
        await db.commit()

async def add_user(user_id: int, username: str, full_name: str, role: str = 'client'):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            '''INSERT OR IGNORE INTO users (user_id, username, full_name, role) VALUES (?, ?, ?, ?)''',
            (user_id, username, full_name, role)
        )
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
            return await cursor.fetchone()

# Operator status toggles
async def update_operator_status(user_id: int, is_online: bool):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET is_online = ? WHERE user_id = ?', (is_online, user_id))
        await db.commit()

async def toggle_ban(user_id: int, is_banned: bool):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (is_banned, user_id))
        await db.commit()

async def get_operators(online_only=False):
    async with aiosqlite.connect(DB_NAME) as db:
        query = 'SELECT * FROM users WHERE role IN ("operator", "superadmin")'
        if online_only:
            query += ' AND is_online = 1'
        async with db.execute(query) as cursor:
            return await cursor.fetchall()

async def create_ticket(client_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('INSERT INTO tickets (client_id) VALUES (?)', (client_id,))
        await db.commit()
        return cursor.lastrowid

async def take_ticket(ticket_id: int, operator_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        # Check if already taken
        async with db.execute('SELECT status FROM tickets WHERE id = ?', (ticket_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] != 'open':
                return False
                
        await db.execute('UPDATE tickets SET operator_id = ?, status = "in_progress" WHERE id = ?', (operator_id, ticket_id))
        await db.commit()
        return True

async def close_ticket(ticket_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute('UPDATE tickets SET status = "closed", closed_at = ? WHERE id = ?', (now, ticket_id))
        await db.commit()

async def get_open_tickets():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT t.id, t.client_id, u.username, t.created_at FROM tickets t LEFT JOIN users u ON t.client_id = u.user_id WHERE t.status = "open"') as cursor:
            return await cursor.fetchall()

async def get_operator_history(operator_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT id, client_id, status, created_at FROM tickets WHERE operator_id = ? AND status = "closed" ORDER BY id DESC LIMIT 20', (operator_id,)) as cursor:
            return await cursor.fetchall()

async def change_ticket_status(ticket_id: int, status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE tickets SET status = ? WHERE id = ?', (status, ticket_id))
        await db.commit()

async def get_active_ticket(user_id: int, role: str):
    async with aiosqlite.connect(DB_NAME) as db:
        column = "client_id" if role == "client" else "operator_id"
        async with db.execute(f'SELECT * FROM tickets WHERE {column} = ? AND status IN ("in_progress", "pending")', (user_id,)) as cursor:
            return await cursor.fetchone()

async def get_ticket(ticket_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)) as cursor:
            return await cursor.fetchone()

async def save_message(ticket_id: int, sender_id: int, text: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO messages (ticket_id, sender_id, text) VALUES (?, ?, ?)', (ticket_id, sender_id, text))
        await db.commit()

async def save_rating(ticket_id: int, client_id: int, operator_id: int, score: int):
    async with aiosqlite.connect(DB_NAME) as db:
        # Check if already rated
        async with db.execute('SELECT ticket_id FROM ratings WHERE ticket_id = ?', (ticket_id,)) as cursor:
            if await cursor.fetchone():
                return False
        
        await db.execute('INSERT INTO ratings (ticket_id, client_id, operator_id, score) VALUES (?, ?, ?, ?)', (ticket_id, client_id, operator_id, score))
        await db.execute('UPDATE users SET rating_score = rating_score + ?, rating_count = rating_count + 1 WHERE user_id = ?', (score, operator_id))
        await db.commit()
        return True

async def add_favorite_operator(client_id: int, operator_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR IGNORE INTO favorite_operators (client_id, operator_id) VALUES (?, ?)', (client_id, operator_id))
        await db.commit()

async def update_user_role(user_id: int, role: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET role = ? WHERE user_id = ?', (role, user_id))
        await db.commit()

async def update_operator_phone(user_id: int, phone: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET phone = ? WHERE user_id = ?', (phone, user_id))
        await db.commit()

async def update_user_name(user_id: int, name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET full_name = ? WHERE user_id = ?', (name, user_id))
        await db.commit()

async def get_favorites_count(operator_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT COUNT(*) FROM favorite_operators WHERE operator_id = ?', (operator_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_favorite_operators(client_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        query = '''
            SELECT u.user_id, u.full_name, u.phone 
            FROM favorite_operators f
            JOIN users u ON f.operator_id = u.user_id
            WHERE f.client_id = ?
        '''
        async with db.execute(query, (client_id,)) as cursor:
            return await cursor.fetchall()

# Templates (Quick Replies)
async def get_templates(operator_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT id, text FROM templates WHERE operator_id = ?', (operator_id,)) as cursor:
            return await cursor.fetchall()

async def add_template(operator_id: int, text: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO templates (operator_id, text) VALUES (?, ?)', (operator_id, text))
        await db.commit()

async def get_operator_detailed_stats(operator_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        # Time-based counts could be added here using SQLite date functions
        async with db.execute('SELECT COUNT(*) FROM tickets WHERE operator_id = ? AND status = "closed"', (operator_id,)) as cursor:
            closed_tickets = (await cursor.fetchone())[0]
            
        async with db.execute('SELECT SUM(score), COUNT(score) FROM ratings WHERE operator_id = ?', (operator_id,)) as cursor:
            row = await cursor.fetchone()
            total_score = row[0] or 0
            ratings_count = row[1] or 0
            
        return {
            "closed_tickets": closed_tickets,
            "total_score": total_score,
            "ratings_count": ratings_count,
            "avg_score": round(total_score / ratings_count, 1) if ratings_count > 0 else 0
        }

async def get_system_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            users_count = (await cursor.fetchone())[0]
            
        async with db.execute('SELECT COUNT(*) FROM users WHERE role IN ("operator", "superadmin")') as cursor:
            ops_count = (await cursor.fetchone())[0]
            
        async with db.execute('SELECT COUNT(*) FROM tickets') as cursor:
            tickets_count = (await cursor.fetchone())[0]
            
        async with db.execute('SELECT COUNT(*) FROM tickets WHERE status = "open"') as cursor:
            open_tickets = (await cursor.fetchone())[0]
            
        return {
            "users": users_count,
            "operators": ops_count,
            "tickets": tickets_count,
            "open_tickets": open_tickets
        }

async def get_all_clients():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            return [row[0] for row in await cursor.fetchall()]

async def get_ticket_messages(ticket_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT sender_id, text, created_at FROM messages WHERE ticket_id = ? ORDER BY created_at ASC', (ticket_id,)) as cursor:
            return await cursor.fetchall()

async def get_messages_by_operator(operator_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        query = '''
            SELECT m.ticket_id, m.sender_id, m.text, m.created_at, t.client_id, t.operator_id 
            FROM messages m 
            JOIN tickets t ON m.ticket_id = t.id 
            WHERE t.operator_id = ?
            ORDER BY m.ticket_id, m.created_at ASC
        '''
        async with db.execute(query, (operator_id,)) as cursor:
            return await cursor.fetchall()

async def get_all_messages_for_pdf():
    async with aiosqlite.connect(DB_NAME) as db:
        query = '''
            SELECT m.ticket_id, m.sender_id, m.text, m.created_at, t.client_id, t.operator_id 
            FROM messages m 
            JOIN tickets t ON m.ticket_id = t.id 
            ORDER BY m.ticket_id, m.created_at ASC
        '''
        async with db.execute(query) as cursor:
            return await cursor.fetchall()
