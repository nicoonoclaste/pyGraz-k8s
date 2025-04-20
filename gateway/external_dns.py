import pulumi
import pulumi_kubernetes as k8s

def deploy(depends_on):
    namespace = k8s.core.v1.Namespace("external-dns")
    etcd_operator = k8s.yaml.v2.ConfigFile(
        "etcd-operator",
        file = "https://github.com/etcd-io/etcd-operator/releases/download/v0.1.0/install-v0.1.0.yaml",
        opts = pulumi.ResourceOptions(depends_on = depends_on),
    )

    # Setup an etcd cluster for the external coredns
    # TODO CRD bindings
    etcd_cluster = k8s.apiextensions.CustomResource(
        "etcd-coredns",
        metadata = { "namespace": namespace },
        api_version = "operator.etcd.io/v1alpha1",
        kind = "EtcdCluster",
    )

    coredns = k8s.helm.v4.Chart(
        "coredns",
        chart = "coredns",
        repository_opts = k8s.helm.v3.RepositoryOptsArgs(
            repo = "https://coredns.github.io/helm",
        ),
        version = "1.39.2",
        namespace = namespace,
        values = {
            "isClusterService": False,  # this is an externally-facing DNS server
            "serviceType": "LoadBalancer",
            "servers" : [ {
                "zones": [ { "zone": "k8s.local." } ],
                "port": 53,
                "plugins": [
                    { "name": "errors" },  # error logging

                    # health, readiness, and metrics endpoints
                    { "name": "health" },
                    { "name": "ready" },
                    { "name": "prometheus",
                      "parameters": "0.0.0.0:9153" },

                    # etcd plugin
                    { "name": "etcd",
                      # "parameters": "k8s.local.",
                      "configBlock": """
                        stubzones
                        endpoint TODO
                        tls CERT KEY CACERT TODO
                      """ },
                ],
            } ],
        },
    )

    # extdns_chart = k8s.helm.v4.Chart(
    #     "external-dns",
    #     chart = "external-dns",
    #     repository_opts = k8s.helm.v3.RepositoryOptsArgs(
    #         repo = "https://kubernetes-sigs.github.io/external-dns/",
    #     ),
    #     version = "1.15.2",
    #     namespace = namespace,
    #     values = {
    #         # Those would be different in a production system,
    #         #  but here we'll run an in-cluster NS authoritative for k8s.local
    #         "domainFilters": [ "k8s.local" ],
    #         "provider": {
    #             "name": "coredns",
    #         },
    #     },
    # )
