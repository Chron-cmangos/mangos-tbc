-- Lua 5.0/5.1 compatible. Real gear comes from the native server inspect path;
-- visible item IDs remain cosmetic. Never change global item-cache prototypes.
ManTechEquipment = { snapshots = {}, pending = nil, requestAt = -10 }
local E = ManTechEquipment
E.cacheQueue = {}; E.cacheQueued = {}
local function queueItem(entry)
    if entry == 0 or GetItemInfo(entry) or E.cacheQueued[entry] then return end
    E.cacheQueued[entry] = true
    table.insert(E.cacheQueue, entry)
end
local rawLink = GetInventoryItemLink
local function integer(s, maximum)
    local n = tonumber(s)
    if n and n >= 0 and n <= maximum and n == math.floor(n) then return n end
end
local function split(s)
    local t = {}
    for value in string.gfind(s .. ":", "(.-):") do table.insert(t, value) end
    return t
end
local function guid(unit)
    if not UnitGUID then return nil end
    local v = UnitGUID(unit)
    if not v then return nil end
    return tonumber(string.sub(v, -8), 16)
end
local function request()
    if GetTime() - E.requestAt < 1 then return end
    E.requestAt = GetTime()
    SendChatMessage(".transmog GetTransmogStatus")
end
local function snapshot(unit)
    local name = UnitName(unit)
    if not name then return nil end
    local scope = UnitIsUnit(unit, "player") and "self" or "inspect"
    local s = E.snapshots[scope]
    if not s or s.name ~= name or GetTime() - s.at > 30 then return nil end
    local id = guid(unit)
    if id and s.guid ~= id then return nil end
    return s
end
local function itemId(link)
    if not link then return nil end
    local _, _, id = string.find(link, "item:(%d+):")
    return tonumber(id)
end
local function trueLink(unit, slot, original)
    local s = snapshot(unit)
    local gear = s and s.slots[slot]
    if not gear then return original end
    if gear.entry == 0 then return nil end
    if itemId(original) == gear.entry then return original end
    local name, link = GetItemInfo(gear.entry)
    if not link then queueItem(gear.entry); return original end
    -- Retain the native equipped enchant/suffix/unique fields.
    if original then
        local _, _, tail = string.find(original, "item:%d+(:[^|]+)")
        if tail then link = string.gsub(link, "item:%d+:[^|]+", "item:" .. gear.entry .. tail, 1) end
    end
    return link
end
GetInventoryItemLink = function(unit, slot)
    return trueLink(unit, slot, rawLink(unit, slot))
end
local function fixSet(tooltip, s, entry)
    if not s or not entry or not tooltip.GetName then return end
    local setId
    for _, gear in pairs(s.slots) do if gear.entry == entry then setId = gear.set end end
    local set = setId and s.sets[setId]
    if not set then return end
    local worn = {}
    for _, gear in pairs(s.slots) do worn[gear.entry] = true end
    for i = 1, tooltip:NumLines() do
        local line = getglobal(tooltip:GetName() .. "TextLeft" .. i)
        local text = line and line:GetText()
        if text then
            if string.find(text, set.name, 1, true) == 1 then
                line:SetText(set.name .. " (" .. set.worn .. "/" .. set.total .. ")")
            else
                for id, name in pairs(set.members) do
                    if text == name then
                        if worn[id] then line:SetTextColor(1, 1, 1) else line:SetTextColor(.5, .5, .5) end
                    end
                end
                local _, _, threshold = string.find(text, "^%((%d+)%)")
                threshold = tonumber(threshold)
                if threshold and set.bonuses[threshold] then
                    if set.active >= threshold then line:SetTextColor(0, 1, 0) else line:SetTextColor(.5, .5, .5) end
                end
            end
        end
    end
end
local painting = false
local function paint(tooltip, unit, slot)
    if painting then return end
    local s = snapshot(unit)
    if not s then if UnitIsUnit(unit, "player") then request() end return end
    local gear = s.slots[slot]
    if not gear or gear.entry == 0 then return end
    local link = trueLink(unit, slot, rawLink(unit, slot))
    if not link or itemId(link) ~= gear.entry then return end
    painting = true
    tooltip:SetHyperlink(link)
    fixSet(tooltip, s, gear.entry)
    tooltip:Show()
    painting = false
end
local function hookTooltip(tooltip)
    if not tooltip then return end
    local original = tooltip.SetInventoryItem
    tooltip.SetInventoryItem = function(self, unit, slot)
        local result, cooldown, repair = original(self, unit, slot)
        if self == GameTooltip then E.hover = {unit = unit, slot = slot} end
        paint(self, unit, slot)
        return result, cooldown, repair
    end
    local hyperlink = tooltip.SetHyperlink
    tooltip.SetHyperlink = function(self, link)
        local result = hyperlink(self, link)
        if not painting then fixSet(self, snapshot("player"), itemId(link)) end
        return result
    end
end
hookTooltip(GameTooltip)
hookTooltip(ItemRefTooltip)
if NotifyInspect then
    local original = NotifyInspect
    NotifyInspect = function(unit)
        E.inspect = {name = UnitName(unit), guid = guid(unit), at = GetTime()}
        E.snapshots.inspect = nil
        return original(unit)
    end
