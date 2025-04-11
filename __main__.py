"""A Kubernetes Python Pulumi program"""

from functools import reduce
import operator

import pulumi
import pulumi_kubernetes as k8s

import cilium

cfg = pulumi.Config()

cilium_chart = cilium.deploy(cfg, features = {
    'hubble', 'l7'
})

pulumi.export(
    "cilium-ingress",
    # FIXME: this should filter by svc name
    cilium_chart.resources.apply(lambda resources: [
        svc.status.load_balancer.apply(lambda lb: [ ingress.ip for ingress in lb.ingress or [] ])
        for svc in resources
        if isinstance(svc, k8s.core.v1.Service)
    ]).apply(lambda out:
        # convert a List[Output[_]] into an Output[List[_]]
        pulumi.Output.all(*out)
    ).apply(lambda out: reduce(operator.add, out, [])),
)

demo_app = k8s.yaml.v2.ConfigFile(
    "bookinfo-app",
    opts = pulumi.ResourceOptions(depends_on = cilium_chart),  # ensure the pods are managed by Cilium
    file = "https://raw.githubusercontent.com/istio/istio/release-1.11/samples/bookinfo/platform/kube/bookinfo.yaml",
)
demo_ingress = k8s.networking.v1.Ingress(
    spec = k8s.networking.v1.IngressSpecArgs(
        rules = [
            k8s.networking.v1.IngressRuleArgs(http = {
                "paths": [
                    {
                        "backend": { "service": {
                            "name": name,
                            "port": { "number": 9080 },
                        }},
                        "path": path,
                        "pathType": "Prefix",
                    }
                    for path, name in {
                            "/details": "details",
                            "/": "productpage",
                    }.items()
                ],
            }),
        ],
    ),
)
pulumi.export("demo-app", demo_ingress.status.load_balancer.ingress.apply(lambda i: map(lambda j: j.ip, i)))
