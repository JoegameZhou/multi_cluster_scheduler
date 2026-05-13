from kubernetes import client, config

class K8sClient:
    def __init__(self, kubeconfig_path):
        self.kubeconfig_path = kubeconfig_path
        self.config = config.load_kube_config(config_file=kubeconfig_path)
        self.api_client = client.ApiClient(self.config)
        self.core_api = client.CoreV1Api(self.api_client)
        self.apps_api = client.AppsV1Api(self.api_client)
        self.batch_api = client.BatchV1Api(self.api_client)

    def create_pod(self, namespace, pod_manifest):
        """创建Pod"""
        try:
            return self.core_api.create_namespaced_pod(namespace, pod_manifest)
        except Exception as e:
            print(f"K8s create pod error: {e}")
            return None

    def create_deployment(self, namespace, deployment_manifest):
        """创建Deployment"""
        try:
            return self.apps_api.create_namespaced_deployment(namespace, deployment_manifest)
        except Exception as e:
            print(f"K8s create deployment error: {e}")
            return None

    def create_statefulset(self, namespace, statefulset_manifest):
        """创建StatefulSet"""
        try:
            return self.apps_api.create_namespaced_stateful_set(namespace, statefulset_manifest)
        except Exception as e:
            print(f"K8s create statefulset error: {e}")
            return None

    def create_job(self, namespace, job_manifest):
        """创建Job"""
        try:
            return self.batch_api.create_namespaced_job(namespace, job_manifest)
        except Exception as e:
            print(f"K8s create job error: {e}")
            return None

    def create_cronjob(self, namespace, cronjob_manifest):
        """创建CronJob"""
        try:
            return self.batch_api.create_namespaced_cron_job(namespace, cronjob_manifest)
        except Exception as e:
            print(f"K8s create cronjob error: {e}")
            return None
