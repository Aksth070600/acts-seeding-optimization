#pragma once

#include <chrono>
#include <cstdint>
#include <iostream>
#include <ostream>
#include <thread>

namespace timer_helper {

#if defined(__x86_64__) || defined(_M_X64)

static inline std::uint64_t tick_now() noexcept {
    unsigned lo, hi;
    __asm__ __volatile__("rdtsc" : "=a"(lo), "=d"(hi));
    return (static_cast<std::uint64_t>(hi) << 32) | lo;
}
static constexpr bool kUsesCycles = true;

#else

static inline std::uint64_t tick_now() noexcept {
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count());
}
static constexpr bool kUsesCycles = false;

#endif

struct Slot {
    const char* name;
    std::uint64_t total_ticks;
    std::uint64_t count;
    Slot* next;

    explicit Slot(const char* n) noexcept;
};

inline Slot*& registry_head() noexcept {
    static Slot* head = nullptr;
    return head;
}

inline Slot::Slot(const char* n) noexcept
    : name(n), total_ticks(0), count(0), next(registry_head()) {
    registry_head() = this;
}

class ScopedTick {
public:
    explicit ScopedTick(Slot& slot) noexcept
        : slot_(slot), start_(tick_now()) {}

    ~ScopedTick() noexcept {
        slot_.total_ticks += tick_now() - start_;
        slot_.count       += 1;
    }

private:
    Slot& slot_;
    std::uint64_t start_;
};

inline double cycles_per_ns() noexcept {
    if constexpr (!kUsesCycles) return 1.0;
    static double cached = 0.0;
    if (cached > 0.0) return cached;
    using namespace std::chrono;
    auto c0 = tick_now();
    auto t0 = steady_clock::now();
    std::this_thread::sleep_for(milliseconds(10));
    auto c1 = tick_now();
    auto t1 = steady_clock::now();
    auto ns = static_cast<double>(
        duration_cast<nanoseconds>(t1 - t0).count());
    cached = static_cast<double>(c1 - c0) / ns;
    return cached;
}

inline std::uint64_t ticks_to_ns(std::uint64_t ticks) noexcept {
    return static_cast<std::uint64_t>(static_cast<double>(ticks)
                                      / cycles_per_ns());
}

inline void dump(std::ostream& os = std::cout) {
    Slot* first = registry_head();
    if (first == nullptr) return;
    os << "\n=== TIMER SUMMARY ===\n";
    for (Slot* s = first; s != nullptr; s = s->next) {
        auto n = s->count;
        if (n == 0) continue;
        auto t_ns = ticks_to_ns(s->total_ticks);
        os << "TIMER NAME: " << s->name
           << ", TOTAL TIME: " << t_ns << " ns"
           << ", COUNT: " << n
           << ", AVG: " << (t_ns / n) << " ns"
           << '\n';
    }
}

inline void reset() {
    for (Slot* s = registry_head(); s != nullptr; s = s->next) {
        s->total_ticks = 0;
        s->count       = 0;
    }
}

} // namespace timer_helper

#define TIMER_HELPER_CONCAT_IMPL(x, y) x##y
#define TIMER_HELPER_CONCAT(x, y) TIMER_HELPER_CONCAT_IMPL(x, y)

#define TIMER(NAME)                                                            \
    static ::timer_helper::Slot TIMER_HELPER_CONCAT(_timer_slot_, __LINE__)(   \
        #NAME);                                                                \
    ::timer_helper::ScopedTick TIMER_HELPER_CONCAT(_timer_tick_, __LINE__)(    \
        TIMER_HELPER_CONCAT(_timer_slot_, __LINE__))

#define TIMER_DUMP() ::timer_helper::dump()
#define TIMER_RESET() ::timer_helper::reset()
