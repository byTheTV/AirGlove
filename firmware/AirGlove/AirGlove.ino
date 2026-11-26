#include <Arduino.h>
#include <Wire.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#if defined(CONFIG_BLUEDROID_ENABLED)
#include <BLE2902.h>
#endif
#include <mbedtls/base64.h>
#include <atomic>
#include "Telemetry.h"

namespace {
constexpr int sdaPin = 5;
constexpr int sclPin = 4;
constexpr uint8_t muxAddress = 0x70;
constexpr uint8_t modeRegister = 0x3D;
constexpr uint32_t periodMs = 20;
constexpr uint32_t calibrationMs = 2000;
constexpr char serviceUuid[] = "8d032000-1a92-4e8d-a5a2-fbeac12bb201";
constexpr char dataUuid[] = "8d032001-1a92-4e8d-a5a2-fbeac12bb201";

// SuperMini boards generally have an active-low blue LED on GPIO8.
constexpr int statusLed = 8;
// Set these only for a board with a measured battery divider wired to an ADC.
constexpr int batteryPin = -1;
constexpr unsigned batteryDividerNumerator = 2;
constexpr unsigned batteryDividerDenominator = 1;
constexpr unsigned batteryLowMv = 3400;

std::atomic<uint16_t> peerMtu{0};
BLECharacteristic* dataCharacteristic = nullptr;

class Connection : public BLEServerCallbacks {
    void onConnect(BLEServer*) override {
        peerMtu = 23;
    }

    void onDisconnect(BLEServer*) override {
        peerMtu = 0;
    }

#if defined(CONFIG_BLUEDROID_ENABLED)
    void onConnect(BLEServer* server, esp_ble_gatts_cb_param_t* param) override {
        server->requestConnParams(param->connect.remote_bda, 8, 16, 0, 400);
    }

    void onMtuChanged(BLEServer*, esp_ble_gatts_cb_param_t* param) override {
        peerMtu = param->mtu.mtu;
    }

#else
    void onConnect(BLEServer* server, ble_gap_conn_desc* peer) override {
        server->requestConnParams(peer->conn_handle, 8, 16, 0, 400);
    }

    void onMtuChanged(BLEServer*, ble_gap_conn_desc*, uint16_t mtu) override {
        peerMtu = mtu;
    }
#endif
};

Connection connection;

enum class Stage : uint8_t { Probe, Power, Start, Verify, Ready };

struct Sensor {
    uint8_t address = 0;
    Stage stage = Stage::Probe;
    uint32_t due = 700;
    int32_t gyroSum[3] = {};
    int16_t offset[3] = {};
    uint16_t count = 0;
    bool biased = false;
};

Sensor sensors[telemetry::channels];
uint32_t calibrationStart;
bool collecting = true;
bool wireReady = false;
uint16_t sequence = 0;

bool selectChannel(uint8_t mask) {
    Wire.beginTransmission(muxAddress);
    Wire.write(mask);
    return Wire.endTransmission() == 0;
}

bool writeRegister(uint8_t address, uint8_t reg, uint8_t value) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    Wire.write(value);
    return Wire.endTransmission() == 0;
}

bool readRegisters(uint8_t address, uint8_t reg, uint8_t* out, size_t size) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0 || Wire.requestFrom(address, size) != size) {
        return false;
    }
    for (size_t i = 0; i < size; ++i) {
        out[i] = Wire.read();
    }
    return true;
}

void retry(Sensor& sensor, uint32_t now) {
    sensor = Sensor{};
    sensor.due = now + 1000;
}

