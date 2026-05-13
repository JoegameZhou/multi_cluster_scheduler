# app/utils/resource_parser.py

def parse_k8s_memory_to_gb(mem_str: str) -> float:
    """
    将 K8s 的内存字符串转换成统一的 GB (浮点数)
    例如: "8Gi" -> 8.0, "500Mi" -> 0.488
    """
    if not mem_str:
        return 0.0
        
    mem_str = str(mem_str).strip()
    
    try:
        if mem_str.endswith("Gi"):
            return float(mem_str[:-2])
        elif mem_str.endswith("Mi"):
            return float(mem_str[:-2]) / 1024.0
        elif mem_str.endswith("G"):
            return float(mem_str[:-1]) * 0.931
        elif mem_str.endswith("M"):
            return float(mem_str[:-1]) / 1000.0
        elif mem_str.isdigit(): # 纯数字默认为 Bytes
            return float(mem_str) / (1024**3)
        return float(mem_str)
    except ValueError:
        return 0.0

def parse_k8s_cpu_to_cores(cpu_str) -> float:
    """
    将 K8s 的 CPU 字符串转换成统一的核心数 (浮点数)
    例如: "500m" -> 0.5, "2" -> 2.0
    """
    if not cpu_str:
        return 0.0
        
    cpu_str = str(cpu_str).strip()
    
    try:
        if cpu_str.endswith("m"):
            return float(cpu_str[:-1]) / 1000.0
        return float(cpu_str)
    except ValueError:
        return 0.0