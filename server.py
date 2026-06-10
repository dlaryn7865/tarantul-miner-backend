from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

app = FastAPI()

# Разрешаем фронтенду делать запросы к бэкенду (CORS политики)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ClickData(BaseModel):
    tg_id: int
    username: str
    clicks: int

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            username TEXT,
            score INTEGER DEFAULT 0,
            league TEXT DEFAULT 'Бронзовый Паук'
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_current_league(score: int) -> str:
    if score >= 5000:
        return "Кибер-Тарантул 👑"
    elif score >= 500:
        return "Алмазный Паук 💎"
    return "Бронзовый Паук 🕷️"

# Получение данных юзера при входе
@app.get("/api/user/{tg_id}")
def get_user(tg_id: int, username: str):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT score, league FROM users WHERE tg_id = ?", (tg_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (tg_id, username, score, league) VALUES (?, ?, 0, 'Бронзовый Паук 🕷️')", (tg_id, username))
        conn.commit()
        score, league = 0, "Бронзовый Паук 🕷️"
    else:
        score, league = user[0], user[1]
        
    conn.close()
    return {"score": score, "league": league}

# Обработка входящих партий кликов
@app.post("/api/click")
def handle_click(data: ClickData):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Обновляем счёт
    cursor.execute("""
        INSERT INTO users (tg_id, username, score) VALUES (?, ?, ?)
        ON CONFLICT(tg_id) DO UPDATE SET score = score + ?, username = ?
    """, (data.tg_id, data.username, data.clicks, data.clicks, data.username))
    
    # Проверяем новую лигу
    cursor.execute("SELECT score FROM users WHERE tg_id = ?", (data.tg_id,))
    current_score = cursor.fetchone()[0]
    new_league = get_current_league(current_score)
    
    cursor.execute("UPDATE users SET league = ? WHERE tg_id = ?", (new_league, data.tg_id))
    conn.commit()
    conn.close()
    
    return {"status": "success", "new_score": current_score, "league": new_league}

# Роут для будущей страницы Лидерборда
@app.get("/api/leaderboard")
def get_leaderboard():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, score, league FROM users ORDER BY score DESC LIMIT 10")
    top_users = cursor.fetchall()
    conn.close()
    return [{"username": u[0], "score": u[1], "league": u[2]} for u in top_users]