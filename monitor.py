#!.env/bin/python3

# System Libraries
import os
import sys
import time
import json
import argparse
import subprocess

# # Activate the virtual environment
# venv_path = os.path.join(os.path.dirname(__file__), '.env', 'bin', 'activate')
#
# if os.path.exists(venv_path):
#     with open(venv_path) as f:
#         exec(f.read(), {'__file__': venv_path})

# Adafruit Libraries
import adafruit_sht31d
import board
import busio

# MySQL Libraries
import mysql.connector
from mysql.connector import Error

# Initialize the I2C bus and sensor
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_sht31d.SHT31D(i2c)

# Default configuration
default_config = {
    "db_host": "localhost",
    "db_name": "sensor_data",
    "db_user": "sensor_user",
    "db_password": "",
    "frequency": 60
}

config_file = "config.cfg"

def load_config():
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        return default_config

def save_config(config):
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)

def configure():
    config = load_config()
    config['db_host'] = input(f"Database Host (current: {config['db_host']}): ") or config['db_host']
    config['db_name'] = input(f"Database Name (current: {config['db_name']}): ") or config['db_name']
    config['db_user'] = input(f"Database Username (current: {config['db_user']}): ") or config['db_user']
    config['db_password'] = input("Database Password: ") or config['db_password']
    config['frequency'] = int(input(f"Frequency in seconds (current: {config['frequency']}): ") or config['frequency'])
    save_config(config)
    print("Configuration saved.")

def log_data(temperature, humidity, config):
    try:
        connection = mysql.connector.connect(
            host=config['db_host'],
            user=config['db_user'],
            password=config['db_password'],
            database=config['db_name']
        )

        if connection.is_connected():
            cursor = connection.cursor()
            sql = "INSERT INTO readings (temperature, humidity, timestamp) VALUES (%s, %s, NOW())"
            cursor.execute(sql, (temperature, humidity))
            connection.commit()
            cursor.close()

    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            connection.close()

def read_sensor():
    temperature = sensor.temperature
    humidity = sensor.relative_humidity
    return temperature, humidity

def create_service(script_path):
    script_dir = os.path.dirname(script_path)
    venv_path = os.path.abspath('.env/bin/activate')
    service_content = f"""
    [Unit]
    Description=SHT30 Sensor Data Logger Service
    After=multi-user.target

    [Service]
    Type=simple
    WorkingDirectory={script_dir}
    ExecStart=/bin/bash -c 'source {venv_path} && python3 {script_path}'
    Restart=on-failure
    User={os.getlogin()}

    [Install]
    WantedBy=multi-user.target
    """
    service_file_path = '/etc/systemd/system/sht30_logger.service'

    try:
        # Write the service file using sudo
        with open('/tmp/sht30_logger.service', 'w') as service_file:
            service_file.write(service_content)

        subprocess.run(['sudo', 'mv', '/tmp/sht30_logger.service', service_file_path], check=True)
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', 'sht30_logger.service'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', 'sht30_logger.service'], check=True)
        print("Service installed, enabled and started.")
    except Exception as e:
        print(f"Failed to install service: {e}")
        sys.exit(1)

def remove_service():
    os.system('sudo systemctl stop sht30_logger.service')
    os.system('sudo systemctl disable sht30_logger.service')
    os.system('sudo rm /etc/systemd/system/sht30_logger.service')
    os.system('sudo systemctl daemon-reload')
    print("Service removed.")

if __name__ == "__main__":
    script_name = sys.argv[0]

    parser = argparse.ArgumentParser(
        description="SHT30 Sensor Data Logger",
        epilog=f"Examples:\n"
               f"  python3 {script_name} --once --verbose\n"
               f"  python3 {script_name} --console\n"
               f"  python3 {script_name} --once --console --verbose\n"
               f"  python3 {script_name}\n\n"
               "The script allows you to:\n"
               "- Run continuously or take a single reading with --once\n"
               "- Print the readings without storing them using --console\n"
               "- Print the readings to the console with --verbose\n"
               "- Install the script as a service with --install\n"
               "- Uninstall the service with --uninstall\n"
               "- Configure the script with --configure",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("--once", action="store_true", help="Retrieve and store the sensor data only once.")
    parser.add_argument("--console", action="store_true", help="Only display the sensor data without storing it.")
    parser.add_argument("--verbose", action="store_true", help="Echo the sensor readings to the console.")
    parser.add_argument("--install", action="store_true", help="Install the script as a systemd service.")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall the script as a systemd service.")
    parser.add_argument("--configure", action="store_true", help="Configure the script settings.")

    args = parser.parse_args()

    if args.configure:
        configure()
    else:
        config = load_config()

        if args.install:
            script_path = os.path.abspath(__file__)
            create_service(script_path)
        elif args.uninstall:
            remove_service()
        else:
            def process_reading():
                temp, hum = read_sensor()
                if args.verbose:
                    print(f"Temperature: {temp} C, Humidity: {hum} %")
                if not args.console:
                    log_data(temp, hum, config)

            if args.once:
                process_reading()
                print("Completed a single reading.")
            else:
                try:
                    def process_reading():
                        temp, hum = read_sensor()
                        if args.verbose:
                            print(f"Temperature: {temp} C, Humidity: {hum} %")
                        if not args.console:
                            log_data(temp, hum, config)

                    if args.once:
                        process_reading()
                        print("Completed a single reading.")
                    else:
                        while True:
                            process_reading()
                            time.sleep(config['frequency'])  # Wait for the configured frequency
                except KeyboardInterrupt:
                    print("\nStopping...")
