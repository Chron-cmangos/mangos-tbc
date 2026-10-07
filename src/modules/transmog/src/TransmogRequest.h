#pragma once

#include <charconv>
#include <cstdint>
#include <set>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace cmangos_module { namespace transmog_detail {
// Addon input is untrusted. Reject overflow, duplicate slots and trailing data
// before charging or changing any equipped item.
inline bool ParseRequest(const std::string& args, std::vector<std::pair<uint32_t, uint32_t>>& slots)
{
    slots.clear();
    if (args.empty() || args.size() > 512) return false;
    std::vector<std::pair<uint32_t, uint32_t>> parsed;
    std::set<uint32_t> seen;
    size_t start = 0;
    while (start < args.size())
    {
        size_t end = args.find(',', start);
        if (end == std::string::npos) end = args.size();
        const std::string_view pair(args.data() + start, end - start);
        const size_t colon = pair.find(':');
        if (colon == std::string_view::npos) return false;
        uint32_t slot = 0, entry = 0;
        auto number = [](std::string_view input, uint32_t& value) {
            if (input.empty()) return false;
            auto result = std::from_chars(input.data(), input.data() + input.size(), value);
            return result.ec == std::errc() && result.ptr == input.data() + input.size();
        };
        if (!number(pair.substr(0, colon), slot) || !number(pair.substr(colon + 1), entry) ||
            slot >= 19 || !seen.insert(slot).second) return false;
        parsed.emplace_back(slot, entry);
        if (end == args.size()) break;
        start = end + 1;
        if (start == args.size()) return false;
    }
    slots = std::move(parsed);
    return !slots.empty();
}
} }
