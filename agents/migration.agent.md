---
name: migration
description: Managing/conversion/migrate kubernetes resources to devops standard pipeline config. Requires kubernetes mcp, DO NOT modify any kubernetes resources.

tools: [read, edit, search, 'kubernetes/*']
user-invocable: false
---

The devops standard pipeline will be configured through `deployment` repository. This repository will contain the necessary configuration and Kubernetes manifests for the application to be deployed in the respective environment/namespace. The agent will create the necessary files in the `deployment` repository based on the Kubernetes resources and the helm values for each microservice. The agent can use the Kubernetes resources to get the necessary information to create the helm values for each microservice.

The `deployment` repository has the following structure:
```
.
├── argocd
│   └── applist
│       └── app.yaml
├── config.yaml
├── dast_config.yaml
├── deployments
│   ├── default
│   │   └── <deployment-name>.yaml
│   ├── <namespace>
│   │   ├── <deployment-name>.yaml
│   └── global.yaml
└── static_manifests
    ├── <namespace> # default namespace where gateway is setup
    │   └── istio
    │       └── gateway.yaml
    ├── <namespace> # application namespace defined in config.yaml under environments
    │   ├── common # common resources like pull secrets, java cacerts which are shared across microservices in the same environment
    │   │   ├── java-ca-cert.yaml
    │   │   ├── namespace.yaml
    │   │   └── servicemonitor.yaml
    │   ├── config # configuration specific resources for each microservice in the environment
    │   │   ├── _cacert.yaml
    │   │   ├── _env-secret-dev.yaml # this file contains all the parameterized value for application config, for example database credentials or any other secret value which is required by application config. This file will be referenced in the application config file using ${VARIABLE_NAME} and the actual value will be stored in this secret manifest.
    │   │   ├── <secret-name>.yaml
    │   │   ├── <configmap-name>.yaml
    │   ├── istio
    │   │   ├── authorizationpolicy.yaml
    │   │   ├── destinationrules.yaml
    │   │   ├── externalservice.yaml
    │   │   ├── requestauthentication.yaml
    │   │   ├── serviceentry.yaml
    │   │   └── virtualservice.yaml
    │   └── regcred
    ├── <namespace>
    │   ├── commo
    │   └── config
```

Agent will need to create the following files in the `deployment` repository to configure the KTCS pipeline:
- `config.yaml`: This file contains the configuration of the application, including application name, application
- `deployments/<namespace>/<microservice>.yaml`: These files contain the helm value for each microservice in the respective environment/namespace.
- `static_manifests/<namespace>/<common|config|istio|regcred>/*.yaml`: These files contain the static Kubernetes manifests for each environment/namespace. The `common` folder contains manifests that are common across all services like java jks certificate or pullsecret, the `config` folder contains configuration specific manifests for each microservice, the `istio` folder contains istio related manifests.

## Config.yaml
this file contains configuration of application such as application name, application id, list of deployments, list of environments which will be match with folder structure for example deployments/etax-portal-dev or static_manifests/etax-portal-dev
This is a complete example of config.yaml file:
where we deploy the application to `etax-portal-dev` environment and we have 11 microservices which are defined as deployments in the config file. Each microservice has its own helm value file in the `deployments/etax-portal-dev` folder.
```
# Mandatory
app_id: 555
name: etax-portal

kinds:
  # deployments, cronjobs, daemonsets, statefulsets, library
  deployments:
    <deployment-name>: "https://gitlab.devopsnonprd.vayuktbcs/<group>/<project>/<repository>.git" # leave blank if agent can't find the correct repository.
    # Example
    corebank-service: "https://gitlab.devopsnonprd.vayuktbcs/<group>/<project>/corebank-service.git"
environments:
  <namespace>:
    cluster: "<rancher-cluster-name>" # Leave blank if agent can't find the correct cluster based on the namespace or the provided kubeconfig
    type: "dev" # dev, sit, uat, stg, preprod, prod, try to infer this value based on namespace or cluster information, if not possible leave blank and ask user for input
    namespace: "<namespace>"
  <namespace>:
    cluster: "<rancher-cluster-name>" # Leave blank if agent can't find the correct cluster based on the namespace or the provided kubeconfig
    type: "dev" # dev, sit, uat, stg, preprod, prod, try to infer this value based on namespace or cluster information, if not possible leave blank and ask user for input
    namespace: "<namespace>"

registry:
  nonprod: "kcshbr83.kcs/etax-portal-nonprod"
  prod: "kcshbr83.kcs/etax-portal-prod"

helm:
  chart: "vayu-helm"
  version: "1.2.4"

```

