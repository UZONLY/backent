"""
Animelar TV Backend API
FastAPI-based REST API with SQLite database
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
import sqlite3
import hashlib
import logging
from contextlib import contextmanager

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI ilovasi
app = FastAPI(
    title="Animelar TV API",
    description="Anime streaming platform backend",
    version="2.0.0"
)

# CORS sozlamalari
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Konstantalar
SUPER_ADMIN_ID = "6526385624"
DB_NAME = "animelar.db"

# ==================== DATABASE ====================

@contextmanager
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_db():
    """Ma'lumotlar bazasini yaratish"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Users jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                balance REAL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        
        # Admins jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id TEXT PRIMARY KEY,
                dubbing_name TEXT NOT NULL,
                added_by TEXT NOT NULL,
                added_at TEXT NOT NULL,
                role TEXT DEFAULT 'admin'
            )
        """)
        
        # Banners jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS banners (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                image_url TEXT NOT NULL,
                added_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)
        
        # Animes jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS animes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                genre TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                poster_url TEXT NOT NULL,
                added_by TEXT NOT NULL,
                dubbing_name TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                purchases INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        
        # Episodes jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                anime_id TEXT NOT NULL,
                title TEXT NOT NULL,
                video_url TEXT NOT NULL,
                episode_number INTEGER NOT NULL,
                views INTEGER DEFAULT 0,
                added_at TEXT NOT NULL,
                FOREIGN KEY (anime_id) REFERENCES animes(id)
            )
        """)
        
        # Purchases jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                anime_id TEXT NOT NULL,
                price REAL NOT NULL,
                purchased_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (anime_id) REFERENCES animes(id)
            )
        """)
        
        # Ads jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                image_url TEXT NOT NULL,
                user_id TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Super admin qo'shish
        cursor.execute("""
            INSERT OR IGNORE INTO admins (id, dubbing_name, added_by, added_at, role)
            VALUES (?, ?, ?, ?, ?)
        """, (SUPER_ADMIN_ID, "Super Admin", "system", datetime.now().isoformat(), "super_admin"))
        
        logger.info("Database initialized successfully")


# ==================== MODELS ====================

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class AdminCreate(BaseModel):
    userId: str
    dubbingName: str = Field(..., min_length=2, max_length=50)
    addedBy: str


class BannerCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)
    imageUrl: str
    addedBy: str


class AnimeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    genre: str = Field(..., min_length=1, max_length=100)
    desc: str = Field(..., min_length=1)
    price: float = Field(..., ge=0)
    posterUrl: str
    addedBy: str


class EpisodeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    videoUrl: str
    addedBy: str


class AdCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    imageUrl: str
    userId: str


class TopUpRequest(BaseModel):
    userId: str
    amount: float = Field(..., gt=0)


class PurchaseRequest(BaseModel):
    userId: str


# ==================== HELPER FUNCTIONS ====================

def hash_password(password: str) -> str:
    """Parolni hash qilish"""
    return hashlib.sha256(password.encode()).hexdigest()


def is_admin(user_id: str) -> bool:
    """Admin ekanligini tekshirish"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM admins WHERE id = ?", (user_id,))
        return cursor.fetchone() is not None or user_id == SUPER_ADMIN_ID


