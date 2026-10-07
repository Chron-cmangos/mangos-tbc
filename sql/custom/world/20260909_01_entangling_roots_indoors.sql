-- ManTech policy: allow learned druid Entangling Roots ranks indoors.
-- Clear only SPELL_ATTR_ONLY_OUTDOORS; preserve all other flags and NPC variants.
UPDATE spell_template
SET Attributes = Attributes & ~0x00008000
WHERE Id IN (339,1062,5195,5196,9852,9853,26989)
  AND SpellFamilyName = 7 AND (SpellFamilyFlags & 0x00000200) <> 0
  AND (Attributes & 0x00008000) <> 0;
