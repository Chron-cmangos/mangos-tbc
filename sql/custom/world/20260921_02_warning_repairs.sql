-- Rank 2 Improved Stings: third aura must target the caster, like adjacent ranks.
-- Guard the original erroneous value. Classic has no third effect and needs no change.
UPDATE spell_template SET EffectImplicitTargetA3=1
WHERE Id=19465 AND Effect3=6 AND EffectImplicitTargetA3=17;
