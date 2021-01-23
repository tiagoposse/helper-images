
local kaniko_cmd (component) = [
  "/kaniko/executor",
  "--dockerfile=./" + component.name + "/Dockerfile --context=" + component.name,
  " --cache=true --cache-repo=registry.tiagoposse.com/" + component.name,
  " --destination=registry.tiagoposse.com/" + component.name,
  if std.objectHas(component, 'args') then " --build-arg=" + std.join(" --build-arg=", component.args) else ""
];

local components = [
  {
    name: 'cluster-droid',
    args: [
      'HELM_VERSION=3.4.2',
      'KUBECTL_VERSION=1.18.10',
      'VAULT_VERSION=1.6.1'
    ]
  },
  { name: 'vault-agent' },
  { name: 'zipalign' },
  { name: 'kaniko-arm' }
];

local Pipeline(component) = {
  kind: "pipeline",
  type: "kubernetes",
  name: component.name,
  platform: {
    os: "linux",
    arch: "arm"
  },
  trigger: {
    paths: [
      component.name + "/*"
    ]
  },
  [if std.objectHas(component, 'depends_on') then 'depends_on']: component.depends_on,
  steps: [
    {
      name: "build",
      image: "registry.tiagoposse.com/kaniko-arm:1.2.0",
      commands: [
        'printf "`cat ' + component.name + '/VERSION`,latest" > .tags',
        std.join(" ", kaniko_cmd(component))
      ],
    }
  ],
};

[ Pipeline(component) for component in components ]