def is_super_admin(user_id: str) -> bool:
    """Super admin ekanligini tekshirish"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM admins WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        return user_id == SUPER_ADMIN_ID or (result and result['role'] == 'super_admin')


def generate_id() -> str:
    """Unique ID yaratish"""
    return str(int(datetime.now().timestamp() * 1000))


# ==================== STARTUP ====================

@app.on_event("startup")
async def startup_event():
    """Ilova ishga tushganda"""
    init_db()
    logger.info("=" * 50)
    logger.info("🎬 Animelar TV Backend API")
    logger.info("=" * 50)
    logger.info(f"👑 Super Admin ID: {SUPER_ADMIN_ID}")
    logger.info(f"💾 Database: {DB_NAME}")
    logger.info("=" * 50)


# ==================== HEALTH CHECK ====================

@app.get("/ping")
async def ping():
    """Health check endpoint"""
    return {"ok": True, "time": datetime.now().isoformat()}


# ==================== AUTHENTICATION ====================

@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    """Yangi foydalanuvchi ro'yxatdan o'tkazish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Email mavjudligini tekshirish
            cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="user_exists"
                )
            
            # Yangi foydalanuvchi yaratish
            user_id = generate_id()
            hashed_password = hash_password(user.password)
            
            cursor.execute("""
                INSERT INTO users (id, name, email, password, balance, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, user.name, user.email, hashed_password, 0, datetime.now().isoformat()))
            
            logger.info(f"New user registered: {user.email}")
            
            return {
                "ok": True,
                "user": {
                    "id": user_id,
                    "name": user.name,
                    "email": user.email,
                    "balance": 0
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/login")
async def login(credentials: UserLogin):
    """Tizimga kirish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            hashed_password = hash_password(credentials.password)
            
            cursor.execute("""
                SELECT id, name, email, balance FROM users
                WHERE email = ? AND password = ?
            """, (credentials.email, hashed_password))
            
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid_credentials"
                )
            
            # Sotib olingan animalarni olish
            cursor.execute("""
                SELECT anime_id FROM purchases WHERE user_id = ?
            """, (user['id'],))
            
            purchased_animes = [row['anime_id'] for row in cursor.fetchall()]
            
            logger.info(f"User logged in: {credentials.email}")
            
            return {
                "ok": True,
                "user": {
                    "id": user['id'],
                    "name": user['name'],
                    "email": user['email'],
                    "balance": user['balance'],
                    "purchasedAnimes": purchased_animes
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== ADMIN MANAGEMENT ====================

@app.post("/add_admin", status_code=status.HTTP_201_CREATED)
async def add_admin(admin: AdminCreate):
    """Yangi admin qo'shish"""
    try:
        if not is_super_admin(admin.addedBy):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="only_super_admin_can_add"
            )
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Allaqachon admin ekanligini tekshirish
            cursor.execute("SELECT id FROM admins WHERE id = ?", (admin.userId,))
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="already_admin"
                )
            
            cursor.execute("""
                INSERT INTO admins (id, dubbing_name, added_by, added_at, role)
                VALUES (?, ?, ?, ?, ?)
            """, (admin.userId, admin.dubbingName, admin.addedBy, datetime.now().isoformat(), "admin"))
            
            logger.info(f"New admin added: {admin.dubbingName} ({admin.userId})")
            
            return {
                "ok": True,
                "admin": {
                    "id": admin.userId,
                    "dubbingName": admin.dubbingName,
                    "addedBy": admin.addedBy,
                    "addedAt": datetime.now().isoformat(),
                    "role": "admin"
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add admin error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/admins")
async def get_admins():
    """Barcha adminlarni olish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, dubbing_name, added_by, added_at, role
                FROM admins
                ORDER BY added_at DESC
            """)
            
            admins = []
            for row in cursor.fetchall():
                admins.append({
                    "id": row['id'],
                    "dubbingName": row['dubbing_name'],
                    "addedBy": row['added_by'],
                    "addedAt": row['added_at'],
                    "role": row['role']
                })
            
            return {"ok": True, "admins": admins}
    except Exception as e:
        logger.error(f"Get admins error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== BANNERS ====================

@app.post("/banner", status_code=status.HTTP_201_CREATED)
async def create_banner(banner: BannerCreate):
    """Yangi banner qo'shish"""
    try:
        if not is_super_admin(banner.addedBy):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="only_super_admin_can_add_banners"
            )
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            banner_id = generate_id()
            
            cursor.execute("""
                INSERT INTO banners (id, text, image_url, added_by, created_at, active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (banner_id, banner.text, banner.imageUrl, banner.addedBy, datetime.now().isoformat(), 1))
            
            logger.info(f"New banner created: {banner.text}")
            
            return {
                "ok": True,
                "banner": {
                    "id": banner_id,
                    "text": banner.text,
                    "imageUrl": banner.imageUrl,
                    "addedBy": banner.addedBy,
                    "createdAt": datetime.now().isoformat()
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create banner error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/banners")
async def get_banners():
    """Barcha bannerlarni olish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, text, image_url, added_by, created_at
                FROM banners
                WHERE active = 1
                ORDER BY created_at DESC
            """)
            
            banners = []
            for row in cursor.fetchall():
                banners.append({
                    "id": row['id'],
                    "text": row['text'],
                    "imageUrl": row['image_url'],
                    "addedBy": row['added_by'],
                    "createdAt": row['created_at']
                })
            
            return {"ok": True, "banners": banners}
    except Exception as e:
        logger.error(f"Get banners error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== ANIMES ====================

@app.post("/anime", status_code=status.HTTP_201_CREATED)
async def create_anime(anime: AnimeCreate):
    """Yangi anime qo'shish"""
    try:
        if not is_admin(anime.addedBy):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="not_admin"
            )
        
        # Narxni tekshirish
        if anime.price not in [2900, 5900]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_price", "allowed": [2900, 5900]}
            )
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Admin ma'lumotlarini olish
            cursor.execute("SELECT dubbing_name FROM admins WHERE id = ?", (anime.addedBy,))
            admin = cursor.fetchone()
            dubbing_name = admin['dubbing_name'] if admin else "Unknown"
            
            anime_id = generate_id()
            
            cursor.execute("""
                INSERT INTO animes (id, title, genre, description, price, poster_url, 
                                   added_by, dubbing_name, views, purchases, revenue, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (anime_id, anime.title, anime.genre, anime.desc, anime.price, anime.posterUrl,
                  anime.addedBy, dubbing_name, 0, 0, 0, datetime.now().isoformat()))
            
            logger.info(f"New anime created: {anime.title} by {dubbing_name}")
            
            return {
                "ok": True,
                "anime": {
                    "id": anime_id,
                    "title": anime.title,
                    "genre": anime.genre,
                    "desc": anime.desc,
                    "price": anime.price,
                    "posterUrl": anime.posterUrl,
                    "addedBy": anime.addedBy,
                    "dubbingName": dubbing_name,
                    "views": 0,
                    "purchases": 0,
                    "revenue": 0,
                    "createdAt": datetime.now().isoformat(),
                    "episodes": []
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create anime error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/animes")
async def get_animes():
    """Barcha animalarni olish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, genre, description, price, poster_url,
                       added_by, dubbing_name, views, purchases, revenue, created_at
                FROM animes
                ORDER BY created_at DESC
            """)
            
            animes = []
            for row in cursor.fetchall():
                anime_id = row['id']
                
                # Qismlarni olish
                cursor.execute("""
                    SELECT id, title, video_url, episode_number, views, added_at
                    FROM episodes
                    WHERE anime_id = ?
                    ORDER BY episode_number ASC
                """, (anime_id,))
                
                episodes = []
                for ep_row in cursor.fetchall():
                    episodes.append({
                        "id": ep_row['id'],
                        "title": ep_row['title'],
                        "videoUrl": ep_row['video_url'],
                        "episodeNumber": ep_row['episode_number'],
                        "views": ep_row['views'],
                        "addedAt": ep_row['added_at']
                    })
                
                animes.append({
                    "id": anime_id,
                    "title": row['title'],
                    "genre": row['genre'],
                    "desc": row['description'],
                    "price": row['price'],
                    "posterUrl": row['poster_url'],
                    "addedBy": row['added_by'],
                    "dubbingName": row['dubbing_name'],
                    "views": row['views'],
                    "purchases": row['purchases'],
                    "revenue": row['revenue'],
                    "createdAt": row['created_at'],
                    "episodes": episodes
                })
            
            return {"ok": True, "animes": animes}
    except Exception as e:
        logger.error(f"Get animes error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/anime/{anime_id}")
async def get_anime(anime_id: str):
    """Bitta animeni olish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, genre, description, price, poster_url,
                       added_by, dubbing_name, views, purchases, revenue, created_at
                FROM animes
                WHERE id = ?
            """, (anime_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="anime_not_found"
                )
            
            # Qismlarni olish
            cursor.execute("""
                SELECT id, title, video_url, episode_number, views, added_at
                FROM episodes
                WHERE anime_id = ?
                ORDER BY episode_number ASC
            """, (anime_id,))
            
            episodes = []
            for ep_row in cursor.fetchall():
                episodes.append({
                    "id": ep_row['id'],
                    "title": ep_row['title'],
                    "videoUrl": ep_row['video_url'],
                    "episodeNumber": ep_row['episode_number'],
                    "views": ep_row['views'],
                    "addedAt": ep_row['added_at']
                })
            
            return {
                "ok": True,
                "anime": {
                    "id": row['id'],
                    "title": row['title'],
                    "genre": row['genre'],
                    "desc": row['description'],
                    "price": row['price'],
                    "posterUrl": row['poster_url'],
                    "addedBy": row['added_by'],
                    "dubbingName": row['dubbing_name'],
                    "views": row['views'],
                    "purchases": row['purchases'],
                    "revenue": row['revenue'],
                    "createdAt": row['created_at'],
                    "episodes": episodes
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get anime error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== EPISODES ====================

@app.post("/anime/{anime_id}/episode", status_code=status.HTTP_201_CREATED)
async def add_episode(anime_id: str, episode: EpisodeCreate):
    """Animega qism qo'shish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Anime mavjudligini tekshirish
            cursor.execute("SELECT added_by FROM animes WHERE id = ?", (anime_id,))
            anime = cursor.fetchone()
            
            if not anime:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="anime_not_found"
                )
            
            # Ruxsat tekshirish
            if anime['added_by'] != episode.addedBy and not is_super_admin(episode.addedBy):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="not_authorized"
                )
            
            # Qism raqamini aniqlash
            cursor.execute("""
                SELECT MAX(episode_number) as max_ep FROM episodes WHERE anime_id = ?
            """, (anime_id,))
            result = cursor.fetchone()
            episode_number = (result['max_ep'] or 0) + 1
            
            episode_id = generate_id()
            
            cursor.execute("""
                INSERT INTO episodes (id, anime_id, title, video_url, episode_number, views, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (episode_id, anime_id, episode.title, episode.videoUrl, episode_number, 0, datetime.now().isoformat()))
            
            # Jami qismlar sonini olish
            cursor.execute("SELECT COUNT(*) as total FROM episodes WHERE anime_id = ?", (anime_id,))
            total = cursor.fetchone()['total']
            
            logger.info(f"New episode added to anime {anime_id}: {episode.title}")
            
            return {
                "ok": True,
                "episode": {
                    "id": episode_id,
                    "title": episode.title,
                    "videoUrl": episode.videoUrl,
                    "episodeNumber": episode_number,
                    "addedAt": datetime.now().isoformat()
                },
                "totalEpisodes": total
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add episode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== VIEWS & PURCHASES ====================

@app.post("/anime/{anime_id}/view")
async def increment_view(anime_id: str):
    """Ko'rishlar sonini oshirish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT views FROM animes WHERE id = ?", (anime_id,))
            anime = cursor.fetchone()
            
            if not anime:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="anime_not_found"
                )
            
            new_views = anime['views'] + 1
            cursor.execute("UPDATE animes SET views = ? WHERE id = ?", (new_views, anime_id))
            
            return {"ok": True, "views": new_views}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Increment view error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/anime/{anime_id}/purchase")
