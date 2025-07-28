# IAG5 Ansible PowerShell Service

An Itential Automation Gateway (IAG5) service that executes PowerShell scripts on Windows machines using Ansible playbooks. This service bridges IAG5 REST API calls to Ansible automation, enabling seamless Windows system management from Itential workflows.

## Architecture

```
IAG5 Service → Python Bridge → Ansible Playbook → PowerShell Script (from Git)
     ↓              ↓               ↓                     ↓
REST Endpoints   Flask App      win_powershell      Remote Execution
```

## Features

- **IAG5 Integration**: Native IAG5 service definition with proper schemas
- **Ansible Orchestration**: Uses Ansible for reliable multi-host execution
- **Git Integration**: Dynamically downloads PowerShell scripts from Git repositories
- **Flexible Parameters**: Support for all PowerShell script parameters
- **Error Handling**: Comprehensive error handling and reporting
- **Health Monitoring**: Built-in health check endpoints
- **Docker Support**: Ready-to-deploy Docker containers

## Repository Structure

```
iag5-ansible-powershell-service/
├── iag5/
│   ├── service.json              # IAG5 service definition
│   └── methods/                  # Service method definitions
│       ├── executeWindowsScript.json
│       ├── manageServices.json
│       ├── getSystemInfo.json
│       └── healthCheck.json
├── ansible/
│   ├── playbooks/
│   │   └── execute-powershell-script.yml
│   ├── inventory/
│   │   └── hosts.yml
│   ├── group_vars/
│   │   └── windows.yml
│   └── ansible.cfg
├── scripts/
│   └── iag-ansible-bridge.py    # Python Flask service
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/
│   └── setup-guide.md
└── examples/
    └── service-calls.json
```

## Quick Start

### 1. Prerequisites

- Python 3.8+
- Ansible 4.0+
- Git
- Access to Windows machines with WinRM enabled
- IAG5 environment

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/keepithuman/iag5-ansible-powershell-service.git
cd iag5-ansible-powershell-service

# Install Python dependencies
pip install -r requirements.txt

# Configure Ansible inventory
cp ansible/inventory/hosts.yml.example ansible/inventory/hosts.yml
# Edit hosts.yml with your Windows machines
```

### 3. Configuration

**Update Ansible Inventory** (`ansible/inventory/hosts.yml`):
```yaml
windows:
  hosts:
    your-windows-server:
      ansible_host: 192.168.1.100
      ansible_user: Administrator
      ansible_password: YourPassword
```

**Configure IAG5 Service**:
1. Import `iag5/service.json` into your IAG5 instance
2. Import method definitions from `iag5/methods/`
3. Configure authentication and connection settings

### 4. Running the Service

**Using Python directly:**
```bash
python scripts/iag-ansible-bridge.py
```

**Using Docker:**
```bash
docker-compose -f docker/docker-compose.yml up -d
```

The service will be available at `http://localhost:3000`

## Service Methods

### executeWindowsScript

Execute any PowerShell script action on target Windows machines.

**Example Request:**
```json
{
  "targets": ["windows-server-01", "windows-server-02"],
  "action": "SystemInfo",
  "parameters": {
    "outputPath": "C:\\Reports"
  },
  "options": {
    "timeout": 300,
    "gitRepo": "https://github.com/keepithuman/ansible-powershell-automation.git"
  }
}
```

**Supported Actions:**
- `ServiceManagement` - Start, stop, restart Windows services
- `FeatureManagement` - Enable/disable Windows features
- `EventLogCheck` - Analyze Windows event logs
- `SystemInfo` - Gather comprehensive system information
- `FileOperations` - File and directory operations
- `RegistryCheck` - Registry key and value operations

### manageServices

Specialized method for Windows service management.

**Example Request:**
```json
{
  "targets": ["web-server-01", "web-server-02"],
  "serviceName": "IIS",
  "action": "Restart",
  "timeout": 120
}
```

### getSystemInfo

Collect comprehensive system information from Windows hosts.

