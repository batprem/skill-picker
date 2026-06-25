---
name: Kubernetes Debugger
description: Diagnose failing pods, crashloops, and networking issues in a Kubernetes cluster.
---

# Kubernetes Debugger

Use this skill to triage workloads that won't start, keep restarting, or can't be reached.

## Triage order

1. **State**: `kubectl get pods -o wide` — look for `CrashLoopBackOff`,
   `ImagePullBackOff`, `Pending`, or `OOMKilled`.
2. **Events**: `kubectl describe pod <pod>` — the Events section explains scheduling
   failures, failed mounts, failed probes, and image-pull errors.
3. **Logs**: `kubectl logs <pod> [-c <container>]`; add `--previous` to read the logs
   of the crashed instance in a crashloop.
4. **Exec** (if it stays up long enough): `kubectl exec -it <pod> -- sh` to inspect
   config, env, and DNS.

## Common causes

- **CrashLoopBackOff**: bad command/entrypoint, missing config/secret, or a failing
  liveness probe killing a healthy-but-slow container (raise `initialDelaySeconds`).
- **ImagePullBackOff**: wrong tag, private registry without `imagePullSecrets`.
- **Pending**: insufficient CPU/memory, unschedulable taints, or unbound PVCs.
- **Networking**: verify the `Service` selector matches pod labels; test in-cluster
  with `kubectl run tmp --rm -it --image=busybox -- wget -qO- <svc>:<port>`.
