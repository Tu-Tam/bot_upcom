import sqlite3
import threading

db_lock = threading.Lock()
DB_FILE = 'vietlott.db'

def init_db():
    """Khởi tạo bảng lưu trữ kết quả Vietlott đa giải"""
    with db_lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                game_type TEXT NOT NULL,
                date TEXT NOT NULL,
                numbers TEXT NOT NULL,
                PRIMARY KEY (game_type, date)
            )
        ''')
        conn.commit()
        conn.close()

def save_result(game_type, date_str, numbers):
    """Lưu hoặc cập nhật kết quả Vietlott theo loại giải và ngày"""
    with db_lock:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            numbers_str = ",".join(map(str, numbers)) if isinstance(numbers, (list, tuple)) else str(numbers)
            
            cursor.execute('''
                INSERT OR REPLACE INTO results (game_type, date, numbers)
                VALUES (?, ?, ?)
            ''', (game_type.lower(), date_str, numbers_str))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"⚠️ Lỗi CSDL khi lưu giải {game_type} ngày {date_str}: {e}", flush=True)
            return False

def get_results(game_type=None, limit=365):
    """Lấy kết quả xổ số gần nhất. Nếu truyền game_type thì lọc theo giải đó."""
    with db_lock:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            if game_type:
                cursor.execute(
                    'SELECT game_type, date, numbers FROM results WHERE game_type = ? ORDER BY date DESC LIMIT ?', 
                    (game_type.lower(), limit)
                )
            else:
                cursor.execute(
                    'SELECT game_type, date, numbers FROM results ORDER BY date DESC LIMIT ?', 
                    (limit,)
                )
                
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for g_type, date_val, numbers_str in rows:
                num_list = [int(n.strip()) for n in numbers_str.split(',') if n.strip().isdigit()]
                results.append({
                    'game': g_type,
                    'date': date_val,
                    'numbers': num_list
                })
            return results
        except Exception as e:
            print(f"⚠️ Lỗi lấy dữ liệu CSDL: {e}", flush=True)
            return []

def get_full(game_type=None, limit=365):
    """Alias tương thích cho get_results"""
    return get_results(game_type=game_type, limit=limit)

def get_date_range(game_type=None):
    """Lấy ngày cũ nhất và mới nhất có trong CSDL"""
    with db_lock:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            if game_type:
                cursor.execute('SELECT MIN(date), MAX(date) FROM results WHERE game_type = ?', (game_type.lower(),))
            else:
                cursor.execute('SELECT MIN(date), MAX(date) FROM results')
                
            row = cursor.fetchone()
            conn.close()
            if row and row[0] and row[1]:
                return row[0], row[1]
            return None, None
        except Exception as e:
            print(f"⚠️ Lỗi lấy phạm vi ngày CSDL: {e}", flush=True)
            return None, None

def count_results(game_type=None):
    """Đếm tổng số bản ghi đã lưu trong CSDL"""
    with db_lock:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            if game_type:
                cursor.execute('SELECT COUNT(*) FROM results WHERE game_type = ?', (game_type.lower(),))
            else:
                cursor.execute('SELECT COUNT(*) FROM results')
                
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"⚠️ Lỗi đếm CSDL: {e}", flush=True)
            return 0

# Tự động khởi tạo DB khi module được import
init_db()
