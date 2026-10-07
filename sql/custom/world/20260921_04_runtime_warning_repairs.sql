-- Aggro events carry their attacker as the action invoker. GetVictim can still
-- be null when the event fires. Preserve the event radius and recipients.
UPDATE creature_ai_scripts SET action2_param3=6
WHERE id=1808901 AND creature_id=18089 AND event_type=4
AND action2_type=45 AND action2_param3=1;
