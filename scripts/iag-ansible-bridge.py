#!/usr/bin/env python3
"""
IAG5 to Ansible Bridge Service
Executes PowerShell scripts on Windows machines using Ansible playbooks
"""

import json
import subprocess
import tempfile
import os
import uuid
import time
from datetime import datetime
from flask import Flask, request, jsonify
from pathlib import Path
import logging
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
ANSIBLE_PLAYBOOK_PATH = "/opt/iag5-powershell-service/ansible/playbooks/execute-powershell-script.yml"
DEFAULT_INVENTORY = "/opt/iag5-powershell-service/ansible/inventory/hosts.yml"
DEFAULT_GIT_REPO = "https://github.com/keepithuman/ansible-powershell-automation.git"
DEFAULT_SCRIPT_PATH = "scripts/Manage-WindowsSystem.ps1"

class AnsibleExecutor:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.playbook_path = self.base_path / "ansible" / "playbooks" / "execute-powershell-script.yml"
        self.inventory_path = self.base_path / "ansible" / "inventory" / "hosts.yml"
        
    def create_temp_inventory(self, targets):
        """Create temporary inventory file for target hosts"""
        inventory_data = {
            'windows': {
                'hosts': {}
            }
        }
        
        for target in targets:
            inventory_data['windows']['hosts'][target] = {
                'ansible_host': target,
                'ansible_connection': 'winrm',
                'ansible_winrm_transport': 'basic',
                'ansible_port': 5985
            }
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
        yaml.dump(inventory_data, temp_file, default_flow_style=False)
        temp_file.close()
        
        return temp_file.name
    
    def execute_playbook(self, targets, action, parameters=None, options=None):
        """Execute Ansible playbook with PowerShell script"""
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # Set default values
        parameters = parameters or {}
        options = options or {}
        
        # Create temporary inventory
        temp_inventory = self.create_temp_inventory(targets)
        
        try:
            # Build Ansible command
            cmd = [
                'ansible-playbook',
                str(self.playbook_path),
                '-i', temp_inventory,
                '--limit', ','.join(targets),
                '-e', f'ps_action={action}',
                '-e', f'execution_id={execution_id}',
                '-e', f'git_repo={options.get("gitRepo", DEFAULT_GIT_REPO)}',
                '-e', f'script_file={options.get("scriptPath", DEFAULT_SCRIPT_PATH)}',
                '-e', f'async_timeout={options.get("timeout", 300)}'
            ]
            
            # Add parameters as extra vars
            if parameters:
                cmd.extend(['-e', f'ps_parameters={json.dumps(parameters)}'])
                
            # Add output path if specified
            if parameters.get('outputPath'):
                cmd.extend(['-e', f'output_path={parameters["outputPath"]}'])
            
            # Add cleanup option
            cmd.extend(['-e', f'cleanup_temp={options.get("cleanup", False)}'])
            
            # Execute Ansible playbook
            logger.info(f"Executing command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=options.get('timeout', 300) + 60  # Add buffer time
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Parse Ansible output for results
            success = result.returncode == 0
            
            # Try to extract structured results from Ansible output
            host_results = self._parse_ansible_output(result.stdout, targets)
            
            response = {
                'success': success,
                'message': f'PowerShell script execution {"completed" if success else "failed"}',
                'executionId': execution_id,
                'results': host_results,
                'summary': {
                    'totalHosts': len(targets),
                    'successful': sum(1 for r in host_results if r['status'] == 'success'),
                    'failed': sum(1 for r in host_results if r['status'] == 'failed'),
                    'unreachable': sum(1 for r in host_results if r['status'] == 'unreachable'),
                    'totalDuration': duration
                },
                'ansible_stdout': result.stdout if not success else None,
                'ansible_stderr': result.stderr if result.stderr else None
            }
            
            return response
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': 'Execution timed out',
                'executionId': execution_id,
                'results': [],
                'summary': {
                    'totalHosts': len(targets),
                    'successful': 0,
                    'failed': 0,
                    'unreachable': len(targets),
                    'totalDuration': options.get('timeout', 300)
                }
            }
        except Exception as e:
            logger.error(f"Execution failed: {str(e)}")
            return {
                'success': False,
                'message': f'Execution failed: {str(e)}',
                'executionId': execution_id,
                'results': [],
                'summary': {
                    'totalHosts': len(targets),
                    'successful': 0,
                    'failed': len(targets),
                    'unreachable': 0,
                    'totalDuration': 0
                }
            }
        finally:
            # Cleanup temporary inventory
            try:
                os.unlink(temp_inventory)
            except:
                pass
    
    def _parse_ansible_output(self, output, targets):
        """Parse Ansible output to extract host results"""
        results = []
        
        # Simple parsing - in production, you might want more sophisticated parsing
        for target in targets:
            if f"ok: [{target}]" in output:
                status = "success"
            elif f"fatal: [{target}]" in output or f"failed: [{target}]" in output:
                status = "failed"
            elif f"unreachable: [{target}]" in output:
                status = "unreachable"
            else:
                status = "unknown"
            
            # Extract output for this host (simplified)
            host_output = ""
            lines = output.split('\n')
            capture_output = False
            for line in lines:
                if f"[{target}]" in line:
                    capture_output = True
                elif capture_output and any(f"[{other}]" in line for other in targets if other != target):
                    capture_output = False
                elif capture_output:
                    host_output += line + "\n"
            
            results.append({
                'host': target,
                'status': status,
                'output': host_output.strip(),
                'changed': "changed: [" + target + "]" in output,
                'duration': 0  # Would need more sophisticated parsing for actual duration
            })
        
        return results

