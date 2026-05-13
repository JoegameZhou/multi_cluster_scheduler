# app/strategies/inter_cluster/load_balance.py
from typing import List, Dict, Any
from app.schemas.payload import ScheduleRequest

class LoadBalanceStrategy:
    """
    跨集群调度：基于硬件感知的负载均衡策略
    核心思想：在满足节点绝对资源容量（防碎片化）的前提下，寻找多维综合负载最低的集群。
    """
    
    # 资源上限常量，用于防御 K8s 节点资源超卖导致的异常计算
    MAX_LOAD = 100.0 

    async def select_cluster(self, request: ScheduleRequest, clusters: List[Dict[str, Any]], context) -> str:
        cluster_loads = {}
        
        for cluster in clusters:
            cluster_name = cluster["name"]
            metrics = context.global_metrics_cache.get(cluster_name)
            
            if not metrics:
                continue

            # ================= 🌟 1. 前置探路 (Lookahead Check) =================
            # 抽离为独立方法，主流程瞬间清爽
            if not self._has_viable_node(request, metrics.get("nodes", {})):
                continue

            # ================= 🌟 2. 提取各项利用率并进行超卖兜底 =================
            cpu_usage = min(self.MAX_LOAD, metrics.get("cpu_util", 100.0))
            memory_usage = min(self.MAX_LOAD, metrics.get("memory_util", 100.0))
            gpu_usage = metrics.get("gpu_util") 
            gpu_mem_usage = metrics.get("gpu_mem_util") 
            
            # ================= 🌟 3. 动态负载计算 =================
            if request.parsed_req_gpu > 0 and gpu_usage is not None and gpu_mem_usage is not None:
                # AI 任务：算力、内存、GPU计算、GPU显存，四项全能平均分！
                gpu_usage = min(self.MAX_LOAD, gpu_usage)
                gpu_mem_usage = min(self.MAX_LOAD, gpu_mem_usage)
                total_load = (cpu_usage + memory_usage + gpu_usage + gpu_mem_usage) / 4.0
            else:
                # 普通任务：侧重 CPU 与内存的基础算力均衡
                total_load = (cpu_usage + memory_usage) / 2.0
                
            # 🚨 修复了原代码中丢失的赋值语句！
            cluster_loads[cluster_name] = total_load
            
        # ================= 🌟 4. 全局择优 =================
        # 选择综合负载得分最低（最闲）的集群
        return min(cluster_loads, key=cluster_loads.get) if cluster_loads else None

    def _has_viable_node(self, request: ScheduleRequest, nodes_data: Dict[str, Any]) -> bool:
        """
        前置探路助手方法：检查集群内是否有任何一个节点能装下该任务的绝对物理需求
        """
        if not nodes_data:
            return False
            
        # 提取局部变量，大幅降低 Python 底层属性查表（点号操作）开销
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
            
            # 找到一个合格的完美宿主机，立即放行该集群
            return True 
            
        return False

