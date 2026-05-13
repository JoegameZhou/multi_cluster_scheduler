# 使用官方轻量级 Python 镜像作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件到容器中
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码到容器中
COPY ./app /app/app
COPY ./config /app/config

# 设置环境变量
ENV PYTHONPATH=/app
ENV KUBECONFIG_PATH=/app/config/kubeconfig

# 暴露 FastAPI 默认端口 (仅声明，方便以后改回来)
EXPOSE 8000

# ================= 核心修改点 =================
# 注释掉原有的自动启动命令
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# 替换为“保活”命令：监听一个黑洞文件，这会让容器永远处于 Running 状态，且不占用 CPU
CMD ["tail", "-f", "/dev/null"]