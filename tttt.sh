#!/bin/bash

echo "🚀 Manual GitLab Credential Extraction"
echo "=" $(printf '%.0s=' {1..80})

echo
echo "🐳 Step 1: Finding GitLab-connected containers..."
GITLAB_CONTAINERS=$(docker ps --format "{{.ID}}\t{{.Image}}\t{{.Names}}" | grep -E "(docker-registry\.tigerbkk\.com|gitlab\.tigerbkk\.com)")

if [ -z "$GITLAB_CONTAINERS" ]; then
    echo "❌ No GitLab-connected containers found"
else
    echo "✅ Found GitLab-connected containers:"
    echo "$GITLAB_CONTAINERS"
fi

echo
echo "🔐 Step 2: Checking Docker registry authentication..."
DOCKER_CONFIG="/root/.docker/config.json"
if [ -f "$DOCKER_CONFIG" ]; then
    echo "📄 Found Docker config at: $DOCKER_CONFIG"
    echo "🔍 Checking for GitLab registry auth..."
    
    # Check if GitLab registry is in the config
    if grep -q "docker-registry.tigerbkk.com" "$DOCKER_CONFIG" 2>/dev/null; then
        echo "🎯 Found docker-registry.tigerbkk.com in Docker config!"
        echo "📋 Registry authentication:"
        cat "$DOCKER_CONFIG" | python3 -c "
import sys, json, base64
try:
    config = json.load(sys.stdin)
    auths = config.get('auths', {})
    for registry, auth_info in auths.items():
        if 'docker-registry.tigerbkk.com' in registry or 'gitlab.tigerbkk.com' in registry:
            print(f'Registry: {registry}')
            if 'auth' in auth_info:
                try:
                    decoded = base64.b64decode(auth_info['auth']).decode('utf-8')
                    username, password = decoded.split(':', 1)
                    print(f'Username: {username}')
                    print(f'Password/Token: {password}')
                    print('---')
                except:
                    print('Could not decode auth')
except:
    pass
"
    else
        echo "ℹ️ No GitLab registry found in Docker config"
    fi
else
    echo "❌ No Docker config found at $DOCKER_CONFIG"
fi

echo
echo "🔍 Step 3: Extracting environment variables from GitLab containers..."
echo "$GITLAB_CONTAINERS" | while IFS=$'\t' read -r CONTAINER_ID IMAGE NAME; do
    if [ -n "$CONTAINER_ID" ]; then
        echo
        echo "📦 Analyzing container: $NAME ($CONTAINER_ID)"
        echo "Image: $IMAGE"
        
        echo "🔑 Environment variables:"
        docker exec "$CONTAINER_ID" env 2>/dev/null | grep -iE "(CI_|GITLAB|GIT_|RUNNER|TOKEN|REGISTRY)" | head -20
        
        echo
        echo "📄 Looking for GitLab config files in container..."
        docker exec "$CONTAINER_ID" find / -name "*.toml" -o -name ".gitlab-ci.yml" -o -name "gitlab.yml" 2>/dev/null | head -10
        
        echo
        echo "📋 Recent container logs (looking for tokens):"
        docker logs --tail=50 "$CONTAINER_ID" 2>&1 | grep -iE "(token|gitlab|ci_)" | head -10
    fi
done

echo
echo "🖥️ Step 4: Checking host system for GitLab files..."
echo "🔍 Looking for GitLab Runner installations..."
find /etc /opt /var /home -name "*gitlab*" -type f 2>/dev/null | grep -v proc | head -10

echo
echo "🔍 Looking for GitLab configuration files..."
find / -name "config.toml" -o -name ".gitlab-ci.yml" 2>/dev/null | grep -v proc | head -10

echo
echo "🏃 Step 5: Checking for GitLab Runner processes..."
ps aux | grep -i gitlab

echo
echo "⚙️ Step 6: Checking systemd services..."
systemctl list-units --type=service --state=running | grep -iE "(gitlab|runner|ci)"

echo
echo "🔐 Step 7: Manual Docker login test..."
echo "If you found credentials above, test them with:"
echo "docker login docker-registry.tigerbkk.com -u <username> -p <password>"
echo
echo "🌐 Step 8: GitLab API test..."
echo "If you found tokens above, test them with:"
echo "curl -H 'PRIVATE-TOKEN: <token>' https://gitlab.tigerbkk.com/api/v4/user"

echo
echo "✅ Manual extraction completed!"
echo "Check the output above for any discovered credentials."
