# 导入必要的模块
# FastAPI：用于创建 Web 应用
# app.api.v1.schedule：调度相关的 API 路由
# app.api.v1.health：健康检查相关的 API 路由
# app.core.context：全局上下文管理
# app.utils.logger：日志设置工具
# asynccontextmanager：用于创建异步上下文管理器
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.v1 import schedule, health
from app.core.context import Context
from app.utils.logger import setup_logger

# 设置日志
# 调用 setup_logger() 函数初始化日志配置
logger = setup_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理
    负责应用启动时的初始化和关闭时的资源释放
    """
    # ================= 启动阶段 (Startup) =================
    logger.info("Starting up Multi-Cluster Scheduler...")
    
    # 使用 await 调用异步初始化
    # 这先去查询集群的数据，然后启动prometheus数据采集任务，每 5 秒更新一次缓存数据，先把数据缓存到本地，然后直接读取速度会很快。
    await Context.initialize()
    logger.info("Context initialized successfully")
    
    yield  
    
    # ================= 关闭阶段 (Shutdown) =================
    logger.info("Shutting down Multi-Cluster Scheduler...")
    
    # 释放 HTTP 连接池
    await Context.close()
    logger.info("Shutdown complete.")

# 创建 FastAPI 应用实例
# title：应用名称
# version：应用版本
# lifespan：应用生命周期管理
app = FastAPI(title="Multi-Cluster Scheduler", version="1.0.0", lifespan=lifespan)

# 注册路由
# 注册健康检查路由，路径前缀为 /health，标签为 "Health"
app.include_router(health.router, prefix="/health", tags=["Health"])
# 注册调度相关路由，路径前缀为 /api/v1，标签为 "Scheduler"
app.include_router(schedule.router, prefix="/api/v1", tags=["Scheduler"])

# 主函数
# 当直接运行该文件时执行
if __name__ == "__main__":
    # 导入 uvicorn 服务器
    import uvicorn
    # 运行应用
    # "app.main:app"：指定应用的入口点，格式为模块名:应用实例名
    # host="0.0.0.0"：允许从任意主机访问
    # port=8000：服务监听的端口
    # reload=True：在开发模式下，当代码修改时自动重启服务
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
