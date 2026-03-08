# Configuration Reference

HEMS is configured via a single `config.yaml` file.
Copy `config.yaml.example` and fill in your values.

The file lives in `HEMS_DATA_DIR` (default: project root, `/data` in Docker).

---

## Top-level sections

```
hems:          General settings (name, location)
integrations:  List of active device integrations
charging:      EV charging behaviour
pricing:       Electricity price source
forecast:      PV production forecast
exports:       Optional InfluxDB export
```

---

## hems

```yaml
hems:
  name: "My Home"      # Displayed in the UI header
  latitude: 51.5       # Used for PV forecast (Open-Meteo)
  longitude: 4.3
```

---

## integrations

Each entry activates one integration instance.

```yaml
integrations:
  - id: "my_enphase"           # Unique ID — used as DB key and in the API
    type: "enphase_iq_gateway" # Plugin type ID (see GET /api/v1/integration-types)
    name: "Zonnepanelen"       # Display name in the UI
    enabled: true
    config:
      host: "192.168.1.50"
      token: "eyJ..."
```

### Available types

| type | Category | Notes |
|---|---|---|
| `enphase_iq_gateway` | solar | Local HTTPS + JWT token |
| `homewizard_p1` | grid | Local REST, enable API in app |
| `homewizard_socket` | smart_plug | Local REST, enable API in app |
| `shelly` | smart_plug | Gen1 or Gen2, set `generation` |
| `alfen_eve` | charger | Modbus TCP port 502 |
| `weheat` | heat_pump | Cloud OAuth2, read-only |

---

## charging

Controls the EV charging state machine.

```yaml
charging:
  mode: "solar"                  # off | min | solar | fast
  solar_start_threshold_w: 1380  # Minimum surplus to start (6A × 230V)
  hysteresis_seconds: 60         # How long below threshold before pausing
  min_soc_percent: 20            # Reserved — requires vehicle API
  target_soc_percent: 80         # Reserved — requires vehicle API
  charge_by_time: null           # e.g. "07:00" — force charge regardless of mode
```

### Modes

| Mode | Behaviour |
|---|---|
| `off` | Charger always paused (0A) |
| `min` | Always charge at minimum current (6A) |
| `solar` | Charge only when solar surplus ≥ threshold; hysteresis prevents rapid cycling |
| `fast` | Charge at maximum current (32A) always |

---

## pricing

```yaml
pricing:
  source: "entso-e"                 # entso-e | manual
  entso_e_token: ""                 # Free token from transparency.entsoe.eu
  bidding_zone: "10YNL----------L"  # Netherlands; see ENTSO-E docs for other zones
  supplier_markup_eur_kwh: 0.04     # Opslag leverancier
  energy_tax_eur_kwh: 0.1228        # Energiebelasting NL 2025
  vat_percent: 21
  manual_price_eur_kwh: 0.25        # Used when source: manual or ENTSO-E unavailable
```

All-in price formula:
`(base + supplier_markup + energy_tax) × (1 + vat/100)`

---

## forecast

```yaml
forecast:
  enabled: true
  system_kwp: 8.5          # Total panel capacity in kWp
  tilt_degrees: 35         # Panel tilt (0 = flat, 90 = vertical)
  azimuth_degrees: 180     # Panel direction (180 = south, 90 = east, 270 = west)
```

Uses Open-Meteo (no API key) + pvlib for irradiance → watts conversion.

---

## exports

### InfluxDB (optional)

Enable to write every poll result to InfluxDB v2 in addition to SQLite.

```yaml
exports:
  influxdb:
    enabled: false
    url: "http://influxdb:8086"  # or your own InfluxDB instance
    token: ""
    org: "hems"
    bucket: "energy"
```

Start with the overlay:
```bash
docker compose -f docker-compose.yml -f docker-compose.influxdb.yml up -d
```

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `HEMS_DATA_DIR` | `.` (project root) | Directory for `config.yaml` and `hems.db` |
| `INFLUXDB_TOKEN` | — | Only needed for `docker-compose.influxdb.yml` |
