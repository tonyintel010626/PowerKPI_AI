---
name: caas
description: Intel Container as a Service (CAAS) - Container registry and orchestration platform
license: MIT
---

# Intel CAAS (Container as a Service)

Intel's enterprise container platform for building, storing, and deploying containerized applications.

## Important Notes

- **Docker Desktop is restricted** due to licensing - use **Podman** as the alternative
- All registries require Intel authentication (SSO/certificates)
- Use `--tls-verify=false` if encountering certificate issues with internal registries

## Image Registries

Intel provides multiple regional container registries:

| Registry | Region/Purpose |
|----------|----------------|
| `gar-registry.caas.intel.com` | Global Artifact Registry (recommended) |
| `amr-registry.caas.intel.com` | Americas |
| `amr-registry-pre.caas.intel.com` | Americas Pre-production |
| `amr-its-registry.caas.intel.com` | Americas ITS |
| `ger-registry-pre.caas.intel.com` | Germany Pre-production |
| `ger-is-registry.caas.intel.com` | Germany IS |
| `ccr-registry.caas.intel.com` | Cloud Container Registry |

## Common Podman Commands

### Authentication
```bash
# Login to registry
podman login gar-registry.caas.intel.com

# Login with explicit credentials
podman login gar-registry.caas.intel.com -u <username> -p <password>
```

### Building Images
```bash
# Build image with tag
podman build -t gar-registry.caas.intel.com/<namespace>/<image>:<tag> -f Containerfile .

# Build with no cache
podman build --no-cache -t gar-registry.caas.intel.com/<namespace>/<image>:<tag> .
```

### Pushing Images
```bash
# Push to registry
podman push gar-registry.caas.intel.com/<namespace>/<image>:<tag>

# Push with TLS verification disabled (if certificate issues)
podman push --tls-verify=false gar-registry.caas.intel.com/<namespace>/<image>:<tag>
```

### Pulling Images
```bash
# Pull from registry
podman pull gar-registry.caas.intel.com/<namespace>/<image>:<tag>

# Pull with TLS verification disabled
podman pull --tls-verify=false gar-registry.caas.intel.com/<namespace>/<image>:<tag>
```

### Running Containers
```bash
# Run container with port mapping
podman run -d --name <container-name> -p <host-port>:<container-port> gar-registry.caas.intel.com/<namespace>/<image>:<tag>

# Run with volume mount
podman run -d --name <container-name> -v <host-path>:<container-path>:Z gar-registry.caas.intel.com/<namespace>/<image>:<tag>

# Run with environment variables
podman run -d -e VAR_NAME=value gar-registry.caas.intel.com/<namespace>/<image>:<tag>
```

### Container Management
```bash
# List running containers
podman ps

# List all containers (including stopped)
podman ps -a

# Stop container
podman stop <container-name>

# Remove container
podman rm <container-name>

# View logs
podman logs <container-name>
podman logs -f <container-name>  # Follow logs

# Execute command in running container
podman exec -it <container-name> /bin/bash
```

### Image Management
```bash
# List local images
podman images

# Remove image
podman rmi gar-registry.caas.intel.com/<namespace>/<image>:<tag>

# Inspect image
podman inspect gar-registry.caas.intel.com/<namespace>/<image>:<tag>
```

## Containerfile Best Practices

```dockerfile
# Use specific base image tags, not 'latest'
FROM node:20-alpine

# Add labels for metadata
LABEL maintainer="Team Name"
LABEL description="Application description"
LABEL org.opencontainers.image.source="https://github.com/..."

# Install dependencies in single layer
RUN apk add --no-cache \
    bash \
    curl \
    ca-certificates

# Set working directory
WORKDIR /app

# Copy dependency files first (better caching)
COPY package*.json ./
RUN npm install

# Copy application code
COPY . .

# Use non-root user when possible
RUN adduser -D appuser
USER appuser

# Expose ports
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Use exec form for ENTRYPOINT
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["--default-args"]
```

## Troubleshooting

### Certificate/TLS Issues
```bash
# Use --tls-verify=false for internal registries
podman pull --tls-verify=false gar-registry.caas.intel.com/<namespace>/<image>

# Or configure in registries.conf
# /etc/containers/registries.conf.d/caas.conf
[[registry]]
location = "gar-registry.caas.intel.com"
insecure = true
```

### Permission Issues (SELinux)
```bash
# Use :Z flag for volume mounts on SELinux systems
podman run -v /host/path:/container/path:Z <image>
```

### Port Conflicts
```bash
# Check what's using a port
netstat -tlnp | grep <port>
# or on Windows
netstat -ano | findstr <port>
```

