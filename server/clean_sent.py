import sqlite3

for p in ['/app/instance/email_classifier.db', '/app/email_classifier.db', '/app/server/instance/email_classifier.db']:
    try:
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        cur.execute("SELECT id, subject, category, folder FROM emails WHERE folder='sent'")
        rows = cur.fetchall()
        print(f"=== {p} Total Sent: {len(rows)} ===")
        for r in rows:
            print("  ", r)
        cur.execute("UPDATE emails SET folder = 'inbox' WHERE folder = 'sent' AND (category = 'Banking' OR subject LIKE '%Bank%')")
        if cur.rowcount > 0:
            print(f"Moved {cur.rowcount} rows from sent to inbox in {p}")
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"{p} Error: {e}")
