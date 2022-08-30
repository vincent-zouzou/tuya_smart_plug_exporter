import sys
import os
from pytz import utc
from loguru import logger
import tinytuya
from flask import Flask, Response
from prometheus_client import Summary, Counter, Gauge, \
    CollectorRegistry, generate_latest
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.executors.pool import ThreadPoolExecutor


registry = CollectorRegistry()
labels = ["name", "ip", "id", "local_key"]
tuya_cur_state = Gauge("tuya_cur_state", "Current state", labels, registry=registry)
tuya_cur_current = Gauge("tuya_cur_current", "Current electric current (mA)", labels, registry=registry)
tuya_cur_voltage = Gauge("tuya_cur_voltage", "Current voltage (V)", labels, registry=registry)
tuya_cur_power = Gauge("tuya_cur_power", "Current power (W)", labels, registry=registry)

app = Flask(__name__)


def load_conf():
    global devices
    global conf_file
    # Load the configuration file.
    with open(os.path.join('conf.yaml')) as f:
        conf_file = yaml.safe_load(f)
        print(conf_file)
        # 判断devices是否为空
        if not conf_file["devices"]:
            logger.error("Devices list is empty, one 'local_key' is needed at least!")
            sys.exit(1)
        devices["conf_file"] = conf_file["devices"]

    # 分离设备到不同的组
    for device in devices["conf_file"]:
        if "local_key" not in device:
            devices["no_local_key"].append(device)
        else:
            devices["has_local_key"].append(device)
    # 去重
    if "has_local_key" in devices:
        devices["has_local_key"] = de_duplicate(devices["has_local_key"], "local_key")
    if "no_local_key" in devices:
        devices["no_local_key"] = de_duplicate(devices["no_local_key"], "local_key")

    # 正常的设备放入normal
    for device in devices["has_local_key"]:
        if "ip" in device:
            d = tinytuya.OutletDevice(device["id"], device["ip"], device["local_key"])
            d.set_version(3.3)
            data = d.status()
            if "Error" not in data:
                device.update({"ip": device["ip"], "id": device["id"], "d": d})
                devices["normal"].append(device)


# 扫描局域网，匹配成功的：添加连接信息，(先清空"normal")并放入"normal"；失败的放入"no_local_key"
def devices_scan(local_key):
    scanned = {"normal": [], "no_local_key": []}
    logger.info("Scanning devices...")
    s = tinytuya.deviceScan()
    # logger.info(s)
    for v in s.values():
        for device in local_key:
            d = tinytuya.OutletDevice(v["gwId"], v["ip"], device["local_key"])
            d.set_version(3.3)
            data = d.status()
            if "Error" in data:
                logger.warning(data)
                scanned["no_local_key"].append(device)
            else:
                # logger.info(data)
                device.update({"ip": v["ip"], "id": v["gwId"], "d": d})
                scanned["normal"].append(device)
    global devices
    devices["normal"].clear()
    devices["normal"] = scanned["normal"]
    devices["no_local_key"] = scanned["no_local_key"]
    logger.info(devices["normal"])
    # for k in devices:
    #     print(k, devices[k])


# 获取单个设备的dps(data point status)
def device_dps(d):
    # data = d.status
    # dps = data["dps"]
    dps = d.detect_available_dps()
    return dps


def devices_validate():
    for device in devices["normal"]:
        d = tinytuya.OutletDevice(device["id"], device["ip"], device["local_key"])
        d.set_version(3.3)
        data = d.status()
        if "Error" in data:
            devices["normal"].remove(device)
            devices["no_ip"].append(device)
        else:
            device.update({"d": d})
    return devices


# 基于key去重，遇重复则取后者
def de_duplicate(lst, key):
    if len(lst) < 2:
        return lst
    new = list()
    new.append(lst[0])
    lst.pop(0)
    for i in lst:
        flag = 1
        # new中无与i相等的，则为非重复项，添加到new
        for index, j in enumerate(new):
            if i[key] == j[key]:
                flag = 0
                # 注释下面行，遇重复则取前者
                new[index] = i
                break
        if flag == 1:
            new.append(i)
    return new


@app.route('/metrics')
def metrics():
    for device in devices["normal"]:
        dps = device_dps(device["d"])
        tuya_cur_state.labels(name=device["name"], ip=device["ip"], id=device["id"], local_key=device["local_key"]).set(dps["1"])
        tuya_cur_current.labels(name=device["name"], ip=device["ip"], id=device["id"], local_key=device["local_key"]).set(dps["18"])
        tuya_cur_voltage.labels(device["name"], device["ip"], device["id"], device["local_key"]).set(dps["20"] / 10)
        tuya_cur_power.labels(name=device["name"], ip=device["ip"], id=device["id"], local_key=device["local_key"]).set(dps["19"] / 10)
    return Response(generate_latest(registry), mimetype="text/plain")


@app.route('/-/reload', methods=['POST'])
def reload():
    return logger.info("ToDo: reloading config file")


if __name__ == '__main__':
    conf_file = {}
    devices = {"conf_file": [], "has_local_key": []}
    # devices = {"conf_file": [{"": ""}, {"": ""}], "has_local_key": [{"": ""}, {"": ""}]}

    load_conf()

    # 扫描任务及间隔设置
    if conf_file["scan"]["enable"]:
        if conf_file["scan"]["interval"]:
            unit = conf_file["scan"]["interval"][-1]
            num = int(conf_file["scan"]["interval"][0:-1])
            if unit == "m":
                T = num * 1
            elif unit == "h":
                T = num * 60
            elif unit == "d":
                T = num * 60 * 24
            elif unit == "w":
                T = num * 60 * 24 * 7
            else:
                T = 60 * 24
            # match unit:
            #     case "m":
            #         T = num * 1
            #     case "h":
            #         T = num * 60
            #     case "d":
            #         T = num * 60 * 24
            #     case "w":
            #         T = num * 60 * 24 * 7
            #     case _:
            #         T = 60 * 24
        # 默认时间间隔
        else:
            T = 60 * 24
        scheduler = BackgroundScheduler()
        # a job to be run immediately
        if devices["has_local_key"]:
            scheduler.add_job(func=devices_scan, timezone=utc, args=[devices["has_local_key"]])
        scheduler.add_job(func=devices_scan, trigger='interval', minutes=T, timezone=utc, args=[devices["has_local_key"]])
        scheduler.start()

    app.run(debug=conf_file["debug"], host=conf_file["listen"], port=conf_file["port"], threaded=True)
