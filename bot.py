@@
 app = Flask(__name__)
 
+@app.route('/_debug')
+def _debug():
+    import os
+    from database import count_results, get_date_range
+    env = dict(os.environ)
+    # mask token
+    if 'BOT_TOKEN' in env:
+        t = env['BOT_TOKEN']
+        env['BOT_TOKEN'] = (t[:8] + '...') if len(t) > 8 else t
+    db_path = env.get('DATABASE_PATH', 'data.db')
+    files = []
+    try:
+        files = os.listdir('.')
+    except Exception as _:
+        files = ['<cannot list>']
+    db_exists = os.path.exists(db_path)
+    rows = None
+    date_rng = (None, None)
+    try:
+        if db_exists:
+            rows = count_results()
+            date_rng = get_date_range()
+    except Exception as e:
+        rows = f'ERROR: {e}'
+
+    out = {
+        'env_preview': {k: env[k] for k in ['BOT_TOKEN','CHAT_ID','DATABASE_PATH'] if k in env},
+        'db_path': db_path,
+        'db_exists': db_exists,
+        'files': files,
+        'rows': rows,
+        'date_range': date_rng
+    }
+    return json.dumps(out, ensure_ascii=False)
+
@@
 def keep_alive():
@@
         return "🤖 Bot hoạt động — Dữ liệu đang được chuẩn bị..."
