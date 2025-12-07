# Oasis-Nav

轻量级导航页应用，基于 Flask + SQLite 构建。
## ✨ 功能特性

- 🎯 简洁美观的导航页界面
- 📁 多级分类管理
- 🔖 私密书签收藏
- 🔒 多重密码保护（管理员/隐藏链接/书签）
- 🌐 图标代理与本地缓存
- 🐳 Docker 一键部署
- 📱 响应式设计，支持多主题
![demo截图](https://youke1.picui.cn/s1/2025/12/07/69352e8cd663b.png)
## 🪶 轻量级设计

Oasis-Nav 采用极简架构，追求最小资源占用：

- **极简依赖**：仅需 3 个核心依赖包（Flask、Gunicorn、Requests）
- **无数据库服务**：使用 SQLite，无需独立数据库服务，零配置启动
- **单文件应用**：核心逻辑集中在 `app.py`，代码简洁易维护
- **轻量镜像**：基于 `python:3.11-slim`，镜像体积小，启动快速
- **低资源占用**：内存占用 < 50MB，CPU 占用极低，适合小型服务器
- **无外部依赖**：除图标代理外，无需连接任何外部服务

## 🔐 安全特性

Oasis-Nav 内置多层安全防护机制，保护用户数据安全：

### 密码安全
- **PBKDF2 哈希**：使用 PBKDF2-SHA256 算法，150,000 次迭代，有效抵御暴力破解
- **强密码策略**：管理员密码要求至少 8 位，需包含字母和数字
- **密码隔离**：管理员密码、隐藏链接密码、书签密码相互独立，互不影响

### 认证与授权
- **Token 认证**：使用安全的随机 Token，30 分钟自动过期
- **IP 绑定**：可选开启 IP 绑定，Token 仅能在固定 IP 使用
- **登录限制**：5 次登录失败后自动锁定 15 分钟，防止暴力破解
- **会话管理**：Token 存储在内存中，服务重启后自动失效

### 防护机制
- **CSRF 保护**：通过 Origin/Referer 验证，防止跨站请求伪造攻击
- **XSS 防护**：严格的 URL 验证，过滤危险协议和脚本代码
- **文件权限**：Docker 容器以非 root 用户运行，数据目录权限 750
- **输入验证**：所有用户输入均经过严格验证和清理

### 数据安全
- **本地存储**：所有数据存储在本地 SQLite 数据库，不上传云端
- **加密存储**：密码以哈希形式存储，即使数据库泄露也无法还原明文
- **安全备份**：支持数据备份，备份文件可加密存储

## 🚀 快速开始

### Docker 部署（推荐）

```bash
# 创建目录并设置权限
mkdir -p ./data ./icon_cache
sudo chown -R 999:999 ./data ./icon_cache
chmod 750 ./data ./icon_cache

# 启动服务
docker run -d --name oasis-nav -p 6966:6966 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/icon_cache:/app/icon_cache \
  --restart unless-stopped \
  ecouus/oasis-nav:latest

docker logs -f oasis-nav  
```

访问：http://YOUR_SERVER_IP:6966

> 💡 **生产环境建议**：使用 Nginx 反向代理 + HTTPS，详见 [Nginx 配置](#-nginx-反向代理配置) 章节

### Docker Compose 部署

```bash
git clone https://github.com/ecouus/Oasis-Nav.git
cd Oasis-Nav
mkdir -p ./data ./icon_cache
sudo chown -R 999:999 ./data ./icon_cache
chmod 750 ./data ./icon_cache
docker-compose up -d
docker logs -f oasis-nav
```

### 本地开发

```bash
git clone https://github.com/ecouus/Oasis-Nav.git
cd Oasis-Nav
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## 💾 数据管理

### 备份

```bash
tar czf oasis-nav-backup-$(date +%Y%m%d).tar.gz ./data ./icon_cache
```

### 恢复

```bash
docker-compose down
tar xzf oasis-nav-backup-20240101.tar.gz
sudo chown -R 999:999 ./data ./icon_cache
chmod 750 ./data ./icon_cache
docker-compose up -d
```

### 迁移到新服务器

```bash
# 旧服务器
tar czf oasis-nav-data.tar.gz ./data ./icon_cache
scp oasis-nav-data.tar.gz user@new-server:~/

# 新服务器
tar xzf oasis-nav-data.tar.gz
sudo chown -R 999:999 ./data ./icon_cache
chmod 750 ./data ./icon_cache
docker-compose up -d
```

## 🌐 Nginx 反向代理配置

在生产环境中，建议使用 Nginx 作为反向代理，提供 HTTPS 支持和更好的性能。

### 通用 Nginx 配置

将以下配置保存到 `/etc/nginx/sites-available/oasis-nav`（或你的域名配置文件）：

```nginx
# HTTP 重定向到 HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com;  # 替换为你的域名
    
    return 301 https://$host$request_uri;
}

# HTTPS 主配置
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com;  # 替换为你的域名

    # SSL 证书配置（使用 Let's Encrypt 或其他证书）
    ssl_certificate /etc/nginx/certs/your-domain.com_cert.pem;
    ssl_certificate_key /etc/nginx/certs/your-domain.com_key.pem;
    
    # SSL 优化配置（可选）
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 上传文件大小限制
    client_max_body_size 100M;

    # 反向代理到后端
    location / {
        # 后端服务地址（如果 Nginx 和 Docker 在同一台机器，使用 127.0.0.1）
        proxy_pass http://127.0.0.1:6966;
        
        # 基础代理头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        
        # 关键：传递 Authorization 头（用于 API 认证）
        proxy_set_header Authorization $http_authorization;
        proxy_pass_header Authorization;
        
        # HTTP 版本
        proxy_http_version 1.1;
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 配置说明

**注意事项：**
- 将 `your-domain.com` 替换为你的实际域名
- 将证书路径替换为你的实际证书路径
- 如果 Docker 容器运行在其他机器，将 `127.0.0.1:6966` 替换为实际 IP 和端口
- 确保防火墙允许 80 和 443 端口访问

### 部署步骤

1. **创建配置文件**
   ```bash
   sudo nano /etc/nginx/sites-available/oasis-nav
   ```
   粘贴上面的配置并修改域名和证书路径

2. **创建软链接（如果使用 sites-available/sites-enabled）**
   ```bash
   sudo ln -s /etc/nginx/sites-available/oasis-nav /etc/nginx/sites-enabled/
   ```

3. **测试配置**
   ```bash
   sudo nginx -t
   ```

4. **重载 Nginx**
   ```bash
   sudo nginx -s reload
   # 或
   sudo systemctl reload nginx
   ```

### 使用 Let's Encrypt 免费 SSL 证书

```bash
# 安装 Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# 自动获取并配置证书
sudo certbot --nginx -d your-domain.com

# 证书会自动续期（Certbot 会配置 cron 任务）
```

## 🔧 常见问题

### 端口被占用

修改 docker-compose.yml 或 docker run 中的端口映射：`-p 8080:6966`

### 权限问题

```bash
sudo chown -R 999:999 ./data ./icon_cache
chmod 750 ./data ./icon_cache
```

### 忘记管理员密码

```bash
docker-compose down
rm -f data/data.db  # 会清空所有数据
docker-compose up -d
```

### 查看日志

```bash
docker logs -f oasis-nav
```

### Nginx 配置后无法访问

如果通过 Nginx 访问时出现问题，检查：
- ✅ 后端服务是否运行：`docker ps`
- ✅ Nginx 配置是否正确：`nginx -t`
- ✅ 防火墙是否允许 80 和 443 端口

## ⚙️ 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_PATH | 数据库路径 | data.db |
| ICON_CACHE_DIR | 图标缓存目录 | icon_cache |
| TZ | 时区 | - |

## 📁 项目结构

```
Oasis-Nav/
├── app.py                 # 核心应用文件（Flask 后端）
├── requirements.txt       # Python 依赖包
├── Dockerfile            # Docker 镜像构建文件
├── docker-compose.yml    # Docker Compose 配置
├── .gitignore            # Git 忽略文件
├── .dockerignore         # Docker 忽略文件
├── README.md             # 项目说明文档
│
├── templates/            # HTML 模板目录
│   ├── index.html        # 首页模板
│   ├── admin.html        # 后台管理页模板
│   ├── bookmarks.html    # 私密书签页模板
│   └── 404.html          # 404 错误页模板
│
└── static/               # 静态资源目录
    ├── css/              # 样式文件
    │   ├── common.css    # 公共样式
    │   ├── index.css     # 首页样式
    │   ├── admin.css     # 后台样式
    │   ├── bookmarks.css # 书签页样式
    │   └── 404.css       # 404 页样式
    │
    └── js/               # JavaScript 文件
        ├── index.js      # 首页逻辑
        ├── admin.js      # 后台管理逻辑
        └── bookmarks.js  # 书签页逻辑

# 运行时生成（不在 Git 中）
├── data/                 # 数据目录（SQLite 数据库）
└── icon_cache/           # 图标缓存目录
```

**核心文件说明：**
- `app.py`：包含所有后端逻辑（路由、API、数据库操作、安全验证等）
- `templates/`：前端页面模板，使用原生 HTML + JavaScript
- `static/`：CSS 样式和 JavaScript 脚本，无前端框架依赖
- `data/`：SQLite 数据库文件存储目录（运行时生成）
- `icon_cache/`：网站图标缓存目录（运行时生成）

## 🔒 安全建议

### 部署安全
- ✅ 使用强密码（至少 8 位，包含字母和数字）
- ✅ **强烈建议使用反向代理（Nginx/Caddy）+ HTTPS 加密传输**（参考 [Nginx 配置](#-nginx-反向代理配置)）
- ✅ 定期备份数据，备份文件加密存储
- ✅ 使用安全权限（chmod 750）
- ✅ 开启 IP 绑定功能（后台 → 安全设置）
- ✅ 定期更新 Docker 镜像获取安全补丁

### 最佳实践
- 🔐 为不同功能设置不同密码（管理员/隐藏链接/书签）
- 🔐 不要在公共网络环境下登录后台
- 🔐 定期检查访问日志，发现异常及时处理
- 🔐 使用防火墙限制访问来源（如仅允许内网访问）

## 📄 许可证

[MIT License](https://github.com/ecouus/Oasis-Nav/blob/main/LICENSE)

## 🔗 其他

- [问题反馈](https://github.com/ecouus/Oasis-Nav/issues)
