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

## 🔒 安全建议

- 使用强密码
- 使用反向代理 + HTTPS
- 定期备份数据
- 使用安全权限（chmod 750）

## 📄 许可证

MIT License

## 🔗 链接

- [项目地址](https://github.com/ecouus/Oasis-Nav)
- [问题反馈](https://github.com/ecouus/Oasis-Nav/issues)
