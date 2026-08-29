-- =============================================================================
-- Appointment Booking API - database schema
-- PostgreSQL 13+
--
-- Run with:  psql -U <user> -d appointment_db -f schema.sql
--
-- This script is transactional: if anything fails, nothing is applied.
-- =============================================================================

BEGIN;

-- Required so an exclusion constraint can compare provider_id/customer_id with
-- "=" inside a GiST index. Without it, the double-booking constraints below
-- cannot be created. May require superuser on first run.
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- PostgreSQL ships range types for timestamps and dates, but not for TIME.
-- We need one to stop a provider declaring overlapping working hours.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'timerange') THEN
        CREATE TYPE timerange AS RANGE (subtype = time);
    END IF;
END
$$;


-- =============================================================================
-- users
-- Every human in the system. Role decides what they may do; identity, login
-- and password handling are shared by all three roles.
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          TEXT        NOT NULL,
    email         TEXT        NOT NULL,
    password_hash TEXT        NOT NULL,
    role          TEXT        NOT NULL DEFAULT 'customer',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT users_email_unique UNIQUE (email),
    CONSTRAINT users_name_not_blank CHECK (length(btrim(name)) > 0),

    -- Emails are stored lowercase so that Bob@x.com and bob@x.com collide on
    -- the UNIQUE constraint. Normalise in the application before inserting.
    CONSTRAINT users_email_lowercase CHECK (email = lower(email)),
    CONSTRAINT users_email_shape     CHECK (email LIKE '_%@_%._%'),

    CONSTRAINT users_role_valid CHECK (role IN ('customer', 'provider', 'admin')),

    -- Tripwire against ever storing a plaintext password: every bcrypt/argon2
    -- hash is 50+ chars, and no sane plaintext password reaches 20.
    CONSTRAINT users_password_is_hashed CHECK (length(password_hash) >= 20)
);


-- =============================================================================
-- providers
-- The professional profile attached to a user. Kept out of `users` because
-- these columns are meaningless for customers and admins.
-- =============================================================================
CREATE TABLE IF NOT EXISTS providers (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- UNIQUE => one provider profile per user, enforced by the database.
    -- CASCADE => deleting the user removes the profile; a profile with no
    -- owner is meaningless.
    user_id        BIGINT      NOT NULL UNIQUE
                   REFERENCES users (id) ON DELETE CASCADE,

    specialization TEXT        NOT NULL,
    description    TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT providers_specialization_not_blank
        CHECK (length(btrim(specialization)) > 0)
);


-- =============================================================================
-- services
-- What a provider sells. duration_minutes is what makes slot generation
-- possible - it defines how long a booking of this service occupies.
-- =============================================================================
CREATE TABLE IF NOT EXISTS services (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider_id      BIGINT      NOT NULL
                     REFERENCES providers (id) ON DELETE CASCADE,
    name             TEXT        NOT NULL,
    description      TEXT,
    duration_minutes INTEGER     NOT NULL,

    -- NUMERIC, never FLOAT: binary floating point cannot represent 0.10
    -- exactly, and money that drifts by a cent is a real bug.
    price            NUMERIC(10, 2) NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT services_name_not_blank CHECK (length(btrim(name)) > 0),
    CONSTRAINT services_duration_positive
        CHECK (duration_minutes > 0 AND duration_minutes <= 480),
    CONSTRAINT services_price_non_negative CHECK (price >= 0),

    -- One provider cannot list the same service name twice.
    CONSTRAINT services_provider_name_unique UNIQUE (provider_id, name),

    -- Not redundant with the primary key: this is the target of the composite
    -- foreign key in `appointments`, which is what stops a customer booking
    -- provider A for a service that belongs to provider B.
    CONSTRAINT services_id_provider_unique UNIQUE (id, provider_id)
);


-- =============================================================================
-- availability
-- A provider's recurring weekly working hours ("Mondays 09:00-17:00").
-- A rule, not a calendar: one row covers every Monday, forever.
--
-- day_of_week uses the ISO numbering 1 = Monday .. 7 = Sunday, matching
-- PostgreSQL's EXTRACT(ISODOW FROM date), so availability can be joined
-- against a date without off-by-one translation in the application.
-- =============================================================================
CREATE TABLE IF NOT EXISTS availability (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider_id BIGINT   NOT NULL
                REFERENCES providers (id) ON DELETE CASCADE,
    day_of_week SMALLINT NOT NULL,
    start_time  TIME     NOT NULL,
    end_time    TIME     NOT NULL,

    CONSTRAINT availability_day_valid CHECK (day_of_week BETWEEN 1 AND 7),
    CONSTRAINT availability_time_order CHECK (end_time > start_time),

    -- A provider must not declare Mon 09:00-17:00 and Mon 13:00-15:00, which
    -- would double-count the afternoon when generating bookable slots.
    -- '[)' semantics: 09:00-12:00 and 12:00-17:00 are adjacent, not overlapping.
    CONSTRAINT availability_no_overlap EXCLUDE USING gist (
        provider_id WITH =,
        day_of_week WITH =,
        timerange(start_time, end_time, '[)') WITH &&
    )
);


