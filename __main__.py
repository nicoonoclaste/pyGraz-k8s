"""A Kubernetes Python Pulumi program"""

import pulumi
from pulumi_kubernetes.apps.v1 import Deployment
from pulumi_kubernetes.core.v1 import Service

import cilium

cfg = pulumi.Config()

cilium_chart = cilium.deploy(cfg, features = {
    'l7'
})

pulumi.export(
    "cilium-ingress",
    # FIXME: this should be a flat list, either filter by svc name or flatten
    cilium_chart.resources.apply(lambda resources: pulumi.Output.all(*[
        svc.metadata.name.apply(lambda name: [name == "cilium-ingress", svc])
        for svc in resources
    ])).apply(lambda resources: pulumi.Output.all(*[
        svc #.status.load_balancer.ingress
        for [p, svc] in resources
        if p
    ]))
)
