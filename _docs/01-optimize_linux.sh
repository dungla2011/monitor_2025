#!/bin/bash

# Function to update or add sysctl parameter
update_sysctl_param() {
    local param="$1"
    local value="$2"
    local file="/etc/sysctl.conf"
    
    # Check if parameter exists
    if grep -q "^${param}" "$file"; then
        # Parameter exists, check if value is correct
        current_value=$(grep "^${param}" "$file" | awk -F'=' '{print $2}' | xargs)
        if [ "$current_value" != "$value" ]; then
            echo "Updating $param: '$current_value' -> '$value'"
            # Use sed to replace the line
            sudo sed -i "s|^${param}.*|${param} = ${value}|" "$file"
        else
            echo "$param already has correct value: $value"
        fi
    else
        # Parameter doesn't exist, add it
        echo "Adding new parameter: $param = $value"
        echo "${param} = ${value}" | sudo tee -a "$file" > /dev/null
    fi
}

# Backup original file
echo "Creating backup of /etc/sysctl.conf..."
sudo cp /etc/sysctl.conf /etc/sysctl.conf.backup.$(date +%Y%m%d_%H%M%S)

echo "Updating sysctl parameters..."

# Update each parameter
update_sysctl_param "net.core.somaxconn" "65535"
update_sysctl_param "net.ipv4.ip_local_port_range" "1024 65535"
update_sysctl_param "net.ipv4.tcp_tw_reuse" "1"
update_sysctl_param "net.ipv4.tcp_fin_timeout" "30"

echo ""
echo "Updated parameters in /etc/sysctl.conf:"
grep -E "(somaxconn|ip_local_port_range|tcp_tw_reuse|tcp_fin_timeout)" /etc/sysctl.conf

echo ""
echo "Applying changes..."
sudo sysctl -p

echo ""
echo "Current values:"
sysctl net.core.somaxconn net.ipv4.ip_local_port_range net.ipv4.tcp_tw_reuse net.ipv4.tcp_fin_timeout