async def purchase_anime(anime_id: str, purchase: PurchaseRequest):
    """Anime sotib olish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Anime va foydalanuvchini tekshirish
            cursor.execute("SELECT title, price FROM animes WHERE id = ?", (anime_id,))
            anime = cursor.fetchone()
            
            if not anime:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="anime_not_found"
                )
            
            cursor.execute("SELECT balance FROM users WHERE id = ?", (purchase.userId,))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="user_not_found"
                )
            
            # Allaqachon sotib olinganligini tekshirish
            cursor.execute("""
                SELECT id FROM purchases WHERE user_id = ? AND anime_id = ?
            """, (purchase.userId, anime_id))
            
            if cursor.fetchone():
                return {"ok": True, "alreadyPurchased": True}
            
            # Balansni tekshirish
            if user['balance'] < anime['price']:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": "insufficient_balance",
                        "required": anime['price'],
                        "current": user['balance']
                    }
                )
            
            # Xaridni amalga oshirish
            new_balance = user['balance'] - anime['price']
            cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, purchase.userId))
            
            purchase_id = generate_id()
            cursor.execute("""
                INSERT INTO purchases (id, user_id, anime_id, price, purchased_at)
                VALUES (?, ?, ?, ?, ?)
            """, (purchase_id, purchase.userId, anime_id, anime['price'], datetime.now().isoformat()))
            
            # Anime statistikasini yangilash
            cursor.execute("""
                UPDATE animes
                SET purchases = purchases + 1, revenue = revenue + ?
                WHERE id = ?
            """, (anime['price'], anime_id))
            
            logger.info(f"Anime purchased: {anime['title']} by user {purchase.userId}")
            
            return {
                "ok": True,
                "purchased": True,
                "newBalance": new_balance,
                "anime": anime['title']
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Purchase error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== ADVERTISEMENTS ====================

@app.post("/ad", status_code=status.HTTP_201_CREATED)
async def create_ad(ad: AdCreate):
    """Reklama joylashtirish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Foydalanuvchini tekshirish
            cursor.execute("SELECT balance FROM users WHERE id = ?", (ad.userId,))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="user_not_found"
                )
            
            # Balansni tekshirish (500 so'm)
            if user['balance'] < 500:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": "insufficient_balance",
                        "required": 500,
                        "current": user['balance']
                    }
                )
            
            # To'lovni amalga oshirish
            new_balance = user['balance'] - 500
            cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, ad.userId))
            
            ad_id = generate_id()
            cursor.execute("""
                INSERT INTO ads (id, title, image_url, user_id, views, clicks, created_at, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ad_id, ad.title, ad.imageUrl, ad.userId, 0, 0, datetime.now().isoformat(), 1))
            
            logger.info(f"New ad created: {ad.title} by user {ad.userId}")
            
            return {
                "ok": True,
                "ad": {
                    "id": ad_id,
                    "title": ad.title,
                    "imageUrl": ad.imageUrl,
                    "userId": ad.userId,
                    "views": 0,
                    "clicks": 0,
                    "createdAt": datetime.now().isoformat(),
                    "active": True
                },
                "newBalance": new_balance
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create ad error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/ads")
async def get_ads():
    """Barcha reklamalarni olish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, image_url, user_id, views, clicks, created_at
                FROM ads
                WHERE active = 1
                ORDER BY created_at DESC
            """)
            
            ads = []
            for row in cursor.fetchall():
                ads.append({
                    "id": row['id'],
                    "title": row['title'],
                    "imageUrl": row['image_url'],
                    "userId": row['user_id'],
                    "views": row['views'],
                    "clicks": row['clicks'],
                    "createdAt": row['created_at']
                })
            
            return {"ok": True, "ads": ads}
    except Exception as e:
        logger.error(f"Get ads error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/ad/{ad_id}/view")
async def increment_ad_view(ad_id: str):
    """Reklama ko'rishlarini oshirish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT views FROM ads WHERE id = ?", (ad_id,))
            ad = cursor.fetchone()
            
            if not ad:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="ad_not_found"
                )
            
            new_views = ad['views'] + 1
            cursor.execute("UPDATE ads SET views = ? WHERE id = ?", (new_views, ad_id))
            
            return {"ok": True, "views": new_views}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Increment ad view error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== USER BALANCE ====================

