from fastapi import APIRouter, Response, status
from app.core.context import Context

router = APIRouter()

@router.get("/live")
async def health_live():
    """存活探针：进程在运行即 OK"""
    return {"status": "ok"}

@router.get("/ready")
async def health_ready(response: Response):
    """就绪探针：检查内存缓存是否有数据"""
    
    # 1. 检查全局指标缓存是否有内容
    # 注意：这里对接你 context.py 里的变量名 global_metrics_cache
    is_data_ready = False
    if Context.global_metrics_cache:
        # 遍历所有集群，只要有一个集群拿到了数据（即包含了 nodes 列表），就认为数据就绪
        for cluster_id, data in Context.global_metrics_cache.items():
            if data and "nodes" in data and data["nodes"]:
                is_data_ready = True
                break
    
    # 2. 检查是否有存活的客户端连接
    has_active_clients = len(Context.prom_clients) > 0
    
    if is_data_ready and has_active_clients:
        return {
            "status": "ready",
            "active_clusters": list(Context.prom_clients.keys()),
            "message": "Scheduler is armed and ready."
        }
    else:
        # 如果数据还没拉取下来，或者网络全断，返回 503 
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "reason": "Waiting for initial Prometheus data collection..."
        }

        