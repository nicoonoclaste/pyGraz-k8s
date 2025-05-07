"""A caching, pull-through OCI image cache.

`ociregistry` requires neither changes to image URLs, nor per-registry configuration,
making it the lowest-touch option I could find.

`containerd` is configured to use the registry through the snippet in `kind-config.yaml`,
which refers to `registry.d/_default`.
"""

from collections.abc import Sequence

import pulumi
import pulumi_kubernetes as k8s

from utils import http_get


def deploy(
    cfg: pulumi.Config, *,
    depends_on: Sequence[pulumi.Resource] = (),
) -> tuple[k8s.apps.v1.Deployment, k8s.core.v1.Service]:
    """Deploy `ociregistry`.

    A persistent volume is created for the service, but (so far) no care is given to
    making the cache persist across cluster creation/destruction.
    """
    ns = k8s.core.v1.Namespace(
        "oci-cache",
        # don't use automatic naming, as the containerd config depends on the name
        metadata = k8s.meta.v1.ObjectMetaArgs(name = "oci-cache"),
    )

    labels = { "app": "oci-cache" }
    meta = k8s.meta.v1.ObjectMetaArgs(
        namespace = ns.metadata.name,
        labels = labels,
    )

    pvc = k8s.core.v1.PersistentVolumeClaim(
        "oci-cache",
        metadata = meta,
        spec = {
            "access_modes": ("ReadWriteOncePod", ),
            "resources": { "requests": { "storage": "2Gi" } },
        },
    )

    # TODO: setup mTLS between containerd and ociregistry?
    dpl = k8s.apps.v1.Deployment(
        "ociregistry",
        metadata = meta,
        opts = pulumi.ResourceOptions(depends_on = depends_on),
        spec = k8s.apps.v1.DeploymentSpecArgs(
            replicas = 1,
            selector = k8s.meta.v1.LabelSelectorArgs(match_labels = labels),
            template = k8s.core.v1.PodTemplateSpecArgs(
                metadata = k8s.meta.v1.ObjectMetaArgs(labels = labels),
                spec = k8s.core.v1.PodSpecArgs(
                    containers = [ k8s.core.v1.ContainerArgs(
                        name = "ociregistry",
                        image = "quay.io/appzygy/ociregistry:1.8.2",
                        ports = [ k8s.core.v1.ContainerPortArgs(
                            name = "http",
                            container_port = 8080,
                        ) ],
                        liveness_probe = http_get("/health"),
                        readiness_probe = http_get("/health"),
                    ) ],
                    volumes = [ k8s.core.v1.VolumeArgs(
                        name = "images",
                        persistent_volume_claim = k8s.core.v1.PersistentVolumeClaimVolumeSourceArgs(
                            claim_name = pvc.metadata.name,
                            read_only = False,
                        ),
                    ) ],
                ),
            ),
        ),
    )

    svc = k8s.core.v1.Service(
        "oci-cache",
        # don't use automatic naming, as the containerd config depends on the name
        # FIXME find official API surface for this
        metadata = k8s.meta.v1.ObjectMetaArgs(name = "oci-cache", **meta.__dict__),
        spec = k8s.core.v1.ServiceSpecArgs(
            type = "ClusterIP",
            ports = [ k8s.core.v1.ServicePortArgs(
                port = 80,
                target_port = "http",
            ) ],
            selector = labels,
        ),
    )

    return (dpl, svc)
