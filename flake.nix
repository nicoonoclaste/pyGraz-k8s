{
  description = "A very basic flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs = { self, nixpkgs }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; config.allowAliases = false; };
    inherit (pkgs) lib;
  in {
    devShells.${system}.default = pkgs.mkShellNoCC {
      buildInputs = with pkgs; [
        # kubernetes
        kubernetes-helm
        kind
        cloud-provider-kind
        kubectl
        k9s

        # cilium (k8s networking)
        cilium-cli
        hubble

        # Pulumi (infra-as-code)
        (pulumi.withPackages (pu: [ pu.pulumi-python ]))
        (python3.withPackages (py: [ py.pip ]))

        # static analysis
        pyright
        ruff
      ];

      PULUMI_CONFIG_PASSPHRASE = "pyGraz-k8s-test";
      LD_LIBRARY_PATH = lib.makeLibraryPath [ pkgs.stdenv.cc.cc ];  # hack so the cygrpc wheel works
    };
  };
}
