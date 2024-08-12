# Usage

```
$ ./run.sh --help
usage: monitor.py [-h] [--once] [--console] [--verbose] [--install] [--uninstall] [--configure]

SHT30 Sensor Data Logger

options:
  -h, --help   show this help message and exit
  --once       Retrieve and store the sensor data only once.
  --console    Only display the sensor data without storing it.
  --verbose    Echo the sensor readings to the console.
  --install    Install the script as a systemd service.
  --uninstall  Uninstall the script as a systemd service.
  --configure  Configure the script settings.

Examples:
  python3 monitor.py --once --verbose
  python3 monitor.py --console
  python3 monitor.py --once --console --verbose
  python3 monitor.py

The script allows you to:
- Run continuously or take a single reading with --once
- Print the readings without storing them using --console
- Print the readings to the console with --verbose
- Install the script as a service with --install
- Uninstall the service with --uninstall
- Configure the script with --configure
```