void configureNext(uint32_t now) {
    static size_t first = 0;
    for (size_t offset = 0; offset < telemetry::channels; ++offset) {
        const size_t channel = (first + offset) % telemetry::channels;
        Sensor& sensor = sensors[channel];
        if (sensor.stage == Stage::Ready || int32_t(now - sensor.due) < 0) {
            continue;
        }
        first = (channel + 1) % telemetry::channels;
        if (!selectChannel(1u << channel)) {
            retry(sensor, now);
            return;
        }
        bool success = false;
        if (sensor.stage == Stage::Probe) {
            for (uint8_t address = 0x28; address <= 0x29; ++address) {
                uint8_t id;
                if (writeRegister(address, 0x07, 0) &&
                    readRegisters(address, 0x00, &id, 1) && id == 0xA0 &&
                    writeRegister(address, modeRegister, 0)) {
                    sensor.address = address;
                    sensor.stage = Stage::Power;
                    sensor.due = now + 25;
                    success = true;
                    break;
                }
            }
        } else if (sensor.stage == Stage::Power) {
            // Bosch default axes, normal power, m/s² and degrees/s.
            success = writeRegister(sensor.address, 0x3E, 0) &&
                      writeRegister(sensor.address, 0x3B, 0);
            sensor.stage = Stage::Start;
            sensor.due = now + 10;
        } else if (sensor.stage == Stage::Start) {
            success = writeRegister(sensor.address, modeRegister, 0x07); // AMG
            sensor.stage = Stage::Verify;
            sensor.due = now + 20;
        } else if (sensor.stage == Stage::Verify) {
            uint8_t mode;
            success = readRegisters(sensor.address, modeRegister, &mode, 1) && (mode & 0x0F) == 7;
            sensor.stage = Stage::Ready;
        }
        if (!success) {
            retry(sensor, now);
        }
        return;
    }
}

int16_t signedReading(const uint8_t* bytes) {
    const uint16_t raw = bytes[0] | (uint16_t(bytes[1]) << 8);
    return raw < 0x8000 ? int16_t(raw) : int16_t(int32_t(raw) - 0x10000);
}

void startCalibration(uint32_t now) {
    calibrationStart = now;
    collecting = true;
    for (Sensor& sensor : sensors) {
        memset(sensor.gyroSum, 0, sizeof(sensor.gyroSum));
        memset(sensor.offset, 0, sizeof(sensor.offset));
        sensor.count = 0;
        sensor.biased = false;
    }
}

void collectBias(Sensor& sensor, const int16_t* values) {
    int64_t accelerationSquared = 0;
    int64_t gyroSquared = 0;
    for (size_t i = 0; i < 3; ++i) {
        accelerationSquared += int64_t(values[i]) * values[i];
        gyroSquared += int64_t(values[3 + i]) * values[3 + i];
    }
    if (accelerationSquared < 850L * 850 || accelerationSquared > 1100L * 1100 ||
        gyroSquared > 128L * 128) {
        sensor.count = 0;
        memset(sensor.gyroSum, 0, sizeof(sensor.gyroSum));
        return;
    }
    ++sensor.count;
    for (size_t i = 0; i < 3; ++i) {
        sensor.gyroSum[i] += values[3 + i];
    }
}

void readSensors(telemetry::Frame& frame) {
    const uint32_t now = frame.millis;
    if (collecting && int32_t(now - calibrationStart) >= int32_t(calibrationMs)) {
        collecting = false;
        for (Sensor& sensor : sensors) {
            if (sensor.count >= 50) {
                for (size_t i = 0; i < 3; ++i) {
                    sensor.offset[i] = sensor.gyroSum[i] / sensor.count;
                }
                sensor.biased = true;
            }
        }
    }
    if (collecting) {
        frame.flags |= telemetry::calibrating;
    }
    if (!wireReady) {
        return;
    }
    for (size_t channel = 0; channel < telemetry::channels; ++channel) {
        Sensor& sensor = sensors[channel];
        if (sensor.stage != Stage::Ready) {
            continue;
        }
        uint8_t bytes[18];
        if (!selectChannel(1u << channel) || !readRegisters(sensor.address, 0x08, bytes, sizeof(bytes))) {
            retry(sensor, now);
            continue;
        }
        frame.valid |= 1u << channel;
        auto& sample = frame.samples[channel];
        for (size_t axis = 0; axis < 3; ++axis) {
            sample[axis] = signedReading(bytes + 2 * axis);
            sample[3 + axis] = signedReading(bytes + 12 + 2 * axis);
            sample[6 + axis] = signedReading(bytes + 6 + 2 * axis);
        }
        if (collecting && int32_t(now - calibrationStart) >= 0) {
            collectBias(sensor, sample);
        }
        if (sensor.biased) {
            frame.biased |= 1u << channel;
            for (size_t axis = 0; axis < 3; ++axis) {
                sample[3 + axis] = constrain(int32_t(sample[3 + axis]) - sensor.offset[axis], -32768, 32767);
            }
        }
    }
    configureNext(now);
    selectChannel(0);
}

