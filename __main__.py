"""A Kubernetes Python Pulumi program"""

import pulumi
from pulumi_kubernetes.apps.v1 import Deployment

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

pulumi.export("name", deployment.metadata["name"])
