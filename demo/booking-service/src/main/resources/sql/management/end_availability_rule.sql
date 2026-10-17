-- Ending a rule is setting effective_until, never deleting it (R20): the rule is
-- retained for audit and simply stops producing availability.
-- With no date given it ends today, and "today" is the provider's calendar day,
-- because the rule itself is wall-clock in that zone (R14) — never UTC's.
-- The rule's resource is locked FOR UPDATE first, as for a BLOCK exception
-- (insert_availability_exception.sql), so a booking in flight is either refused
-- or reported as a conflict.
WITH r AS (
    SELECT res.resource_id, p.timezone
      FROM availability_rule ar
      JOIN resource res ON res.resource_id = ar.resource_id
      JOIN provider p   ON p.provider_id = res.provider_id
     WHERE ar.public_ref = :ruleRef::uuid
       AND res.provider_id = :providerId::bigint
       FOR UPDATE OF res
)
UPDATE availability_rule ar
   SET effective_until = COALESCE(:effectiveUntil::date,
                                  (:now::timestamptz AT TIME ZONE r.timezone)::date),
       updated_at      = :now::timestamptz
  FROM r
 WHERE ar.resource_id = r.resource_id
   AND ar.public_ref = :ruleRef::uuid
