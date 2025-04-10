from pulumi_kubernetes.helm.v3 import Release, ReleaseArgs, RepositoryOptsArgs

def deploy():
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
            },
        ),
    )

    return cilium
