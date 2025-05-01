"""Convenience wrappers around :py:module:`pulumi_kubernetes`.

The `k8s` module directly maps Kubernetes' APIs, which are relatively low-level and verbose.
This module is meant to “fill-in the gap” and provide terser, higher-level APIs.
"""

import pulumi_kubernetes as k8s


def http_get(path: str, port: str | int = "http") -> k8s.core.v1.ProbeArgs:
    """Construct a liveness or readiness probe."""
    return k8s.core.v1.ProbeArgs(
        http_get = k8s.core.v1.HTTPGetActionArgs(path = path, port = port),
    )
