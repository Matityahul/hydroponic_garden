from time import sleep

from enum import Enum
from flask import Flask, jsonify

import adafruit_ads1x15.ads1115 as ADS

app = Flask(__name__)

MAX_VAULT = 4096

class LightRange(Enum):
    LAW = 1
    MEDIUM = 2
    HIGH = 3
    MAX = 4


class TempRange(Enum):
    COLD = 1
    NORMAL = 2
    HOT = 3


class PHRange(Enum):
    ACID = 1
    NORMAL = 2
    BASE = 3


class AlertStatus(Enum):
    GREEN = 1
    YELLOW = 2
    RED = 3



from w1thermsensor import W1ThermSensor

@app.route('/temperature')
def temp():
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


    return jsonify({
        "value": temperature,
        "status": range.name,
        "alert": alert.name,
    })


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
def voltage():
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

    return jsonify({
        "value": y,
        "status": range.name,
        "alert": alert.name,
    })

@app.route('/light')
def light():
    voltage = analog(ADS.P0).voltage * 1000

    if voltage < 1000:
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

    return jsonify({
        "value": voltage,
        "status": range.name,
        "alert": alert.name,
    })




if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)