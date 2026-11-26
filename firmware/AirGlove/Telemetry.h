#pragma once

#include <stddef.h>
#include <stdint.h>

namespace telemetry {
constexpr size_t channels = 6;
constexpr size_t axes = 9;
constexpr size_t frameSize = 14 + channels * axes * 2 + 2;
constexpr uint16_t unknownBattery = 0xFFFF;
constexpr uint8_t calibrating = 1;
constexpr uint8_t batteryLow = 2;

struct Frame {
    uint16_t sequence = 0;
    uint32_t millis = 0;
    uint8_t valid = 0;
    uint8_t biased = 0;
    uint8_t flags = 0;
    uint16_t battery = unknownBattery;
    int16_t samples[channels][axes] = {};
};

inline void write16(uint8_t*& destination, uint16_t value) {
    *destination++ = value & 0xFF;
    *destination++ = value >> 8;
}

inline uint16_t crc(const uint8_t* data, size_t length) {
    uint16_t result = 0xFFFF;
    for (size_t i = 0; i < length; ++i) {
        result ^= uint16_t(data[i]) << 8;
        for (int bit = 0; bit < 8; ++bit) {
            result = (result & 0x8000) ? (result << 1) ^ 0x1021 : result << 1;
        }
    }
    return result;
}

inline void encode(const Frame& frame, uint8_t (&data)[frameSize]) {
    uint8_t* out = data;
    *out++ = 'A';
    *out++ = 'G';
    *out++ = 1;
    *out++ = frame.flags;
    write16(out, frame.sequence);
    write16(out, uint16_t(frame.millis));
    write16(out, uint16_t(frame.millis >> 16));
    *out++ = frame.valid;
    *out++ = frame.biased;
    write16(out, frame.battery);
    for (const auto& channel : frame.samples) {
        for (int16_t sample : channel) {
            write16(out, uint16_t(sample));
        }
    }
    write16(out, crc(data, frameSize - 2));
}
}  // namespace telemetry
