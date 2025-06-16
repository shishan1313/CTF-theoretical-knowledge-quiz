import mysql.connector
from mysql.connector import Error

# MySQL配置（根据实际修改）
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # 替换为实际用户名
    'password': '011101',  # 替换为实际密码
    'port': 3306  # 确认端口与MySQL配置一致
}

def init_db():
    conn = None  # 初始化conn变量
    try:
        # 连接到MySQL服务器（不指定数据库）
        conn = mysql.connector.connect(
            host=MYSQL_CONFIG['host'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            port=MYSQL_CONFIG['port']
        )
        cursor = conn.cursor()

        # 创建数据库
        cursor.execute("CREATE DATABASE IF NOT EXISTS exam_system")
        conn.commit()
        print("Database 'exam_system' created successfully")

        # 切换到新数据库
        conn.database = 'exam_system'
        cursor = conn.cursor()

        # 创建表
# 修改建表语句
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                question TEXT,
                options TEXT,
                answer TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE,
                password_hash TEXT,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')


        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exams (
                id INT AUTO_INCREMENT PRIMARY KEY,
                exam_name VARCHAR(255) NOT NULL,
                question_ids TEXT,
                start_time DATETIME,
                end_time DATETIME,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_papers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                exam_id INT,
                score INT,
                start_time DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (exam_id) REFERENCES exams(id)
            )
        ''')

        # 插入示例数据
        sample_questions = [
            ("TCP属于OSI哪一层？", "传输层,网络层,应用层", "传输层"),
            ("HTTP默认端口？", "80,443,8080,21", "80"),
            ("Python中用于创建虚拟环境的命令是？", "pipenv,pip,virtualenv,conda", "virtualenv"),
            ("Flask默认监听哪个端口？", "5000,8080,80,3000", "5000")
        ]
        cursor.executemany(
            "INSERT INTO questions (question, options, answer) VALUES (%s, %s, %s)",
            sample_questions
        )
        conn.commit()
        print("Tables created and sample data inserted")

    except Error as e:
        print(f"Database Error: {e}")
    finally:
        if conn is not None and conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL connection closed")

if __name__ == '__main__':
    init_db()