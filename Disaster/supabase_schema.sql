create schema if not exists public;

-- Ensure role constraint and emergency head flag are present on users
alter table if exists public.users drop constraint if exists users_role_check;
alter table if exists public.users add constraint users_role_check check (role in ('user', 'admin', 'government', 'emergency'));
alter table if exists public.users add column if not exists is_emergency_head boolean default false;

-- User types with role-based access
create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  name text not null,
  email text not null unique,
  phone text not null,
  place text,
  city text,
  state text,
  pincode text,
  role text default 'user' check (role in ('user', 'admin', 'government', 'emergency')),
  is_emergency_head boolean default false,
  created_at timestamptz default now()
);

-- Incidents reported by users
create table if not exists public.incidents (
  id bigserial primary key,
  user_id uuid not null references public.users(id) on delete cascade,
  location text not null,
  address text,
  city text,
  state text,
  cause text,
  pincode text not null,
  description text not null,
  status text default 'pending' check (status in ('pending', 'resolved')),
  timestamp timestamptz default now()
);

-- Ensure incidents columns exist even if table pre-existed
alter table if exists public.incidents add column if not exists address text;
alter table if exists public.incidents add column if not exists city text;
alter table if exists public.incidents add column if not exists state text;
alter table if exists public.incidents add column if not exists cause text;
alter table if exists public.incidents add column if not exists pincode text;

-- Backfill/ensure pincode not null for existing data
update public.incidents set pincode = coalesce(pincode, '000000') where pincode is null;
alter table if exists public.incidents alter column pincode set not null;

-- Donations from users
create table if not exists public.donations (
  id bigserial primary key,
  user_id uuid not null references public.users(id) on delete cascade,
  amount numeric(10,2) not null,
  method text not null,
  timestamp timestamptz default now()
);

-- Shelters for emergency situations
create table if not exists public.shelters (
  id bigserial primary key,
  name text not null,
  location text not null,
  capacity integer not null,
  available integer not null default 0,
  created_at timestamptz default now()
);

-- Announcements from admins
create table if not exists public.announcements (
  id bigserial primary key,
  admin_id uuid not null references public.users(id) on delete cascade,
  title text not null,
  description text not null,
  severity text default 'medium' check (severity in ('low', 'medium', 'high', 'critical')),
  timestamp timestamptz default now()
);

-- Requests from admin to government
create table if not exists public.requests (
  id bigserial primary key,
  admin_id uuid not null references public.users(id) on delete cascade,
  incident_id bigint not null references public.incidents(id) on delete cascade,
  status text default 'pending' check (status in ('pending', 'accepted', 'rejected')),
  timestamp timestamptz default now()
);

-- Team allocations by government
create table if not exists public.team_allocations (
  id bigserial primary key,
  gov_id uuid not null references public.users(id) on delete cascade,
  request_id bigint not null references public.requests(id) on delete cascade,
  team_name text not null,
  assigned_at timestamptz default now()
);

-- Medical requests from users
create table if not exists public.medical_requests (
  id bigserial primary key,
  user_id uuid not null references public.users(id) on delete cascade,
  request_type text not null,
  description text,
  urgency text,
  status text default 'Pending',
  created_at timestamptz default now()
);

-- Resources allocated to shelters
create table if not exists public.resources (
  id bigserial primary key,
  gov_id uuid not null references public.users(id) on delete cascade,
  shelter_id bigint not null references public.shelters(id) on delete cascade,
  food integer default 0,
  water integer default 0,
  medicine integer default 0,
  allocated_at timestamptz default now()
);

-- Weather data for announcements
create table if not exists public.weather_data (
  id bigserial primary key,
  location text not null,
  temperature numeric(5,2),
  humidity integer,
  wind_speed numeric(5,2),
  weather_condition text,
  is_extreme boolean default false,
  weather_alert text,
  fetched_at timestamptz default now()
);

