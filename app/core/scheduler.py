# app/core/scheduler.py

# 导入必要的模块
from app.core.context import Context
from app.schemas.payload import ScheduleRequest, ScheduleResponse
from app.utils.resource_parser import parse_k8s_memory_to_gb

# 导入第一阶段：跨集群调度策略
from app.strategies.inter_cluster.load_balance import LoadBalanceStrategy
from app.strategies.inter_cluster.proximity import ProximityStrategy
from app.strategies.inter_cluster.resource_match import ResourceMatchStrategy

class Scheduler:
    """调度器核心类"""
    
    def __init__(self):
        # 存储全局上下文实例
        self.context = Context

    async def run(self, request: ScheduleRequest) -> ScheduleResponse:
        """执行完整任务调度流水线"""
        
        # ================= 🌟 1. 统一数据预处理 (硬约束翻译) =================
        try:
            # 必须使用 setattr 确保 Pydantic extra="allow" 生效
            setattr(request, 'parsed_req_cpu_cores', float(request.resources.cpu))
            setattr(request, 'parsed_req_mem_gb', parse_k8s_memory_to_gb(request.resources.memory))
            setattr(request, 'parsed_req_gpu', int(request.resources.gpu or 0))
            
            if request.resources.gpu_memory:
                setattr(request, 'parsed_req_gpu_mem_gb', parse_k8s_memory_to_gb(request.resources.gpu_memory))
            else:
                setattr(request, 'parsed_req_gpu_mem_gb', 0.0)
                
        except Exception as e:
            return ScheduleResponse(success=False, message=f"资源解析失败: {str(e)}")

        # ================= 🌟 2. 第一阶段：选集群 (跨集群分发) =================
        cluster_name = None
        if request.target_cluster:
            # 如果强制指定了集群
            if request.target_cluster in self.context.prom_clients:
                cluster_name = request.target_cluster
            else:
                return ScheduleResponse(
                    success=False,
                    message=f"Target cluster '{request.target_cluster}' not found or offline"
                )
        else:
            # 否则根据策略选择集群
            cluster_name = await self._select_cluster(request)
            if not cluster_name:
                return ScheduleResponse(
                    success=False,
                    message="Stage 1 Failed: No suitable cluster found (Resources insufficient in all clusters)"
                )

        # ================= 🌟 3. 第二阶段：选节点 (集群内分发) =================
        node_name = None
        k8s_native_strategy = None
        
        if request.intra_cluster_strategy == "resource_load":
            node_name = await self._select_node(request, cluster_name)
            if not node_name:
                return ScheduleResponse(
                    success=False,
                    message=f"Stage 2 Failed: Cluster '{cluster_name}' has no suitable nodes (Full load)",
                    cluster_name=cluster_name
                )
        else:
            # node_affinity 或 task_priority 策略交回给 K8s 调度
            k8s_native_strategy = request.intra_cluster_strategy

        # ================= 🌟 4. 最终返回 =================
        return ScheduleResponse(
            success=True,
            message="Scheduling successful" if not k8s_native_strategy else f"Delegated to K8s {k8s_native_strategy}",
            cluster_name=cluster_name,
            node_name=node_name,
            k8s_native_strategy=k8s_native_strategy 
        )

    async def _select_cluster(self, request: ScheduleRequest) -> str:
        """跨集群策略分发"""
        clusters = self.context.clusters_config
        strategy_name = request.inter_cluster_strategy
        
        if strategy_name == "load_balance":
            strategy = LoadBalanceStrategy()
        elif strategy_name == "proximity":
            strategy = ProximityStrategy()
        elif strategy_name == "resource_match":
            strategy = ResourceMatchStrategy()
        else:
            return None
        
        return await strategy.select_cluster(request, clusters, self.context)

    async def _select_node(self, request: ScheduleRequest, cluster_name: str) -> str:
        """集群内策略分发"""
        if request.intra_cluster_strategy == "resource_load":
            from app.strategies.intra_cluster.resource_load import ResourceLoadStrategy
            strategy = ResourceLoadStrategy()
            return await strategy.select_node(request, cluster_name, self.context)
        return None


        