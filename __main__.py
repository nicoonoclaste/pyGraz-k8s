"""A Kubernetes Python Pulumi program"""

import pulumi
import pulumi_kubernetes as k8s

import cilium


# Setup Cilium
cfg = pulumi.Config()

cilium_chart = cilium.deploy(cfg, features = {
    "hubble",
})


# Deploy Nginx as a demo app (NOT how it is normally used with k8s)
app_name = "demo-app"
app_labels = { "app": app_name }
deployment = k8s.apps.v1.Deployment(
    app_name,
    opts = pulumi.ResourceOptions(
        depends_on = [ cilium_chart ],  # Necessary to ensure the pod is managed by cilium
    ),
    spec = {
        "selector": { "match_labels": app_labels },
        "replicas": 1,
        "template": {
            "metadata": { "labels": app_labels },
            "spec": { "containers": [{ "name": app_name, "image": "nginx" }] }
        },
    },
)

# Allocate an address for the Deployment
service = k8s.core.v1.Service(
    "demo-svc",
    metadata = {
        "labels": deployment.spec["template"]["metadata"]["labels"],
    },
    spec = {
        "type": "LoadBalancer",
        "ports": [{ "port": 80, "target_port": 80, "protocol": "TCP" }],
        "selector": app_labels,
    }
)

pulumi.export(
    "ip",
    service.status.load_balancer.ingress.apply(lambda i: map(lambda j: j.ip, i))
)