# Initialize Ansible executor
ansible_executor = AnsibleExecutor()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check dependencies
        dependencies = {
            'ansible': subprocess.run(['ansible', '--version'], capture_output=True).returncode == 0,
            'python': True,  # Obviously true if we're running
            'git': subprocess.run(['git', '--version'], capture_output=True).returncode == 0
        }
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'dependencies': dependencies
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@app.route('/execute-script', methods=['POST'])
def execute_script():
    """Execute PowerShell script via Ansible"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('targets'):
            return jsonify({'error': 'targets field is required'}), 400
        if not data.get('action'):
            return jsonify({'error': 'action field is required'}), 400
        
        targets = data['targets']
        action = data['action']
        parameters = data.get('parameters', {})
        options = data.get('options', {})
        
        # Execute via Ansible
        result = ansible_executor.execute_playbook(targets, action, parameters, options)
        
        status_code = 200 if result['success'] else 500
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in execute_script: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'executionId': str(uuid.uuid4()),
            'results': [],
            'summary': {
                'totalHosts': 0,
                'successful': 0,
                'failed': 0,
                'unreachable': 0,
                'totalDuration': 0
            }
        }), 500

@app.route('/manage-services', methods=['POST'])
def manage_services():
    """Specialized endpoint for service management"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['targets', 'serviceName', 'action']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} field is required'}), 400
        
        # Transform to generic script execution
        parameters = {
            'serviceName': data['serviceName'],
            'serviceAction': data['action']
        }
        
        options = {
            'timeout': data.get('timeout', 120)
        }
        
        result = ansible_executor.execute_playbook(
            data['targets'], 
            'ServiceManagement', 
            parameters, 
            options
        )
        
        # Transform response for service management
        service_results = []
        for host_result in result['results']:
            service_results.append({
                'host': host_result['host'],
                'serviceName': data['serviceName'],
                'previousStatus': 'unknown',  # Would need to parse from output
                'currentStatus': 'unknown',   # Would need to parse from output
                'changed': host_result['changed'],
                'message': host_result['output']
            })
        
        return jsonify({
            'success': result['success'],
            'results': service_results
        })
        
    except Exception as e:
        logger.error(f"Error in manage_services: {str(e)}")
        return jsonify({
            'success': False,
            'results': []
        }), 500

@app.route('/system-info', methods=['POST'])
def get_system_info():
    """Specialized endpoint for system information collection"""
    try:
        data = request.get_json()
        
        if not data.get('targets'):
            return jsonify({'error': 'targets field is required'}), 400
        
        parameters = {
            'outputPath': data.get('outputPath', 'C:\\temp\\ps-output')
        }
        
        result = ansible_executor.execute_playbook(
            data['targets'],
            'SystemInfo',
            parameters
        )
        
        # Transform response for system info
        system_results = []
        for host_result in result['results']:
            system_results.append({
                'host': host_result['host'],
                'systemInfo': {
                    'computerName': host_result['host'],
                    'os': 'Windows',  # Would need to parse from output
                    'osVersion': 'unknown',
                    'totalMemoryGB': 0,
                    'processor': 'unknown',
                    'lastBootTime': 'unknown'
                },
                'diskInfo': [],  # Would need to parse from output
                'reportPath': parameters['outputPath']
            })
        
        return jsonify({
            'success': result['success'],
            'results': system_results
        })
        
    except Exception as e:
        logger.error(f"Error in get_system_info: {str(e)}")
        return jsonify({
            'success': False,
            'results': []
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)