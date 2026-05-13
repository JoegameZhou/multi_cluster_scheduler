# Multi-Cluster Scheduler

多集群调度器是一个基于Python和FastAPI的服务，用于在多个Kubernetes集群之间调度任务。采用了"决策与执行解耦"的架构模式，只负责计算"应该去哪个集群"，而将与API Server交互的具体"执行"动作交还给调用方。

## 项目结构

项目采用了分层架构和策略模式，结构清晰，易于扩展和维护：

- 核心代码目录 ( app/ )：包含了FastAPI应用、API路由、核心逻辑、数据模型、外部客户端和调度策略
- 配置文件目录 ( config/ )：包含集群配置文件
- 依赖文件 ( requirements.txt )：列出了项目所需的Python依赖
- Dockerfile ：用于容器化部署
- README.md ：项目说明文档

```
multi-cluster-scheduler/
├── app/                        # 核心代码目录
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口程序
│   ├── api/                    # 路由层
│   │   └── v1/                 # v1 API
│   │       ├── __init__.py
│   │       ├── schedule.py     # 调度接口
│   │       └── health.py       # 健康检查接口
│   ├── core/                   # 核心配置
│   │   ├── __init__.py
│   │   ├── context.py          # 全局上下文
│   │   └── scheduler.py        # 调度器核心逻辑
│   ├── schemas/                # 数据模型
│   │   ├── __init__.py
│   │   └── payload.py          # 请求与响应的结构定义
│   ├── clients/                # 外部客户端
│   │   ├── __init__.py
│   │   ├── k8s_client.py       # Kubernetes客户端（保留但未使用）
│   │   └── prom_client.py      # Prometheus客户端
│   ├── strategies/             # 调度策略
│   │   ├── inter_cluster/      # 集群间策略
│   │   │   ├── __init__.py
│   │   │   ├── load_balance.py # 负载均衡策略
│   │   │   ├── proximity.py    # 就近性策略
│   │   │   └── resource_match.py # 资源匹配度策略
│   │   ├── intra_cluster/      # 集群内策略
│   │   │   ├── __init__.py
│   │   │   ├── resource_load.py # 资源负载策略
│   │   │   ├── node_affinity.py # 节点亲和性策略
│   │   │   └── task_priority.py # 任务优先级策略
│   │   └── __init__.py
│   ├── services/               # 服务层（预留）
│   │   └── __init__.py
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       ├── logger.py           # 日志配置
│       └── resource_parser.py  # 资源解析工具
├── config/                     # 配置文件
│   └── clusters.yaml           # 集群配置
├── .env.example                # 环境变量示例
├── Dockerfile                  # Docker构建文件
├── README.md                   # 项目说明文档
└── requirements.txt            # Python依赖
```

## 功能特性

- **多集群管理**：支持管理多个Kubernetes集群
- **集群间调度**：支持基于负载均衡、就近性、资源匹配度的调度策略
- **集群内调度**：支持基于资源负载、节点亲和性、任务优先级的调度策略
- **RESTful API**：提供标准的RESTful API接口
- **容器化部署**：支持Docker容器化部署
- **高可用**：支持多副本部署
- **内存缓存**：使用Python内存缓存替代Redis，提高调度性能
- **异步架构**：使用asyncio和httpx实现全异步架构，提高并发处理能力

## 技术栈

项目使用了以下技术栈和依赖库：

- **后端框架**：FastAPI - 高性能的Python Web框架，用于构建RESTful API
- **容器编排**：Kubernetes - 用于容器编排和管理（仅作为目标平台）
- **监控系统**：Prometheus - 用于监控集群资源使用情况
- **容器化**：Docker - 用于构建和部署应用
- **Python库**：
  - `prometheus-api-client` - Prometheus API客户端，用于查询监控数据
  - `pydantic` - 数据验证库，用于定义请求和响应模型
  - `python-dotenv` - 环境变量管理库
  - `structlog` - 结构化日志库
  - `httpx` - 异步HTTP客户端，用于与Prometheus交互
  - `asyncio` - 异步I/O库，用于实现异步架构
- **部署工具**：kubectl - Kubernetes命令行工具，用于部署和管理应用

