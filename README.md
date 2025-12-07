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
- ✅ 使用反向代理（Nginx/Caddy）+ HTTPS 加密传输
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

MIT License

## 🔗 链接

- [项目地址](https://github.com/ecouus/Oasis-Nav)
- [问题反馈](https://github.com/ecouus/Oasis-Nav/issues)
