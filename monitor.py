#!.env/bin/python3

# System Libraries
import os
import sys
import time
import json
import argparse
import datetime
import subprocess

# Adafruit Libraries
import adafruit_sht31d
import board
import busio

# SMTP Libraries
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate

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
    "db_username": "sensor_user",
    "db_password": "",
    "frequency": 60,
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_username": "user@example.com",
    "smtp_password": "",
    "recipient": "alert@example.com",
    "temp_threshold_high": 27,
    "temp_threshold_low": 18,
    "humidity_threshold_high": 80,
    "humidity_threshold_low": 20
}

script_dir = os.path.dirname(os.path.abspath(__file__))
venv_path = os.path.join(script_dir, ".env/bin/activate")
config_file = os.path.join(script_dir, "config.cfg")
service_name = "sht30_logger"

def is_service_installed():
    result = subprocess.run(['systemctl', 'list-units', '--type=service', '--all'], stdout=subprocess.PIPE)
    return f'{service_name}.service' in result.stdout.decode()

def load_config():
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
            return config
    else:
        return default_config

def save_config(config):
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)
    if args.verbose:
        print("Configuration saved.")

def configure():
    config = load_config()
    config['db_host'] = input(f"Database Host (current: {config['db_host']}): ") or config['db_host']
    config['db_name'] = input(f"Database Name (current: {config['db_name']}): ") or config['db_name']
    config['db_username'] = input(f"Database Username (current: {config['db_username']}): ") or config['db_username']
    config['db_password'] = input("Database Password: ") or config['db_password']
    config['frequency'] = int(input(f"Frequency in seconds (current: {config['frequency']}): ") or config['frequency'])
    config['smtp_host'] = input(f"SMTP Server (current: {config['smtp_host']}): ") or config['smtp_host']
    config['smtp_port'] = int(input(f"SMTP Port (current: {config['smtp_port']}): ") or config['smtp_port'])
    config['smtp_username'] = input(f"SMTP Username (current: {config['smtp_username']}): ") or config['smtp_username']
    config['smtp_password'] = input("SMTP Password: ") or config['smtp_password']
    config['recipient'] = input(f"Recipient (current: {config['recipient']}): ") or config['recipient']
    config['temp_threshold_high'] = float(input(f"High Temperature Threshold (current: {config['temp_threshold_high']}): ") or config['temp_threshold_high'])
    config['temp_threshold_low'] = float(input(f"Low Temperature Threshold (current: {config['temp_threshold_low']}): ") or config['temp_threshold_low'])
    config['humidity_threshold_high'] = float(input(f"High Humidity Threshold (current: {config['humidity_threshold_high']}): ") or config['humidity_threshold_high'])
    config['humidity_threshold_low'] = float(input(f"Low Humidity Threshold (current: {config['humidity_threshold_low']}): ") or config['humidity_threshold_low'])
    save_config(config)
    if args.verbose:
        print("Configuration saved.")

def log_error(message):
    with open(os.path.join(script_dir, 'error.log'), 'a') as f:
        f.write(f"{datetime.datetime.now()} - {message}\n")

def log_data(temperature, humidity, config):
    try:
        connection = mysql.connector.connect(
            host=config['db_host'],
            user=config['db_username'],
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
        log_error(f"Database error: {e}")
        if args.verbose:
            print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Function to send an email
def send_email(subject, body, config):
    msg = MIMEMultipart()
    msg['From'] = config['smtp_username']
    msg['To'] = config['recipient']
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)  # Adding Date header

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])
        server.starttls()
        server.login(config['smtp_username'], config['smtp_password'])
        text = msg.as_string()
        server.sendmail(config['smtp_username'], config['recipient'], text)
        server.quit()
        if args.verbose:
            print("Email sent successfully!")
    except Exception as e:
        log_error(f"Failed to send email: {e}")
        if args.verbose:
            print(f"Failed to send email: {e}")

