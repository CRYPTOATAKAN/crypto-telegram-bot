import sqlite3
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bot_data.db")


class DatabaseManager:
    """
    SQLite tabanlı yerel kalıcı veritabanı.
    Kullanıcının özel takip listesi, fiyat alarmları ve açık/kapalı işlemlerini saklar.
    """
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Tabloları otomatik oluşturur."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Özel Takip Listesi Tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_watchlist (
                    symbol TEXT PRIMARY KEY,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Fiyat Seviye Alarmları Tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    target_price REAL NOT NULL,
                    condition TEXT NOT NULL, -- 'ABOVE' veya 'BELOW'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_triggered INTEGER DEFAULT 0
                )
            """)

            # 3. İşlem & Pozisyon Günlüğü (Trade Journal) Tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL, -- 'LONG' veya 'SHORT'
                    entry_price REAL NOT NULL,
                    stop_price REAL NOT NULL,
                    target_price REAL,
                    position_size_usd REAL NOT NULL,
                    coin_amount REAL NOT NULL,
                    risk_usd REAL NOT NULL,
                    status TEXT DEFAULT 'OPEN', -- 'OPEN' veya 'CLOSED'
                    exit_price REAL,
                    pnl_usd REAL,
                    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("SQLite veritabanı tabloları başarıyla hazırlandı.")

    # --- Takip Listesi İşlemleri ---
    def add_watchlist_symbol(self, symbol: str) -> bool:
        """Kişisel takip listesine yeni sembol ekler."""
        symbol = symbol.upper().strip()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO custom_watchlist (symbol) VALUES (?)", (symbol,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Watchlist ekleme hatası: {e}")
            return False

    def remove_watchlist_symbol(self, symbol: str) -> bool:
        """Kişisel takip listesinden sembol siler."""
        symbol = symbol.upper().strip()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM custom_watchlist WHERE symbol = ?", (symbol,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Watchlist silme hatası: {e}")
            return False

    def get_custom_watchlist(self) -> List[str]:
        """Kullanıcının veritabanındaki tüm özel takip listesini döner."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT symbol FROM custom_watchlist ORDER BY added_at ASC")
                rows = cursor.fetchall()
                return [r["symbol"] for r in rows]
        except Exception as e:
            logger.error(f"Watchlist okuma hatası: {e}")
            return []

    # --- Fiyat Alarmı İşlemleri ---
    def add_price_alert(self, symbol: str, target_price: float, condition: str) -> int:
        """Yeni bir fiyat hedef alarmı kaydeder."""
        symbol = symbol.upper().strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_alerts (symbol, target_price, condition)
                VALUES (?, ?, ?)
            """, (symbol, target_price, condition.upper()))
            conn.commit()
            return cursor.lastrowid

    def get_active_price_alerts(self) -> List[Dict[str, Any]]:
        """Tetiklenmemiş aktif fiyat alarmlarını getirir."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM price_alerts WHERE is_triggered = 0 ORDER BY created_at ASC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def mark_alert_triggered(self, alert_id: int):
        """Alarmı tetiklendi olarak işaretler."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE price_alerts SET is_triggered = 1 WHERE id = ?", (alert_id,))
            conn.commit()

    def delete_price_alert(self, alert_id: int) -> bool:
        """Alarmı siler."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_alerts WHERE id = ?", (alert_id,))
            conn.commit()
            return cursor.rowcount > 0

    # --- İşlem & Pozisyon Günlüğü (Trade Journal) ---
    def open_trade(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_price: float,
        target_price: Optional[float],
        position_size_usd: float,
        coin_amount: float,
        risk_usd: float
    ) -> int:
        """Yeni bir açık pozisyon kaydeder."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (
                    symbol, direction, entry_price, stop_price, target_price,
                    position_size_usd, coin_amount, risk_usd, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """, (
                symbol.upper().strip(),
                direction.upper().strip(),
                entry_price,
                stop_price,
                target_price,
                position_size_usd,
                coin_amount,
                risk_usd
            ))
            conn.commit()
            return cursor.lastrowid

    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Şu anda açık olan pozisyonları getirir."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY opened_at DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def close_trade(self, trade_id: int, exit_price: float) -> Optional[Dict[str, Any]]:
        """Açık pozisyonu kapatır ve net kâr/zararı hesaplar."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE id = ? AND status = 'OPEN'", (trade_id,))
            row = cursor.fetchone()
            if not row:
                return None

            trade = dict(row)
            direction = trade["direction"]
            entry = trade["entry_price"]
            size_usd = trade["position_size_usd"]

            # Kâr/Zarar hesabı
            if direction == "LONG":
                pnl_pct = (exit_price - entry) / entry
            else:
                pnl_pct = (entry - exit_price) / entry
            pnl_usd = size_usd * pnl_pct

            cursor.execute("""
                UPDATE trades
                SET status = 'CLOSED', exit_price = ?, pnl_usd = ?, closed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (exit_price, pnl_usd, trade_id))
            conn.commit()

            trade["exit_price"] = exit_price
            trade["pnl_usd"] = pnl_usd
            trade["pnl_pct"] = pnl_pct * 100
            return trade

    def get_trade_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Kapanmış geçmiş işlemleri döner."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE status = 'CLOSED' ORDER BY closed_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
