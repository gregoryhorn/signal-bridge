create table if not exists pilots(
  pilot_id integer primary key,
  name text not null,
  corp_id integer,
  corp_name text,
  alliance_id integer,
  alliance_name text,
  first_seen text,
  last_seen text,
  created_at text,
  updated_at text
);

create table if not exists sightings(
  id integer primary key autoincrement,
  pilot_id integer,
  pilot_name text,
  timestamp text,
  system_name text,
  ship_name text,
  channel text,
  confidence text,
  source text,
  dedupe_key text unique,
  duplicate_count integer default 1,
  created_at text
);

create table if not exists pilot_stats(
  pilot_id integer primary key,
  report_count integer default 0,
  first_seen text,
  last_seen text,
  top_ships_json text,
  top_systems_json text,
  threat_level text,
  threat_reasons_json text,
  updated_at text
);

create table if not exists pilot_flags(
  id integer primary key autoincrement,
  pilot_id integer,
  flag text,
  label text,
  icon text,
  source text,
  confidence text,
  reason text,
  created_at text,
  expires_at text,
  active integer default 1
);

create index if not exists idx_sightings_pilot_time on sightings(pilot_id, timestamp desc);
create index if not exists idx_sightings_system_time on sightings(system_name, timestamp desc);
create index if not exists idx_sightings_ship_time on sightings(ship_name, timestamp desc);
create index if not exists idx_sightings_channel_time on sightings(channel, timestamp desc);
create index if not exists idx_sightings_time on sightings(timestamp desc);
create index if not exists idx_pilot_flags_pilot_active on pilot_flags(pilot_id, active);
