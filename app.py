import string
from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import mysql.connector
from mysql.connector import Error
import random
import pandas as pd
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# MySQL配置
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '011101',
    'database': 'exam_system',
    'port': 3306  # 确保端口正确
}

# 添加允许的文件扩展名
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# ================== 题目去重函数 ==================
def is_duplicate_question(cursor, question_text):
    """检查题目是否重复"""
    cursor.execute("SELECT id FROM questions WHERE question = %s", (question_text,))
    return cursor.fetchone() is not None
# ================== 数据库连接助手 ==================
def get_db_connection():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        return conn
    except Error as e:
        print(f"数据库连接失败: {e}")
        return None

# ================== 权限装饰器 ==================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin', False):
            flash('无管理员权限')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 首页
@app.route('/')
def index():
    return render_template('index.html')

# 修改start_exam路由，传递考试结束时间
# ================== 修改开始考试函数 ==================
# ================== 修改开始考试路由 ==================
@app.route('/exam/<int:exam_id>')
def start_exam(exam_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # 检查考试有效性
        cursor.execute('''SELECT question_ids, end_time FROM exams 
                       WHERE id=%s AND is_active=TRUE 
                       AND start_time <= NOW() AND end_time >= NOW()''', (exam_id,))
        exam_data = cursor.fetchone()
        if not exam_data:
            flash('考试不可用')
            return redirect(url_for('exam_list'))
        
        # 检查用户是否已参加过此考试
        cursor.execute('''
            SELECT COUNT(*) FROM test_papers 
            WHERE user_id = %s AND exam_id = %s
        ''', (session['user_id'], exam_id))
        attempt_count = cursor.fetchone()[0]
        
        if attempt_count > 0:
            flash('注意：您已参加过此考试，再次提交将更新您的成绩', 'warning')
        
        # 获取题目（包含分值）
        question_ids = exam_data[0].split(',')
        placeholders = ','.join(['%s'] * len(question_ids))
        cursor.execute(f'''SELECT id, question, options, score 
                         FROM questions 
                         WHERE id IN ({placeholders})''', tuple(question_ids))
        questions = [{'id': row[0], 'text': row[1], 'options': row[2].split(','), 'score': row[3]} for row in cursor.fetchall()]
        
        # 传递考试结束时间
        end_time = exam_data[1]
        
        return render_template('exam.html', questions=questions, exam_id=exam_id, end_time=end_time)
    except Error as e:
        print(f"Error: {e}")
        return redirect(url_for('exam_list'))
    finally:
        if conn.is_connected():
            conn.close()

@app.route('/exam')
def exam_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, exam_name, start_time, end_time 
            FROM exams 
            WHERE is_active=TRUE AND end_time >= NOW()
        ''')
        exams = cursor.fetchall()
        return render_template('exam_list.html', exams=exams)
    except Error as e:
        print(f"Error: {e}")
        return redirect(url_for('index'))
    finally:
        if conn.is_connected():
            conn.close()
# 提交试卷
# ================== 修改提交试卷路由 ==================
@app.route('/submit/<int:exam_id>', methods=['POST'])
def submit(exam_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    answers = {k: v for k, v in request.form.items() if k.startswith('q_')}
    score = 0
    conn = get_db_connection()
    if not conn:
        flash('数据库连接失败')
        return redirect(url_for('index'))
    
    try:
        cursor = conn.cursor()
        # 计算总分（使用题目的分值）
        for q_id, user_ans in answers.items():
            q_id = q_id.replace('q_', '')
            cursor.execute("SELECT answer, score FROM questions WHERE id=%s", (q_id,))
            result = cursor.fetchone()
            if result:
                correct_ans, question_score = result
                if user_ans == correct_ans:
                    score += question_score
        
        # 检查用户是否已参加过此考试
        cursor.execute('''
            SELECT id FROM test_papers 
            WHERE user_id = %s AND exam_id = %s
        ''', (session['user_id'], exam_id))
        existing_record = cursor.fetchone()
        
        if existing_record:
            # 更新现有记录
            cursor.execute('''
                UPDATE test_papers 
                SET score = %s, start_time = %s
                WHERE id = %s
            ''', (score, datetime.datetime.now(), existing_record[0]))
            flash('您已更新了考试成绩')
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO test_papers (user_id, exam_id, score, start_time)
                VALUES (%s, %s, %s, %s)
            ''', (session['user_id'], exam_id, score, datetime.datetime.now()))
            flash('考试提交成功')
            
        conn.commit()
        return redirect(url_for('profile'))
    except Error as e:
        print(f"Error: {e}")
        return redirect(url_for('index'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# 注册功能
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_pw = generate_password_hash(password)
        
        conn = get_db_connection()
        if not conn:
            flash('数据库连接失败')
            return redirect(url_for('register'))
        
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", 
                         (username, hashed_pw))
            conn.commit()
            flash('注册成功！请登录')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('用户名已存在')
        except Error as e:
            print(f"Error: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('register.html')


# 添加上传路由
@app.route('/upload', methods=['GET', 'POST'])
@admin_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('未选择文件')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('未选择文件')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            try:
                # 读取Excel文件
                df = pd.read_excel(file)
                
                # 统计信息
                total_questions = 0
                duplicates = 0
                
                # 插入数据库
                conn = get_db_connection()
                cursor = conn.cursor()
                
                for _, row in df.iterrows():
                    question_text = row['题目']
                    options_str = ','.join(row['选项'].split(','))
                    answer = row['正确答案']
                    
                    total_questions += 1
                    
                    # 检查题目是否重复
                    if is_duplicate_question(cursor, question_text):
                        duplicates += 1
                        continue
                    
                    # 插入新题目
                    cursor.execute('''
                        INSERT INTO questions (question, options, answer)
                        VALUES (%s, %s, %s)
                    ''', (question_text, options_str, answer))
                
                conn.commit()
                
                if duplicates > 0:
                    flash(f'成功上传{total_questions - duplicates}道题目，跳过{duplicates}道重复题目')
                else:
                    flash(f'成功上传{total_questions}道题目')
                    
            except Exception as e:
                print(f"解析错误: {e}")
                flash('文件格式不正确')
            finally:
                if conn.is_connected():
                    cursor.close()
                    conn.close()
            return redirect(url_for('upload'))
        else:
            flash('仅支持Excel文件')
    return render_template('upload.html')
# ================== 修改题目分值路由 ==================
@app.route('/update_question_score/<int:question_id>', methods=['POST'])
@admin_required
def update_question_score(question_id):
    """更新题目分值"""
    score = request.form.get('score')
    
    if not score or not score.isdigit() or int(score) <= 0:
        flash('分值必须是正整数', 'error')
        return redirect(url_for('question_bank'))
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE questions SET score = %s WHERE id = %s", (int(score), question_id))
        conn.commit()
        flash('题目分值更新成功', 'success')
    except Error as e:
        print(f"数据库错误: {e}")
        flash('分值更新失败', 'error')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('question_bank'))
# ------------------------- 用户管理功能 -------------------------
@app.route('/user_management')
@admin_required
def user_management():
    """用户管理页面"""
    conn = get_db_connection()
    if not conn:
        flash('数据库连接失败', 'error')
        return redirect(url_for('index'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, is_admin, created_at FROM users")
        users = cursor.fetchall()
        return render_template('user_management.html', users=users)
    except Error as e:
        print(f"数据库错误: {e}")
        flash('获取用户列表失败', 'error')
        return redirect(url_for('index'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/add_user', methods=['POST'])
@admin_required
def add_user():
    """添加用户"""
    username = request.form.get('username')
    password = request.form.get('password')
    is_admin = True if request.form.get('is_admin') == 'on' else False

    if not username or not password:
        flash('用户名和密码不能为空', 'error')
        return redirect(url_for('user_management'))

    hashed_pw = generate_password_hash(password)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, %s)",
            (username, hashed_pw, is_admin)
        )
        conn.commit()
        flash('用户添加成功', 'success')
    except mysql.connector.IntegrityError:
        flash('用户名已存在', 'error')
    except Error as e:
        print(f"数据库错误: {e}")
        flash('用户添加失败', 'error')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('user_management'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """删除用户"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        flash('用户删除成功', 'success')
    except Error as e:
        print(f"数据库错误: {e}")
        conn.rollback()
        flash('用户删除失败', 'error')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return redirect(url_for('user_management'))
# ================== 修改题库管理路由 ==================
@app.route('/question_bank')
@admin_required
def question_bank():
    conn = get_db_connection()
    if not conn:
        flash('数据库连接失败')
        return redirect(url_for('index'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, question, options, answer, score FROM questions ORDER BY id")
        questions = cursor.fetchall()
        return render_template('question_bank.html', questions=questions)
    except Error as e:
        print(f"Error: {e}")
        flash('获取题库失败')
        return redirect(url_for('index'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
# 新增删除题目路由
@app.route('/delete_question/<int:question_id>', methods=['POST'])
@admin_required
def delete_question(question_id):
    conn = get_db_connection()
    if not conn:
        flash('数据库连接失败')
        return redirect(url_for('question_bank'))
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
        conn.commit()
        flash('题目删除成功')
    except Error as e:
        print(f"Error: {e}")
        conn.rollback()
        flash('题目删除失败')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('question_bank'))

# 个人中心
# ================== 修改个人中心查询 ==================
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        flash('数据库连接失败')
        return redirect(url_for('index'))
    
    try:
        cursor = conn.cursor()
        # 修改查询，只获取每个考试的最后一次记录
        cursor.execute('''
            SELECT e.exam_name, tp.score, tp.start_time 
            FROM test_papers tp 
            JOIN exams e ON tp.exam_id = e.id 
            WHERE tp.user_id = %s
            ORDER BY tp.start_time DESC
        ''', (session['user_id'],))
        history = cursor.fetchall()
        return render_template('profile.html', history=history)
    except Error as e:
        print(f"Error: {e}")
        return redirect(url_for('index'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# 登录功能
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        if not conn:
            flash('数据库连接失败')
            return redirect(url_for('login'))
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['is_admin'] = user[3]
                return redirect(url_for('index'))
            else:
                flash('用户名或密码错误')
        except Error as e:
            print(f"Error: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    return render_template('login.html')
# 退出登录功能
@app.route('/logout')
def logout():
    # 清除会话中的所有用户数据
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    # 重定向到首页
    return redirect(url_for('index'))

# ================== 修改创建考试路由 ==================
@app.route('/create_exam', methods=['GET', 'POST'])
@admin_required
def create_exam():
    if request.method == 'GET':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, question, score FROM questions ORDER BY id")
        questions = cursor.fetchall()
        conn.close()
        if not questions:
            flash('请先上传题目')
            return redirect(url_for('upload'))
        return render_template('create_exam.html', questions=questions)
    
    if request.method == 'POST':
        exam_name = request.form['exam_name']
        question_ids = request.form.getlist('question_ids')
        start_time = datetime.datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
        end_time = datetime.datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
        question_ids_str = ','.join(question_ids)
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO exams (exam_name, question_ids, start_time, end_time)
                           VALUES (%s, %s, %s, %s)''',
                           (exam_name, question_ids_str, start_time, end_time))
            conn.commit()
            flash('考试创建成功')
            return redirect(url_for('exam_list'))
        except Error as e:
            print(f"Error: {e}")
            flash('考试创建失败')
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
# ================== 修改考试成绩查询 ==================
@app.route('/exam_results/<int:exam_id>')
@admin_required
def exam_results(exam_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 获取考试信息
        cursor.execute('''
            SELECT id, exam_name, start_time, end_time 
            FROM exams 
            WHERE id = %s
        ''', (exam_id,))
        exam = cursor.fetchone()
        
        if not exam:
            flash('考试不存在')
            return redirect(url_for('exam_list'))
        
        # 获取考试成绩 - 只获取每个用户的最后一次考试记录
        cursor.execute('''
            SELECT tp.id, tp.user_id, u.username, tp.score, tp.start_time,
                   TIMESTAMPDIFF(MINUTE, tp.start_time, NOW()) as duration
            FROM test_papers tp
            JOIN users u ON tp.user_id = u.id
            WHERE tp.exam_id = %s
            AND tp.start_time = (
                SELECT MAX(start_time) 
                FROM test_papers 
                WHERE user_id = tp.user_id AND exam_id = %s
            )
            ORDER BY tp.score DESC
        ''', (exam_id, exam_id))
        results = cursor.fetchall()
        
        # 计算平均分和最高分
        avg_score = 0
        max_score = 0
        if results:
            total_score = sum(result['score'] for result in results)
            avg_score = round(total_score / len(results), 1)
            max_score = max(result['score'] for result in results)
        
        return render_template('exam_results.html', 
                              exam=exam, 
                              results=results, 
                              avg_score=avg_score, 
                              max_score=max_score)
    except Error as e:
        print(f"Error: {e}")
        flash('获取考试成绩失败')
        return redirect(url_for('exam_list'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now()}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=39801, debug=True)