import os
import yaml
import asyncio
from typing import Dict, Any

from app.clients.prom_client import AsyncPromClient

class Context:
    """全局上下文类，用于管理各个集群的客户端连接和内存缓存"""
    
    prom_clients: Dict[str, AsyncPromClient] = {}
    clusters_config: list = []
    global_metrics_cache: Dict[str, Any] = {}
    
    # 🌟 必须加上这个策略缓存，否则 API 接口 /policies/schedule 会报错
    global_policy_cache: Dict[str, str] = {
        "inter_cluster_strategy": "load_balance",
        "intra_cluster_strategy": "resource_load"
    }
    
    _polling_task: asyncio.Task = None

    @classmethod
    async def initialize(cls):
        """异步初始化全局上下文"""
        config_path = os.getenv("CLUSTER_CONFIG_PATH", "/app/config/clusters.yaml")
        
        def load_yaml():
            """同步加载 YAML 配置文件"""
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
                
        config_data = await asyncio.to_thread(load_yaml)
        cls.clusters_config = config_data.get("clusters", [])

        for cluster in cls.clusters_config:
            cluster_id = cluster["name"]
            prom_url = cluster.get("prometheus_url")
            if prom_url:
                cls.prom_clients[cluster_id] = AsyncPromClient(prom_url)
                cls.global_metrics_cache[cluster_id] = {} 

        cls._polling_task = asyncio.create_task(cls._poll_prometheus_data())
        print("后台数据采集任务已启动")

    @classmethod
    async def _poll_prometheus_data(cls):
        """后台静默运行的定时任务，持续更新本地内存字典"""
        while True:
            try:
                for cluster_id, prom_client in cls.prom_clients.items():
                    # 1. 获取并发采集数据 (总共 14 个任务)
                    tasks = [
                        prom_client.get_cluster_cpu_usage(),         # 1
                        prom_client.get_cluster_memory_usage(),      # 2
                        prom_client.get_cluster_gpu_usage(),         # 3
                        # 🌟 新增：集群级平均显存利用率
                        prom_client.get_cluster_gpu_memory_usage(),  # 4 
                        
                        prom_client.get_node_status(),               # 5
                        prom_client.get_node_cpu_usage(),            # 6
                        prom_client.get_node_memory_usage(),         # 7
                        prom_client.get_node_gpu_usage(),            # 8
                        prom_client.get_node_gpu_mem_usage(),        # 9
                        prom_client.get_node_gpu_power(),            # 10
                        
                        # 四大绝对剩余量采集
                        prom_client.get_node_gpu_memory_available_gb(), # 11
                        prom_client.get_node_memory_available_gb(),     # 12
                        prom_client.get_node_cpu_available_cores(),     # 13
                        prom_client.get_node_gpu_available_count()      # 14
                    ]
                    results = await asyncio.gather(*tasks)
                    
                    # 严格对应上面的 14 个任务顺序拆包
                    (c_cpu, c_mem, c_gpu, c_gpu_mem, 
                     n_status, n_cpu, n_mem, n_gpu, n_gpu_mem, n_gpu_pwr, 
                     n_gpu_mem_avail, n_mem_avail, n_cpu_avail, n_gpu_avail) = results

                    # 2. 整合节点数据
                    nodes_data = {}
                    for node_name, is_up in n_status.items():
                        nodes_data[node_name] = {
                            "is_up": is_up,
                            "cpu_util": n_cpu.get(node_name, 100.0),
                            "memory_util": n_mem.get(node_name, 100.0),
                            "gpu_util": n_gpu.get(node_name),      
                            "gpu_mem_util": n_gpu_mem.get(node_name), 
                            "gpu_power": n_gpu_pwr.get(node_name),
                            
                            # 四大绝对剩余容量
                            "gpu_mem_avail_gb": n_gpu_mem_avail.get(node_name, 0.0) if n_gpu_mem_avail else 0.0,
                            "memory_avail_gb": n_mem_avail.get(node_name, 0.0) if n_mem_avail else 0.0,
                            "cpu_avail_cores": n_cpu_avail.get(node_name, 0.0) if n_cpu_avail else 0.0,
                            "gpu_avail_count": int(n_gpu_avail.get(node_name, 0)) if n_gpu_avail else 0
                        }

                    # 3. 更新全局缓存
                    cls.global_metrics_cache[cluster_id] = {
                        "cpu_util": c_cpu if c_cpu is not None else 100.0,
                        "memory_util": c_mem if c_mem is not None else 100.0,
                        "gpu_util": c_gpu,
                        "gpu_mem_util": c_gpu_mem, # 🌟 存入集群级显存利用率
                        "memory_remaining": 100 - c_mem if c_mem is not None else 0,
                        "nodes": nodes_data 
                    }
                    
            except Exception as e:
                print(f"后台采集数据失败: {e}")
            
            await asyncio.sleep(5)

    @classmethod
    async def close(cls):
        """优雅释放资源"""
        if cls._polling_task:
            cls._polling_task.cancel()
            print("后台数据采集任务已取消")
            
        for client in cls.prom_clients.values():
            if hasattr(client, "close"):
                await client.close()
        print("所有 Prometheus 客户端连接已关闭")