-- UC3.  BLOCK removes availability and beats rules and OPEN alike.
-- The resource row is locked FOR UPDATE, which waits for any booking that holds
-- it FOR SHARE (fn_create_booking, fn_reschedule_booking): an edit and a create
-- on one resource serialise, so R20's conflict list never misses a booking.
WITH r AS (
    SELECT resource_id FROM resource
     WHERE public_ref = :resourceRef::uuid
       AND provider_id = :providerId::bigint
       FOR UPDATE
)
INSERT INTO availability_exception (public_ref, resource_id, availability_exception_type_id,
                                    starts_at, ends_at, reason)
SELECT :publicRef::uuid, r.resource_id,
       (SELECT availability_exception_type_id FROM availability_exception_type
         WHERE code = :type::text),
       :startsAt::timestamptz, :endsAt::timestamptz, :reason::text
  FROM r
RETURNING availability_exception_id
