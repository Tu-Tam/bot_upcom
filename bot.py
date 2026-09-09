def generate_v34_entropy_swarm(history_data: list, game="655", num_combos=150, seed_key=None) -> tuple:
    if seed_key:
        numeric_seed = int(re.sub(r'\D', '', str(seed_key))) if re.sub(r'\D', '', str(seed_key)) else 42
        random.seed(numeric_seed)

    is_655 = (str(game) == "655")
    max_num = 55 if is_655 else 45
    
    if len(history_data) < 20:
        base = list(range(1, 7))
        return [base] * num_combos, base

    draws_recent = [d["result"] for d in history_data[-60:]]
    freq = Counter([n for draw in draws_recent for n in draw])
    
    sorted_all = sorted(range(1, max_num + 1), key=lambda x: freq.get(x, 0), reverse=True)

    # TINH CHỈNH V34.1: Tăng mật độ cho Power 6/55
    if is_655:
        hot_pool = sorted_all[:15]        # Thu gọn Hot Pool từ 18 -> 15
        warm_pool = sorted_all[15:30]
        cold_pool = sorted_all[30:]
        top_matrix = sorted(sorted_all[:32]) # Co ma trận trọng tâm từ 38 -> 32
        min_tens = 2                      # Nới lỏng lọc chục (2 thay vì 3)
    else:
        hot_pool = sorted_all[:14]
        warm_pool = sorted_all[14:28]
        cold_pool = sorted_all[28:]
        top_matrix = sorted(sorted_all[:30])
        min_tens = 3

    min_s, max_s = (85, 230) if is_655 else (60, 200)
    
    combos = []
    attempts = 0

    while len(combos) < num_combos and attempts < 100000:
        attempts += 1

        n_hot = random.choice([3, 4])
        n_warm = random.choice([1, 2])
        n_cold = 6 - n_hot - n_warm

        if n_cold <= 0:
            n_cold = 1

        try:
            combo = sorted(
                random.sample(hot_pool, n_hot) + 
                random.sample(warm_pool, n_warm) + 
                random.sample(cold_pool, n_cold)
            )
        except ValueError:
            continue

        if len(combo) < 6:
            continue

        # Lọc 1: Kiểm tra khoảng cách các chục theo min_tens
        tens_coverage = len(set(x // 10 for x in combo))
        if tens_coverage < min_tens:
            continue

        # Lọc 2: Tối đa 2 cặp liền kề
        adj_count = sum(1 for i in range(5) if combo[i+1] - combo[i] == 1)
        if adj_count > 2:
            continue

        # Lọc 3: Tỷ lệ Chẵn / Lẻ (1-5 đến 5-1)
        evens = sum(1 for x in combo if x % 2 == 0)
        if evens < 1 or evens > 5:
            continue

        # Lọc 4: Tổng dải rộng
        if not (min_s <= sum(combo) <= max_s):
            continue

        # Lọc 5: Giảm trùng lặp nội bộ
        if combos and attempts < 70000:
            limit = 4 if len(combos) < 100 else 5
            if max(len(set(combo) & set(c)) for c in combos) > limit:
                continue

        if combo not in combos:
            combos.append(combo)

    # Nới lỏng bổ sung từ Ma trận trọng tâm nếu chưa đủ bộ
    while len(combos) < num_combos:
        combo = sorted(random.sample(top_matrix, 6))
        if combo not in combos:
            combos.append(combo)

    return combos, top_matrix