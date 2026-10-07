# Portable utility grants

Player characters receive one-time grants for Portable Mailbox (65000), Portable Repair Hammer (65001), and Portable Auctioneer / Camotron 9000 (65002). Random bot accounts and deleted characters remain excluded using the existing eligibility rules. Creation and login hooks use the same grant path as the startup backfill.

Each item has its own grant key: portable_mailbox_v1, portable_repair_v1, portable_auctioneer_v1. The older portable_utilities_v1 bundle still counts as having issued the mailbox and hammer; it does not suppress the new auctioneer. Existing recipients therefore receive only Camotron unless other utilities have never been granted or owned.

Before sending an item, the core checks existing grant history, persisted bag/bank inventory joined to item instances, existing mail attachments joined to their receiver's mail, and the online player's inventory including bank. Ownership without a history record is acknowledged with mail_id=0, without creating empty mail. Failed ownership reads defer that grant. Actual mail, item, attachment and unique grant recording use the existing synchronous mail transaction. Repeated startup/login calls do not issue another grant.

Classic supports only one attachment per mail, so utilities are sent separately in all three versions. Existing duplicate mail is not deleted by this change; it prevents additional grants.

## Character-copy website

Keep item entry IDs 65000-65002 and use the usual expansion-specific item conversion with fresh destination instance GUIDs. Copy the destination character, inventory and bank atomically before allowing its first login or any creation/grant callback. The core detects items already present even if grant-history rows were not copied. It cannot detect items the website has not inserted yet. If the website also copies grant history, remap character GUIDs and use the destination mail IDs only for mail that is actually copied; use zero for ownership acknowledgements.

## Rollout and validation

No world/character schema migration, client patch, icon change, or addon change is included. After the world-server restart, the startup backfill issues the new auctioneer once to eligible existing player characters, skips owners (including manual test recipients), and records owned items. Newly created player characters receive their missing utilities through the existing hooks.

Tests run the actual grant source with mocked database/mail boundaries for fresh characters, old bundle/per-item history, partial and complete transfers, bags/bank, pending mail, unsaved online inventory, repeated calls, bot/deleted-character exclusion, failed ownership reads and mismatched online players. The release also exercises the actual ownership SQL against temporary copies of all three production schemas. These checks and native compilation do not replace live gameplay verification.
