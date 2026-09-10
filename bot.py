def generate_v36_diverse_top5(history_data: list, game="645", seed_key=None) -> tuple:
    if seed_key:
        numeric_seed = int(re.sub(r'\D', '', str(seed_key))) if re.sub(r'\D', '', str(seed_key)) else 42
        random.seed(numeric_seed)

    is_655 = (str(game) == "655")
    max_num = 55 if is_655 else 45
    
    # Phân tích tần suất
    all_draws = [d["result"] for d in history_data[-50:]]
    flat_nums = [n for d in all_draws for n in d]
    freq = Counter(flat_nums)
    
    sorted_all = sorted(range(1, max_num + 1), key=lambda x: freq.get(x, 0), reverse=True)
    
    hot_pool = sorted_all[:15]
    warm_pool = sorted_all[15:30]
    cold_pool = sorted_all[30:]
    
    combos = []
    
    # BỘ 1: HOT CORE (Tập trung số xu hướng cao)
    c1 = sorted(random.sample(hot_pool, 4) + random.sample(warm_pool, 2))
    combos.append(c1)
    
    # BỘ 2: BALANCED (Cân bằng Hot - Warm - Cold)
    c2 = sorted(random.sample(hot_pool, 2) + random.sample(warm_pool, 2) + random.sample(cold_pool, 2))
    combos.append(c2)

    # BỘ 3: COLD REBOUND (Bắt số lâu chưa ra)
    c3 = sorted(random.sample(cold_pool, 3) + random.sample(hot_pool, 2) + random.sample(warm_pool, 1))
    combos.append(c3)

    # BỘ 4: TEN-SPREAD (Mỗi chục 1 số - Phủ rộng)
    c4 = []
    tens_buckets = {}
    for n in range(1, max_num + 1):
        bucket = n // 10
        tens_buckets.setdefault(bucket, []).append(n)
        
    available_buckets = list(tens_buckets.keys())
    selected_buckets = random.sample(available_buckets, min(6, len(available_buckets)))
    for b in selected_buckets:
        c4.append(random.choice(tens_buckets[b]))
    c4 = sorted(c4)
    combos.append(c4)

    # BỘ 5: MATRIX RANDOM (Chọn ngẫu nhiên trong Top 28 ma trận trọng tâm)
    top_matrix = sorted(sorted_all[:28])
    c5 = sorted(random.sample(top_matrix, 6))
    combos.append(c5)

    return combos, top_matrix