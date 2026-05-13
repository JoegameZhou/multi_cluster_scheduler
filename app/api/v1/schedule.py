
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.payload import ScheduleRequest, ScheduleResponse, GlobalPolicyUpdate
from app.core.scheduler import Scheduler
from app.core.context import Context  # 🌟 引入全局上下文

router = APIRouter()

def get_scheduler():
    return Scheduler()

# ================= 1. 任务执行接口 =================
@router.post("/schedule", response_model=ScheduleResponse, summary="提交调度任务")
async def schedule_task(
    request: ScheduleRequest,
    scheduler: Scheduler = Depends(get_scheduler)
):
    result = await scheduler.run(request)
    # if not result.success:
        # raise HTTPException(status_code=400, detail=result.message)

    # ================= 🌟 核心修改说明 =================
    # 删除了之前类似下面这种抛出异常的代码：
    # if not result.success:
    #     raise HTTPException(status_code=400, detail=result.message)
    #
    # 无论有没有找到节点，我们都直接返回 result 对象！
    # 这样 FastAPI 永远会返回 HTTP 200 OK
    # ===================================================
    return result

# ================= 2. 策略查询接口 (🌟 增加安全容错) =================
@router.get("/policies/schedule", summary="查询系统支持的调度策略选项")
async def get_schedule_policies():
    
    # 🌟 安全读取：如果系统刚启动还没设置过，给一个默认配置
    current_policy = getattr(Context, "global_policy_cache", {
        "inter_cluster_strategy": "load_balance",
        "intra_cluster_strategy": "resource_load"
    })
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "current_default_policy": current_policy, 
            
            "inter_cluster_policies": [
                { "value": "load_balance", "label": "集群负载均衡", "desc": "将任务均匀分配到各集群" },
                { "value": "proximity", "label": "就近性(同地域优先)", "desc": "优先调度到地理位置最近的集群" },
                { "value": "resource_match", "label": "资源匹配度", "desc": "根据任务资源需求选择最匹配的集群" }
            ],
            "intra_cluster_policies": [
                { "value": "resource_load", "label": "基于资源负载", "desc": "优先选择当前资源使用率最低的节点" },
                { "value": "node_affinity", "label": "节点亲和性", "desc": "根据节点标签规则进行匹配" },
                { "value": "task_priority", "label": "任务优先级", "desc": "结合任务优先级进行抢占式调度" }
            ]
        }
    }

# ================= 3. 策略设置接口 =================
@router.put("/policies/schedule", summary="设置系统全局默认调度策略")
async def update_global_schedule_policy(policy: GlobalPolicyUpdate):
    # 将前端传来的新策略，写入到内存缓存中
    Context.global_policy_cache = {
        "inter_cluster_strategy": policy.default_inter_strategy,
        "intra_cluster_strategy": policy.default_intra_strategy
    }
    
    return {
        "code": 0,
        "message": "全局策略更新成功",
        "data": Context.global_policy_cache
    }


