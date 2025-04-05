"""A Kubernetes Python Pulumi program"""

import pulumi
from pulumi_kubernetes.apps.v1 import Deployment
from pulumi_kubernetes.core.v1 import Service

app_name = "nginx"
app_labels = { "app": app_name }

# Deploy Nginx
deployment = Deployment(
    app_name,
    spec = {
        "selector": { "match_labels": app_labels },
        "replicas": 1,
        "template": {
            "metadata": { "labels": app_labels },
            "spec": { "containers": [{ "name": app_name, "image": "nginx" }] }
        },
    },
)

# Allocate an IP to the Deployment.
frontend = Service(
    app_name,
    metadata = {
        "labels": deployment.spec["template"]["metadata"]["labels"],
    },
    spec = {
        "type": "LoadBalancer",
        "ports": [{ "port": 80, "target_port": 80, "protocol": "TCP" }],
        "selector": app_labels,
    }
)

ingress = frontend.status.load_balancer.apply(lambda v: v["ingress"][0] if "ingress" in v else "output<string>")
pulumi.export(
    "ip",
    ingress.apply(lambda v: v["ip"] if v and "ip" in v else (v["hostname"] if v and "hostname" in v else "output<string>"))
)
