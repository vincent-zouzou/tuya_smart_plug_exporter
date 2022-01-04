Support Tuya Plug, Switch - Version 3.3
How to get the `local_key` of devices: https://github.com/jasonacox/tinytuya#setup-wizard

## Run
```bash
pipenv sync
pipenv run python main.py
```
## Docker
### Test
```bash
docker run --rm -it \
-p 6666-6667:6666-6667/udp \
-p 16666:16666 \
-v $PWD:/app \
python:3.10-slim-buster bash
```
#### Build image
```bash
docker build -t tuya_smart_plug_exporter -f Dockerfile .
```
#### Run Docker
```bash
docker run -d \
-p 6666-6667:6666-6667/udp \
-p 16666:16666 \
-v $PWD:/app \
--name tuya_smart_plug_exporter \
tuya_smart_plug_exporter
```

## Prometheus
```yaml
- job_name: 'tuya smart plug'
  metrics_path: /metrics 
  static_configs:
  - targets:
    - '127.0.0.1:16666'
```

## Grafana
Import grafana_dashboard.json.

## Reference
https://pypi.org/project/tinytuya/