"""Set up a local DNS cache on each node, make cluster-local names resolvable by the host.

Uses Hickory DNS as a caching, validating, stub resolver.
"""

import pulumi
import pulumi_kubernetes as k8s
import tomlkit


def deploy(cfg: pulumi.Config) -> k8s.core.v1.Service:
    """Deploy a local DNS cache on each node, and update host-side `resolv.conf`.

    The resolver is Hickory DNS, configured with the following zones:
    - `cluster.local`, forwarded to `kube-dns` ;
    - `.`, forwarded to `9.9.9.9`.
    """
    labels = { "app": "dns-cache" }
    ns = k8s.core.v1.Namespace("dns")
    meta = k8s.meta.v1.ObjectMetaArgs(namespace = ns.metadata.name, labels = labels)
    hickory_address = "10.96.0.53"
    coredns_address = "10.96.0.10"

    _ = k8s.apps.v1.DaemonSet(
        "dns-cache",
        metadata = meta,
        spec = k8s.apps.v1.DaemonSetSpecArgs(
            selector = k8s.meta.v1.LabelSelectorArgs(match_labels = labels),
            template = k8s.core.v1.PodTemplateSpecArgs(
                metadata = meta,
                spec = k8s.core.v1.PodSpecArgs(
                    tolerations = (
                        k8s.core.v1.TolerationArgs(
                            # Run the DNS resolver on control-plane nodes too
                            key = "node-role.kubernetes.io/control-plane",
                            operator = "Exists",
                            effect = "NoSchedule",
                        ),
                    ),
                    # dns_policy = "None",
                    priority_class_name = "system-node-critical",
                    containers = (
                        k8s.core.v1.ContainerArgs(
                            name = "hickory-dns",
                            image = "docker.io/hickorydns/hickory-dns:latest",
                            image_pull_policy = "IfNotPresent",
                            args = [
                                "-c", "/run/cm/hickory.toml",
                            ],
                            ports = [
                                k8s.core.v1.ContainerPortArgs(
                                    container_port = 53,
                                    name = f"dns-{proto.lower()}",
                                    protocol = proto,
                                )
                                for proto in ( "TCP", "UDP" )
                            ],
                            # TODO use a build with Prometheus metrics, set {live, readi}ness_probe
                            volume_mounts = [
                                k8s.core.v1.VolumeMountArgs(
                                    name = "configmap",
                                    mount_path = "/run/cm",
                                    read_only = True,
                                ),
                            ],
                        ),
                    ),
                    init_containers = (  # HACK this should ideally run once hickory-dns is up
                        k8s.core.v1.ContainerArgs(
                            name = "update-host-resolvconf",
                            image = "busybox",
                            image_pull_policy = "IfNotPresent",
                            args = [ "sh", "-c", "cat /run/cm/resolv.conf > /host/resolv.conf" ],
                            volume_mounts = [
                                k8s.core.v1.VolumeMountArgs(
                                    name = "host-resolvconf",
                                    mount_path = "/host/resolv.conf",
                                    read_only = False,
                                ),
                                k8s.core.v1.VolumeMountArgs(
                                    name = "configmap",
                                    mount_path = "/run/cm",
                                    read_only = True,
                                ),
                            ],
                        ),
                    ),
                    volumes = [
                        k8s.core.v1.VolumeArgs(
                            name = "host-resolvconf",
                            host_path = k8s.core.v1.HostPathVolumeSourceArgs(
                                path = "/etc/resolv.conf",
                                type = "File",
                            ),
                        ),
                        k8s.core.v1.VolumeArgs(
                            name = "configmap",
                            config_map = k8s.core.v1.ConfigMapVolumeSourceArgs(
                                name = k8s.core.v1.ConfigMap(
                                    "dns-cache-cm",
                                    metadata = meta,
                                    data = {
                                        "resolv.conf": "\n".join((
                                            f"nameserver {hickory_address}",
                                            "search svc.cluster.local cluster.local",
                                            "options edns0 trust-ad ndots:5",
                                        )) + "\n",
                                        "hickory.toml": tomlkit.dumps({
                                            "listen_addrs_ipv4": [ "0.0.0.0" ],
                                            # TODO default zones, DNS-over-QUIC
                                            "zones": [
                                                {
                                                    "zone": zone,
                                                    "zone_type": "External",
                                                    "stores": {
                                                        "type": "forward",
                                                        "name_servers": [ {
                                                            "socket_addr": addr,
                                                            "protocol": "tcp",
                                                            "trust_negative_responses": True,
                                                        } ],
                                                    },
                                                }
                                                for zone, addr in {
                                                    "cluster.local": f"{coredns_address}:53",
                                                    ".": "9.9.9.9:53",
                                                }.items()
                                            ],
                                        }),
                                    },
                                ).metadata.name,
                            ),
                        ),
                    ],
                ),
            ),
        ),
    )

    return k8s.core.v1.Service(
        "dns-cache",
        metadata = meta,
        spec = k8s.core.v1.ServiceSpecArgs(
            type = "ClusterIP",
            cluster_ip = hickory_address,
            ports = [
                k8s.core.v1.ServicePortArgs(
                    name = f"dns-{proto.lower()}",
                    port = 53,
                    target_port = f"dns-{proto.lower()}",
                    protocol = proto,
                )
                for proto in ("TCP", "UDP")
            ],
            selector = labels,
        ),
    )
