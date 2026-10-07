#pragma once
#include <algorithm>
namespace ManTech {
// A finite batch: every due map runs exactly once, with its original diff.
// Start the previously expensive work first so it does not form a long tail
// after other workers have gone idle. Equal estimates retain map order.
template<class Entries> void OrderMapUpdates(Entries& entries) {
    std::stable_sort(entries.begin(), entries.end(), [](auto const& a, auto const& b) {
        return a.estimatedMicros > b.estimatedMicros;
    });
}
}
