import threading

from copy import copy
from enum import Enum
from flask import Flask, jsonify

import adafruit_ads1x15.ads1115 as ADS
import time

from pip._vendor.html5lib._utils import memoize

from gpiozero import Button, LED
water_level_switch = Button(25)
# green_led = LED(5)
# yellow_led = LED(6)
# red_led = LED(13)


app = Flask(__name__)

MAX_VAULT = 4096


class LightRange(Enum):
    VERY_LOW = "Increase light now!"
    LAW = "suggest to increase light"
    MEDIUM = None
    HIGH = None
    MAX = "Light is to strong! decrease light"


class TempRange(Enum):
    COLD = "Increase temperature"
    NORMAL = None
    HOT = "Decrease temperature"


class PHRange(Enum):
    ACID = "Water are too Acid! Please adjust it with new water and fertilizer"
    NORMAL = None
    BASE = "Water are too base! Please adjust it with new water and fertilizer"


class WaterLevelRange(Enum):
    LOW = "Water level is low!"
    NORMAL = None


class AlertStatus(Enum):
    GREEN = 1
    YELLOW = 2
    RED = 3


FUNC_TO_RANGE = {
    "_temp": (TempRange, 10*60),
    "_light": (LightRange, 8*60*60),
    "_ph": (PHRange, 60*60),
    "_water_level": (WaterLevelRange, 60*60)
}


from w1thermsensor import W1ThermSensor


global metrics


def test():
    alive = 0
    global metrics
    metrics = {func.__name__: {} for func in [_temp, _light, _ph]}

    while True:
        for func in [_temp, _light, _ph]:

            res = func()
            if res["alert"] == AlertStatus.RED.name:
                metrics[func.__name__][res["status"]] = metrics[func.__name__].get(res["status"], 0) + 1

                print(metrics[func.__name__][res["status"]])
        time.sleep(1)

        alive += 1

        if alive > 60*60*24:  # day
            alive = 0
            metrics = {func.__name__: {} for func in [_temp, _light, _ph]}

        # TODO : Switch on & off the led lights (for example green_led.on() & green_led.off())


@app.route('/temperature')
def temp():
    return jsonify(_temp())


def _temp():
    sensor = W1ThermSensor()
    temperature = sensor.get_temperature()
    if temperature > 30:
        range = TempRange.HOT
        if temperature > 35:
            alert = AlertStatus.RED
        else:
            alert = AlertStatus.YELLOW
    elif temperature < 15:
        range = TempRange.COLD
        if temperature < 10:
            alert = AlertStatus.RED
        else:
            alert = AlertStatus.YELLOW
    else:
        alert = AlertStatus.GREEN
        range = TempRange.NORMAL

    return {
        "value": temperature,
        "status": range.name,
        "alert": alert.name,
        "action": range.value,
    }


@app.route('/')
def hello():
    return "Alla Yesh Botnim"


def analog(ads_port):
    import board
    import busio
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    return AnalogIn(ads, ads_port)


@app.route('/ph')
def ph():
    return jsonify(_ph())


def _ph():
    voltage = analog(ADS.P3).voltage
    y = 60 * voltage - 62.5
    if y < 4.5:
        range = PHRange.ACID
        if y < 3:
            alert = AlertStatus.RED
        else:
            alert = AlertStatus.YELLOW
    elif y > 9.5:
        range = PHRange.BASE
        if y > 11:
            alert = AlertStatus.RED
        else:
            alert = AlertStatus.YELLOW
    else:
        range = PHRange.NORMAL
        alert = AlertStatus.GREEN
    return {
        "value": y,
        "status": range.name,
        "alert": alert.name,
        "action": range.value,
    }


@app.route('/light')
def light():
    return jsonify(_light())


def _light():
    voltage = analog(ADS.P0).voltage * 1000
    if voltage < 100:
        range = LightRange.VERY_LOW
        alert = AlertStatus.RED
    elif voltage < 1000:
        range = LightRange.LAW
        alert = AlertStatus.YELLOW
    elif voltage > 1000 and voltage < 3000:
        range = LightRange.MEDIUM
        alert = AlertStatus.GREEN
    elif voltage == 4096:
        range = LightRange.MAX
        alert = AlertStatus.RED
    else:
        range = LightRange.HIGH
        alert = AlertStatus.GREEN

    return {
        "value": voltage,
        "status": range.name,
        "alert": alert.name,
        "action": range.value,
    }


@app.route('/water_level')
def water_level():
    return jsonify(_water_level())


def _water_level():
    is_active = water_level_switch.is_active

    if is_active:
        alert = AlertStatus.GREEN
        water_level_range = WaterLevelRange.NORMAL
    else:
        alert = AlertStatus.RED
        water_level_range = WaterLevelRange.LOW

    return {
        "value": is_active,
        "status": water_level_range.name,
        "alert": alert.name,
        "action": water_level_range.value,
    }


@app.route("/alerts")
def cur_alerts():
    alerts = []
    global metrics
    cur_metrics = copy(metrics)
    for func, res in cur_metrics.items():
        for status, count in res.items():
            if count > FUNC_TO_RANGE[func][1]:
                alerts.append({
                    "func": func,
                    "status": status,
                    "suggest": FUNC_TO_RANGE[func][0][status].value,
                })
    return jsonify(alerts)


if __name__ == '__main__':
    deref_thread = threading.Thread(target=test)
    deref_thread.daemon = True
    deref_thread.start()

    app.run(debug=True, host="0.0.0.0", port=8000)
