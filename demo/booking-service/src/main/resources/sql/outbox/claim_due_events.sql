-- The dispatcher takes the OLDEST undispatched event per booking, never the
-- oldest overall (architecture-design.md AQ6).  That is what preserves
-- per-booking ordering (R29): event N+1 for a booking is never sent while N is
-- still unsent, so a stuck event delays that one booking and nothing else.
--
-- Deliberately not locked.  Holding row locks across a broker round trip would
-- make lock duration depend on network latency.  Two relay instances may
-- therefore publish the same event twice, which R29 already permits — consumers
-- deduplicate on eventId.  Ordering still holds regardless, because a booking's
-- next event is only ever claimed once its predecessor is marked dispatched.
--
-- The head is chosen BEFORE the backoff filter: picking among due events first
-- would let N+1 through while N waits out its backoff.  A booking whose head is
-- not yet due contributes nothing to this pass.
SELECT oe.outbox_event_id,
       oe.event_id,
       oe.booking_id,
       oe.transition_sequence_no,
       et.code AS event_type,
       oe.schema_version,
       oe.payload::text AS payload,
       oe.created_at,
       oe.attempt_count,
       b.public_ref AS booking_ref
  FROM outbox_event oe
  JOIN event_type et ON et.event_type_id = oe.event_type_id
  JOIN booking b     ON b.booking_id = oe.booking_id
 WHERE oe.outbox_event_id IN (
       SELECT head.outbox_event_id
         FROM (SELECT DISTINCT ON (booking_id) outbox_event_id, next_attempt_at
                 FROM outbox_event
                WHERE dispatched_at IS NULL
                ORDER BY booking_id, outbox_event_id) head
        WHERE head.next_attempt_at <= :now::timestamptz
 )
 ORDER BY oe.outbox_event_id
 LIMIT :limit::int
