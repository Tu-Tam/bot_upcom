⁵import sys
from datetime import datetime, timedelta
import database as db
import predictor

def run_backtest_cli(game_type="655", days=30):
    """
    Chạy thử nghiệm thuật toán lùi ngày cho một giải Vietlott cụ thể
    """
    print(f"🧪 BẮT ĐẦU BACKTEST GIẢI [{game_type.upper()}] TRONG {days} KỲ LẦN TRƯỚC", flush=True)
    print("=" * 60, flush=True)

    all_data = db.get_results(game_type=game_type, limit=500)
    if not all_data:
        print("❌ Chưa có dữ liệu trong CSDL! Vui lòng chạy backfill_365_days.py trước.", flush=True)
        return

    # Lấy danh sách các ngày có dữ liệu
    available_dates = sorted([r['date'] for r in all_data], reverse=True)[:days]
    
    valid_cnt = 0
    total_matched = 0
    total_possible = 0

    for target_date in available_dates:
        # Lọc dữ liệu LÙI VỀ TRƯỚC ngày test
        historical_data = [r for r in all_data if r['date'] < target_date]
        actual_row = next((r for r in all_data if r['date'] == target_date), None)

        if not actual_row or not historical_data:
            continue

        # Chạy kiểm thử
        res = predictor.test_prediction_accuracy(
            game_type=game_type, 
            historical_data=historical_data, 
            actual_numbers=actual_row['numbers']
        )

        if not res:
            continue

        valid_cnt += 1
        total_matched += res['matched_count']
        total_possible += res['total_possible']

        print(f"📅 Ngày {target_date}: Dự đoán [{res['predicted']}] | Thực tế [{res['actual']}] | Trùng [{res['matched']}] ({res['accuracy_rate']}%)")

    print("=" * 60, flush=True)
    if valid_cnt > 0:
        avg_acc = (total_matched / total_possible) * 100 if total_possible > 0 else 0
        print(f"📊 TỔNG KẾT [{game_type.upper()}]: Test {valid_cnt} kỳ | Tổng trùng {total_matched}/{total_possible} số | Chính xác TB: {avg_acc:.2f}%")
    else:
        print("❌ Không đủ dữ liệu đối soát!")

if __name__ == "__main__":
    game = sys.argv[1] if len(sys.argv) > 1 else "655"
    days_cnt = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    run_backtest_cli(game_type=game, days=days_cnt)
