-- OPERATOR-ONLY REPAIR, NOT AN AUTOMATIC WORLD DATABASE UPDATE.
-- Select the CHARACTER database. Stop mangosd first.
-- Only for a realm that ran with the module omitted/disabled, after confirming
-- character_action represents the current in-game bars. Do not run against a
-- healthy module-enabled realm. No characters, purchases or inactive specs are
-- deleted. A tiny migration receipt makes an accidental second run a no-op.
CREATE TABLE IF NOT EXISTS mantech_feature_repairs (
    repair_key VARCHAR(96) NOT NULL PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
START TRANSACTION;
INSERT IGNORE INTO mantech_feature_repairs (repair_key)
VALUES ('dualspec_module_reactivation_20260905_single_spec');
SET @apply_dualspec_repair := ROW_COUNT();
-- No purchased secondary specs were found in the inspected affected realms.
-- Leave any purchased/multi-spec character entirely alone for manual review.
DELETE a FROM custom_dualspec_action a
JOIN custom_dualspec_characters c ON c.guid=a.guid
JOIN characters ch ON ch.guid=c.guid
WHERE @apply_dualspec_repair=1 AND c.spec_count=1 AND c.active_spec=0 AND a.spec=0;
INSERT INTO custom_dualspec_action (guid,spec,button,action,type)
SELECT b.guid,0,b.button,b.action,b.type FROM character_action b
JOIN custom_dualspec_characters c ON c.guid=b.guid
JOIN characters ch ON ch.guid=c.guid
WHERE @apply_dualspec_repair=1 AND c.spec_count=1 AND c.active_spec=0;
-- With no saved talent rows, the native module imports the character's current
-- learned talents at next login. Do not reset character_spell or talent points.
DELETE t FROM custom_dualspec_talent t
JOIN custom_dualspec_characters c ON c.guid=t.guid
JOIN characters ch ON ch.guid=c.guid
WHERE @apply_dualspec_repair=1 AND c.spec_count=1 AND c.active_spec=0 AND t.spec=0;
COMMIT;
SELECT @apply_dualspec_repair AS repair_applied;
