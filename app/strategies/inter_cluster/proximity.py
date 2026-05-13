# app/strategies/inter_cluster/proximity.py
from typing import List, Dict, Any
from app.schemas.payload import ScheduleRequest

class ProximityStrategy:
    """集群间调度：基于就近性（同地域优先）策略"""

    # ================= 业务规则配置 (消除魔法数字) =================
    MAX_BASE_SCORE = 100.0      # 基础健康分满分 (越闲分越高)
    REGION_MATCH_BONUS = 500.0  # 匹配目标地域的绝对权重加分
    # =========================================================
    
    async def select_cluster(self, request: ScheduleRequest, clusters: List[Dict[str, Any]], context) -> str:
        # 尝试获取期望地域
        target_region = getattr(request, "preferred_region", None)
        valid_clusters = {}

        for cluster in clusters:
            cluster_name = cluster["name"]
            cluster_region = cluster.get("region")
            
            metrics = context.global_metrics_cache.get(cluster_name)
            if not metrics:
                continue
                
            # 1. 前置探路：调用独立方法，主逻辑瞬间变得极其干净
            if not self._has_viable_node(request, metrics.get("nodes", {})):
                continue

            # 2. 动态负载计算：使用 min(100.0, x) 防御超卖导致的异常值
            cpu_usage = min(100.0, metrics.get("cpu_util", 100.0))
            mem_usage = min(100.0, metrics.get("memory_util", 100.0))
            gpu_usage = metrics.get("gpu_util")

            # 优雅地计算 base_load，告别复杂的嵌套三元表达式
            total_usage = cpu_usage + mem_usage
            metric_count = 2

            if request.parsed_req_gpu > 0 and gpu_usage is not None:
                total_usage += min(100.0, gpu_usage)
                metric_count = 3
                
            base_load = total_usage / metric_count
            
            # 3. 基础得分计算
            score = self.MAX_BASE_SCORE - base_load 
            
            # 4. 地域亲和力绝对加权
            if target_region and cluster_region == target_region:
                score += self.REGION_MATCH_BONUS
                
            valid_clusters[cluster_name] = score

        # 5. 选取得分最高的集群
        return max(valid_clusters, key=valid_clusters.get) if valid_clusters else None

    def _has_viable_node(self, request: ScheduleRequest, nodes_data: Dict[str, Any]) -> bool:
        """
        前置探路助手方法：检查集群内是否有任何一个节点能装下该任务
        """
        if not nodes_data:
            return False
            
        # 提取局部变量，大幅降低 Python 在底层大循环中的属性查表开销
        req_cpu = request.parsed_req_cpu_cores
        req_mem = request.parsed_req_mem_gb
        req_gpu = request.parsed_req_gpu
        req_gpu_mem = request.parsed_req_gpu_mem_gb
            
        for stats in nodes_data.values():
            if not stats.get("is_up", False):
                continue
            if stats.get("cpu_avail_cores", 0.0) < req_cpu:
                continue
            if stats.get("memory_avail_gb", 0.0) < req_mem:
                continue
                
            if req_gpu > 0:
                if stats.get("gpu_avail_count", 0) < req_gpu:
                    continue
                if stats.get("gpu_mem_avail_gb", 0.0) < req_gpu_mem:
                    continue
            
            return True 
            
        return False

        