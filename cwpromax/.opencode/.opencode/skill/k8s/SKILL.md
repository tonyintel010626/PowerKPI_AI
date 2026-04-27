# Intel CAAS Kubernetes Deployment

Deploy applications to Intel CAAS (Container as a Service) Kubernetes clusters.

## Overview

This skill provides guidance for deploying applications to Intel's CAAS Kubernetes infrastructure, including ingress configuration for `*.intel.com` domains, deployment management, and troubleshooting common issues.

## Prerequisites

- Access to Intel CAAS Kubernetes cluster
- `kubectl` CLI installed and configured
- Namespace access (e.g., `fvpm`)
- VPN connection to Intel network
- DNS records already created (see `skill_dns`)

## Usage

### Basic Commands

```bash
# Check cluster connection
kubectl cluster-info

# List namespaces you have access to
kubectl get namespaces

# Set default namespace (optional)
kubectl config set-context --current --namespace=fvpm
```

## Ingress Configuration

### Creating Ingress for Intel Domains

```yaml
# Example: k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ocode-marketplace-ingress
  namespace: fvpm
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
  - host: ocode.intel.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ocode-marketplace-svc
            port:
              number: 80
  - host: omnicode.intel.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ocode-marketplace-svc
            port:
              number: 80
```

### Apply Ingress Configuration

```bash
# Apply ingress manifest
kubectl apply -f k8s/ingress.yaml -n fvpm

# Verify ingress created
kubectl get ingress -n fvpm

# Describe ingress for details
kubectl describe ingress ocode-marketplace-ingress -n fvpm
```

## Deployment Management

### Apply Deployment Manifests

```bash
# Apply all manifests in directory
kubectl apply -f k8s/ -n fvpm

# Apply specific manifest
kubectl apply -f k8s/deployment.yaml -n fvpm
```

### Restart Deployment (Rolling Restart)

```bash
# Restart deployment to pull new image
kubectl rollout restart deployment/ocode-marketplace -n fvpm

# Check rollout status
kubectl rollout status deployment/ocode-marketplace -n fvpm

# View rollout history
kubectl rollout history deployment/ocode-marketplace -n fvpm
```

### Check Deployment Status

```bash
# Get pods
kubectl get pods -n fvpm

# Get deployment status
kubectl get deployment ocode-marketplace -n fvpm

# Describe deployment
kubectl describe deployment ocode-marketplace -n fvpm
```

## ConfigMap and Secret Management

### ConfigMap

```bash
# Create configmap from file
kubectl create configmap app-config --from-file=config.json -n fvpm

# Apply configmap manifest
kubectl apply -f k8s/configmap.yaml -n fvpm

# View configmap
kubectl get configmap app-config -n fvpm -o yaml
```

### Secret

```bash
# Create secret from literal
kubectl create secret generic app-secret --from-literal=password=abc123 -n fvpm

# Apply secret manifest
kubectl apply -f k8s/secret.yaml -n fvpm

# View secret (base64 encoded)
kubectl get secret app-secret -n fvpm -o yaml
```

## Service Management

### Check Services

```bash
# List services
kubectl get svc -n fvpm

# Describe service
kubectl describe svc ocode-marketplace-svc -n fvpm

# Get service endpoints
kubectl get endpoints ocode-marketplace-svc -n fvpm
```

## Logs and Debugging

### View Pod Logs

```bash
# Get pod name
kubectl get pods -n fvpm

# View logs
kubectl logs <pod-name> -n fvpm

# Follow logs (live)
kubectl logs -f <pod-name> -n fvpm

# Previous pod logs (if crashed)
kubectl logs <pod-name> -n fvpm --previous
```

### Execute Commands in Pod

```bash
# Shell into pod
kubectl exec -it <pod-name> -n fvpm -- /bin/bash

# Run single command
kubectl exec <pod-name> -n fvpm -- ls -la /app
```

### Port Forwarding for Local Testing

```bash
# Forward pod port to localhost
kubectl port-forward <pod-name> 8080:80 -n fvpm

# Forward service port to localhost
kubectl port-forward svc/ocode-marketplace-svc 8080:80 -n fvpm

# Access at http://localhost:8080
```