**Example Request:**
```json
{
  "targets": ["all-windows-servers"],
  "includeProcesses": true,
  "includeDiskInfo": true,
  "outputPath": "C:\\SystemReports"
}
```

## Integration Examples

### From Itential Workflow

```javascript
// Call IAG5 service from Itential workflow
const response = await this.callService('PowerShellAutomation', 'executeWindowsScript', {
  targets: ['prod-web-01', 'prod-web-02'],
  action: 'ServiceManagement',
  parameters: {
    serviceName: 'W3SVC',
    serviceAction: 'Restart'
  }
});
```

### Direct REST API Call

```bash
curl -X POST http://localhost:3000/execute-script \
  -H "Content-Type: application/json" \
  -d '{
    "targets": ["windows-server-01"],
    "action": "SystemInfo",
    "parameters": {
      "outputPath": "C:\\temp\\reports"
    }
  }'
```

## Configuration

### Ansible Configuration

Edit `ansible/ansible.cfg` for your environment:
- Connection timeouts
- SSH/WinRM settings
- Logging preferences
- Performance tuning

### Windows Host Setup

Ensure your Windows machines have:
- WinRM enabled and configured
- PowerShell execution policy set appropriately
- Network connectivity to the service
- Appropriate user permissions

**Enable WinRM on Windows:**
```powershell
# Run on Windows machines
winrm quickconfig
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
```

### IAG5 Service Configuration

The service configuration includes:
- Authentication methods
- Health check settings
- Throttling parameters
- SSL/TLS settings
- Retry and timeout configurations

## Error Handling

The service provides comprehensive error handling:

- **Connection Errors**: WinRM/network connectivity issues
- **Authentication Errors**: Invalid credentials or permissions
- **Script Errors**: PowerShell execution failures
- **Timeout Errors**: Long-running operations
- **Git Errors**: Repository access or script missing

All errors are logged and returned with structured error responses.

## Monitoring and Logging

### Health Check

```bash
curl http://localhost:3000/health
```

Response includes:
- Service status
- Dependency checks (Ansible, Git, Python)
- Version information
- Timestamp

### Logging

- **Service Logs**: Flask application logs
- **Ansible Logs**: Playbook execution logs (`/var/log/ansible.log`)
- **PowerShell Logs**: Script execution logs on target machines

## Security Considerations

- **Credentials**: Use Ansible Vault for sensitive information
- **Network Security**: Secure WinRM communications
- **Access Control**: Implement proper IAG5 authentication
- **Audit Trail**: All executions are logged with unique IDs
- **Script Validation**: Only execute scripts from trusted Git repositories

## Troubleshooting

### Common Issues

1. **WinRM Connection Failed**
   ```bash
   # Test WinRM connectivity
   ansible windows -m win_ping -i inventory/hosts.yml
   ```

2. **PowerShell Execution Policy**
   ```powershell
   # On Windows machines
   Set-ExecutionPolicy RemoteSigned -Force
   ```

3. **Git Access Issues**
   ```bash
   # Test Git access
   git clone https://github.com/keepithuman/ansible-powershell-automation.git /tmp/test
   ```

### Debug Mode

Run the service in debug mode for detailed logging:
```bash
FLASK_ENV=development python scripts/iag-ansible-bridge.py
```

## Performance Tuning

- **Ansible Forks**: Adjust `forks` in `ansible.cfg` for parallel execution
- **Connection Pooling**: Configure WinRM connection pooling
- **Script Caching**: Enable local Git repository caching
- **Timeout Settings**: Optimize timeouts for your environment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in this repository
- Check the troubleshooting section
- Review Ansible and IAG5 documentation

## Related Projects

- [PowerShell Scripts Repository](https://github.com/keepithuman/ansible-powershell-automation)
- [Itential Automation Gateway Documentation](https://docs.itential.com/)
- [Ansible Windows Documentation](https://docs.ansible.com/ansible/latest/user_guide/windows.html)