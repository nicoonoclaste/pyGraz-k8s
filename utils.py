import pulumi_kubernetes as k8s


def http_get(path: str, port: str | int = "http") -> k8s.core.v1.ProbeArgs:
    return k8s.core.v1.ProbeArgs(
        http_get = k8s.core.v1.HTTPGetActionArgs(path = path, port = port),
    )