## Troubleshooting

### Issue: Ingress not routing traffic

**Symptoms:**
- DNS resolves correctly
- 404 or connection refused when accessing domain

**Solutions:**
```bash
# 1. Check ingress exists
kubectl get ingress -n fvpm

# 2. Verify ingress configuration
kubectl describe ingress ocode-marketplace-ingress -n fvpm

# 3. Check service is running
kubectl get svc ocode-marketplace-svc -n fvpm

# 4. Verify pods are running
kubectl get pods -n fvpm

# 5. Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

### Issue: Pod not starting (CrashLoopBackOff)

**Symptoms:**
```
NAME                    READY   STATUS             RESTARTS   AGE
ocode-marketplace-xxx   0/1     CrashLoopBackOff   5          3m
```

**Solutions:**
```bash
# 1. Check pod logs
kubectl logs <pod-name> -n fvpm

# 2. Check previous logs (if restarting)
kubectl logs <pod-name> -n fvpm --previous

# 3. Describe pod for events
kubectl describe pod <pod-name> -n fvpm

# 4. Check resource limits
kubectl get pod <pod-name> -n fvpm -o yaml | grep -A 5 resources
```

### Issue: ImagePullBackOff

**Symptoms:**
```
NAME                    READY   STATUS             RESTARTS   AGE
ocode-marketplace-xxx   0/1     ImagePullBackOff   0          1m
```

**Solutions:**
```bash
# 1. Check image name in deployment
kubectl get deployment ocode-marketplace -n fvpm -o yaml | grep image:

# 2. Verify image exists in registry
# Use skill_caas to check GAR registry

# 3. Check imagePullSecrets (if using private registry)
kubectl get secret -n fvpm | grep regcred

# 4. Describe pod for detailed error
kubectl describe pod <pod-name> -n fvpm
```

### Issue: Service not reaching pods

**Symptoms:**
- Service exists but returns 503 or connection errors

**Solutions:**
```bash
# 1. Check if pods are ready
kubectl get pods -n fvpm -l app=ocode-marketplace

# 2. Verify service selector matches pod labels
kubectl get svc ocode-marketplace-svc -n fvpm -o yaml | grep selector:
kubectl get pods -n fvpm -o yaml | grep -A 2 labels:

# 3. Check service endpoints
kubectl get endpoints ocode-marketplace-svc -n fvpm

# 4. If no endpoints, selector mismatch or pods not ready
```

## Common Missteps to Avoid

### 1. ⚠️ Missing Namespace Flag

**Problem**: Commands fail or operate on wrong namespace

```bash
# ❌ Wrong (uses default namespace)
kubectl apply -f k8s/deployment.yaml

# ✅ Correct (specifies namespace)
kubectl apply -f k8s/deployment.yaml -n fvpm
```

**Solution**: Always specify `-n <namespace>` or set default namespace

### 2. ⚠️ Not Updating Ingress for New Hostnames

**Problem**: Added DNS for new domain but forgot to update ingress

**Example**: Created DNS for `omnicode.intel.com` but ingress only has `ocode.intel.com`

```yaml
# ❌ Wrong (missing omnicode.intel.com)
spec:
  rules:
  - host: ocode.intel.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ocode-marketplace-svc
            port:
              number: 80

# ✅ Correct (includes both domains)
spec:
  rules:
  - host: ocode.intel.com
    http:
      paths: [...]
  - host: omnicode.intel.com
    http:
      paths: [...]
```

### 3. ⚠️ Testing Before DNS Propagates

**Problem**: Ingress configured but DNS not yet propagated

**Solution**: 
1. Create DNS first (see `skill_dns`)
2. Wait 5-15 minutes for propagation
3. Verify DNS: `nslookup ocode.intel.com`
4. Then test ingress

### 4. ⚠️ Forgetting to Restart Deployment After Image Push

**Problem**: Pushed new container image but pods still running old version

```bash
# After pushing new image to GAR, restart deployment
kubectl rollout restart deployment/ocode-marketplace -n fvpm
```

### 5. ⚠️ Service Selector Mismatch

**Problem**: Service not routing to pods due to label mismatch

```yaml
# Deployment labels
metadata:
  labels:
    app: ocode-marketplace
    
