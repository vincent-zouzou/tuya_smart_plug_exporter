支持涂鸦系列智能插座 - 3.3版本

如何获取设备的`local_key`: https://github.com/jasonacox/tinytuya#setup-wizard

## Run
```bash
pip install pipenv
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
docker build -t tuya_smart_plug_exporter -f manifest/Dockerfile .
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
导入grafana_dashboard.json.

## Reference
https://pypi.org/project/tinytuya/