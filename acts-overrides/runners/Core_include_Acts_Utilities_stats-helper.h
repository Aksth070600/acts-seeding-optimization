#pragma once

#include <cstdint>
#include <iostream>
#include <mutex>
#include <string>
#include <unordered_map>

namespace stats_helper {

struct StatsData {
    std::int64_t total = 0;
    std::uint64_t count = 0;
    std::unordered_map<std::int64_t, std::uint64_t> value_count;
};

class Registry {
public:
    static Registry& instance() {
        static Registry reg;
        return reg;
    }

    void add(const char* name, std::int64_t value) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto& entry = data_[name];
        entry.total += value;
        entry.count += 1;
        entry.value_count[value] += 1;
    }

    void dump(std::ostream& os = std::cout) {
        std::lock_guard<std::mutex> lock(mutex_);

        for (const auto& [name, entry] : data_) {
            os << "STATS NAME: " << name
               << ", TOTAL: " << entry.total
               << ", COUNT: " << entry.count
               << ", VALUE_COUNT: [";

            bool first = true;
            for (const auto& [value, count] : entry.value_count) {
                if (!first) {
                    os << ", ";
                }
                os << value << ":" << count;
                first = false;
            }

            os << "]\n";
        }
    }

    void reset() {
        std::lock_guard<std::mutex> lock(mutex_);
        data_.clear();
    }

private:
    std::unordered_map<std::string, StatsData> data_;
    std::mutex mutex_;
};

class StatsCollector {
public:
    explicit StatsCollector(const char* name) : name_(name) {}

    void operator()(std::int64_t value) const {
        Registry::instance().add(name_, value);
    }

private:
    const char* name_;
};

inline void dump() {
    Registry::instance().dump();
}

inline void reset() {
    Registry::instance().reset();
}

} // namespace stats_helper

#define STATS(NAME) \
    ::stats_helper::StatsCollector NAME(#NAME)

#define STATS_DUMP() ::stats_helper::dump()
#define STATS_RESET() ::stats_helper::reset()

#define STATS(NAME) \
    ::stats_helper::StatsCollector NAME(#NAME)

#define STATS_DUMP() ::stats_helper::dump()
#define STATS_RESET() ::stats_helper::reset()
