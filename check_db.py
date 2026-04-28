import sqlite3

def check_users():
    conn = sqlite3.connect("todo_agent.db")
    cursor = conn.cursor()
    
    print("Checking users table...")
    try:
        cursor.execute("SELECT id, username, password_hash FROM users")
        users = cursor.fetchall()
        if not users:
            print("No users found in database.")
        else:
            print(f"Found {len(users)} users:")
            for u in users:
                print(f"ID: {u[0]}, Username: {u[1]}, Hash: {u[2][:20]}...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_users()
