from pydantic import BaseModel, Field
from typing import Optional

# ================= 核心算力需求 =================
class ResourceRequirement(BaseModel):
    cpu: float = Field(..., description="请求的 CPU 核心数，例如 2.0")
    memory: str = Field(..., description="请求的内存量，例如 '4Gi'")
    gpu: int = Field(default=0, description="请求的 GPU 数量，默认为 0（普通任务）")
    gpu_memory: Optional[str] = Field(default=None, description="请求的显存大小，例如 '8Gi' 或 '8000Mi'")

# ================= 任务调度载荷 (极简架构版) =================
class ScheduleRequest(BaseModel):
    """任务调度请求模型"""
    
    # 1. 追踪标识
    task_name: str = Field(..., description="任务名称，仅用于 Python 后端打印调度日志以便追踪")
    
    # 2. 调度策略指引
    inter_cluster_strategy: str = Field(..., pattern="^(load_balance|proximity|resource_match)$")
    intra_cluster_strategy: str = Field(..., pattern="^(resource_load|node_affinity|task_priority)$")
    target_cluster: Optional[str] = Field(default=None, description="若指定，则跳过跨集群调度，直接在该集群内寻找节点")
    priority: int = Field(default=1, description="任务优先级")
    
    # 3. 核心硬约束 (大脑计算的唯一依据)
    resources: ResourceRequirement

    # 🌟 必须添加这一段：开启“额外属性”允许模式
    model_config = {
        "extra": "allow"
    }
    
    # 4. 扩展储备 (可选)
    # container_image: Optional[str] = Field(default=None, description="备用字段：未来可用于实现镜像本地化(Image Locality)优先调度")

# ================= 返回结果 (出参不变) =================
class ScheduleResponse(BaseModel):
    success: bool
    message: str
    cluster_name: Optional[str] = None
    node_name: Optional[str] = None
    k8s_native_strategy: Optional[str] = None

# ================= 全局策略 (不变) =================
class GlobalPolicyUpdate(BaseModel):
    default_inter_strategy: str = Field(..., pattern="^(load_balance|proximity|resource_match)$")
    default_intra_strategy: str = Field(..., pattern="^(resource_load|node_affinity|task_priority)$")