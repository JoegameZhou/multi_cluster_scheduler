import httpx
from typing import Dict, Optional, List

class AsyncPromClient:
    def __init__(self, url):
        self.url = url
        self.client = httpx.AsyncClient(timeout=5.0)

    async def _query_single_value(self, promql: str) -> Optional[float]:
        """异步执行聚合查询，返回单个值（没查到返回 None）"""
        try:
            response = await self.client.get(self.url, params={"query": promql})
            response.raise_for_status()
            data = response.json()
            if data["status"] == "success" and data["data"]["result"]:
                return round(float(data["data"]["result"][0]["value"][1]), 2)
            # 🌟 查不到数据时返回 None，而不是 0.0 或 -1.0
            return None
        except Exception:
            return None

    async def _query_map(self, promql: str) -> Dict[str, float]:
        """异步执行查询，返回节点名到指标值的映射（节点级）"""
        try:
            response = await self.client.get(self.url, params={"query": promql})
            response.raise_for_status()
            data = response.json()
            
            res_map = {}
            if data["status"] == "success":
                for item in data["data"]["result"]:
                    instance = item["metric"].get("instance", "")
                    node_name = instance.split(":")[0]
                    if node_name:
                        res_map[node_name] = round(float(item["value"][1]), 2)
            return res_map
        except Exception:
            return {}

    # ================= 1. CPU & Memory (百分比) =================
    async def get_cluster_cpu_usage(self) -> float:
        return await self._query_single_value('100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)')

    async def get_cluster_memory_usage(self) -> float:
        return await self._query_single_value('100 - (sum(node_memory_MemAvailable_bytes) / sum(node_memory_MemTotal_bytes)) * 100')

    async def get_node_status(self) -> Dict[str, bool]:
        """获取节点健康状态"""
        results = await self._query_map('up{instance=~".+"}')
        return {k: v == 1.0 for k, v in results.items()}

    async def get_node_cpu_usage(self) -> Dict[str, float]:
        return await self._query_map('100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)')

    async def get_node_memory_usage(self) -> Dict[str, float]:
        return await self._query_map('100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100')

    # ================= 2. GPU 相关 (百分比/数值) =================
    async def get_cluster_gpu_usage(self) -> float:
        """集群平均 GPU 利用率"""
        return await self._query_single_value('avg(DCGM_FI_DEV_GPU_UTIL)')

    async def get_cluster_gpu_memory_usage(self) -> float:
        """🌟 新增：集群平均 GPU 显存利用率"""
        promql = 'avg(DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL * 100)'
        return await self._query_single_value(promql)

    async def get_node_gpu_usage(self) -> Dict[str, float]:
        """节点级 GPU 利用率"""
        return await self._query_map('max by (instance) (DCGM_FI_DEV_GPU_UTIL)')

    async def get_node_gpu_mem_usage(self) -> Dict[str, float]:
        """节点级 GPU 显存使用率"""
        promql = 'max by (instance) (DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL * 100)'
        return await self._query_map(promql)

    async def get_node_gpu_power(self) -> Dict[str, float]:
        """节点级 GPU 功耗 (W)"""
        return await self._query_map('max by (instance) (DCGM_FI_DEV_POWER_USAGE)')

    # ================= 🌟 3. 四大核心算力绝对剩余量 (硬约束专用) =================
    
    async def get_node_memory_available_gb(self) -> Dict[str, float]:
        """获取节点绝对剩余内存 (GB)"""
        promql = 'node_memory_MemAvailable_bytes / 1024 / 1024 / 1024'
        return await self._query_map(promql)

    async def get_node_cpu_available_cores(self) -> Dict[str, float]:
        """🌟 新增：获取节点绝对剩余 CPU 核心数"""
        # 原理：直接将空闲状态的 CPU 速率相加，得出精确的闲置核数
        promql = 'sum by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m]))'
        return await self._query_map(promql)

    async def get_node_gpu_memory_available_gb(self) -> Dict[str, float]:
        """🌟 新增：获取节点绝对剩余显存 (GB)"""
        # DCGM 默认显存单位是 MiB，除以 1024 转换为 GB
        promql = 'sum by (instance) (DCGM_FI_DEV_FB_FREE) / 1024'
        return await self._query_map(promql)

    async def get_node_gpu_available_count(self) -> Dict[str, float]:
        """🌟 新增：获取节点 GPU 物理卡数"""
        # 统计每个节点上监控到了多少张 GPU 卡
        promql = 'count by (instance) (DCGM_FI_DEV_GPU_UTIL)'
        return await self._query_map(promql)

    async def close(self):
        await self.client.aclose()