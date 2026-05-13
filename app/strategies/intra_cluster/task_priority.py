from typing import Dict, Any
from app.schemas.payload import ScheduleRequest

class TaskPriorityStrategy:
    def apply(self, request: ScheduleRequest, pod_manifest: Dict[str, Any]) -> Dict[str, Any]:
        """应用基于任务优先级的集群内调度策略"""
        # 这里可以添加优先级相关的配置
        # 例如，设置Pod的优先级类
        if "spec" not in pod_manifest:
            pod_manifest["spec"] = {}
        
        # 示例：设置Pod的优先级类
        # pod_manifest["spec"]["priorityClassName"] = "high-priority"
        
        return pod_manifest
