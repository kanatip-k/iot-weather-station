# IoT Weather and Air Quality Station

An educational monitoring pipeline connecting ESP32/ESP8266 firmware, MQTT, a Python collector, MongoDB, and a FastAPI dashboard.

## Features and structure

The source and existing documentation describe temperature, humidity, and PM2.5 reporting, station discovery, latest readings, and reading history. Hardware behavior and the running services have not been verified during migration.

- `esp32/`: Arduino firmware
- `mqtt/`: Mosquitto broker configuration
- `collector/`: MQTT subscriber and MongoDB writer
- `webapp/`: FastAPI application and dashboard
- `docker-compose.yml`: service configuration, if cleared for copying

## Requirements and installation

Install Docker with Compose for the server stack. For hardware, use a compatible ESP32/ESP8266 board, Arduino IDE, PubSubClient, ArduinoJson, Adafruit DHT Sensor Library, and Adafruit Unified Sensor. Confirm wiring against the firmware.

The original `.env` was withheld. A reviewed `.env.example` contains non-secret local laboratory defaults; copy it to `.env` and review the ports before starting. The firmware has been restored after confirming that its Wi-Fi values are placeholders. Replace those placeholders locally before flashing and keep actual credentials out of Git. Runtime validation remains pending.

## Running after configuration review

```sh
docker compose up -d --build
```

The supplied documentation uses `http://localhost:8000` for the dashboard and `/api/stations`, `/api/stations/{id}/latest`, and `/api/stations/{id}/history` for readings. Firmware must connect to the broker host's LAN address. Stop services with `docker compose down`.

## Status and limitations

Academic prototype; runtime and hardware checks pending. The original firmware documentation warns that PM2.5 conversion needs calibration for the actual sensor. The separate DHT11/PMS7003 sketch is an alternative candidate and has not been merged. Anonymous MQTT access is configured for laboratory use; authentication, TLS, database security, and API authentication need review before deployment.

## Screenshots, contributions and license

No verified screenshots or live demo are included. Individual contribution and redistribution rights require confirmation. No new license is assigned.
