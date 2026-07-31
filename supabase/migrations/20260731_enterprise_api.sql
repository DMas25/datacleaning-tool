-- ── Enterprise API — Supabase migration ──────────────────────────────────────
-- Run once in the Supabase SQL editor (or via supabase db push).

-- API keys table (hashed — raw key never stored)
create table if not exists api_keys (
    id           uuid        primary key default gen_random_uuid(),
    key_hash     text        unique not null,
    label        text        not null,
    email        text        not null,
    is_active    boolean     not null default true,
    created_at   timestamptz not null default now(),
    last_used_at timestamptz
);

-- Fast auth lookup by hash
create index if not exists api_keys_key_hash_idx on api_keys (key_hash);

-- Usage log: one row per API call
create table if not exists api_usage_log (
    id             uuid        primary key default gen_random_uuid(),
    api_key_id     uuid        not null references api_keys (id) on delete cascade,
    domain         text        not null,
    rows_processed integer     not null,
    input_format   text        not null check (input_format in ('csv', 'json')),
    requested_at   timestamptz not null default now()
);

-- Reporting indices
create index if not exists api_usage_log_key_idx  on api_usage_log (api_key_id);
create index if not exists api_usage_log_date_idx on api_usage_log (requested_at);

-- Convenience view: monthly usage per key
create or replace view api_usage_monthly as
select
    k.email,
    k.label,
    l.domain,
    date_trunc('month', l.requested_at) as month,
    count(*)                            as calls,
    sum(l.rows_processed)               as total_rows
from api_usage_log l
join api_keys k on k.id = l.api_key_id
group by k.email, k.label, l.domain, date_trunc('month', l.requested_at)
order by month desc, calls desc;
