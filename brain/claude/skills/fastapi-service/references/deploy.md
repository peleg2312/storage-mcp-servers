# Image and OpenShift
- Dockerfile: `python:3.13-slim`, `PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`, `pip install
  --no-cache-dir -r requirements.txt`, copy only the service files, `chgrp -R 0 /app && chmod -R g=u /app`,
  `USER 1001`, `EXPOSE 8000`. No secrets, no test files in the image.
- `openshift.yaml`: Deployment (`envFrom: secretRef`), readiness + liveness on `/healthz`,
  `securityContext: {allowPrivilegeEscalation: false, readOnlyRootFilesystem: true, runAsNonRoot: true,
  capabilities: {drop: [ALL]}}`, requests + memory limit, Service on 8000; header comments with the exact
  `oc create secret generic <name> --from-env-file=.env` and `oc apply` commands.
- Air-gapped delivery: build with podman on a connected machine, `podman save | gzip`, split into 45 MB
  parts under `images/` with `SHA256SUMS` (see `images/join.sh`), or an OpenShift `BuildConfig` from the
  repo (`openshift/buildconfigs.yaml`). Python dependencies on the VM come from bundled wheels, never pip.
- Version the image tag in the Deployment, the BuildConfig and the tarball name together.
