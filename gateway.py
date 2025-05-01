"""Deploy a Gateway API implementation.

The Gateway API supersedes the Ingress API, capturing L7 routing rules in a frontend-agnostic way.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache, reduce

import pulumi
import pulumi_kubernetes as k8s


@cache
def crds() -> pulumi.Resource:
    """Deploy the Gateway API's Custom Resource Definitions.

    Singleton, can be called by each resource depending on those definitions.
    """
    return k8s.yaml.v2.ConfigFile(
        "gateway-api-CRDs",
        file = "https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml",
    )


@dataclass(frozen = True, slots = True)
class GatewayDeployment:
    """Typed dict for :py:func:`gateway.deploy`'s return type."""

    namespace: k8s.core.v1.Namespace
    chart: k8s.helm.v4.Chart
    gw: k8s.apiextensions.CustomResource


def deploy(depends_on: Sequence[pulumi.Resource] = ()) -> GatewayDeployment:
    """Deploy Nginx Gateway Fabric as the Gateway API implementation."""
    namespace = k8s.core.v1.Namespace("gateway")

    chart = k8s.helm.v4.Chart(
        "nginx-gateway-fabric",
        chart = "oci://ghcr.io/nginx/charts/nginx-gateway-fabric",
        version = "1.6.2",
        namespace = namespace.metadata.name,
        opts = pulumi.ResourceOptions(depends_on = [ crds(), *depends_on ]),
    )

    # TODO: find a reasonable way to handle CRDs, crd2pulumi is not useable as-is
    default_gw = k8s.apiextensions.CustomResource(
        "default-gw",
        api_version = "gateway.networking.k8s.io/v1",
        kind = "Gateway",
        metadata = k8s.meta.v1.ObjectMetaArgs(namespace = namespace.metadata.name),
        opts = pulumi.ResourceOptions(depends_on = crds()),
        spec = {
            "gatewayClassName": "nginx",
            "listeners": [ {
                "name": "http",
                "port": 80,
                "protocol": "HTTP",
                "hostname": "*.k8s.local",
                "allowedRoutes": {
                    "kinds": [ { "kind": "HTTPRoute" } ],
                    "namespaces": { "from": "All" },  # TODO: restrict to specific namespaces
                },
            } ],
        },
    )

    pulumi.export(
        "nginx-ingress",
        chart.resources.apply(lambda resources: pulumi.Output.all(*(
            pulumi.Output.all(
                ips = svc.status.load_balancer.apply(
                    lambda lb: [ ingress.ip for ingress in lb.ingress or [] ],
                ),
                pred = svc.metadata.apply(lambda m: m.name == "nginx-gateway-fabric"),
            )
            for svc in resources  # type: ignore
            if isinstance(svc, k8s.core.v1.Service)
        ))).apply(lambda out: reduce(
            lambda acc, x: acc + (x["ips"] if x["pred"] else []),
            out,
            [],
        )),
    )

    return GatewayDeployment(namespace, chart, default_gw)
