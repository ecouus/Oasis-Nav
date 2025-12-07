"""
Oasis-Nav - 轻量级导航页后端
Flask + SQLite 方案
"""

from flask import Flask, request, jsonify, render_template, send_from_directory, session, Response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from urllib.parse import urlparse
import sqlite3
import secrets
import os
import re
import hashlib
import requests
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = secrets.token_hex(32)  # 每次启动随机生成，重启后登录失效

# CSRF Token 存储
csrf_tokens = {}

# 配置（支持环境变量，便于 Docker 部署）
DATABASE = os.environ.get('DATABASE_PATH', 'data.db')

# 图标缓存配置
ICON_CACHE_DIR = os.environ.get('ICON_CACHE_DIR', 'icon_cache')
ICON_CACHE_EXPIRE_DAYS = 7  # 缓存过期天数

# Token 存储 (简单实现，生产环境建议用 Redis)
# 结构: {token: {'expires': datetime, 'ip': str}}
active_tokens = {}

# 登录失败计数器（防暴力破解）
login_attempts = {}  # {ip: {'count': 0, 'locked_until': datetime}}
MAX_LOGIN_ATTEMPTS = 5  # 最大尝试次数
LOCKOUT_DURATION = 15  # 锁定时间（分钟）

def get_client_ip():
    """获取真实客户端 IP（支持反向代理）"""
    # 优先从 X-Forwarded-For 获取（Nginx 转发）
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # X-Forwarded-For 可能包含多个 IP，取第一个（真实客户端 IP）
        return forwarded_for.split(',')[0].strip()
    # 其次从 X-Real-IP 获取（Nginx 直接设置）
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    # 最后使用 remote_addr（直接访问或没有配置 Nginx）
    return request.remote_addr

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
    # 使用 150,000 次迭代，在安全性和性能之间取得平衡
    return generate_password_hash(password, method='pbkdf2:sha256:150000')

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

def is_valid_url(url):
    """验证 URL 是否安全"""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        # 禁止危险协议
        dangerous_schemes = ['javascript', 'data', 'vbscript', 'file']
        if parsed.scheme.lower() in dangerous_schemes:
            return False
        # 只允许 http/https 或相对路径
        if parsed.scheme and parsed.scheme.lower() not in ['http', 'https']:
            return False
        # 检查是否包含可疑的 JavaScript 代码
        suspicious_patterns = [
            r'javascript:', r'on\w+\s*=', r'<script', r'</script>',
            r'data:', r'vbscript:'
        ]
        url_lower = url.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, url_lower, re.IGNORECASE):
                return False
        return True
    except Exception:
        return False

def generate_csrf_token():
    """生成 CSRF Token"""
    token = secrets.token_hex(32)
    csrf_tokens[token] = datetime.now() + timedelta(hours=24)
    return token

def validate_csrf_token(token):
    """验证 CSRF Token"""
    if not token or token not in csrf_tokens:
        return False
    if csrf_tokens[token] < datetime.now():
        del csrf_tokens[token]
        return False
    return True

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
        
        token_info = active_tokens[token]
        # 检查 token 是否过期
        if token_info['expires'] < datetime.now():
            del active_tokens[token]
            return jsonify({'error': 'Token 已过期'}), 401
        
        # 检查 IP 绑定（如果开启，且 token 有记录 IP）
        ip_binding_enabled = get_config('ip_binding_enabled') == '1'
        if ip_binding_enabled and token_info.get('ip'):  # 只有当 ip 值存在且不为 None 时才检查
            client_ip = request.remote_addr
            if token_info['ip'] != client_ip:
                return jsonify({'error': 'IP 地址不匹配'}), 401
        
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

def check_csrf():
    """检查 CSRF（通过验证 Origin/Referer 头）"""
    # GET 请求不需要检查
    if request.method == 'GET':
        return True
    
    # 获取 Origin 或 Referer
    origin = request.headers.get('Origin', '')
    referer = request.headers.get('Referer', '')
    
    # 如果没有 Origin 和 Referer，拒绝请求（可能是跨站请求）
    # 但允许本地开发时没有这些头
    if not origin and not referer:
        # 允许没有 Origin/Referer 的请求（某些情况下浏览器不发送）
        return True
    
    # 获取当前请求的 Host
    host = request.headers.get('Host', '')
    
    # 验证 Origin 或 Referer 是否匹配当前 Host
    if origin:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            if parsed.netloc != host:
                return False
        except:
            return False
    elif referer:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            if parsed.netloc != host:
                return False
        except:
            return False
    
    return True