def create_service():
    service_content = f"""
    [Unit]
    Description=SHT30 Sensor Data Logger Service
    After=multi-user.target

    [Service]
    Type=simple
    WorkingDirectory={script_dir}
    ExecStart=/bin/bash -c 'source {venv_path} && python3 {script_dir}'
    Restart=on-failure
    User={os.getlogin()}

    [Install]
    WantedBy=multi-user.target
    """
    service_file_path = f'/etc/systemd/system/{service_name}.service'

    try:
        # Write the service file using sudo
        with open(f'/tmp/{service_name}.service', 'w') as service_file:
            service_file.write(service_content)

        subprocess.run(['sudo', 'mv', f'/tmp/{service_name}.service', service_file_path], check=True)
        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        subprocess.run(['sudo', 'systemctl', 'enable', f'{service_name}.service'], check=True)
        subprocess.run(['sudo', 'systemctl', 'start', f'{service_name}.service'], check=True)
        if args.verbose:
            print("Service installed, enabled and started.")
    except Exception as e:
        log_error(f"Failed to install service: {e}")
        if args.verbose:
            print(f"Failed to install service: {e}")
        sys.exit(1)

def remove_service():
    if is_service_installed():
        os.system(f'sudo systemctl stop {service_name}.service')
        os.system(f'sudo systemctl disable {service_name}.service')
        os.system(f'sudo rm /etc/systemd/system/{service_name}.service')
        os.system('sudo systemctl daemon-reload')
        if args.verbose:
            print("Service removed.")
    else:
        if args.verbose:
            print(f"Service '{service_name}.service' is not installed.")

def start_service():
    if is_service_installed():
        subprocess.run(['sudo', 'systemctl', 'start', f'{service_name}.service'])
        if args.verbose:
            print("Service started.")
    else:
        if args.verbose:
            print(f"Service '{service_name}.service' is not installed.")

def stop_service():
    if is_service_installed():
        subprocess.run(['sudo', 'systemctl', 'stop', f'{service_name}.service'])
        if args.verbose:
            print("Service stopped.")
    else:
        if args.verbose:
            print(f"Service '{service_name}.service' is not installed.")

def read_sensor():
    temperature = sensor.temperature
    humidity = sensor.relative_humidity
    return temperature, humidity

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
               "- start the service with --start\n"
               "- stop the service with --stop\n"
               "- Configure the script with --configure",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("--once", action="store_true", help="Retrieve and store the sensor data only once.")
    parser.add_argument("--console", action="store_true", help="Only display the sensor data without storing it.")
    parser.add_argument("--verbose", action="store_true", help="Echo the sensor readings to the console.")
    parser.add_argument("--install", action="store_true", help="Install the script as a systemd service.")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall the script as a systemd service.")
    parser.add_argument("--start", action="store_true", help="Start the service if installed.")
    parser.add_argument("--stop", action="store_true", help="Stop the service if installed.")
    parser.add_argument("--configure", action="store_true", help="Configure the script settings.")

    args = parser.parse_args()

    if args.configure:
        configure()
    else:
        config = load_config()

        if args.install:
            create_service()
        elif args.uninstall:
            remove_service()
        elif args.start:
            start_service()
        elif args.stop:
            stop_service()
        else:
            try:
                def process_reading():
                    temp, hum = read_sensor()

                    if args.verbose:
                        print(f"Temperature: {temp} C, Humidity: {hum} %")

                    if not args.console:
                        log_data(temp, hum, config)

                    # Check temperature thresholds
                    if temp > config['temp_threshold_high'] or temp < config['temp_threshold_low']:
                        send_email(
                            subject="Temperature Alert",
                            body=f"Temperature out of range: {temp} C",
                            config=config
                        )

                    # Check humidity thresholds
                    if hum > config['humidity_threshold_high'] or hum < config['humidity_threshold_low']:
                        send_email(
                            subject="Humidity Alert",
                            body=f"Humidity out of range: {hum} %",
                            config=config
                        )

                if args.once:
                    process_reading()
                    if args.verbose:
                        print("Completed a single reading.")
                else:
                    if config['frequency'] < 5:
                        log_error(f"Frequency too low ({config['frequency']}s). Setting to minimum value of 5s.")
                        if args.verbose:
                            print(f"Frequency too low ({config['frequency']}s). Setting to minimum value of 5s.")
                        config['frequency'] = 5
                    while True:
                        process_reading()
                        time.sleep(config['frequency'])
            except KeyboardInterrupt:
                if args.verbose:
                    print("\nStopping...")