@app.post("/topup")
async def topup_balance(topup: TopUpRequest):
    """Balansni to'ldirish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT balance FROM users WHERE id = ?", (topup.userId,))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="user_not_found"
                )
            
            new_balance = user['balance'] + topup.amount
            cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, topup.userId))
            
            logger.info(f"Balance topped up: user {topup.userId}, amount {topup.amount}")
            
            return {"ok": True, "newBalance": new_balance}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Topup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/user/{user_id}/balance")
async def get_user_balance(user_id: str):
    """Foydalanuvchi balansini olish"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="user_not_found"
                )
            
            # Sotib olingan animalarni olish
            cursor.execute("SELECT anime_id FROM purchases WHERE user_id = ?", (user_id,))
            purchased_animes = [row['anime_id'] for row in cursor.fetchall()]
            
            return {
                "ok": True,
                "balance": user['balance'],
                "purchasedAnimes": purchased_animes
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get balance error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== STATISTICS ====================

@app.get("/stats")
async def get_stats():
    """Umumiy statistika"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Umumiy statistika
            cursor.execute("SELECT COUNT(*) as total FROM users")
            total_users = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM animes")
            total_animes = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM banners WHERE active = 1")
            total_banners = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM ads WHERE active = 1")
            total_ads = cursor.fetchone()['total']
            
            cursor.execute("SELECT SUM(views) as total FROM animes")
            total_views = cursor.fetchone()['total'] or 0
            
            cursor.execute("SELECT COUNT(*) as total FROM purchases")
            total_purchases = cursor.fetchone()['total']
            
            cursor.execute("SELECT SUM(price) as total FROM purchases")
            total_revenue = cursor.fetchone()['total'] or 0
            
            # Admin statistikasi
            cursor.execute("""
                SELECT a.id, a.dubbing_name, a.role,
                       COUNT(DISTINCT an.id) as total_animes,
                       COALESCE(SUM(an.views), 0) as total_views,
                       COALESCE(SUM(an.purchases), 0) as total_purchases,
                       COALESCE(SUM(an.revenue), 0) as total_revenue
                FROM admins a
                LEFT JOIN animes an ON a.id = an.added_by
                GROUP BY a.id, a.dubbing_name, a.role
                ORDER BY total_revenue DESC
            """)
            
            admin_stats = []
            for row in cursor.fetchall():
                admin_stats.append({
                    "id": row['id'],
                    "dubbingName": row['dubbing_name'],
                    "role": row['role'],
                    "totalAnimes": row['total_animes'],
                    "totalViews": row['total_views'],
                    "totalPurchases": row['total_purchases'],
                    "totalRevenue": row['total_revenue']
                })
            
            # Top animeler
            cursor.execute("""
                SELECT id, title, dubbing_name, views, purchases, revenue
                FROM animes
                ORDER BY views DESC
                LIMIT 10
            """)
            
            top_animes = []
            for row in cursor.fetchall():
                top_animes.append({
                    "id": row['id'],
                    "title": row['title'],
                    "dubbingName": row['dubbing_name'],
                    "views": row['views'],
                    "purchases": row['purchases'],
                    "revenue": row['revenue']
                })
            
            return {
                "ok": True,
                "stats": {
                    "totalUsers": total_users,
                    "totalAnimes": total_animes,
                    "totalBanners": total_banners,
                    "totalAds": total_ads,
                    "totalViews": total_views,
                    "totalPurchases": total_purchases,
                    "totalRevenue": total_revenue
                },
                "adminStats": admin_stats,
                "topAnimes": top_animes
            }
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/admin/{admin_id}/stats")
async def get_admin_stats(admin_id: str):
    """Admin statistikasi"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Admin ma'lumotlari
            cursor.execute("""
                SELECT id, dubbing_name, role, added_at
                FROM admins
                WHERE id = ?
            """, (admin_id,))
            
            admin = cursor.fetchone()
            if not admin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="admin_not_found"
                )
            
            # Admin animelari
            cursor.execute("""
                SELECT id, title, genre, price, views, purchases, revenue, created_at,
                       (SELECT COUNT(*) FROM episodes WHERE anime_id = animes.id) as episode_count
                FROM animes
                WHERE added_by = ?
                ORDER BY created_at DESC
            """, (admin_id,))
            
            animes = []
            total_views = 0
            total_purchases = 0
            total_revenue = 0
            
            for row in cursor.fetchall():
                anime_data = {
                    "id": row['id'],
                    "title": row['title'],
                    "genre": row['genre'],
                    "price": row['price'],
                    "views": row['views'],
                    "purchases": row['purchases'],
                    "revenue": row['revenue'],
                    "episodeCount": row['episode_count'],
                    "createdAt": row['created_at']
                }
                animes.append(anime_data)
                
                total_views += row['views']
                total_purchases += row['purchases']
                total_revenue += row['revenue']
            
            return {
                "ok": True,
                "admin": {
                    "id": admin['id'],
                    "dubbingName": admin['dubbing_name'],
                    "role": admin['role'],
                    "addedAt": admin['added_at']
                },
                "stats": {
                    "totalAnimes": len(animes),
                    "totalViews": total_views,
                    "totalPurchases": total_purchases,
                    "totalRevenue": total_revenue
                },
                "animes": animes
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get admin stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
