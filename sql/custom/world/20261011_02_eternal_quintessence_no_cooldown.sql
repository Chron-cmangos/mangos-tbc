-- Matching world DB only. Eternal remains reusable; Aqual is untouched.
UPDATE item_template
SET spellcooldown_1 = 0, spellcategorycooldown_1 = 0
WHERE entry = 22754 AND spellid_1 = 21358;
SELECT entry, name, spellid_1, spellcooldown_1, spellcategorycooldown_1
FROM item_template WHERE entry IN (17333, 22754);