-- =============================================================================
-- appointments
-- The actual bookings. The only table where concurrency can cause real damage,
-- so the correctness guarantee lives here in the database - see the exclusion
-- constraints at the bottom.
-- =============================================================================
CREATE TABLE IF NOT EXISTS appointments (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- RESTRICT on all three: appointment history is a financial and legal
    -- record. Deactivate a user instead of deleting them.
    customer_id      BIGINT      NOT NULL
                     REFERENCES users (id) ON DELETE RESTRICT,
    provider_id      BIGINT      NOT NULL
                     REFERENCES providers (id) ON DELETE RESTRICT,
    service_id       BIGINT      NOT NULL,

    appointment_date DATE        NOT NULL,
    start_time       TIME        NOT NULL,
    end_time         TIME        NOT NULL,
    status           TEXT        NOT NULL DEFAULT 'pending',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Derived by PostgreSQL from the columns above, stored on disk, and always
    -- in sync because the application cannot write them. They exist so the
    -- exclusion constraints below have a single timestamp range to compare.
    starts_at TIMESTAMP GENERATED ALWAYS AS (appointment_date + start_time) STORED,
    ends_at   TIMESTAMP GENERATED ALWAYS AS (appointment_date + end_time)   STORED,

    CONSTRAINT appointments_time_order CHECK (end_time > start_time),
    CONSTRAINT appointments_status_valid
        CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed')),

    -- Composite FK: the service must belong to THIS provider. Two independent
    -- foreign keys would allow booking provider A for provider B's service.
    CONSTRAINT appointments_service_belongs_to_provider
        FOREIGN KEY (service_id, provider_id)
        REFERENCES services (id, provider_id) ON DELETE RESTRICT,

    -- -------------------------------------------------------------------
    -- DOUBLE-BOOKING PREVENTION
    --
    -- "SELECT to check the slot is free, then INSERT" is broken: two
    -- concurrent requests both read a free slot before either writes, and
    -- both succeed. That cannot be fixed in application code, because the
    -- check and the insert are separate round trips.
    --
    -- This constraint makes overlapping bookings unrepresentable. PostgreSQL
    -- locks the range during insert, so the loser of the race fails with an
    -- ExclusionViolation - catch it in the API and return HTTP 409.
    --
    -- tsrange defaults to '[)', so a 10:00-11:00 and an 11:00-12:00 booking
    -- do NOT overlap: back-to-back appointments work correctly.
    --
    -- The WHERE clause means cancelled appointments release their slot
    -- immediately, with no cleanup job.
    -- -------------------------------------------------------------------
    CONSTRAINT appointments_no_provider_double_booking EXCLUDE USING gist (
        provider_id WITH =,
        tsrange(starts_at, ends_at) WITH &&
    ) WHERE (status IN ('pending', 'confirmed')),

    -- Same protection from the other side: one customer cannot be in two
    -- places at once.
    CONSTRAINT appointments_no_customer_double_booking EXCLUDE USING gist (
        customer_id WITH =,
        tsrange(starts_at, ends_at) WITH &&
    ) WHERE (status IN ('pending', 'confirmed'))
);


-- =============================================================================
-- Indexes
--
-- Primary keys, UNIQUE constraints and the EXCLUDE constraints already create
-- indexes. These cover the remaining query patterns the API will actually use.
-- =============================================================================

-- "show this provider's calendar for a date / date range" - the hottest query
-- in the system, run on every availability lookup.
CREATE INDEX IF NOT EXISTS idx_appointments_provider_date
    ON appointments (provider_id, appointment_date);

-- "show me my bookings, newest first"
CREATE INDEX IF NOT EXISTS idx_appointments_customer_date
    ON appointments (customer_id, appointment_date DESC);

-- Partial index: admin dashboards and reminder jobs only ever scan active
-- appointments, so cancelled/completed rows are kept out of the index.
CREATE INDEX IF NOT EXISTS idx_appointments_active_status
    ON appointments (status, appointment_date)
    WHERE status IN ('pending', 'confirmed');

CREATE INDEX IF NOT EXISTS idx_appointments_service
    ON appointments (service_id);

CREATE INDEX IF NOT EXISTS idx_services_provider
    ON services (provider_id);

CREATE INDEX IF NOT EXISTS idx_availability_provider_day
    ON availability (provider_id, day_of_week);

-- Browsing/filtering the provider directory.
CREATE INDEX IF NOT EXISTS idx_providers_specialization
    ON providers (specialization);

COMMIT;


-- =============================================================================
-- Rules the database cannot enforce - these belong in the service layer:
--
--   * appointments.customer_id must reference a user whose role = 'customer'.
--     (A cross-table CHECK is not possible in PostgreSQL without triggers.)
--   * An appointment must fall inside the provider's availability window.
--   * end_time should equal start_time + the service's duration_minutes.
--   * Bookings must not be in the past.
--   * Status transitions: pending -> confirmed -> completed, with cancelled
--     reachable from pending/confirmed but nothing reachable from cancelled
--     or completed.
--
-- Deliberate omissions, to be added when a feature needs them:
--   * updated_at columns (no update-tracking requirement yet)
--   * users.is_active for soft deactivation
--   * a `slots` table - slots are derived from availability minus booked
--     appointments; materialising them creates a second source of truth
--   * one-off date overrides (holidays, sick days)
-- =============================================================================