@app.before_request
def csrf_protect():
    """CSRF 防护中间件"""
    # 只检查修改数据的请求
    if request.method in ['POST', 'PUT', 'DELETE']:
        # 排除登录和初始化 API（这些需要从任何来源访问）
        safe_endpoints = ['/api/login', '/api/init', '/api/verify-hidden', '/api/verify-bookmark']
        if request.path not in safe_endpoints:
            if not check_csrf():
                return jsonify({'error': '请求来源验证失败'}), 403

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

@app.route('/api/check-init', methods=['GET'])
def api_check_init():
    """检查是否已初始化（不需要认证，不记录失败）"""
    initialized = bool(get_config('admin_password'))
    return jsonify({'initialized': initialized, 'need_init': not initialized})

@app.route('/api/verify-token', methods=['GET'])
@require_auth
def api_verify_token():
    """验证 token 是否有效（需要认证）"""
    return jsonify({'valid': True})

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
    client_ip = get_client_ip()
    
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
    
    # 生成 token，有效期 30 分钟
    token = secrets.token_hex(32)
    expires = datetime.now() + timedelta(minutes=30)
    
    # 如果开启 IP 绑定，记录 IP
    ip_binding_enabled = get_config('ip_binding_enabled') == '1'
    active_tokens[token] = {
        'expires': expires,
        'ip': client_ip if ip_binding_enabled else None
    }
    
    return jsonify({'token': token, 'expires_in': 1800})

@app.route('/api/verify-hidden', methods=['POST'])
def api_verify_hidden():
    """验证隐藏密码"""
    client_ip = get_client_ip()
    
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
        # 生成临时 token，有效期 2 分钟（仅用于当前页面会话，刷新后前端会清除）
        token = secrets.token_hex(16)
        expires = datetime.now() + timedelta(minutes=2)
        
        # 如果开启 IP 绑定，记录 IP
        ip_binding_enabled = get_config('ip_binding_enabled') == '1'
        active_tokens[f'hidden_{token}'] = {
            'expires': expires,
            'ip': client_ip if ip_binding_enabled else None
        }
        return jsonify({'token': token, 'expires_in': 120})
    
    record_login_failure(client_ip)
    return jsonify({'error': '密码错误'}), 401

# ==================== 图标代理 ====================

def get_icon_cache_path(icon_url):
    """根据 URL 生成缓存文件路径"""
    # 使用 MD5 哈希作为文件名
    cache_key = hashlib.md5(icon_url.encode()).hexdigest()
    return os.path.join(ICON_CACHE_DIR, f"{cache_key}.ico")

def get_icon_meta_path(icon_url):
    """获取图标元信息文件路径"""
    cache_key = hashlib.md5(icon_url.encode()).hexdigest()
    return os.path.join(ICON_CACHE_DIR, f"{cache_key}.meta")

def is_cache_valid(cache_path):
    """检查缓存是否有效（未过期）"""
    if not os.path.exists(cache_path):
        return False
    
    # 检查文件修改时间
    file_mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
    expire_time = file_mtime + timedelta(days=ICON_CACHE_EXPIRE_DAYS)
    return datetime.now() < expire_time

def save_icon_to_cache(icon_url, content, content_type):
    """保存图标到缓存"""
    # 确保缓存目录存在
    if not os.path.exists(ICON_CACHE_DIR):
        os.makedirs(ICON_CACHE_DIR, mode=0o755, exist_ok=True)
    
    cache_path = get_icon_cache_path(icon_url)
    meta_path = get_icon_meta_path(icon_url)
    
    # 保存图标文件
    with open(cache_path, 'wb') as f:
        f.write(content)
    
    # 保存元信息（Content-Type）
    with open(meta_path, 'w') as f:
        f.write(content_type)

def load_icon_from_cache(icon_url):
    """从缓存加载图标"""
    cache_path = get_icon_cache_path(icon_url)
    meta_path = get_icon_meta_path(icon_url)
    
    if not is_cache_valid(cache_path):
        return None, None
    
    try:
        with open(cache_path, 'rb') as f:
            content = f.read()
        
        content_type = 'image/x-icon'  # 默认类型
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                content_type = f.read().strip() or content_type
        
        return content, content_type
    except Exception:
        return None, None

