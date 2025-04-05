{
  description = "A very basic flake";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs = { self, nixpkgs }: {
    devShells."x86_64-linux".default = let
      pkgs = import nixpkgs { system = "x86_64-linux"; config.allowAliases = false; };
      inherit (pkgs) lib;
    in pkgs.mkShellNoCC {
      buildInputs = with pkgs; [
        kind
        kubectl
        (pulumi.withPackages (pu: [ pu.pulumi-python ]))
        (python3.withPackages (py: [ py.pip ]))
      ];

      PULUMI_CONFIG_PASSPHRASE = "pyGraz-k8s-test";
      LD_LIBRARY_PATH = lib.makeLibraryPath [ pkgs.stdenv.cc.cc ];  # hack so the cygrpc wheel works
    };
  };
}
