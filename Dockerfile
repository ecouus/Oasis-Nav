# Oasis-Nav Docker 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 创建非 root 用户运行应用（安全最佳实践）
# 固定 UID/GID 为 999，方便宿主机设置权限
RUN groupadd -r -g 999 navuser && useradd -r -u 999 -g navuser navuser

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 复制应用代码
COPY app.py .
COPY static/ ./static/
COPY templates/ ./templates/

# 创建数据目录并设置权限
RUN mkdir -p /app/data && chown -R navuser:navuser /app

# 切换到非 root 用户
USER navuser

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/data.db

# 暴露端口
EXPOSE 6966

# 启动命令（使用 gunicorn 生产环境服务器）
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:6966", "app:app"]