# Service selector must match
selector:
  app: ocode-marketplace
```

## Examples

### Example 1: Deploy New Application

```bash
# Step 1: Ensure DNS is created (skill_dns)
nslookup ocode.intel.com

# Step 2: Apply all manifests
kubectl apply -f k8s/ -n fvpm

# Step 3: Verify deployment
kubectl get pods -n fvpm
kubectl get svc -n fvpm
kubectl get ingress -n fvpm

# Step 4: Check logs
kubectl logs -l app=ocode-marketplace -n fvpm

# Step 5: Test application
curl -I http://ocode.intel.com
```

### Example 2: Update Application with New Image

```bash
# Step 1: Build and push new image (skill_caas)
podman build -t gar-registry.caas.intel.com/fvpm/ocode-marketplace:v2 .
podman push gar-registry.caas.intel.com/fvpm/ocode-marketplace:v2

# Step 2: Update deployment image tag
kubectl set image deployment/ocode-marketplace \
  ocode-marketplace=gar-registry.caas.intel.com/fvpm/ocode-marketplace:v2 \
  -n fvpm

# OR: Restart deployment if using :latest tag
kubectl rollout restart deployment/ocode-marketplace -n fvpm

# Step 3: Monitor rollout
kubectl rollout status deployment/ocode-marketplace -n fvpm

# Step 4: Verify new pods
kubectl get pods -n fvpm
```

### Example 3: Add New Domain to Existing Ingress

```bash
# Step 1: Create DNS for new domain (skill_dns)
# Create CNAME: omnicode.intel.com → apps1-fm-int.icloud.intel.com.

# Step 2: Edit ingress manifest (k8s/ingress.yaml)
# Add new host rule for omnicode.intel.com

# Step 3: Apply updated ingress
kubectl apply -f k8s/ingress.yaml -n fvpm

# Step 4: Verify ingress updated
kubectl get ingress ocode-marketplace-ingress -n fvpm -o yaml

# Step 5: Test new domain (after DNS propagates)
curl -I http://omnicode.intel.com
```

### Example 4: Debug Application Not Accessible

```bash
# Step 1: Check DNS
nslookup ocode.intel.com

# Step 2: Check ingress
kubectl get ingress -n fvpm
kubectl describe ingress ocode-marketplace-ingress -n fvpm

# Step 3: Check service
kubectl get svc ocode-marketplace-svc -n fvpm
kubectl get endpoints ocode-marketplace-svc -n fvpm

# Step 4: Check pods
kubectl get pods -n fvpm -l app=ocode-marketplace

# Step 5: Check pod logs
kubectl logs -l app=ocode-marketplace -n fvpm

# Step 6: Port-forward to test directly
kubectl port-forward svc/ocode-marketplace-svc 8080:80 -n fvpm
# Test at http://localhost:8080
```

## Related Skills

- `skill_dns` - Create DNS records before configuring ingress
- `skill_caas` - Build and push container images to GAR registry
- `skill_github` - Manage k8s manifests in git repositories

## Intel-Specific Notes

- Default namespace pattern: `<team-name>` (e.g., `fvpm`)
- Ingress class: `nginx` (Intel CAAS uses nginx ingress controller)
- Load balancer: `apps1-fm-int.icloud.intel.com` (10.64.22.120)
- Container registry: `gar-registry.caas.intel.com`
- Always use VPN when accessing CAAS clusters
- Contact CAAS support for namespace provisioning and access issues

## Best Practices

1. **Always specify namespace** in kubectl commands
2. **Use labels consistently** for services, deployments, and pods
3. **Set resource limits** to prevent resource exhaustion
4. **Use readiness/liveness probes** for better health checks
5. **Version your images** (avoid `:latest` in production)
6. **Keep manifests in git** for version control and rollback capability
7. **Test DNS before configuring ingress**
8. **Monitor rollout status** after deployments