void updateBatteryAndLed(telemetry::Frame& frame) {
    static uint16_t battery = telemetry::unknownBattery;
    static uint32_t lastBatteryCheck = 0;
    const uint32_t now = frame.millis;
    if (batteryPin >= 0 && (battery == telemetry::unknownBattery || now - lastBatteryCheck >= 1000)) {
        lastBatteryCheck = now;
        battery = analogReadMilliVolts(batteryPin) * batteryDividerNumerator / batteryDividerDenominator;
    }
    frame.battery = battery;
    if (battery != telemetry::unknownBattery && battery <= batteryLowMv) {
        frame.flags |= telemetry::batteryLow;
    }
    const uint32_t phase = now % 1000;
    bool on;
    if (frame.flags & telemetry::batteryLow) {
        on = now % 200 < 100;
    } else if (collecting) {
        on = phase < 400;
    } else if (frame.valid != 0x3F) {
        on = phase < 80 || (phase >= 160 && phase < 240);
    } else {
        on = peerMtu.load() != 0 || phase < 100;
    }
    digitalWrite(statusLed, on ? LOW : HIGH);
}

void transmit(const telemetry::Frame& frame) {
    uint8_t data[telemetry::frameSize];
    telemetry::encode(frame, data);
    const uint16_t mtu = peerMtu.load();
    if (mtu >= 23) {
        uint8_t packet[telemetry::frameSize + 4];
        packet[0] = 0xAF;
        uint8_t* seq = packet + 1;
        telemetry::write16(seq, frame.sequence);
        for (size_t offset = 0; offset < sizeof(data) && peerMtu.load(); ) {
            const size_t length = min(sizeof(data) - offset, size_t(mtu - 7));
            packet[3] = offset;
            memcpy(packet + 4, data + offset, length);
            dataCharacteristic->setValue(packet, length + 4);
            dataCharacteristic->notify();
            offset += length;
        }
    }
    constexpr size_t lineSize = 4 + 4 * ((telemetry::frameSize + 2) / 3) + 1;
    if (Serial && Serial.availableForWrite() >= int(lineSize)) {
        uint8_t line[lineSize] = {'A', 'G', '1', ' '};
        size_t length;
        if (mbedtls_base64_encode(line + 4, sizeof(line) - 4, &length, data, sizeof(data)) == 0) {
            line[4 + length] = '\n';
            Serial.write(line, 5 + length);
        }
    }
}
}  // namespace

void setup() {
    Serial.begin(115200);
#if ARDUINO_USB_CDC_ON_BOOT && ARDUINO_USB_MODE
    Serial.setTxTimeoutMs(2);
#endif
    pinMode(statusLed, OUTPUT);
    digitalWrite(statusLed, HIGH);
    wireReady = Wire.begin(sdaPin, sclPin, 100000);
    Wire.setTimeOut(3);
    BLEDevice::init("AirGlove");
    BLEDevice::setMTU(185);
    BLEServer* server = BLEDevice::createServer();
    server->setCallbacks(&connection);
    server->advertiseOnDisconnect(true);
    BLEService* service = server->createService(serviceUuid);
    dataCharacteristic = service->createCharacteristic(dataUuid, BLECharacteristic::PROPERTY_NOTIFY);
#if defined(CONFIG_BLUEDROID_ENABLED)
    dataCharacteristic->addDescriptor(new BLE2902());
#endif
    service->start();
    BLEAdvertising* advertising = BLEDevice::getAdvertising();
    advertising->addServiceUUID(serviceUuid);
    advertising->setScanResponse(true);
    BLEDevice::startAdvertising();
    startCalibration(950);
}

void loop() {
    const uint32_t now = millis();
    for (int n = 0; n < 16 && Serial.available(); ++n) {
        const int command = Serial.read();
        if (command == 'r' || command == 'R') {
            startCalibration(now);
        }
    }
    static uint32_t nextFrame = now;
    if (int32_t(now - nextFrame) >= 0) {
        nextFrame += periodMs;
        if (int32_t(now - nextFrame) >= 0) {
            nextFrame = now + periodMs;
        }
        telemetry::Frame frame;
        frame.sequence = sequence++;
        frame.millis = now;
        readSensors(frame);
        updateBatteryAndLed(frame);
        transmit(frame);
    }
    delay(1);
}
