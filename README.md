# Oasis-Nav

一个轻量级的导航页应用，基于 Flask + SQLite 构建，支持分类管理、书签收藏、隐藏链接等功能。

## ✨ 功能特性

- 🎯 简洁美观的导航页界面
- 📁 多级分类管理
- 🔖 书签收藏与管理
- 🔒 密码保护（管理员密码、隐藏链接密码、书签密码）
- 🐳 Docker 一键部署
- 📱 响应式设计

## 📋 系统要求

- Python 3.11+
- 或 Docker & Docker Compose

## 🚀 快速开始

### 方式一：本机部署

#### 1. 克隆项目

```bash
git clone https://github.com/ecouus/Oasis-Nav.git
cd Oasis-Nav
```

#### 2. 创建虚拟环境（推荐）

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 运行应用

```bash
# 开发模式（开启 DEBUG）
export DEBUG=1  # macOS/Linux
# 或
set DEBUG=1  # Windows

python app.py
```

#### 5. 访问应用

- 首页: http://localhost:6966
- 后台管理: http://localhost:6966/admin

首次访问后台需要设置管理员密码。

---

### 方式二：Docker 部署

#### 使用 Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/ecouus/Oasis-Nav.git
cd Oasis-Nav

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 停止服务
docker-compose down
```

#### 使用 Docker 命令

```bash
# 1. 构建镜像
docker build -t oasis-nav:latest .

# 2. 运行容器
docker run -d \
  --name oasis-nav \
  -p 6966:6966 \
  -v $(pwd)/data:/app/data \
  -e DATABASE_PATH=/app/data/data.db \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  oasis-nav:latest

# 3. 查看日志
docker logs -f oasis-nav

# 4. 停止容器
docker stop oasis-nav
docker rm oasis-nav
```

#### 访问应用

- 首页: http://localhost:6966
- 后台管理: http://localhost:6966/admin

---

## 🐳 Docker 构建与推送

### 构建镜像

```bash
# 构建本地镜像
docker build -t oasis-nav:latest .

# 或指定标签
docker build -t oasis-nav:v1.0.0 .
```

### 推送到 Docker Hub

```bash
# 1. 登录 Docker Hub
docker login

# 2. 标记镜像（替换 YOUR_USERNAME 为你的 Docker Hub 用户名）
docker tag oasis-nav:latest YOUR_USERNAME/oasis-nav:latest
docker tag oasis-nav:latest YOUR_USERNAME/oasis-nav:v1.0.0

# 3. 推送镜像
docker push YOUR_USERNAME/oasis-nav:latest
docker push YOUR_USERNAME/oasis-nav:v1.0.0
```

### 推送到其他镜像仓库

#### GitHub Container Registry (ghcr.io)

```bash
# 1. 登录 GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# 2. 标记镜像
docker tag oasis-nav:latest ghcr.io/YOUR_USERNAME/oasis-nav:latest

# 3. 推送镜像
docker push ghcr.io/YOUR_USERNAME/oasis-nav:latest
```

#### 阿里云容器镜像服务

```bash
# 1. 登录阿里云容器镜像服务
docker login --username=YOUR_USERNAME registry.cn-hangzhou.aliyuncs.com

# 2. 标记镜像
docker tag oasis-nav:latest registry.cn-hangzhou.aliyuncs.com/YOUR_NAMESPACE/oasis-nav:latest

# 3. 推送镜像
docker push registry.cn-hangzhou.aliyuncs.com/YOUR_NAMESPACE/oasis-nav:latest
```

### 使用远程镜像运行

```bash
# 从 Docker Hub 拉取并运行
docker run -d \
  --name oasis-nav \
  -p 6966:6966 \
  -v $(pwd)/data:/app/data \
  YOUR_USERNAME/oasis-nav:latest
```

---

## ⚙️ 环境变量配置

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `DATABASE_PATH` | 数据库文件路径 | `data.db` | `/app/data/data.db` |
| `DEBUG` | 调试模式 | `0` | `1` 开启调试 |
| `TZ` | 时区设置 | - | `Asia/Shanghai` |

### 使用环境变量文件

创建 `.env` 文件（不要提交到 Git）：

```env
DATABASE_PATH=/app/data/data.db
DEBUG=0
TZ=Asia/Shanghai
```

使用 Docker Compose 时会自动加载 `.env` 文件。

---

## 📁 项目结构

```
Oasis-Nav/
├── app.py                 # 主应用文件
├── requirements.txt       # Python 依赖
├── Dockerfile            # Docker 镜像构建文件
├── docker-compose.yml    # Docker Compose 配置
├── .gitignore           # Git 忽略规则
├── .dockerignore        # Docker 构建忽略规则
├── static/              # 静态资源
│   ├── css/            # 样式文件
│   └── js/             # JavaScript 文件
├── templates/           # HTML 模板
│   ├── index.html      # 首页
│   ├── admin.html      # 后台管理
│   └── bookmarks.html  # 书签页
└── data/               # 数据目录（自动创建，不提交到 Git）
    └── data.db         # SQLite 数据库
```

---

## 🔧 常见问题

### 1. 端口被占用

如果 6966 端口被占用，可以修改端口：

**Docker Compose:**
```yaml
ports:
  - "8080:6966"  # 将本地 8080 映射到容器 6966
```

**Docker 命令:**
```bash
docker run -p 8080:6966 ...
```

**本机部署:**
修改 `app.py` 最后一行：
```python
app.run(host='0.0.0.0', port=8080, debug=debug_mode)
```

### 2. 数据库权限问题

确保数据目录有正确的权限：

```bash
chmod 755 data
chmod 644 data/data.db
```

### 3. 忘记管理员密码

删除数据库文件重新初始化（**会丢失所有数据**）：

```bash
rm data/data.db
# 重启应用，首次访问后台会提示设置新密码
```

---

## 📝 开发说明

### 开发模式

```bash
export DEBUG=1
python app.py
```

开发模式下会：
- 开启 Flask 的调试模式
- 自动重载代码更改
- 显示详细的错误信息

### 生产模式

使用 Docker 部署或使用 Gunicorn：

```bash
gunicorn -w 2 -b 0.0.0.0:6966 app:app
```

---

## 📄 许可证

本项目采用 MIT 许可证。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 🔗 相关链接

- 项目地址: https://github.com/ecouus/Oasis-Nav
- 问题反馈: https://github.com/ecouus/Oasis-Nav/issues

---

**享受使用 Oasis-Nav！** 🎉
