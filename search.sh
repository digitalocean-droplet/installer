#!/bin/bash

# Search GitLab Patterns in Current Directory
# Usage: ./search_gitlab_patterns.sh [directory]

SEARCH_DIR="${1:-.}"  # Use provided directory or current directory
OUTPUT_FILE="gitlab_patterns_found_$(date +%Y%m%d_%H%M%S).txt"

echo "🔍 Searching for GitLab patterns in: $SEARCH_DIR"
echo "📊 Output will be saved to: $OUTPUT_FILE"
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
        "RUNNER_TOKEN"
        "CI_REGISTRY_USER"
        "CI_PROJECT_PATH"
        "CI_COMMIT_SHA"
    )
    
    local found_patterns=0
    
    for pattern in "${patterns[@]}"; do
        if grep -l "$pattern" "$file" 2>/dev/null >/dev/null; then
            if [ $found_patterns -eq 0 ]; then
                echo "🎯 Found GitLab patterns in: $context"
                echo "📄 File: $file"
                echo "📋 Content:"
                found_patterns=1
            fi
            echo "  🔍 Pattern: $pattern"
            grep -n -A2 -B2 --color=never "$pattern" "$file" 2>/dev/null | head -10
            echo "  ---"
        fi
    done
    
    if [ $found_patterns -eq 1 ]; then
        echo "========================================"
        echo
    fi
}

# Start output redirection
exec > >(tee "$OUTPUT_FILE")

echo "🚀 GitLab Pattern Search Started"
echo "================================="
echo "Search Directory: $SEARCH_DIR"
echo "Timestamp: $(date)"
echo

# Search through all files in the directory
echo "🔍 Scanning files for GitLab patterns..."
echo

find "$SEARCH_DIR" -type f \( \
    -name "*.json" -o \
    -name "*.yml" -o \
    -name "*.yaml" -o \
    -name "*.toml" -o \
    -name "*.env" -o \
    -name "*env*" -o \
    -name "*.conf" -o \
    -name "*.config" -o \
    -name "*.txt" -o \
    -name "*.log" -o \
    -name "*.sh" -o \
    -name "*.py" -o \
    -name "Dockerfile*" -o \
    -name "docker-compose*" \
\) 2>/dev/null | while read -r file; do
    # Skip binary files
    if file "$file" | grep -q "text\|empty"; then
        search_gitlab_patterns "$file" "$(basename "$file")"
    fi
done

echo
echo "🔍 Quick pattern search across all text files..."
echo "================================================"

# Quick search for common GitLab token patterns
echo "🎯 Searching for Personal Access Tokens (glpat-):"
grep -r "glpat-[a-zA-Z0-9_-]\{20,\}" "$SEARCH_DIR" 2>/dev/null | head -10

echo
echo "🎯 Searching for Deploy Tokens (gldt-):"
grep -r "gldt-[a-zA-Z0-9_-]\{20,\}" "$SEARCH_DIR" 2>/dev/null | head -10

echo
echo "🎯 Searching for CI Job Tokens:"
grep -r "CI_JOB_TOKEN" "$SEARCH_DIR" 2>/dev/null | head -10

echo
echo "🎯 Searching for Registry Passwords:"
grep -r "CI_REGISTRY_PASSWORD" "$SEARCH_DIR" 2>/dev/null | head -10

echo
echo "🎯 Searching for GitLab URLs:"
grep -r "gitlab\.tigerbkk\.com\|docker-registry\.tigerbkk\.com" "$SEARCH_DIR" 2>/dev/null | head -10

echo
echo "🎯 Searching for gitlab-ci-token:"
grep -r "gitlab-ci-token" "$SEARCH_DIR" 2>/dev/null | head -10

echo
echo "✅ Search completed!"
echo "📊 Results saved to: $OUTPUT_FILE"
