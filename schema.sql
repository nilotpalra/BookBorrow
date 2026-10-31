-- ============================================================
-- BookBorrow — Supabase schema
-- Run this in your Supabase project: SQL Editor → New query → Run
-- ============================================================

-- Kids: one row per child in the apartment building
create table if not exists public.kids (
  id            uuid primary key default gen_random_uuid(),
  name          text not null,
  apartment_no  text not null,
  created_at    timestamptz not null default now()
);

-- Books: one row per book in the shared library
create table if not exists public.books (
  id           uuid primary key default gen_random_uuid(),
  title        text not null,
  author       text,
  status       text not null default 'Available'
               check (status in ('Available', 'Borrowed')),
  borrowed_by  uuid references public.kids (id) on delete set null,
  loan_date    date,
  created_at   timestamptz not null default now()
);

-- Indexes for the two lookups the app does most
create index if not exists books_status_idx      on public.books (status);
create index if not exists books_borrowed_by_idx on public.books (borrowed_by);

-- ------------------------------------------------------------
-- Optional sample data — delete this section to start empty
-- ------------------------------------------------------------
insert into public.kids (name, apartment_no) values
  ('Aarav', 'B-204'),
  ('Diya',  'A-101'),
  ('Meera', 'C-310');

insert into public.books (title, author) values
  ('Charlotte''s Web', 'E.B. White'),
  ('The Gruffalo', 'Julia Donaldson'),
  ('Matilda', 'Roald Dahl'),
  ('Harry Potter and the Sorcerer''s Stone', 'J.K. Rowling');

-- ------------------------------------------------------------
-- Row Level Security (optional)
-- Tables created in the SQL Editor have RLS OFF by default, which
-- is fine for a small private app using the anon key. If you want
-- to harden it later, enable RLS and add permissive policies:
--
--   alter table public.kids  enable row level security;
--   alter table public.books enable row level security;
--   create policy "public read/write kids"  on public.kids
--     for all using (true) with check (true);
--   create policy "public read/write books" on public.books
--     for all using (true) with check (true);
-- ------------------------------------------------------------
