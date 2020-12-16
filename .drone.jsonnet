
// local restore_cache = {
//   name: "restore-cache-with-filesystem",
//   image: "meltwater/drone-cache:dev",
//   pull: true,
//   settings: {
//     backend: "filesystem",
//     debug: true,
//     restore: true,
//     cache_key: "volume",
//     archive_format: "gzip",
//     # filesystem_cache_root: "/tmp/cache"
//     mount: [ 'vendor' ],
//   },
//   volumes: [
//     {
//       name: "cache",
//       path: "/tmp/cache"
//     },
//   ]
// };

// local rebuild_cache = {
//   name: "rebuild-cache-with-filesystem",
//   image: "meltwater/drone-cache:dev",
//   pull: true,
//   settings: {
//     debug: true,
//     backend: "filesystem",
//     rebuild: true,
//     cache_key: "volume",
//     archive_format: "gzip",
//     # filesystem_cache_root: "/tmp/cache"
//     mount: [ 'vendor' ],
//   },
//   volumes: [
//     {
//       name: "cache",
//       path: "/tmp/cache"
//     },
//   ]
// };

local components = [
  {
    name: 'cluster-droid',
    args: [
      'HELM_VERSION=3.4.2',
      'KUBECTL_VERSION=1.18.10',
      'VAULT_VERSION=1.6.1'
    ]
  },
  { name: 'vault-droid' },
  // { name: 'vault-agent' }
  { name: 'zipalign' }
];

local Pipeline(component) = {
  kind: "pipeline",
  type: "kubernetes",
  name: component.name,
  platform: {
    os: "linux",
    arch: "arm64"
  },
  trigger: {
    paths: [
      component.name + "/*"
    ]
  },
  [if std.objectHas(component, 'depends_on') then 'depends_on']: component.depends_on,
  steps: [
    {
      name: "Prep version",
      image: "alpine",
      commands: [
        'printf "`cat ' + component.name + '/VERSION`,latest" > .tags'
      ],
    },
    {
      name: "build",
      image: "registry.192.168.178.48.nip.io/drone-kaniko",
      settings: {
        username: "tiago",
        password: "empty",
        repo: "registry-docker-registry.tools.svc.cluster.local:5000/" + component.name,
        registry: "registry-docker-registry.tools.svc.cluster.local:5000",
        context: "./" + component.name,
        dockerfile: "./" + component.name + "/Dockerfile",
        insecure: true,
        use_cache: true,
        mtu: 1440,
        [if std.objectHas(component, 'args') then 'build_args']: component.args,
      }
    }
  ],
  volumes: [
    {
      name: "cache",
      host: {
        path: "/var/cache"
      }
    },
    {
      name: "docker",
      host: {
        path: "/var/cache/${DRONE_REPO}/docker"
      }
    },
  ],
};

[ Pipeline(component) for component in components ]