-- WoWRaidExport.lua

WoWRaidData = WoWRaidData or {}

-- JSON-Helper
local function escape(str)
    return str:gsub("\\", "\\\\"):gsub("\"", "\\\"")
end

local function toJSON(tbl)
    local function serialize(t)
        local s = "{"
        local first = true
        for k, v in pairs(t) do
            if not first then s = s .. "," end
            first = false
            s = s .. '"' .. escape(k) .. '":' .. toString(v)
        end
        return s .. "}"
    end

    function toString(v)
        if type(v) == "table" then
            local isArray = #v > 0
            if isArray then
                local s = "["
                for i, val in ipairs(v) do
                    s = s .. (i > 1 and "," or "") .. toString(val)
                end
                return s .. "]"
            else
                return serialize(v)
            end
        elseif type(v) == "string" then
            return '"' .. escape(v) .. '"'
        else
            return tostring(v)
        end
    end

    return toString(tbl)
end

local function ExportRaidEvents()
    WoWRaidData.events = {}
    WoWRaidData.timestamp = date("%Y-%m-%d %H:%M:%S")

    C_Calendar.OpenCalendar()

    C_Timer.After(2.0, function()
        local found = 0

        for day = 1, 31 do
            local numEvents = C_Calendar.GetNumDayEvents(0, day)

            for i = 1, numEvents do
                local event = C_Calendar.GetDayEvent(0, day, i)

                if event and event.title then
                    local titleLower = event.title:lower()
                    if titleLower:find("gildenraid") then
                        local dateObj = C_DateAndTime.GetDateFromCalendarTime(event.startTime)

                        local eventData = {
                            title = event.title,
                            date = string.format("%04d-%02d-%02d", dateObj.year, dateObj.month, dateObj.monthDay),
                            time = string.format("%02d:%02d", event.startTime.hour, event.startTime.minute),
                            invites = {}
                        }

                        -- Debugausgabe
                        print("✅ Gildenraid erkannt:")
                        print("   ➤ Titel: " .. eventData.title)
                        print("   ➤ Datum: " .. eventData.date)
                        print("   ➤ Uhrzeit: " .. eventData.time)

                        -- Versuche, Einladungen zu laden (meist nur bei Gilden-Events)
                        if event.eventID then
                            local numInvites = C_Calendar.GetNumInvites(event.eventID)
                            for j = 1, numInvites do
                                local invite = C_Calendar.GetInvite(event.eventID, j)
                                if invite then
                                    table.insert(eventData.invites, {
                                        name = invite.name or "Unbekannt",
                                        className = invite.className or "UNKNOWN"
                                    })
                                end
                            end
                        end

                        if #eventData.invites > 0 then
                            print("   ➤ Teilnehmer:")
                            for _, inv in ipairs(eventData.invites) do
                                print("      - " .. inv.name .. " (" .. inv.className .. ")")
                            end
                        else
                            print("   ⚠️ Keine Teilnehmerdaten verfügbar.")
                        end

                        table.insert(WoWRaidData.events, eventData)
                        found = found + 1
                        print("   ➤ Event exportiert.\n")
                    end
                end
            end
        end

        WoWRaidData.json = toJSON(WoWRaidData.events)

        if found > 0 then
            print("✅ |cff00ff00[WoWRaidExport]: " .. found .. " Gildenraid-Event(s) exportiert.|r")
        else
            print("⚠️ |cffff0000[WoWRaidExport]: Keine Gildenraid-Events gefunden.|r")
        end
    end)
end

-- UI + Slash
local function OnPlayerLogin()
    SLASH_RAIDEXPORT1 = "/raidexport"
    SlashCmdList["RAIDEXPORT"] = function()
        ExportRaidEvents()
    end

    local exportBtn = CreateFrame("Button", "WoWRaidExportButton", UIParent, "UIPanelButtonTemplate")
    exportBtn:SetSize(160, 30)
    exportBtn:SetText("Raid exportieren")
    exportBtn:SetPoint("TOPLEFT", UIParent, "TOPLEFT", 10, -10)
    exportBtn:SetScript("OnClick", ExportRaidEvents)
end

local frame = CreateFrame("Frame")
frame:RegisterEvent("PLAYER_LOGIN")
frame:SetScript("OnEvent", function(self, event)
    if event == "PLAYER_LOGIN" then
        OnPlayerLogin()
    end
end)
