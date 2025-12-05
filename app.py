"""
NavHub - 轻量级导航页后端
Flask + SQLite 方案
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import secrets
import os
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = secrets.token_hex(32)  # 每次启动随机生成，重启后登录失效

# 配置（支持环境变量，便于 Docker 部署）
DATABASE = os.environ.get('DATABASE_PATH', 'data.db')

# Token 存储 (简单实现，生产环境建议用 Redis)
active_tokens = {}

# 登录失败计数器（防暴力破解）
login_attempts = {}  # {ip: {'count': 0, 'locked_until': datetime}}
MAX_LOGIN_ATTEMPTS = 5  # 最大尝试次数
LOCKOUT_DURATION = 15  # 锁定时间（分钟）

def get_db():
    """获取数据库连接"""
    # 确保数据库目录存在（Docker 挂载卷时可能为空）
    db_dir = os.path.dirname(DATABASE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, mode=0o755, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE, timeout=10)  # 10秒超时，避免数据库锁定错误
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 创建分类表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建链接表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            icon TEXT,
            description TEXT,
            category_id INTEGER,
            is_hidden INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    
    # 创建配置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # 创建私密书签表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 检查是否需要插入默认数据
    cursor.execute('SELECT COUNT(*) FROM categories')
    if cursor.fetchone()[0] == 0:
        # 插入默认分类
        default_categories = [
            ('搜索引擎', None, 1),
            ('社交媒体', None, 2),
            ('开发工具', None, 3),
            ('AI 工具', None, 4),
            ('影音娱乐', None, 5),
            ('实用工具', None, 6),
        ]
        cursor.executemany(
            'INSERT INTO categories (name, parent_id, sort_order) VALUES (?, ?, ?)',
            default_categories
        )
        
        # 插入默认链接
        default_links = [
            # 搜索引擎
            ('Google', 'https://www.google.com', None, '全球最大的搜索引擎', 1, 0, 1),
            ('Bing', 'https://www.bing.com', None, '微软必应搜索', 1, 0, 2),
            ('DuckDuckGo', 'https://duckduckgo.com', None, '注重隐私的搜索引擎', 1, 0, 3),
            
            # 开发工具
            ('GitHub', 'https://github.com', None, '代码托管与协作平台', 3, 0, 1),
            
            # AI 工具
            ('ChatGPT', 'https://chat.openai.com', None, 'OpenAI 对话式 AI', 4, 0, 1),
            ('Claude', 'https://claude.ai', None, 'Anthropic AI 助手', 4, 0, 2),
            ('Midjourney', 'https://www.midjourney.com', None, 'AI 绘画工具', 4, 0, 3),
            
            # 影音娱乐
            ('YouTube', 'https://www.youtube.com', None, '全球最大视频平台', 5, 0, 1),
            ('Bilibili', 'https://www.bilibili.com', None, '国内弹幕视频网站', 5, 0, 2),
            ('Spotify', 'https://www.spotify.com', None, '流媒体音乐平台', 5, 0, 3),
            ('Netflix', 'https://www.netflix.com', None, '流媒体影视平台', 5, 0, 4),
            
            # 隐藏链接示例
            ('Secret Site', 'https://example.com/secret', None, '这是一个隐藏链接示例', 6, 1, 99),
        ]
        cursor.executemany(
            '''INSERT INTO links (title, url, icon, description, category_id, is_hidden, sort_order) 
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            default_links
        )
        print("已插入默认演示数据")
    
    conn.commit()
    conn.close()

def hash_password(password):
    """安全的密码哈希（使用 PBKDF2 + Salt）"""
    return generate_password_hash(password, method='pbkdf2:sha256')

def verify_password(password, password_hash):
    """验证密码"""
    return check_password_hash(password_hash, password)

def is_strong_password(password):
    """检查密码是否为至少8位字母与数字的组合"""
    if not password or len(password) < 8:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit

def get_config(key):
    """获取配置"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else None

def set_config(key, value):
    """设置配置"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def require_auth(f):
    """需要认证的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token or token not in active_tokens:
            return jsonify({'error': '未授权'}), 401
        # 检查 token 是否过期
        if active_tokens[token] < datetime.now():
            del active_tokens[token]
            return jsonify({'error': 'Token 已过期'}), 401
        return f(*args, **kwargs)
    return decorated