-- Update announcements table to include weather data
alter table if exists public.announcements 
add column if not exists weather_data_id bigint references public.weather_data(id),
add column if not exists is_weather_alert boolean default false;

-- Normalize FK from announcements → weather_data to avoid duplicate relationships
-- Drop any legacy/extra FK that may have been created elsewhere
alter table if exists public.announcements drop constraint if exists announcements_weather_data_fk;
-- Ensure the canonical FK exists with a stable name
do $$
begin
  if not exists (
    select 1 from information_schema.table_constraints tc
    where tc.constraint_name = 'announcements_weather_data_id_fkey'
      and tc.table_name = 'announcements') then
    alter table public.announcements
    add constraint announcements_weather_data_id_fkey
    foreign key (weather_data_id) references public.weather_data(id);
  end if;
end $$;

-- Helpful index for embeds/filters
create index if not exists idx_announcements_weather_data_id on public.announcements(weather_data_id);

-- Emergency response: teams, assignments, and updates
create table if not exists public.emergency_assignments (
  id bigserial primary key,
  request_id bigint not null references public.requests(id) on delete cascade,
  team_name text not null,
  team_type text not null check (team_type in ('Rescue', 'FoodSupply', 'Escort', 'Liaison')),
  team_lead_id uuid not null references public.users(id) on delete cascade,
  location_text text,
  status text default 'Assigned' check (status in ('Assigned', 'Enroute', 'OnSite', 'Completed', 'NeedsSupport')),
  notes text,
  assigned_at timestamptz default now()
);

create table if not exists public.emergency_updates (
  id bigserial primary key,
  assignment_id bigint not null references public.emergency_assignments(id) on delete cascade,
  author_id uuid not null references public.users(id) on delete cascade,
  reached boolean,
  rescued_count integer,
  need_more_support boolean,
  severity text,
  critical_count integer,
  need_medical boolean,
  message text,
  created_at timestamptz default now()
);

-- Emergency units under a head (15 typical units with categories)
create table if not exists public.emergency_units (
  id bigserial primary key,
  head_id uuid not null references public.users(id) on delete cascade,
  unit_name text not null,
  unit_category text not null check (unit_category in ('Rescue', 'Escort', 'Medical', 'ResourceCollector')),
  status text not null default 'Free' check (status in ('Free', 'Busy', 'Offline')),
  last_update timestamptz default now()
);

-- Government to emergency head notifications per request
create table if not exists public.emergency_notifications (
  id bigserial primary key,
  request_id bigint not null references public.requests(id) on delete cascade,
  gov_id uuid not null references public.users(id) on delete cascade,
  head_id uuid not null references public.users(id) on delete cascade,
  status text not null default 'Pending' check (status in ('Pending', 'Acknowledged', 'Completed')),
  created_at timestamptz default now()
);

-- Insert sample shelters
insert into public.shelters (name, location, capacity, available) values
('Central Emergency Shelter', 'Downtown District', 200, 150),
('North Community Center', 'North Side', 100, 80),
('South Relief Center', 'South District', 150, 120),
('East Emergency Hub', 'East Side', 120, 90)
on conflict do nothing;

-- Insert sample announcements (only if admin exists)
insert into public.announcements (admin_id, title, description, severity) 
select 
  u.id,
  'Weather Alert',
  'Heavy rain expected in the next 24 hours. Please stay indoors.',
  'high'
from public.users u 
where u.role = 'admin' 
limit 1
on conflict do nothing;

-- Optional: enable RLS and add proper policies prior to production
-- alter table public.users enable row level security;
-- alter table public.incidents enable row level security;
-- alter table public.donations enable row level security;
-- alter table public.shelters enable row level security;
-- alter table public.announcements enable row level security;
-- alter table public.requests enable row level security;
-- alter table public.team_allocations enable row level security;
-- alter table public.resources enable row level security;
-- alter table public.medical_requests enable row level security;