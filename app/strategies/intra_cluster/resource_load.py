# app/strategies/intra_cluster/resource_load.py
from typing import Dict, Any
from app.schemas.payload import ScheduleRequest

class ResourceLoadStrategy:
    """
    集群内调度：基于真实资源负载的节点选择算法
    核心思想：在满足绝对资源硬约束（死亡过滤）的前提下，寻找负载最低、最健康的节点。
    """

    # ================= 业务规则配置 (消除魔法数字) =================
    HEALTHY_THRESHOLD = 60.0    # 资源健康水位线 (利用率 <= 60% 视为极度健康)
    BONUS_GPU_HEALTHY = 1000.0  # GPU 双重健康 (算力+显存) 的超级奖励分
    BONUS_SYS_HEALTHY = 500.0   # CPU 与 内存 双重健康的系统奖励分
    LINEAR_WEIGHT = 0.25        # 线性空闲得分的权重乘数
    # =========================================================

    async def select_node(self, request: ScheduleRequest, cluster_name: str, context) -> str:
        cluster_metrics = context.global_metrics_cache.get(cluster_name, {})
        nodes_data = cluster_metrics.get("nodes", {})
        
        if not nodes_data:
            return None

        # 🌟 极客优化：打擂台变量 (空间复杂度 O(N) -> O(1))
        best_node_name = None
        highest_score = -1.0
        
        # 🌟 极客优化：提取局部变量，消除大循环中的属性查表开销
        req_cpu = request.parsed_req_cpu_cores
        req_mem = request.parsed_req_mem_gb
        req_gpu = request.parsed_req_gpu
        req_gpu_mem = request.parsed_req_gpu_mem_gb

        for node_name, stats in nodes_data.items():
            if not stats.get("is_up", False):
                continue
                
            # ================= 🌟 第一阶段：死亡过滤 (Hard Constraints) =================
            # 1. 查 CPU (可压缩资源：核数必须足够)
            if stats.get("cpu_avail_cores", 0.0) < req_cpu:
                continue

            # 2. 查 内存 (不可压缩资源：差一兆都会 OOM)
            if stats.get("memory_avail_gb", 0.0) < req_mem:
                continue 

            # 3. 查 GPU (独占资源：物理卡数与显存必须双满足)
            if req_gpu > 0:
                if stats.get("gpu_avail_count", 0) < req_gpu:
                    continue
                if stats.get("gpu_mem_avail_gb", 0.0) < req_gpu_mem:
                    continue
            # =========================================================================

            # ================= 🌟 第二阶段：软约束打分 (Priorities Scoring) =================
            # 提取利用率，并使用 min(100.0, x) 防御 K8s 资源超卖导致的异常值 (>100%)
            cpu_usage = min(100.0, stats.get("cpu_util", 100.0))
            mem_usage = min(100.0, stats.get("memory_util", 100.0))
            gpu_usage = stats.get("gpu_util")
            gpu_mem_usage = stats.get("gpu_mem_util")
            
            current_node_score = 0.0
            
            # 1. GPU 专项打分 (针对 AI 任务)
            if req_gpu > 0 and gpu_usage is not None and gpu_mem_usage is not None:
                gpu_usage = min(100.0, gpu_usage)
                gpu_mem_usage = min(100.0, gpu_mem_usage)
                
                # 门槛奖励：只有当 GPU 算力和显存都不拥挤时，给予超级奖励
                if gpu_usage <= self.HEALTHY_THRESHOLD and gpu_mem_usage <= self.HEALTHY_THRESHOLD:
                    current_node_score += self.BONUS_GPU_HEALTHY
                    
                # 线性加分：越闲分越高
                current_node_score += (100.0 - gpu_usage) * self.LINEAR_WEIGHT
                current_node_score += (100.0 - gpu_mem_usage) * self.LINEAR_WEIGHT
                
            # 2. 系统基础打分 (CPU + 内存)
            # 门槛奖励：系统整体资源不拥挤时，给予基础奖励
            if cpu_usage <= self.HEALTHY_THRESHOLD and mem_usage <= self.HEALTHY_THRESHOLD:
                current_node_score += self.BONUS_SYS_HEALTHY
                
            # 线性加分：越闲分越高
            current_node_score += (100.0 - cpu_usage) * self.LINEAR_WEIGHT
            current_node_score += (100.0 - mem_usage) * self.LINEAR_WEIGHT
            # =========================================================================

            # ================= 🌟 第三阶段：擂台结算 (Winner Selection) =================
            # 如果当前节点的分数超越了历史最高分，则篡位成为最优节点
            if current_node_score > highest_score:
                highest_score = current_node_score
                best_node_name = node_name

        # 遍历结束后，返回最终的擂主（最闲且满足所有约束的节点）
        return best_node_name