"""Set up the Cilium CNI, as well as (optionally) Hubble observability platform.

Cilium handles basic inter-node networking, service mesh, as well as security functions:
- traffic policy enforcement, from L2/L3 firewalling to L7 policies ;
- logging of network flows, via the Hubble feature.

Cilium implements as much functionality as possible through eBPF programs executed
in-kernel, to avoid the overhead of copying data to userspace and switching contexts.
"""

from collections.abc import Set
from typing import Literal

import pulumi
import pulumi_kubernetes as k8s

Feature = Literal["hubble"]


def deploy(cfg: pulumi.Config, *, features: Set[Feature] = frozenset()) -> k8s.helm.v4.Chart:
    """Deploy Cilium with a given set of features.

    Requires `k8sEndpoint` to be set in the Pulumi configuration;
      possible values can be obtained from `kubectl get endpoints kubernetes`.
    """
    # address and port of the k8s API server to use
    host, port = cfg.require("k8sEndpoint").rsplit(":", 1)

    return k8s.helm.v4.Chart(
        "cilium",
        chart = "./cilium-1.17.2.tgz",  # FIXME pulumi somehow gets something else from the repo?
        repository_opts = k8s.helm.v4.RepositoryOptsArgs(
            repo = "https://helm.cilium.io/",
        ),
        version = "1.17.2",  # TODO: autoupdate?
        namespace = "kube-system",
        # TODO signature verification?
        values = {
            "image": { "pullPolicy": "IfNotPresent" },
            "operator": { "replicas": 1 },  # No HA, this is a demo cluster

            # Avoid `kube-proxy`, let Cilium sling packets around
            #  requires `kubeProxyMode: "none"` in `kind-config.yaml`
            "kubeProxyReplacement": True,
            "k8sServiceHost": host,
            "k8sServicePort": port,

            # Optionally enable the Hubble observability tool
            "hubble": {
                "relay": { "enabled": True },
                "ui": { "enabled": True },
            } if "hubble" in features else {},
        },
    )
