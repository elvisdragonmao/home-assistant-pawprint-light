# Home Assistant PawPrint Light Controller

A local Bluetooth integration for the **DG-LAB PawPrint Wireless Button Sensor V1.1** (`47L120300`). It turns PawPrint button and motion gestures into Home Assistant light controls and exposes the device's battery report as a diagnostic sensor.

## Features

- Local BLE connection; no cloud account required
- Short press cycles through a color palette
- Long stationary press turns the light off
- Hold and tilt adjusts brightness
- Publishes gesture events as `pawprint_light_gesture`
- Exposes `sensor.pawprint_battery` with battery device class and `%` unit

## Installation

Copy `custom_components/pawprint_light` into your Home Assistant configuration directory:

```text
/config/custom_components/pawprint_light/
```

Then add the integration to `configuration.yaml`:

```yaml
pawprint_light: !include pawprint_light.yaml
```

Example `pawprint_light.yaml`:

```yaml
light: light.desk_lamp
address: "AA:BB:CC:DD:EE:FF"
axis: x
left: -60
right: 60
hold_seconds: 0.5
motion_threshold: 12
speed_threshold: 35
debug: false
dry_run: false
```

Restart Home Assistant after validating the configuration.

## Battery telemetry

PawPrint V1.1 sends a `0x51` status message after the integration writes its existing D0-mode initialization command. The fourth byte is the battery percentage. The integration validates the packet header, device type (`0x03`), and range before updating the Home Assistant sensor.

## Gesture event

Each recognized gesture fires `pawprint_light_gesture` with:

```yaml
gesture: brightness | color | off
brightness_pct: 0-100 | null
```

## Testing

The parser tests run with the Python standard library:

```bash
python -m unittest tests/test_gesture.py -v
```

The complete suite imports Home Assistant and should be run in a Home Assistant Python environment:

```bash
python -m unittest discover -s tests -v
```

## Protocol reference

- [DG-LAB PawPrint Bluetooth protocol](https://github.com/dungeonlab-open/dglab-bluetooth-protocol/blob/main/paw-prints/README.md)

## License

MIT
