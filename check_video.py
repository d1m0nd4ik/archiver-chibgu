import sqlite3

conn = sqlite3.connect('vk_archive.db')
cursor = conn.cursor()

print("📊 Анализ базы данных")
print("=" * 50)

print("\n1. Типы медиа в базе:")
cursor.execute("SELECT DISTINCT media_type FROM posts")
for row in cursor.fetchall():
    print(f"   {row[0]}")

print("\n2. Количество по типам:")
cursor.execute("SELECT media_type, COUNT(*) FROM posts GROUP BY media_type")
for row in cursor.fetchall():
    print(f"   {row[0]}: {row[1]}")

print("\n3. Всего записей:")
cursor.execute("SELECT COUNT(*) FROM posts")
print(f"   {cursor.fetchone()[0]}")

print("\n4. Видео (через LOWER):")
cursor.execute("SELECT COUNT(*) FROM posts WHERE LOWER(media_type) = 'video'")
print(f"   {cursor.fetchone()[0]}")

print("\n5. Примеры записей:")
cursor.execute("SELECT media_type, media_path FROM posts LIMIT 10")
for row in cursor.fetchall():
    print(f"   {row[0]}: {row[1]}")

print("\n" + "=" * 50)

conn.close()