# Firewall Configuration Guide

This guide explains how to configure your firewall to allow the necessary ports for Prompt Portal.

## 🔥 Quick Setup (Recommended)

Run the automated firewall setup script:

```bash
chmod +x setup-firewall.sh
./setup-firewall.sh
```

This script will automatically configure all necessary ports.

---

## 🛠 Manual Configuration

### For Ubuntu/Debian (UFW Firewall)

#### Step 1: Install UFW
```bash
sudo apt update
sudo apt install ufw
```

#### Step 2: Configure Basic Rules
```bash
# Reset to defaults
sudo ufw --force reset

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (CRITICAL - don't lock yourself out!)
sudo ufw allow ssh
sudo ufw allow 22/tcp
```

#### Step 3: Open Required Ports
```bash
# Web server ports
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Prompt Portal application ports
sudo ufw allow 5173/tcp  # Frontend (Vite dev server)
sudo ufw allow 8000/tcp  # Backend API (FastAPI)

# Optional: MQTT broker
sudo ufw allow 1883/tcp  # MQTT
```

#### Step 4: Enable Firewall
```bash
sudo ufw enable
```

#### Step 5: Verify Configuration
```bash
sudo ufw status verbose
```

### For CentOS/RHEL/Rocky Linux (firewalld)

#### Step 1: Install firewalld
```bash
sudo yum install firewalld
sudo systemctl enable firewalld
sudo systemctl start firewalld
```

#### Step 2: Open Required Ports
```bash
# Web server ports
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https

# Prompt Portal ports
sudo firewall-cmd --permanent --add-port=5173/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp

# Optional: MQTT
sudo firewall-cmd --permanent --add-port=1883/tcp

# SSH (usually enabled by default)
sudo firewall-cmd --permanent --add-service=ssh
```

#### Step 3: Reload Configuration
```bash
sudo firewall-cmd --reload
```

#### Step 4: Verify Configuration
```bash
sudo firewall-cmd --list-all
```

### For Amazon Linux/AWS EC2

#### Using Security Groups (Recommended)
1. Go to AWS Console → EC2 → Security Groups
2. Select your instance's security group
3. Edit inbound rules
4. Add the following rules:

| Type | Protocol | Port Range | Source | Description |
|------|----------|------------|---------|-------------|
| SSH | TCP | 22 | Your IP | SSH access |
| HTTP | TCP | 80 | 0.0.0.0/0 | Web traffic |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Secure web |
| Custom TCP | TCP | 5173 | 0.0.0.0/0 | Frontend |
| Custom TCP | TCP | 8000 | 0.0.0.0/0 | Backend API |
| Custom TCP | TCP | 1883 | 0.0.0.0/0 | MQTT (optional) |

#### Using iptables (Alternative)
```bash
# Allow SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow web traffic
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow Prompt Portal ports
sudo iptables -A INPUT -p tcp --dport 5173 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 1883 -j ACCEPT

# Save rules (varies by system)
sudo service iptables save
```

---

## 🧪 Testing Your Firewall Configuration

### Check Port Status
```bash
# Check if ports are listening
sudo ss -tlnp | grep ':5173'  # Frontend
sudo ss -tlnp | grep ':8000'  # Backend
sudo ss -tlnp | grep ':1883'  # MQTT

# Check firewall status
sudo ufw status              # UFW
sudo firewall-cmd --list-all # firewalld
```

### Test Port Connectivity
```bash
# From another machine, test connectivity
curl -I http://YOUR_SERVER_IP:8000  # Backend API
curl -I http://YOUR_SERVER_IP:5173  # Frontend

# Test with telnet
telnet YOUR_SERVER_IP 8000
telnet YOUR_SERVER_IP 5173
```

### Check Application Logs
```bash
# Check if applications are running
pm2 status

# Check application logs
pm2 logs prompt-portal-backend
pm2 logs prompt-portal-frontend
```

---

## 🔐 Security Best Practices

### 1. Limit SSH Access
```bash
# Only allow SSH from your IP
sudo ufw delete allow 22
sudo ufw allow from YOUR_IP_ADDRESS to any port 22
```

### 2. Use HTTPS in Production
```bash
# Disable HTTP in production
sudo ufw delete allow 80
# Keep only HTTPS
sudo ufw allow 443
```

### 3. Monitor Firewall Logs
```bash
# Enable UFW logging
sudo ufw logging on

# View logs
sudo tail -f /var/log/ufw.log
```

### 4. Regular Security Updates
```bash
# Update system regularly
sudo apt update && sudo apt upgrade -y

# Check for security updates
sudo unattended-upgrades --dry-run
```

---

## 📋 Required Ports Summary

| Port | Service | Protocol | Required | Description |
|------|---------|----------|----------|-------------|
| 22 | SSH | TCP | Yes | Remote server access |
| 80 | HTTP | TCP | Production | Web traffic (redirect to HTTPS) |
| 443 | HTTPS | TCP | Production | Secure web traffic |
| 5173 | Frontend | TCP | Yes | Vite development server |
| 8000 | Backend | TCP | Yes | FastAPI backend |
| 1883 | MQTT | TCP | Optional | MQTT broker |

---

## 🚨 Troubleshooting

### Issue: Can't Access Application
```bash
# Check if firewall is blocking
sudo ufw status

# Check if application is running
pm2 status
sudo ss -tlnp | grep ':8000'

# Temporarily disable firewall for testing
sudo ufw disable
# Test access, then re-enable
sudo ufw enable
```

### Issue: SSH Access Lost
```bash
# If you can still access via console:
sudo ufw allow ssh
sudo ufw reload

# Or disable firewall completely
sudo ufw disable
```

### Issue: Port Already in Use
```bash
# Find what's using the port
sudo lsof -i :8000
sudo kill -9 <PID>

# Or change the application port
# Edit backend/.env and frontend/.env files
```

---

## 📞 Quick Commands Reference

```bash
# UFW Commands
sudo ufw status                 # Show status
sudo ufw enable                 # Enable firewall
sudo ufw disable                # Disable firewall
sudo ufw allow 8000            # Allow port
sudo ufw delete allow 8000     # Remove rule
sudo ufw reset                 # Reset all rules

# Check listening ports
sudo ss -tlnp                  # All listening ports
sudo ss -tlnp | grep :8000     # Specific port

# Test connectivity
curl -I http://IP:PORT         # HTTP test
telnet IP PORT                 # TCP test
```

Your Prompt Portal should now be accessible through the configured firewall!