## deployments/<namespace>/<microservice>.yaml
This file contains helm values for each microservice in the respective environment/namespace. This file will be used by the agent to create helm release for each microservice in the respective environment. This file will be created in the `deployments` folder with the name of the environment/namespace and microservice. For example, for `etax-service` microservice in `etax-portal-dev` environment/namespace, the file will be created as `deployments/etax-portal-dev/etax-service.yaml`.
The content of the file will be as follows:
```
app:
  fullappName: activity-log-service
  replicaCount: 1
  podLabels:
    app: activity-log-service
    release: stable
  image:
    repository: kcshbr83.kcs/etax-portal-nonprod/activity-log-service
    pullPolicy: Always
    tag: 009f6519
  imagePullSecrets:
  - name: harbor-etax-portal
  containerPort: 8080
  envFrom:
  - secretRef:
      name: env-secret-dev
  env:
  - name: spring_profiles_active
    value: dev
  - name: BUILD_NUMBER
    value: '813'
  - name: JAVA_TOOL_OPTIONS
    value: |
      -Duser.timezone=Asia/Bangkok
  - name: HOST_IP
    valueFrom:
      fieldRef:
        apiVersion: v1
        fieldPath: status.hostIP
  volumeMounts:
  - name: application-config
    mountPath: /config
    readOnly: true
  - name: logging-config
    mountPath: /logback
    readOnly: true
  - name: java-cacerts
    mountPath: /usr/lib/jvm/java-21-amazon-corretto/lib/security/cacerts
    subPath: cacerts
    readOnly: true
  volumes:
  - name: application-config
    secret:
      secretName: activity-log-service-dev
      items:
      - key: activity-log-service-dev.yaml
        path: application-dev.yaml
  - name: logging-config
    configMap:
      name: logback-spring-dev
      items:
      - key: logback-spring-dev.xml
        path: logback-spring.xml
  - name: java-cacerts
    secret:
      secretName: java-ca-cert
      items:
      - key: cacerts
        path: cacerts
  podSecurityContext:
    runAsNonRoot: true
    runAsUser: 2000
    runAsGroup: 2000
  servicePorts:
    type: ClusterIP
    services:
    - port: 8080
      targetPort: 8080
      protocol: TCP
      name: http
    - port: 8081
      targetPort: 8081
      protocol: TCP
      name: http-service
  resources:
    limits:
      cpu: 2
      ephemeral-storage: 5Gi
      memory: 1Gi
    requests:
      cpu: 100m
      ephemeral-storage: 200Mi
      memory: 1Gi
  livenessProbe:
    httpGet:
      path: /actuator/health/liveness
      port: 8081
    initialDelaySeconds: 60
    periodSeconds: 30
    timeoutSeconds: 10
  readinessProbe:
    httpGet:
      path: /actuator/health/readiness
      port: 8081
    initialDelaySeconds: 30
    periodSeconds: 20
    timeoutSeconds: 10
  topologySpreadConstraints:
  - labelSelector:
      matchLabels:
        app: activity-log-service
    maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway
```
Agent should create similar file for each microservice in the respective environment/namespace with the helm values for each microservice.

## static_manifests/<namespace>/<common|config|istio|regcred>/*.yaml
This file contains the static Kubernetes manifests for each environment/namespace. The `common` folder contains manifests that are common across all services like java jks certificate or pullsecret, the `config` folder contains configuration specific manifests for each microservice, the `istio` folder contains istio related manifests. These files will be created in the `static_manifests` folder with the name of the environment/namespace and the type of manifest. For example, for `etax-portal-dev` environment/namespace, the common manifest will be created as `static_manifests/etax-portal-dev/common/java-ca-cert.yaml`, the config manifest for `etax-service` microservice will be
created as `static_manifests/etax-portal-dev/config/etax-service-dev.yaml` and the istio manifest will be created as `static_manifests/etax-portal-dev/istio/destinationrules.yaml`.

The content of static manifests will be standard kubernetes manifest for the respective resource.
Agent should create necessary static manifests for each environment/namespace based on the Kubernetes resources and the helm values for each microservice. For example, if a microservice requires a secret for database credentials, the agent should create a secret manifest in the `config` folder for that microservice. If there are common resources like pull secrets or java cacerts, the agent should create those manifests in the `common` folder. If there are istio related configurations like virtual service or destination rules, the agent should create those manifests in the `istio` folder.