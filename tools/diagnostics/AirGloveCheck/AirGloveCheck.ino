#include <Wire.h>

namespace {
constexpr int sdaPin = 5;
constexpr int sclPin = 4;
constexpr uint8_t muxAddress = 0x70;
constexpr size_t muxChannelCount = 8;
constexpr uint8_t pageReg = 0x07;
constexpr uint8_t chipIdReg = 0x00;
constexpr uint8_t selfTestResultReg = 0x36;
constexpr uint8_t systemErrorReg = 0x3A;
constexpr uint8_t modeReg = 0x3D;
constexpr uint8_t powerReg = 0x3E;
constexpr uint8_t triggerReg = 0x3F;
constexpr uint8_t dataReg = 0x08;
constexpr uint8_t chipId = 0xA0;
constexpr uint8_t amgMode = 0x07;
constexpr uint8_t clockSelectBit = 0x80;
constexpr uint8_t selfTestBit = 0x01;
constexpr const char* positions[] = {
    "hand", "thumb", "index", "middle", "ring", "pinky"
};
constexpr size_t sensorCount = sizeof(positions) / sizeof(positions[0]);
uint8_t addresses[muxChannelCount] = {};
bool busReady = false;

const char* channelLabel(size_t channel) {
    return channel < sensorCount ? positions[channel] : "reserve";
}

bool selectChannels(uint8_t mask) {
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

bool readRegisters(uint8_t address, uint8_t reg, uint8_t* data, size_t count) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0 ||
        Wire.requestFrom(address, count) != count) {
        return false;
    }
    for (size_t i = 0; i < count; ++i) {
        data[i] = Wire.read();
    }
    return true;
}

bool configureSensor(uint8_t address) {
    if (!writeRegister(address, modeReg, 0x00)) { // CONFIGMODE
        return false;
    }
    delay(25);
    if (!writeRegister(address, powerReg, 0x00)) { // Normal power
        return false;
    }
    delay(10);
    if (!writeRegister(address, modeReg, amgMode)) {
        return false;
    }
    delay(20);
    uint8_t mode = 0;
    return readRegisters(address, modeReg, &mode, 1) && (mode & 0x0F) == amgMode;
}

void scanSensors() {
    for (uint8_t& address : addresses) {
        address = 0;
    }
    if (!busReady) {
        busReady = Wire.begin(sdaPin, sclPin, 100000);
    }
    if (!busReady) {
        Serial.println("FAIL I2C init (SDA GPIO5, SCL GPIO4)");
        return;
    }
    Wire.setTimeOut(50);
    if (!selectChannels(0)) {
        Serial.println("FAIL TCA9548A at 0x70. Check 3V3, GND, SDA and SCL.");
        return;
    }
    Serial.println("OK TCA9548A at 0x70");
    unsigned detected = 0;
    for (size_t i = 0; i < muxChannelCount; ++i) {
        const bool reserve = i >= sensorCount;
        Serial.printf("CH%u %-7s ", unsigned(i), channelLabel(i));
        if (!selectChannels(1u << i)) {
            Serial.println("FAIL mux channel select");
            continue;
        }
        bool validId = false;
        for (uint8_t address = 0x28; address <= 0x29; ++address) {
            uint8_t id = 0;
            if (!writeRegister(address, pageReg, 0) ||
                !readRegisters(address, chipIdReg, &id, 1)) {
                continue;
            }
            if (id != chipId) {
                Serial.printf("0x%02X CHIP_ID=0x%02X (expected 0xA0) ",
                              unsigned(address), unsigned(id));
                continue;
            }
            validId = true;
            if (configureSensor(address)) {
                addresses[i] = address;
                if (!reserve) {
                    ++detected;
                }
                Serial.printf("OK BNO055 at 0x%02X\n", unsigned(address));
                break;
            }
        }
        if (!addresses[i]) {
            if (validId) {
                Serial.println("FAIL sensor configuration");
            } else {
                Serial.println(reserve ? "BNO055 not found at 0x28/0x29" :
                                         "FAIL BNO055 not found at 0x28/0x29");
            }
        }
    }
    selectChannels(0);
    Serial.printf("Configured: %u/%u. Send r to rescan.\n",
                  detected, unsigned(sensorCount));
}