# ==================== 页面路由 ====================

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """后台管理页（默认路径）"""
    # 检查是否设置了自定义路径
    custom_path = get_config('admin_path')
    if custom_path and custom_path != '/admin':
        # 如果设置了自定义路径，默认路径返回 404
        return render_template('404.html'), 404
    return render_template('admin.html')

@app.route('/<path:custom_path>')
def custom_admin(custom_path):
    """自定义后台路径"""
    # 获取数据库中存储的自定义路径
    stored_path = get_config('admin_path')
    # 比较请求路径（加上前导斜杠）
    if stored_path and stored_path.lstrip('/') == custom_path:
        return render_template('admin.html')
    # 不匹配则返回 404
    return render_template('404.html'), 404

@app.errorhandler(404)
def page_not_found(e):
    """全局 404 处理"""
    return render_template('404.html'), 404

# ==================== API 路由 ====================

@app.route('/api/init', methods=['POST'])
def api_init():
    """初始化管理员账号（仅首次）"""
    if get_config('admin_password'):
        return jsonify({'error': '已初始化'}), 400
    
    data = request.json
    password = data.get('password')
    if not is_strong_password(password):
        return jsonify({'error': '密码至少8位，需包含字母和数字'}), 400
    
    # 设置默认用户名为 admin
    set_config('admin_username', 'admin')
    set_config('admin_password', hash_password(password))
    return jsonify({'message': '初始化成功'})

def check_login_limit(ip):
    """检查是否超过登录限制"""
    if ip not in login_attempts:
        return True, None
    
    attempt = login_attempts[ip]
    
    # 检查是否在锁定期
    if 'locked_until' in attempt and attempt['locked_until'] > datetime.now():
        remaining = (attempt['locked_until'] - datetime.now()).seconds // 60 + 1
        return False, f'登录失败次数过多，请 {remaining} 分钟后重试'
    
    # 锁定期已过，重置计数
    if 'locked_until' in attempt and attempt['locked_until'] <= datetime.now():
        login_attempts[ip] = {'count': 0}
    
    return True, None

def record_login_failure(ip):
    """记录登录失败"""
    if ip not in login_attempts:
        login_attempts[ip] = {'count': 0}
    
    login_attempts[ip]['count'] += 1
    
    # 超过最大次数，锁定账户
    if login_attempts[ip]['count'] >= MAX_LOGIN_ATTEMPTS:
        login_attempts[ip]['locked_until'] = datetime.now() + timedelta(minutes=LOCKOUT_DURATION)

def clear_login_attempts(ip):
    """清除登录失败记录"""
    if ip in login_attempts:
        del login_attempts[ip]

@app.route('/api/login', methods=['POST'])
def api_login():
    """登录"""
    client_ip = request.remote_addr
    
    # 检查登录限制
    allowed, error_msg = check_login_limit(client_ip)
    if not allowed:
        return jsonify({'error': error_msg}), 429
    
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    
    stored_hash = get_config('admin_password')
    if not stored_hash:
        return jsonify({'error': '请先初始化密码', 'need_init': True}), 400
    
    # 验证用户名
    stored_username = get_config('admin_username') or 'admin'
    if username != stored_username:
        record_login_failure(client_ip)
        return jsonify({'error': '用户名或密码错误'}), 401
    
    # 验证密码
    if not verify_password(password, stored_hash):
        record_login_failure(client_ip)
        return jsonify({'error': '用户名或密码错误'}), 401
    
    # 登录成功，清除失败记录
    clear_login_attempts(client_ip)
    
    # 生成 token
    token = secrets.token_hex(32)
    active_tokens[token] = datetime.now() + timedelta(hours=24)
    
    return jsonify({'token': token, 'expires_in': 86400})

