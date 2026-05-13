# app/strategies/inter_cluster/resource_match.py
from typing import List, Dict, Any
from app.schemas.payload import ScheduleRequest

class ResourceMatchStrategy:
    """集群间调度：基于资源匹配度策略"""
    
    # ================= 业务规则配置 (消除魔法数字) =================
    SAFE_THRESHOLD_PCT = 20.0  # 集群整体剩余资源安全红线 (20%)
    
    # 普通任务打分权重
    WEIGHT_NORMAL_CPU = 0.5
    WEIGHT_NORMAL_MEM = 0.5
    
    # AI 任务打分权重
    WEIGHT_AI_CPU = 0.2
    WEIGHT_AI_MEM = 0.2
    WEIGHT_AI_GPU = 0.6
    # =========================================================

    async def select_cluster(self, request: ScheduleRequest, clusters: List[Dict[str, Any]], context) -> str:
        cluster_scores = {}
        
        for cluster in clusters:
            cluster_name = cluster["name"]
            metrics = context.global_metrics_cache.get(cluster_name)
            
            if not metrics:
                continue
                
            # 1. 前置探路：调用独立方法，代码瞬间清爽
            if not self._has_viable_node(request, metrics.get("nodes", {})):
                continue
                
            # 2. 获取使用率并计算剩余率，使用 max(0.0, x) 防止超卖出现负数
            cpu_usage = metrics.get("cpu_util", 100.0)
            mem_usage = metrics.get("memory_util", 100.0)
            gpu_usage = metrics.get("gpu_util")
            
            cpu_remaining = max(0.0, 100.0 - cpu_usage)
            mem_remaining = max(0.0, 100.0 - mem_usage)
            gpu_remaining = max(0.0, 100.0 - gpu_usage) if gpu_usage is not None else None

            # 3. PRD 硬约束检查：集群整体警戒线
            if cpu_remaining < self.SAFE_THRESHOLD_PCT or mem_remaining < self.SAFE_THRESHOLD_PCT:
                continue 
                
            if request.parsed_req_gpu > 0:
                if gpu_remaining is None or gpu_remaining < self.SAFE_THRESHOLD_PCT:
                    continue 

            # 4. 匹配度打分
            if request.parsed_req_gpu > 0 and gpu_remaining is not None:
                score = (cpu_remaining * self.WEIGHT_AI_CPU) + \
                        (mem_remaining * self.WEIGHT_AI_MEM) + \
                        (gpu_remaining * self.WEIGHT_AI_GPU)
            else:
                score = (cpu_remaining * self.WEIGHT_NORMAL_CPU) + \
                        (mem_remaining * self.WEIGHT_NORMAL_MEM)
                
            cluster_scores[cluster_name] = score
            
        # 5. 选取得分最高的集群
        return max(cluster_scores, key=cluster_scores.get) if cluster_scores else None

    def _has_viable_node(self, request: ScheduleRequest, nodes_data: Dict[str, Any]) -> bool:
        """
        前置探路助手方法：检查集群内是否有任何一个节点能装下该任务
        """
        if not nodes_data:
            return False
            
        # 🌟 极客优化：将对象属性提取为局部变量，消除大循环中的点号寻址开销
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
            
            # 找到一个合格的节点，直接返回 True
            return True 
            
        return False