"""Set up best practices and common functionality on a Kubernetes cluster."""

import pulumi
import pulumi_kubernetes as k8s

import cilium
import gateway
from utils import http_get

# Setup Cilium
cfg = pulumi.Config()

cilium_chart = cilium.deploy(cfg, features = {
    "hubble",
})

# Setup Nginx Gateway Fabric, as the Gateway API implementation
#  see https://gateway-api.sigs.k8s.io/
gw = gateway.deploy(depends_on = ( cilium_chart, ))

# Demo application
# adapted from https://docs.nginx.com/nginx-gateway-fabric/get-started/
demo_ns = k8s.core.v1.Namespace("cafe")

for beverage in ("coffee", "tea"):
    labels = { "beverage": beverage }
    meta = k8s.meta.v1.ObjectMetaArgs(
        namespace = demo_ns,
        labels = labels,
    )

    dpl = k8s.apps.v1.Deployment(
        beverage,
        metadata = meta,
        opts = pulumi.ResourceOptions(depends_on = ( cilium_chart, )),
        spec = k8s.apps.v1.DeploymentSpecArgs(
            replicas = 1,
            selector = k8s.meta.v1.LabelSelectorArgs(match_labels = labels),
            template = k8s.core.v1.PodTemplateSpecArgs(
                metadata = k8s.meta.v1.ObjectMetaArgs(labels = labels),
                spec = k8s.core.v1.PodSpecArgs(
                    containers = [ k8s.core.v1.ContainerArgs(
                        name = beverage,
                        image = "nginxdemos/nginx-hello:plain-text",
                        ports = [ k8s.core.v1.ContainerPortArgs(
                            name = "http",
                            container_port = 8080,
                        ) ],
                        liveness_probe = http_get("/"),
                        readiness_probe = http_get("/"),
                    ) ],
                ),
            ),
        ),
    )

    svc = k8s.core.v1.Service(
        beverage,
        metadata = meta,
        spec = k8s.core.v1.ServiceSpecArgs(
            ports = [ k8s.core.v1.ServicePortArgs(
                port = 80,
                target_port = "http",
            ) ],
            selector = labels,
        ),
    )

    _ = k8s.apiextensions.CustomResource(
        f"{beverage}-route",
        api_version = "gateway.networking.k8s.io/v1",
        kind = "HTTPRoute",
        opts = pulumi.ResourceOptions(depends_on = gw["crd"]),
        spec = {
            "parentRefs": [ {
                "name": "gateway",
                "namespace": gw["namespace"],
                "sectionName": "http",
            } ],
            "hostnames": [ "cafe.k8s.local" ],
            "rules": [ {
                "backendRefs": [ {
                    "name": svc.metadata.name,
                    "port": 80,
                } ],
            } ],
        },
    )