@app.route('/api/verify-hidden', methods=['POST'])
def api_verify_hidden():
    """验证隐藏密码"""
    client_ip = request.remote_addr
    
    # 检查登录限制
    allowed, error_msg = check_login_limit(client_ip)
    if not allowed:
        return jsonify({'error': error_msg}), 429
    
    data = request.json
    password = data.get('password', '')
    
    stored_hash = get_config('hidden_password')
    if not stored_hash:
        stored_hash = get_config('admin_password')
    
    if verify_password(password, stored_hash):
        # 验证成功，清除失败记录
        clear_login_attempts(client_ip)
        # 生成临时 token，有效期 10 分钟
        token = secrets.token_hex(16)
        active_tokens[f'hidden_{token}'] = datetime.now() + timedelta(minutes=10)
        return jsonify({'token': token, 'expires_in': 600})
    
    record_login_failure(client_ip)
    return jsonify({'error': '密码错误'}), 401

@app.route('/api/categories', methods=['GET'])
def api_get_categories():
    """获取所有分类"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories ORDER BY sort_order, id')
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(categories)

@app.route('/api/categories', methods=['POST'])
@require_auth
def api_create_category():
    """创建分类"""
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO categories (name, parent_id, sort_order) VALUES (?, ?, ?)',
        (data.get('name'), data.get('parent_id'), data.get('sort_order', 0))
    )
    conn.commit()
    category_id = cursor.lastrowid
    conn.close()
    return jsonify({'id': category_id, 'message': '创建成功'})

@app.route('/api/categories/<int:id>', methods=['PUT'])
@require_auth
def api_update_category(id):
    """更新分类"""
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE categories SET name = ?, parent_id = ?, sort_order = ? WHERE id = ?',
        (data.get('name'), data.get('parent_id'), data.get('sort_order', 0), id)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': '更新成功'})

@app.route('/api/categories/<int:id>', methods=['DELETE'])
@require_auth
def api_delete_category(id):
    """删除分类"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM categories WHERE id = ?', (id,))
    cursor.execute('UPDATE links SET category_id = NULL WHERE category_id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '删除成功'})

@app.route('/api/links', methods=['GET'])
def api_get_links():
    """获取链接列表"""
    show_hidden = request.args.get('show_hidden')
    hidden_token = request.args.get('hidden_token')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 检查是否有权限查看隐藏内容
    can_see_hidden = False
    
    # 方式1: 通过隐藏密码获取的临时 token
    if show_hidden and hidden_token:
        token_key = f'hidden_{hidden_token}'
        if token_key in active_tokens and active_tokens[token_key] > datetime.now():
            can_see_hidden = True
    
    # 方式2: 后台管理员登录的 token（Bearer token）
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        admin_token = auth_header.replace('Bearer ', '')
        if admin_token in active_tokens and active_tokens[admin_token] > datetime.now():
            can_see_hidden = True
    
    if can_see_hidden:
        cursor.execute('SELECT * FROM links ORDER BY sort_order, id')
    else:
        cursor.execute('SELECT * FROM links WHERE is_hidden = 0 ORDER BY sort_order, id')
    
    links = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(links)

@app.route('/api/links', methods=['POST'])
@require_auth
def api_create_link():
    """创建链接"""
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO links (title, url, icon, description, category_id, is_hidden, sort_order) 
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (
            data.get('title'),
            data.get('url'),
            data.get('icon'),
            data.get('description'),
            data.get('category_id'),
            1 if data.get('is_hidden') else 0,
            data.get('sort_order', 0)
        )
    )
    conn.commit()
    link_id = cursor.lastrowid
    conn.close()
    return jsonify({'id': link_id, 'message': '创建成功'})