end
function E.Receive(message)
    if type(message) ~= "string" or string.len(message) > 240 then return end
    local v = split(message)
    if v[1] == "GearBegin" then
        E.pending = nil
        local serial, id = integer(v[3], 4294967295), integer(v[5], 4294967295)
        if v[2] ~= "1" or not serial or not id or not v[6] then return end
        if v[4] == "self" then
            if v[6] ~= UnitName("player") or (guid("player") and guid("player") ~= id) then return end
        elseif v[4] == "inspect" then
            local n = E.inspect
            if not n or GetTime() - n.at > 5 or n.name ~= v[6] or (n.guid and n.guid ~= id) then return end
        else return end
        E.pending = {serial = serial, scope = v[4], guid = id, name = v[6], at = GetTime(), slots = {}, sets = {}, count = 0}
        return
    end
    local s = E.pending
    if not s or integer(v[2], 4294967295) ~= s.serial or GetTime() - s.at > 5 then return end
    if v[1] == "GearSlot" then
        local slot, entry, appearance, set = integer(v[3], 19), integer(v[4], 2000000), integer(v[5], 2000000), integer(v[6], 100000)
        if not slot or slot == 0 or not entry or not appearance or not set or s.slots[slot] then E.pending = nil return end
        s.slots[slot] = {entry = entry, appearance = appearance, set = set}; s.count = s.count + 1
    elseif v[1] == "GearSet" then
        local id, worn, active, total = integer(v[3], 100000), integer(v[4], 19), integer(v[5], 19), integer(v[6], 17)
        if not id or not worn or not active or not total or not v[7] or s.sets[id] then E.pending = nil return end
        s.sets[id] = {worn = worn, active = active, total = total, name = v[7], members = {}, bonuses = {}, memberCount = 0, bonusCount = 0}
    elseif v[1] == "GearMember" or v[1] == "GearBonus" then
        local set = s.sets[integer(v[3], 100000)]
        if not set then E.pending = nil return end
        if v[1] == "GearMember" then
            local id = integer(v[4], 2000000)
            if not id or id == 0 or not v[5] or set.members[id] or set.memberCount >= 17 then E.pending = nil return end
            set.members[id] = v[5]; set.memberCount = set.memberCount + 1
        else
            local threshold = integer(v[4], 19)
            if not threshold or threshold == 0 or set.bonusCount >= 8 then E.pending = nil return end
            set.bonuses[threshold] = true; set.bonusCount = set.bonusCount + 1
        end
    elseif v[1] == "GearEnd" then
        E.pending = nil
        if s.count ~= 19 then return end
        for _, gear in pairs(s.slots) do if gear.set ~= 0 and not s.sets[gear.set] then return end end
        E.snapshots[s.scope] = s
        for _, gear in pairs(s.slots) do queueItem(gear.entry) end
        E.repaintUntil = GetTime() + 5
        if E.hover and GameTooltip:IsShown() then paint(GameTooltip, E.hover.unit, E.hover.slot) end
    else E.pending = nil end
end
local frame = CreateFrame("Frame")
frame:RegisterEvent("CHAT_MSG_ADDON")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:RegisterEvent("UNIT_INVENTORY_CHANGED")
frame:SetScript("OnEvent", function(_, ev, prefix, message)
    ev = ev or event
    prefix = prefix or arg1; message = message or arg2
    if ev == "CHAT_MSG_ADDON" then
        if prefix == "mantechequip" then E.Receive(message) end
    elseif ev == "PLAYER_ENTERING_WORLD" or (ev == "UNIT_INVENTORY_CHANGED" and prefix == "player") then
        if ev == "PLAYER_ENTERING_WORLD" then E.cacheQueue = {}; E.cacheQueued = {} end
        E.snapshots.self = nil; E.due = GetTime() + .2
    end
end)
frame:SetScript("OnUpdate", function()
    if E.due and GetTime() >= E.due then E.due = nil; request() end
    if getn(E.cacheQueue) > 0 and (not E.cacheAt or GetTime() >= E.cacheAt) then
        local entry = table.remove(E.cacheQueue, 1)
        if not E.cacheTooltip then
            E.cacheTooltip = CreateFrame("GameTooltip", "ManTechRealGearCache", UIParent, "GameTooltipTemplate")
        end
        E.cacheTooltip:SetOwner(UIParent, "ANCHOR_NONE")
        -- Let the native tooltip issue CMSG_ITEM_QUERY for the real ID.
        -- Never replace the appearance item's global cache record.
        E.cacheTooltip:SetHyperlink("item:" .. entry .. ":0:0:0:0")
        E.cacheTooltip:Hide()
        E.cacheAt = GetTime() + .1
    end
    if E.repaintUntil and GetTime() <= E.repaintUntil and E.hover and GameTooltip:IsShown() and
       (not E.repaintAt or GetTime() >= E.repaintAt) then
        E.repaintAt = GetTime() + .25
        paint(GameTooltip, E.hover.unit, E.hover.slot)
    end
end)
E.frame = frame
if GameTooltip and GameTooltip.HookScript then
    GameTooltip:HookScript("OnHide", function() E.hover = nil end)
end
