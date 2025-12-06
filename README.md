# Oasis-Nav
1
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
````

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
export DEBUG=1 # macOS/Linux
set DEBUG=1 # Windows
python app.py
```

#### 5. 访问应用

- 首页: [http://localhost:6966](http://localhost:6966/)
    
- 后台管理: [http://localhost:6966/admin](http://localhost:6966/admin)  
    首次访问后台需要设置管理员密码。
    

### 方式二：Docker 部署（推荐）

#### 使用 Docker Compose

```bash
git clone https://github.com/ecouus/Oasis-Nav.git
cd Oasis-Nav
mkdir -p ./data
chmod 777 ./data
docker-compose up -d
docker-compose logs -f
```

安全部署：

```bash
git clone https://github.com/ecouus/Oasis-Nav.git
cd Oasis-Nav
mkdir -p ./data
sudo chown -R 999:999 ./data
chmod 750 ./data
docker-compose up -d
docker-compose logs -f
```

停止服务：

```bash
docker-compose down
```

#### 使用 Docker 命令

```bash
git clone https://github.com/ecouus/Oasis-Nav.git
cd Oasis-Nav
docker build -t oasis-nav:latest .
mkdir -p ./data
sudo chown -R 999:999 ./data
chmod 750 ./data
docker run -d --name oasis-nav -p 6966:6966 -v $(pwd)/data:/app/data -e DATABASE_PATH=/app/data/data.db -e TZ=Asia/Shanghai --restart unless-stopped oasis-nav:latest
docker logs -f oasis-nav
docker stop oasis-nav
docker rm oasis-nav
```

访问应用：

- 首页: http://YOUR_SERVER_IP:6966
    
- 后台管理: http://YOUR_SERVER_IP:6966/admin
    

### 🐳 Docker 多架构构建与推送

```bash
docker login
docker buildx create --name multiarch --use --bootstrap
docker buildx build --platform linux/amd64,linux/arm64 --tag YOUR_USERNAME/oasis-nav:v1.0.1 --tag YOUR_USERNAME/oasis-nav:latest --push .
docker buildx imagetools inspect YOUR_USERNAME/oasis-nav:latest
```

运行远程镜像：

```bash
mkdir -p ./data
sudo chown -R 999:999 ./data
chmod 750 ./data
docker run -d --name oasis-nav -p 6966:6966 -v $(pwd)/data:/app/data YOUR_USERNAME/oasis-nav:latest
```

## 💾 数据备份与恢复

```bash
cp -r ./data ./backup-$(date +%Y%m%d)
tar czf oasis-nav-backup-$(date +%Y%m%d).tar.gz ./data
cp ./data/data.db ./data.db.backup
```

恢复：

```bash
docker-compose down
cp ./backup/data.db ./data/
tar xzf oasis-nav-backup-20240101.tar.gz
sudo chown -R 999:999 ./data
chmod 750 ./data
docker-compose up -d
```

## ⚙️ 环境变量配置

|变量名|说明|默认值|示例|
|---|---|---|---|
|DATABASE_PATH|数据库文件路径|data.db|/app/data/data.db|
|DEBUG|调试模式|0|1|
|TZ|时区设置|-|Asia/Shanghai|
|`.env` 示例：||||

```env
DATABASE_PATH=/app/data/data.db
DEBUG=0
TZ=Asia/Shanghai
```

## 📁 项目结构

```
Oasis-Nav/
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .gitignore
├── .dockerignore
├── static/
│   ├── css/
│   └── js/
├── templates/
│   ├── index.html
│   ├── admin.html
│   └── bookmarks.html
└── data/
    └── data.db
```

## 🔧 常见问题

### 1. 端口被占用

```yaml
ports:
- "8080:6966"
```

### 2. 数据库权限问题

```bash
mkdir -p ./data
chmod 777 ./data
mkdir -p ./data
sudo chown -R 999:999 ./data
chmod 750 ./data
docker-compose down
docker-compose up -d
```

### 3. 忘记管理员密码

```bash
docker-compose down
rm -f data/data.db
docker-compose up -d
```

### 4. 查看容器日志

```bash
docker-compose logs -f
docker logs -f oasis-nav
docker-compose logs --tail=100
```

### 5. 数据迁移

```bash
tar czf oasis-nav-data.tar.gz ./data
scp oasis-nav-data.tar.gz user@new-server:/path/to/Oasis-Nav/
cd /path/to/Oasis-Nav
tar xzf oasis-nav-data.tar.gz
sudo chown -R 999:999 ./data
chmod 750 ./data
docker-compose up -d
```

## 📝 开发说明

```bash
export DEBUG=1
python app.py
```

生产模式：

```bash
gunicorn -w 2 -b 0.0.0.0:6966 app:app
```

## 🔒 安全建议

- 使用安全权限（chmod 750）
    
- 使用强密码
    
- 使用反向代理 + HTTPS
    
- 定期备份数据库
    

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 🔗 相关链接

- 项目地址：[https://github.com/ecouus/Oasis-Nav](https://github.com/ecouus/Oasis-Nav)
    
- 问题反馈：[https://github.com/ecouus/Oasis-Nav/issues](https://github.com/ecouus/Oasis-Nav/issues)


---

如你需要：

✔ 自动生成 **README 目录**  
✔ 自动生成 **Obsidian Callout 高亮版本**  
✔ 自动生成 **可折叠章节（folding）版**  
我也可以继续帮你优化。