## 技术架构

项目采用了分层架构设计：

1. **API层**：处理HTTP请求，验证输入参数，返回响应
2. **核心层**：包含调度器核心逻辑，负责执行调度策略
3. **策略层**：实现各种调度策略，包括集群间和集群内策略
4. **客户端层**：封装与外部系统的交互，如Prometheus
5. **工具层**：提供通用工具函数，如日志管理和资源解析

这种架构设计使得项目具有良好的可扩展性和可维护性，便于添加新的调度策略或集成新的外部系统。

## 部署步骤

### 1. 准备工作

- 安装Docker
- 准备Prometheus服务（每个集群需要部署Prometheus）

### 2. 构建镜像

```bash
# 1. 本地构建极简名称
docker build -t multi-cluster-scheduler:v1.0.0 .
# 2. 贴上目标仓库的“快递单”
docker tag multi-cluster-scheduler:v1.0.0 your-registry.com/multi-cluster-scheduler:v1.0.0
# 3. 发往目标仓库
docker push your-registry.com/multi-cluster-scheduler:v1.0.0

```

### 3. 部署到Kubernetes

```bash
# 创建命名空间
kubectl create namespace scheduler-system

# 创建配置文件
kubectl create configmap scheduler-config --from-file=config/clusters.yaml -n scheduler-system

# 部署服务（使用修改后的deployment.yaml和service.yaml）
kubectl apply -f deploy/deployment.yaml
kubectl apply -f deploy/service.yaml

```

### 4. 验证部署

```bash
kubectl get pods -n scheduler-system
curl http://scheduler-svc.scheduler-system.svc.cluster.local/health/live
```

## API接口

### 1. 调度任务

- **URL**: `/api/v1/schedule`
- **Method**: POST
- **Request Body**:
  ```json
  {
    "task_name": "ai-vision-inspection-01",
    "inter_cluster_strategy": "load_balance",
    "intra_cluster_strategy": "resource_load",
    "priority": 10,
    "resources": {
      "cpu": 4.0,
      "memory": "8Gi",
      "gpu": 1,
      "gpu_memory": null
    }
  }
  ```
- **Response**:
  ```json
  {
  "success": true,
  "message": "Scheduling successful",
  "cluster_name": "Jetson-K3s",
  "node_name": "ubuntu",
  "k8s_native_strategy": null
  }
  ```

### 2. 健康检查

- **URL**: `/health/live`
- **Method**: GET
- **Response**:
  ```json
  {
    "status": "ok"
  }
  ```

## 本地开发

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

3. 访问API文档

```
http://localhost:8000/docs
```

## 调测步骤

1. **环境准备**：
   - 激活UV虚拟环境：根据你的操作系统，可能是`source .venv/bin/activate`（Linux/MacOS）或`venv\Scripts\activate`（Windows）
   - 安装依赖：`pip install -r requirements.txt`

2. **配置修改**：
   - 修改`config/clusters.yaml`文件，配置你的集群信息
   - 创建`.env`文件，配置环境变量

3. **启动服务**：
   - 运行：`uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

4. **测试API**：
   - 使用Postman或curl测试调度API
   - 检查服务日志，确认调度过程

5. **验证结果**：
   - API返回的`cluster_name`字段即为选中的集群
   - 调用方可以使用这个结果进行实际的Pod部署

## 架构设计说明

### 决策与执行解耦

项目采用了"决策与执行解耦"的架构模式：

- **决策**：Python后端作为"调度算法引擎"，只负责计算"应该去哪个集群"
- **执行**：与API Server交互、创建Pod的具体"执行"动作交还给调用方

### 内存缓存机制

项目使用Python内存缓存替代Redis，实现了以下功能：

- **后台轮询**：每5秒自动更新集群指标数据
- **毫秒级响应**：调度算法直接从内存读取数据，响应时间≤1秒
- **零外部依赖**：不需要部署Redis，降低了部署复杂性和运维成本

### 异步架构

项目使用asyncio和httpx实现全异步架构：
- **高并发**：支持同时处理多个调度请求
- **非阻塞**：后台轮询任务不会阻塞主事件循环
- **性能优化**：适合多集群环境下的高并发调度场景
