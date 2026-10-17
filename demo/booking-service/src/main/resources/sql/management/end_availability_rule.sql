-- Ending a rule is setting effective_until, never deleting it (R20): the rule is
-- retained for audit and simply stops producing availability.
-- With no date given it ends today, and "today" is the provider's calendar day,
-- because the rule itself is wall-clock in that zone (R14) — never UTC's.
UPDATE availability_rule ar
   SET effective_until = COALESCE(:effectiveUntil::date,
                                  (:now::timestamptz AT TIME ZONE p.timezone)::date),
       updated_at      = :now::timestamptz
  FROM resource r
  JOIN provider p ON p.provider_id = r.provider_id
 WHERE ar.resource_id = r.resource_id
   AND ar.public_ref = :ruleRef::uuid
   AND r.provider_id = :providerId::bigint