void testSensor(size_t channel) {
    const uint8_t address = addresses[channel];
    Serial.printf("CH%u BIST ", unsigned(channel));
    if (!address) {
        Serial.println("SKIP no configured BNO055. Send r to rescan.");
        return;
    }
    if (!selectChannels(1u << channel)) {
        Serial.println("FAIL mux channel select");
        selectChannels(0);
        return;
    }

    uint8_t trigger = 0;
    uint8_t result = 0;
    uint8_t error = 0;
    bool readResult = false;
    if (writeRegister(address, modeReg, 0x00)) { // CONFIGMODE
        delay(25);
        if (readRegisters(address, triggerReg, &trigger, 1) &&
            writeRegister(address, triggerReg, (trigger & clockSelectBit) | selfTestBit)) {
            delay(450); // Bosch specifies at least 400 ms before reading SYS_ERR.
            readResult = readRegisters(address, systemErrorReg, &error, 1) &&
                         readRegisters(address, selfTestResultReg, &result, 1);
        }
    }
    const bool restored = configureSensor(address);
    if (!restored) {
        addresses[channel] = 0;
    }
    selectChannels(0);

    if (readResult) {
        Serial.printf("ACC=%s GYR=%s MAG=%s ST_RESULT=0x%02X SYS_ERR=0x%02X ",
                      result & 0x01 ? "PASS" : "FAIL",
                      result & 0x04 ? "PASS" : "FAIL",
                      result & 0x02 ? "PASS" : "FAIL",
                      unsigned(result), unsigned(error));
    } else {
        Serial.print("FAIL I2C self-test transaction ");
    }
    Serial.println(restored ? "AMG restored" : "FAIL AMG restore. Send r to rescan.");
}

void printVector(const char* label, const uint8_t* bytes) {
    int values[3];
    for (size_t axis = 0; axis < 3; ++axis) {
        const uint16_t raw = bytes[2 * axis] | (uint16_t(bytes[2 * axis + 1]) << 8);
        values[axis] = raw < 0x8000 ? int(raw) : int(raw) - 0x10000;
    }
    Serial.printf(" %s=(%d,%d,%d)", label, values[0], values[1], values[2]);
}

void printReadings() {
    bool attemptedRead = false;
    for (size_t i = 0; i < muxChannelCount; ++i) {
        if (!addresses[i]) {
            continue;
        }
        attemptedRead = true;
        const bool channelSelected = selectChannels(1u << i);
        uint8_t data[18]; // Page 0: ACC, MAG, GYR, six bytes each.
        Serial.printf("CH%u %-7s", unsigned(i), channelLabel(i));
        if (!channelSelected || !readRegisters(addresses[i], dataReg, data, sizeof(data))) {
            Serial.println(" FAIL I2C read");
            continue;
        }
        printVector("ACC", data);
        printVector("GYR", data + 12);
        printVector("MAG", data + 6);
        Serial.println();
    }
    if (attemptedRead) {
        selectChannels(0);
    }
}
} // namespace

void setup() {
    Serial.begin(115200);
    delay(1000); // Allow the BNO055 units to finish booting.
    Serial.println("\nAirGlove diagnostics. Send r to rescan.");
    scanSensors();
}

void loop() {
    while (Serial.available()) {
        const int command = Serial.read();
        if (command == 'r' || command == 'R') {
            scanSensors();
        } else if (command >= '0' && command < '0' + int(muxChannelCount)) {
            testSensor(size_t(command - '0'));
        }
    }
    static unsigned long lastRead = 0;
    if (millis() - lastRead >= 250) {
        lastRead = millis();
        printReadings();
    }
    delay(5);
}
