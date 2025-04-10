import pulumi
from pulumi_kubernetes.helm.v3 import Release, ReleaseArgs, RepositoryOptsArgs

def deploy(cfg: pulumi.Config):
    # address and port of the k8s API server to use
    host, port = cfg.require("k8sEndpoint").rsplit(":", 1)

    cilium = Release(
        "cilium",
        ReleaseArgs(
            chart = "cilium",
            repository_opts = RepositoryOptsArgs(
                repo = "https://helm.cilium.io/",
            ),
            version = "1.17.2",  # TODO: autoupdate?
            namespace = "kube-system",
            values = {
                "image": { "pullPolicy": "IfNotPresent" },
                "operator": { "replicas": 1 },  # No HA, this is a demo cluster

                # Avoid `kube-proxy`, let Cilium sling packets around
                #  requires `kubeProxyMode: "none"` in `kind-config.yaml`
                "kubeProxyReplacement": True,
                "k8sServiceHost": host,
                "k8sServicePort": port,
            },
        ),
    )

    return cilium