@app.route('/api/links/<int:id>', methods=['PUT'])
@require_auth
def api_update_link(id):
    """更新链接"""
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''UPDATE links SET title = ?, url = ?, icon = ?, description = ?, 
           category_id = ?, is_hidden = ?, sort_order = ? WHERE id = ?''',
        (
            data.get('title'),
            data.get('url'),
            data.get('icon'),
            data.get('description'),
            data.get('category_id'),
            1 if data.get('is_hidden') else 0,
            data.get('sort_order', 0),
            id
        )
    )
    conn.commit()
    conn.close()
    return jsonify({'message': '更新成功'})

@app.route('/api/links/<int:id>', methods=['DELETE'])
@require_auth
def api_delete_link(id):
    """删除链接"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM links WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '删除成功'})

@app.route('/api/links/reorder', methods=['PUT'])
@require_auth
def api_reorder_links():
    """批量更新链接排序"""
    data = request.json
    orders = data.get('orders', [])  # [{id: 1, sort_order: 0}, ...]
    
    conn = get_db()
    cursor = conn.cursor()
    for item in orders:
        cursor.execute('UPDATE links SET sort_order = ? WHERE id = ?', 
                      (item['sort_order'], item['id']))
    conn.commit()
    conn.close()
    return jsonify({'message': '排序更新成功'})

@app.route('/api/categories/reorder', methods=['PUT'])
@require_auth
def api_reorder_categories():
    """批量更新分类排序"""
    data = request.json
    orders = data.get('orders', [])  # [{id: 1, sort_order: 0}, ...]
    
    conn = get_db()
    cursor = conn.cursor()
    for item in orders:
        cursor.execute('UPDATE categories SET sort_order = ? WHERE id = ?', 
                      (item['sort_order'], item['id']))
    conn.commit()
    conn.close()
    return jsonify({'message': '排序更新成功'})

@app.route('/api/config/hidden-password', methods=['PUT'])
@require_auth
def api_update_hidden_password():
    """更新隐藏密码（可以和管理密码不同）"""
    data = request.json
    password = data.get('password')
    if not password or len(password) < 4:
        return jsonify({'error': '密码至少4位'}), 400
    set_config('hidden_password', hash_password(password))
    return jsonify({'message': '隐藏密码更新成功'})

@app.route('/api/site-settings', methods=['GET'])
def api_get_site_settings():
    """获取站点设置（公开）"""
    return jsonify({
        'site_title': get_config('site_title') or 'Nav',
        'site_icon': get_config('site_icon') or '🥭',
        'favicon': get_config('favicon') or '',
        'footer_text': get_config('footer_text') or '',
        'project_url': 'https://github.com/your-username/nav'  # 固定的项目地址
    })

@app.route('/api/site-settings', methods=['PUT'])
@require_auth
def api_update_site_settings():
    """更新站点设置"""
    data = request.json
    
    if 'site_title' in data:
        set_config('site_title', data['site_title'])
    if 'site_icon' in data:
        set_config('site_icon', data['site_icon'])
    if 'favicon' in data:
        set_config('favicon', data['favicon'])
    if 'footer_text' in data:
        set_config('footer_text', data['footer_text'])
    
    return jsonify({'message': '站点设置更新成功'})

@app.route('/api/admin-account', methods=['GET'])
@require_auth
def api_get_admin_account():
    """获取管理员账号信息（仅管理员）"""
    return jsonify({
        'username': get_config('admin_username') or 'admin'
    })

@app.route('/api/admin-account', methods=['PUT'])
@require_auth
def api_update_admin_account():
    """更新管理员账号（仅管理员）"""
    data = request.json
    
    # 更新用户名
    if 'username' in data:
        new_username = data['username'].strip()
        if not new_username or len(new_username) < 3:
            return jsonify({'error': '用户名至少3个字符'}), 400
        if len(new_username) > 32:
            return jsonify({'error': '用户名最多32个字符'}), 400
        set_config('admin_username', new_username)
    
    # 更新密码（可选）
    if 'password' in data and data['password']:
        new_password = data['password']
        if not is_strong_password(new_password):
            return jsonify({'error': '密码至少8位，需包含字母和数字'}), 400
        set_config('admin_password', hash_password(new_password))
    
    return jsonify({'message': '账号信息更新成功'})

@app.route('/api/admin-path', methods=['GET'])
@require_auth
def api_get_admin_path():
    """获取后台路径（仅管理员）"""
    return jsonify({
        'admin_path': get_config('admin_path') or '/admin'
    })

@app.route('/api/admin-path', methods=['PUT'])
@require_auth
def api_update_admin_path():
    """更新后台路径（仅管理员）"""
    data = request.json
    new_path = data.get('admin_path', '').strip()
    
    # 验证路径格式
    if not new_path:
        return jsonify({'error': '路径不能为空'}), 400
    
    if not new_path.startswith('/'):
        new_path = '/' + new_path
    
    if new_path == '/':
        return jsonify({'error': '不能使用根路径'}), 400
    
    # 不允许使用已存在的 API 路径
    reserved_paths = ['/api', '/static']
    if any(new_path.startswith(p) for p in reserved_paths):
        return jsonify({'error': '不能使用系统保留路径'}), 400
    
    # 保存新路径
    set_config('admin_path', new_path)
    
    return jsonify({
        'message': '后台路径已更新',
        'admin_path': new_path
    })

# ==================== 私密书签 API ====================

@app.route('/bookmarks')
def bookmarks_page():
    """私密书签页"""
    return render_template('bookmarks.html')

@app.route('/api/bookmarks/auth', methods=['POST'])
def api_bookmarks_auth():
    """书签页密码验证（独立密码，返回临时 token，不缓存）"""
    client_ip = request.remote_addr
    
    # 检查登录限制（与管理员登录共享限制）
    allowed, error_msg = check_login_limit(client_ip)
    if not allowed:
        return jsonify({'error': error_msg}), 429
    
    data = request.json
    password = data.get('password', '')
    
    stored_hash = get_config('bookmark_password')
    if not stored_hash:
        return jsonify({'error': '请先在后台设置书签密码'}), 400
    
    if not verify_password(password, stored_hash):
        record_login_failure(client_ip)
        return jsonify({'error': '密码错误'}), 401
    
    # 验证成功，清除失败记录
    clear_login_attempts(client_ip)
    
    # 生成短期 token，有效期 30 分钟
    token = secrets.token_hex(32)
    active_tokens[f'bookmark_{token}'] = datetime.now() + timedelta(minutes=30)
    
    return jsonify({'token': token, 'expires_in': 1800})

@app.route('/api/config/bookmark-password', methods=['PUT'])
@require_auth
def api_update_bookmark_password():
    """更新书签密码（仅管理员）"""
    data = request.json
    password = data.get('password')
    if not is_strong_password(password):
        return jsonify({'error': '密码至少8位，需包含字母和数字'}), 400
    set_config('bookmark_password', hash_password(password))
    return jsonify({'message': '书签密码更新成功'})

def require_bookmark_auth(f):
    """书签页认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        token_key = f'bookmark_{token}'
        if not token or token_key not in active_tokens:
            return jsonify({'error': '未授权'}), 401
        if active_tokens[token_key] < datetime.now():
            del active_tokens[token_key]
            return jsonify({'error': 'Token 已过期'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/bookmarks', methods=['GET'])
@require_bookmark_auth
def api_get_bookmarks():
    """获取所有书签"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookmarks ORDER BY sort_order, id DESC')
    bookmarks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(bookmarks)

@app.route('/api/bookmarks', methods=['POST'])
@require_bookmark_auth
def api_create_bookmark():
    """创建书签"""
    data = request.json
    title = data.get('title', '').strip()
    url = data.get('url', '').strip()
    
    if not title or not url:
        return jsonify({'error': '标题和链接不能为空'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO bookmarks (title, url, sort_order) VALUES (?, ?, ?)',
        (title, url, 0)
    )
    conn.commit()
    bookmark_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'id': bookmark_id, 'message': '添加成功'})

@app.route('/api/bookmarks/<int:id>', methods=['DELETE'])
@require_bookmark_auth
def api_delete_bookmark(id):
    """删除书签"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bookmarks WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'message': '删除成功'})

# ==================== 启动 ====================

# 确保数据库初始化（无论是直接运行还是通过 gunicorn 启动）
init_db()

if __name__ == '__main__':
    # 通过环境变量控制是否开启 debug 模式
    # 生产环境: DEBUG=0 或不设置
    # 开发环境: DEBUG=1
    debug_mode = os.environ.get('DEBUG', '0') == '1'
    
    print("=" * 50)
    print("NavHub 导航页后端已启动")
    print(f"运行模式: {'开发模式 (DEBUG)' if debug_mode else '生产模式'}")
    print("首页: http://localhost:6966")
    print("后台: http://localhost:6966/admin")
    print("=" * 50)
    app.run(host='0.0.0.0', port=6966, debug=debug_mode)
