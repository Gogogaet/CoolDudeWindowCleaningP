create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null default '',
  business_name text not null default 'Cool Dudes Window Cleaning',
  email text not null default '',
  phone text not null default '',
  monthly_goal numeric(12,2) not null default 1000,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.customers (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  phone text not null default '',
  email text not null default '',
  address text not null default '',
  status text not null default 'Active',
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.bookings (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  customer_id uuid references public.customers(id) on delete set null,
  customer_name text not null default '',
  service_date date not null,
  service_time time not null default '09:00',
  service text not null default 'Exterior window cleaning',
  amount numeric(12,2) not null default 0,
  status text not null default 'Booked',
  address text not null default '',
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.leads (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  customer_id uuid references public.customers(id) on delete set null,
  name text not null default '',
  phone text not null default '',
  email text not null default '',
  address text not null default '',
  source text not null default 'Door-to-door',
  status text not null default 'New',
  estimated_value numeric(12,2) not null default 0,
  next_followup date,
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.doorsteps (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  address text not null default '',
  lat double precision,
  lng double precision,
  status text not null default 'not',
  note text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.territories (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  name text not null default 'Fremont Service Area',
  geojson jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.expenses (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  expense_date date not null default current_date,
  category text not null default 'Other',
  amount numeric(12,2) not null default 0,
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists customers_owner_id_idx on public.customers(owner_id);
create index if not exists bookings_owner_id_date_idx on public.bookings(owner_id, service_date);
create index if not exists leads_owner_id_followup_idx on public.leads(owner_id, next_followup);
create index if not exists doorsteps_owner_id_idx on public.doorsteps(owner_id);
create index if not exists territories_owner_id_idx on public.territories(owner_id);
create index if not exists expenses_owner_id_date_idx on public.expenses(owner_id, expense_date);

alter table public.profiles enable row level security;
alter table public.customers enable row level security;
alter table public.bookings enable row level security;
alter table public.leads enable row level security;
alter table public.doorsteps enable row level security;
alter table public.territories enable row level security;
alter table public.expenses enable row level security;

grant select, insert, update, delete on public.profiles to authenticated;
grant select, insert, update, delete on public.customers to authenticated;
grant select, insert, update, delete on public.bookings to authenticated;
grant select, insert, update, delete on public.leads to authenticated;
grant select, insert, update, delete on public.doorsteps to authenticated;
grant select, insert, update, delete on public.territories to authenticated;
grant select, insert, update, delete on public.expenses to authenticated;

drop policy if exists "profiles own rows" on public.profiles;
create policy "profiles own rows" on public.profiles
for all to authenticated using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists "customers own rows" on public.customers;
create policy "customers own rows" on public.customers
for all to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid());

drop policy if exists "bookings own rows" on public.bookings;
create policy "bookings own rows" on public.bookings
for all to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid());

drop policy if exists "leads own rows" on public.leads;
create policy "leads own rows" on public.leads
for all to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid());

drop policy if exists "doorsteps own rows" on public.doorsteps;
create policy "doorsteps own rows" on public.doorsteps
for all to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid());

drop policy if exists "territories own rows" on public.territories;
create policy "territories own rows" on public.territories
for all to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid());

drop policy if exists "expenses own rows" on public.expenses;
create policy "expenses own rows" on public.expenses
for all to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid());

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, full_name, business_name, email)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', ''),
    coalesce(new.raw_user_meta_data->>'business_name', 'Cool Dudes Window Cleaning'),
    coalesce(new.email, '')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_updated_at on public.profiles;
create trigger profiles_updated_at before update on public.profiles for each row execute procedure public.set_updated_at();
drop trigger if exists customers_updated_at on public.customers;
create trigger customers_updated_at before update on public.customers for each row execute procedure public.set_updated_at();
drop trigger if exists bookings_updated_at on public.bookings;
create trigger bookings_updated_at before update on public.bookings for each row execute procedure public.set_updated_at();
drop trigger if exists leads_updated_at on public.leads;
create trigger leads_updated_at before update on public.leads for each row execute procedure public.set_updated_at();
drop trigger if exists doorsteps_updated_at on public.doorsteps;
create trigger doorsteps_updated_at before update on public.doorsteps for each row execute procedure public.set_updated_at();
drop trigger if exists territories_updated_at on public.territories;
create trigger territories_updated_at before update on public.territories for each row execute procedure public.set_updated_at();
drop trigger if exists expenses_updated_at on public.expenses;
create trigger expenses_updated_at before update on public.expenses for each row execute procedure public.set_updated_at();