@app.route('/api/icon-proxy', methods=['GET'])
def api_icon_proxy():
    """图标代理：从服务器端获取图标并返回给客户端，支持文件缓存"""
    icon_url = request.args.get('url')
    
    if not icon_url:
        return jsonify({'error': '缺少 url 参数'}), 400
    
    # 验证 URL 安全性
    if not is_valid_url(icon_url):
        return jsonify({'error': 'URL 格式无效或包含不安全内容'}), 400
    
    # 尝试从缓存加载
    cached_content, cached_type = load_icon_from_cache(icon_url)
    if cached_content:
        return Response(
            cached_content,
            mimetype=cached_type,
            headers={
                'Cache-Control': 'public, max-age=86400',
                'Content-Length': str(len(cached_content)),
                'X-Cache': 'HIT'  # 标记缓存命中
            }
        )
    
    # 缓存未命中，从源站获取
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        }
        
        response = requests.get(
            icon_url,
            headers=headers,
            timeout=10,
            stream=True,
            allow_redirects=True
        )
        
        response.raise_for_status()
        
        # 限制文件大小（1MB）
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > 1024 * 1024:
            return jsonify({'error': '文件过大'}), 400
        
        # 读取内容
        content = b''
        max_size = 1024 * 1024
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > max_size:
                return jsonify({'error': '文件过大'}), 400
        
        # 获取 Content-Type
        content_type = response.headers.get('Content-Type', 'image/x-icon')
        
        # 保存到缓存
        try:
            save_icon_to_cache(icon_url, content, content_type)
        except Exception as e:
            print(f"保存图标缓存失败: {e}")
        
        return Response(
            content,
            mimetype=content_type,
            headers={
                'Cache-Control': 'public, max-age=86400',
                'Content-Length': str(len(content)),
                'X-Cache': 'MISS'  # 标记缓存未命中
            }
        )
        
    except requests.exceptions.Timeout:
        return jsonify({'error': '请求超时'}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'获取图标失败'}), 502
    except Exception as e:
        return jsonify({'error': '服务器错误'}), 500

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
    name = data.get('name', '').strip()
    
    # 验证分类名称
    if not name:
        return jsonify({'error': '分类名称不能为空'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO categories (name, parent_id, sort_order) VALUES (?, ?, ?)',
        (name, data.get('parent_id'), data.get('sort_order', 0))
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
    name = data.get('name', '').strip()
    
    # 验证分类名称
    if not name:
        return jsonify({'error': '分类名称不能为空'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE categories SET name = ?, parent_id = ?, sort_order = ? WHERE id = ?',
        (name, data.get('parent_id'), data.get('sort_order', 0), id)
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
    
    # 如果删除的是默认分类，清除默认分类设置
    default_cat = get_config('default_category_id')
    if default_cat and int(default_cat) == id:
        set_config('default_category_id', '')
    
    return jsonify({'message': '删除成功'})

@app.route('/api/default-category', methods=['GET'])
def api_get_default_category():
    """获取默认分类 ID"""
    default_id = get_config('default_category_id')
    return jsonify({'default_category_id': int(default_id) if default_id else None})

@app.route('/api/default-category', methods=['PUT'])
@require_auth
def api_set_default_category():
    """设置默认分类"""
    data = request.json
    category_id = data.get('category_id')
    
    if category_id:
        # 验证分类是否存在
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM categories WHERE id = ?', (category_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': '分类不存在'}), 400
        conn.close()
        set_config('default_category_id', str(category_id))
    else:
        # 清除默认分类
        set_config('default_category_id', '')
    
    return jsonify({'message': '默认分类设置成功'})

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
        if token_key in active_tokens:
            token_info = active_tokens[token_key]
            if token_info['expires'] > datetime.now():
                # 检查 IP 绑定（如果开启）
                ip_binding_enabled = get_config('ip_binding_enabled') == '1'
                if not ip_binding_enabled or token_info.get('ip') == get_client_ip():
                    can_see_hidden = True
    
    # 方式2: 后台管理员登录的 token（Bearer token）
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        admin_token = auth_header.replace('Bearer ', '')
        if admin_token in active_tokens:
            token_info = active_tokens[admin_token]
            if token_info['expires'] > datetime.now():
                # 检查 IP 绑定（如果开启）
                ip_binding_enabled = get_config('ip_binding_enabled') == '1'
                if not ip_binding_enabled or token_info.get('ip') == get_client_ip():
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
    title = data.get('title', '').strip()
    url = data.get('url', '').strip()
    
    # 验证必填字段
    if not title:
        return jsonify({'error': '链接标题不能为空'}), 400
    if not url:
        return jsonify({'error': '链接地址不能为空'}), 400
    
    # 验证 URL 安全性
    if not is_valid_url(url):
        return jsonify({'error': 'URL 格式无效或包含不安全内容'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO links (title, url, icon, description, category_id, is_hidden, sort_order) 
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (
            title,
            url,
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
    title = data.get('title', '').strip()
    url = data.get('url', '').strip()
    
    # 验证必填字段
    if not title:
        return jsonify({'error': '链接标题不能为空'}), 400
    if not url:
        return jsonify({'error': '链接地址不能为空'}), 400
    
    # 验证 URL 安全性
    if not is_valid_url(url):
        return jsonify({'error': 'URL 格式无效或包含不安全内容'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''UPDATE links SET title = ?, url = ?, icon = ?, description = ?, 
           category_id = ?, is_hidden = ?, sort_order = ? WHERE id = ?''',
        (
            title,
            url,
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
        'site_title': get_config('site_title') or 'Oasis-Nav',
        'site_icon': get_config('site_icon') or '🥭',
        'favicon': get_config('favicon') or '',
        'footer_text': get_config('footer_text') or '',
        'bookmark_hidden': get_config('bookmark_hidden') == '1',  # 书签是否隐藏
        'project_url': 'https://github.com/ecouus/Oasis-Nav'  # 固定的项目地址
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
    if 'bookmark_hidden' in data:
        set_config('bookmark_hidden', '1' if data['bookmark_hidden'] else '0')
    
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

@app.route('/api/security-settings', methods=['GET'])
@require_auth
def api_get_security_settings():
    """获取安全设置（仅管理员）"""
    return jsonify({
        'ip_binding_enabled': get_config('ip_binding_enabled') == '1'
    })

@app.route('/api/security-settings', methods=['PUT'])
@require_auth
def api_update_security_settings():
    """更新安全设置（仅管理员）"""
    data = request.json
    if 'ip_binding_enabled' in data:
        set_config('ip_binding_enabled', '1' if data['ip_binding_enabled'] else '0')
    return jsonify({'message': '安全设置更新成功'})

# ==================== 私密书签 API ====================

@app.route('/bookmarks')
def bookmarks_page():
    """私密书签页"""
    return render_template('bookmarks.html')

@app.route('/api/bookmarks/check', methods=['GET'])
def api_bookmarks_check():
    """检查书签是否需要认证"""
    is_hidden = get_config('bookmark_hidden') == '1'
    return jsonify({
        'need_auth': is_hidden,
        'has_password': bool(get_config('bookmark_password'))
    })

@app.route('/api/bookmarks/auth', methods=['POST'])
def api_bookmarks_auth():
    """书签页密码验证（独立密码，返回临时 token，不缓存）"""
    client_ip = get_client_ip()
    
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
    
    # 生成短期 token，有效期 5 分钟（仅用于当前页面会话，刷新后前端会清除）
    token = secrets.token_hex(32)
    expires = datetime.now() + timedelta(minutes=5)
    
    # 如果开启 IP 绑定，记录 IP
    ip_binding_enabled = get_config('ip_binding_enabled') == '1'
    active_tokens[f'bookmark_{token}'] = {
        'expires': expires,
        'ip': client_ip if ip_binding_enabled else None
    }
    
    return jsonify({'token': token, 'expires_in': 300})

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
    """书签页认证装饰器（如果书签未隐藏则跳过认证）"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 如果书签没有设置为隐藏，则无需认证
        if get_config('bookmark_hidden') != '1':
            return f(*args, **kwargs)
        
        # 书签已隐藏，需要验证 token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        token_key = f'bookmark_{token}'
        if not token or token_key not in active_tokens:
            return jsonify({'error': '未授权'}), 401
        
        token_info = active_tokens[token_key]
        if token_info['expires'] < datetime.now():
            del active_tokens[token_key]
            return jsonify({'error': 'Token 已过期'}), 401
        
        # 检查 IP 绑定（如果开启，且 token 有记录 IP）
        ip_binding_enabled = get_config('ip_binding_enabled') == '1'
        if ip_binding_enabled and token_info.get('ip'):  # 只有当 ip 值存在且不为 None 时才检查
            client_ip = get_client_ip()
            if token_info['ip'] != client_ip:
                return jsonify({'error': 'IP 地址不匹配'}), 401
        
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
    print("Oasis-Nav 导航页后端已启动")
    print(f"运行模式: {'开发模式 (DEBUG)' if debug_mode else '生产模式'}")
    print("首页: http://localhost:6966")
    print("后台: http://localhost:6966/admin")
    print("=" * 50)
    app.run(host='0.0.0.0', port=6966, debug=debug_mode)
