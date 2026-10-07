# ManTech Transmog — Tbc

Source: flekz-games/cmangos-transmog revision 0abf98b38e80724b5a2847b029ccf72e09d98ef2.
Vendored in src/modules/transmog. BUILD_MODULE_TRANSMOG is required by this baseline.

## Install

1. Build with the existing Build-Local-TBC.cmd launcher.
2. Before starting the new binary with transmog enabled, run ONLY
   sql/custom/transmog/INSTALL-TBC.sql. It selects mangos_tbc and
   character_tbc explicitly, installs NPC 190010 in Stormwind/Orgrimmar, and
   creates the two character tables without deleting saved appearance data.
3. Copy transmog.conf beside mangosd.exe with Transmog.Enable = 1.
   Defaults: vendor-value price, no extra fee, multiplier 1, no token requirement.
4. Deploy the new binary and restart the realm.
5. Install addons/2.4.3/Transmog in the client's Interface/AddOns directory.
   The path must end in Interface/AddOns/Transmog/Transmog.toc.
6. Talk to Magister Stellaria in the Stormwind Mage Tower or Orgrimmar Valley of
   Spirits. For testing, GM can locate the existing entry 190010 using .go creature
   commands; do not repeatedly spawn duplicate NPCs.

## Behavior and local changes

Appearances are learned from equipped eligible gear, including currently equipped
gear on login. Previously sold/deleted items cannot be reconstructed retroactively.
Collections are per character. Equipping items records future discoveries.
Appearance changes retain the equipped item's stats. Matching armor/weapon subclass
and inventory type are required (robes and chest armor are equivalent).
Applying changes requires being alive, out of combat and interacting with NPC 190010.
Requests are bounded and checked for duplicate slots, overflow, discovered appearances
and equipment compatibility before any item is changed or payment taken.
Shared state is guarded for the core's concurrent callbacks. Random free bots are
excluded by the upstream module. Price configuration is bounded. Character install
SQL is nondestructive; loading one character cannot delete another's discoveries.
Addon initialization tolerates missing BattlefieldMinimapOptions.

## Verify after restart

Open the UI with the client addon, learn an appearance by equipping gear, apply it
to a compatible item, check the price and unchanged stats, relog and confirm it
persists, then restore its original appearance. Check another player sees the look.
Check a second character's collection remains separate and dual spec/dummies work.
This integration was checked with module-only compilation and targeted tests;
full server build and gameplay validation are performed by the operator.

Disable: set Transmog.Enable = 0 and restart. Keep the tables to retain progress.
Do not run the upstream uninstall SQL unless intentionally deleting transmog data.
