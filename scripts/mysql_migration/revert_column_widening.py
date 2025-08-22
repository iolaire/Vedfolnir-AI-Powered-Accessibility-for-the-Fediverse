#!/usr/bin/env python3
"""
Database Column Reversion Script

This script can be used to revert the column widening changes if needed.
Generated automatically by widen_database_columns.py
"""

import pymysql

def revert_changes():
    conn = pymysql.connect(
        host='localhost',
        user='database_user_1d7b0d0696a20',
        password='EQA&bok7',
        database='vedfolnir',
        charset='utf8mb4'
    )

    try:
        with conn.cursor() as cursor:
            # Revert users.username
            cursor.execute("ALTER TABLE users MODIFY COLUMN username varchar(64)")

            # Revert users.email
            cursor.execute("ALTER TABLE users MODIFY COLUMN email varchar(120)")

            # Revert users.first_name
            cursor.execute("ALTER TABLE users MODIFY COLUMN first_name varchar(100)")

            # Revert users.last_name
            cursor.execute("ALTER TABLE users MODIFY COLUMN last_name varchar(100)")

            # Revert images.image_post_id
            cursor.execute("ALTER TABLE images MODIFY COLUMN image_post_id varchar(100)")

            # Revert images.original_filename
            cursor.execute("ALTER TABLE images MODIFY COLUMN original_filename varchar(200)")

            # Revert images.local_path
            cursor.execute("ALTER TABLE images MODIFY COLUMN local_path varchar(500)")

            # Revert images.image_url
            cursor.execute("ALTER TABLE images MODIFY COLUMN image_url varchar(1000)")

            # Revert posts.post_id
            cursor.execute("ALTER TABLE posts MODIFY COLUMN post_id varchar(500)")

            # Revert posts.user_id
            cursor.execute("ALTER TABLE posts MODIFY COLUMN user_id varchar(200)")

            # Revert posts.post_url
            cursor.execute("ALTER TABLE posts MODIFY COLUMN post_url varchar(500)")

            # Revert platform_connections.name
            cursor.execute("ALTER TABLE platform_connections MODIFY COLUMN name varchar(100)")

            # Revert platform_connections.username
            cursor.execute("ALTER TABLE platform_connections MODIFY COLUMN username varchar(200)")

        conn.commit()
        print('✅ All changes reverted successfully')

    except Exception as e:
        print(f'❌ Error reverting changes: {e}')

    finally:
        conn.close()

if __name__ == '__main__':
    revert_changes()