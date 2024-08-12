#!/bin/bash

# Function to prompt the user for MariaDB installation
prompt_mariadb_installation() {
  read -p "Do you want to install MariaDB on this Raspberry Pi? (y/n): " install_mariadb
  echo
}

# Function to prompt the user for the MariaDB password
prompt_mariadb_password() {
  read -sp "Please specify the password to be used for the MariaDB user 'sensor_user': " password_mariadb
  echo
}

# Function to update the system
update_system() {
  echo "Updating the system..."
  sudo apt-get update && sudo apt-get upgrade -y
  if [[ $? -ne 0 ]]; then
    echo "System update failed. Exiting."
    exit 1
  fi
  echo "System update completed."
}

# Function to install dependencies
install_dependencies() {
  echo "Installing dependencies..."
  sudo apt-get install -y git python3 python3-pip mariadb-client
  if [[ $? -ne 0 ]]; then
    echo "Failed to install dependencies. Exiting."
    exit 1
  fi

  # Automatically enable I2C without user interaction
  sudo raspi-config nonint do_i2c 0

  # Create a Python virtual environment
  python3 -m venv .env
  source .env/bin/activate

  # Install python3 libraries within the virtual environment
  pip3 install adafruit-circuitpython-sht31d
  pip3 install mysql-connector-python
  deactivate

  echo "Dependencies installation completed."
}

# Function to install MariaDB
install_mariadb() {
  sudo apt-get install -y mariadb-server
  sudo mysql_secure_installation

  # Automate database setup
  sudo mariadb -u root <<EOF
CREATE DATABASE sensor_data;
CREATE USER 'sensor_user'@'localhost' IDENTIFIED BY '$password_mariadb';
GRANT ALL PRIVILEGES ON sensor_data.* TO 'sensor_user'@'localhost';
FLUSH PRIVILEGES;
USE sensor_data;
CREATE TABLE readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    temperature FLOAT NOT NULL,
    humidity FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF

  sudo systemctl enable mariadb
}

# Function to create the configuration file
create_config_file() {
  config_file="config.cfg"
  if [ ! -f "$config_file" ]; then
    echo "Creating configuration file: $config_file"
    cat <<EOF > $config_file
{
    "db_host": "localhost",
    "db_name": "sensor_data",
    "db_user": "sensor_user",
    "db_password": "$password_mariadb",
    "frequency": 60
}
EOF
    echo "Configuration file created."
  else
    echo "Configuration file already exists."
  fi
}

# Main script execution
update_system
install_dependencies
prompt_mariadb_installation
prompt_mariadb_password
create_config_file

if [ "$install_mariadb" == "y" ]; then
  install_mariadb
  echo "MariaDB installation and configuration completed."
else
  echo "Skipping MariaDB installation."
fi

echo "Installation process completed."
