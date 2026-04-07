-- database/seed.sql
-- Seed data: tags taxonomy, countries, 38 monitored sources
-- Applied by docker-entrypoint-initdb.d/02_seed.sql after schema.sql

SET search_path TO climate;

-- ── Countries ──────────────────────────────────────────────────────────────

INSERT INTO countries (code, name, region) VALUES
  ('BR', 'Brazil', 'south_america'),
  ('CO', 'Colombia', 'south_america'),
  ('AR', 'Argentina', 'south_america'),
  ('CL', 'Chile', 'south_america'),
  ('PE', 'Peru', 'south_america'),
  ('DE', 'Germany', 'europe'),
  ('GB', 'United Kingdom', 'europe'),
  ('ES', 'Spain', 'europe'),
  ('FR', 'France', 'europe'),
  ('NL', 'Netherlands', 'europe'),
  ('PL', 'Poland', 'europe'),
  ('ID', 'Indonesia', 'asia'),
  ('IN', 'India', 'asia'),
  ('JP', 'Japan', 'asia'),
  ('KR', 'South Korea', 'asia'),
  ('ZA', 'South Africa', 'africa'),
  ('NG', 'Nigeria', 'africa'),
  ('KE', 'Kenya', 'africa'),
  ('MA', 'Morocco', 'africa')
ON CONFLICT (code) DO NOTHING;

-- ── Tag taxonomy ───────────────────────────────────────────────────────────

INSERT INTO tags (slug, category, label) VALUES
  -- sector
  ('coal',      'sector', 'Coal'),
  ('gas',       'sector', 'Natural Gas'),
  ('oil',       'sector', 'Oil'),
  ('solar',     'sector', 'Solar'),
  ('wind',      'sector', 'Wind'),
  ('hydrogen',  'sector', 'Hydrogen'),
  ('hydro',     'sector', 'Hydropower'),
  ('nuclear',   'sector', 'Nuclear'),
  ('storage',   'sector', 'Energy Storage'),
  ('biofuel',   'sector', 'Biofuel'),
  ('biomass',   'sector', 'Biomass'),
  -- geography (regional)
  ('south_america', 'geography', 'South America'),
  ('europe',        'geography', 'Europe'),
  ('asia',          'geography', 'Asia'),
  ('africa',        'geography', 'Africa'),
  ('global',        'geography', 'Global'),
  -- actor_type
  ('government',    'actor_type', 'Government'),
  ('ngo',           'actor_type', 'NGO'),
  ('industry',      'actor_type', 'Industry'),
  ('international', 'actor_type', 'International Organisation'),
  ('media',         'actor_type', 'Media'),
  ('academic',      'actor_type', 'Academic'),
  -- policy_stage
  ('proposed',      'policy_stage', 'Proposed'),
  ('consultation',  'policy_stage', 'Open for Consultation'),
  ('enacted',       'policy_stage', 'Enacted'),
  ('repealed',      'policy_stage', 'Repealed'),
  ('under_review',  'policy_stage', 'Under Review'),
  -- topic
  ('stranded_asset',    'topic', 'Stranded Assets'),
  ('just_transition',   'topic', 'Just Transition'),
  ('permitting',        'topic', 'Permitting'),
  ('financing',         'topic', 'Financing'),
  ('cop30',             'topic', 'COP30'),
  ('ndc',               'topic', 'NDC'),
  ('auction',           'topic', 'Energy Auction'),
  ('licensing',         'topic', 'Licensing'),
  ('phase_out',         'topic', 'Fossil Fuel Phase-Out'),
  ('green_hydrogen',    'topic', 'Green Hydrogen'),
  ('offshore_wind',     'topic', 'Offshore Wind'),
  -- urgency
  ('breaking',    'urgency', 'Breaking'),
  ('this_week',   'urgency', 'This Week'),
  ('this_month',  'urgency', 'This Month'),
  ('ongoing',     'urgency', 'Ongoing'),
  -- company
  ('petrobras',   'company', 'Petrobras'),
  ('bndes',       'company', 'BNDES'),
  ('aneel',       'company', 'ANEEL'),
  ('anp',         'company', 'ANP'),
  ('mme',         'company', 'MME'),
  ('enel',        'company', 'Enel'),
  ('total',       'company', 'TotalEnergies'),
  ('shell',       'company', 'Shell'),
  ('bp',          'company', 'BP'),
  ('equinor',     'company', 'Equinor'),
  ('world_bank',  'company', 'World Bank'),
  ('ifc',         'company', 'IFC'),
  ('idb',         'company', 'IDB'),
  ('vale',        'company', 'Vale'),
  ('eletrobras',  'company', 'Eletrobras')
ON CONFLICT (slug) DO NOTHING;

-- ── Sources — RSS feeds, GDELT, Yahoo Finance, hash monitors ───────────────

INSERT INTO sources (name, url, feed_url, country_code, source_type, language, fetch_frequency) VALUES
  -- Specialist renewable energy publications
  ('Recharge News',          'https://rechargenews.com',          'https://services.rechargenews.com/app/rss',                           NULL, 'rss', 'en', 'hourly'),
  ('PV Magazine Global',     'https://pv-magazine.com',           'https://pv-magazine.com/feed',                                       NULL, 'rss', 'en', 'hourly'),
  ('PV Magazine Brasil',     'https://pv-magazine.com.br',        'https://pv-magazine.com.br/feed',                                    'BR', 'rss', 'pt', 'hourly'),
  ('PV Tech',                'https://pvtech.org',                'https://pvtech.org/feed',                                            NULL, 'rss', 'en', 'hourly'),
  ('Renewables Now',         'https://renewablesnow.com',         'https://renewablesnow.com/feed',                                     NULL, 'rss', 'en', 'hourly'),
  ('Windpower Monthly',      'https://windpowermonthly.com',      'https://windpowermonthly.com/rss',                                   NULL, 'rss', 'en', 'hourly'),
  ('Energy Storage News',    'https://energy-storage.news',       'https://energy-storage.news/feed',                                   NULL, 'rss', 'en', 'hourly'),
  ('CleanTechnica',          'https://cleantechnica.com',         'https://cleantechnica.com/feed',                                     NULL, 'rss', 'en', 'hourly'),
  ('Carbon Brief',           'https://carbonbrief.org',           'https://carbonbrief.org/feed',                                       NULL, 'rss', 'en', 'hourly'),
  ('Ember Energy',           'https://ember-energy.org',          'https://ember-energy.org/feed',                                      NULL, 'rss', 'en', 'hourly'),
  ('Clean Energy Wire',      'https://cleanenergywire.org',       'https://cleanenergywire.org/feed',                                   NULL, 'rss', 'en', 'hourly'),
  ('Euractiv Energy',        'https://euractiv.com',              'https://euractiv.com/sections/energy/feed',                          NULL, 'rss', 'en', 'hourly'),
  ('H2 View',                'https://h2-view.com',               'https://h2-view.com/feed',                                           NULL, 'rss', 'en', 'hourly'),
  ('Energía Estratégica',    'https://energiastrategica.com',     'https://energiastrategica.com/feed',                                 NULL, 'rss', 'es', 'hourly'),
  ('Energy Monitor',         'https://energymonitor.ai',          'https://energymonitor.ai/feed',                                      NULL, 'rss', 'en', 'hourly'),
  ('RenewEconomy',           'https://reneweconomy.com.au',       'https://reneweconomy.com.au/feed',                                   NULL, 'rss', 'en', 'hourly'),
  ('China Dialogue Energy',  'https://dialogue.earth',            'https://dialogue.earth/en/energy/feed',                              NULL, 'rss', 'en', 'hourly'),
  ('Renewable Energy World', 'https://renewableenergyworld.com',  'https://renewableenergyworld.com/feed',                              NULL, 'rss', 'en', 'hourly'),
  -- Google News RSS (Brazil)
  ('Google News — Brazil Energy EN', 'https://news.google.com/en/brazil', 'https://news.google.com/rss/search?q=brazil+energy&hl=en-US&gl=US', 'BR', 'rss', 'en', 'hourly'),
  ('Google News — Brazil Energy PT', 'https://news.google.com/pt/brazil', 'https://news.google.com/rss/search?q=energia+renovavel+brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419', 'BR', 'rss', 'pt', 'hourly'),
  -- Yahoo Finance ticker feeds
  ('Yahoo Finance — Petrobras (PBR)', 'https://finance.yahoo.com/quote/PBR', 'https://finance.yahoo.com/rss/headline?s=PBR', NULL, 'rss', 'en', 'hourly'),
  ('Yahoo Finance — Vale (VALE)',     'https://finance.yahoo.com/quote/VALE', 'https://finance.yahoo.com/rss/headline?s=VALE', NULL, 'rss', 'en', 'hourly'),
  ('Yahoo Finance — Shell (SHEL)',    'https://finance.yahoo.com/quote/SHEL', 'https://finance.yahoo.com/rss/headline?s=SHEL', NULL, 'rss', 'en', 'hourly'),
  ('Yahoo Finance — Total (TTE)',     'https://finance.yahoo.com/quote/TTE',  'https://finance.yahoo.com/rss/headline?s=TTE',  NULL, 'rss', 'en', 'hourly'),
  -- Reddit RSS
  ('Reddit — r/energy',   'https://reddit.com/r/energy',  'https://www.reddit.com/r/energy/.rss',  NULL, 'rss', 'en', 'hourly'),
  ('Reddit — r/brasil',   'https://reddit.com/r/brasil',  'https://www.reddit.com/r/brasil/.rss',  'BR', 'rss', 'pt', 'hourly'),
  ('Reddit — r/climate',  'https://reddit.com/r/climate', 'https://www.reddit.com/r/climate/.rss', NULL, 'rss', 'en', 'hourly'),
  -- Government hash monitors (Alert agent — 4-hourly)
  ('MME Press Office',  'https://www.gov.br/mme/pt-br/assuntos/noticias', 'https://www.gov.br/mme/pt-br/assuntos/noticias', 'BR', 'hash_monitor', 'pt', '4hourly'),
  ('ANEEL Announcements', 'https://www.aneel.gov.br/sala-de-imprensa',    'https://www.aneel.gov.br/sala-de-imprensa',       'BR', 'hash_monitor', 'pt', '4hourly'),
  ('ANP News',          'https://www.anp.gov.br/noticias',                'https://www.anp.gov.br/noticias',                 'BR', 'hash_monitor', 'pt', '4hourly'),
  ('Petrobras Investor', 'https://www.petrobras.com.br/fatos-e-dados',    'https://www.petrobras.com.br/fatos-e-dados',      'BR', 'hash_monitor', 'pt', '4hourly'),
  ('IBAMA News',        'https://www.ibama.gov.br/noticias',              'https://www.ibama.gov.br/noticias',               'BR', 'hash_monitor', 'pt', '4hourly'),
  -- Nitter RSS (official X/Twitter accounts)
  ('MME Twitter',   'https://nitter.privacydev.net/mme_gov',  'https://nitter.privacydev.net/mme_gov/rss',  'BR', 'social', 'pt', 'hourly'),
  ('ANEEL Twitter', 'https://nitter.privacydev.net/aneel_gov', 'https://nitter.privacydev.net/aneel_gov/rss', 'BR', 'social', 'pt', 'hourly'),
  ('ANP Twitter',   'https://nitter.privacydev.net/anp_gov',  'https://nitter.privacydev.net/anp_gov/rss',  'BR', 'social', 'pt', 'hourly'),
  -- GDELT
  ('GDELT Brazil Energy', 'https://api.gdeltproject.org', 'https://api.gdeltproject.org/api/v2/doc/doc?query=brazil+energy&mode=artlist&maxrecords=25&format=json&timespan=24h', 'BR', 'gdelt', 'en', 'hourly')
ON CONFLICT (url) DO NOTHING;

-- ── Dev tenant (local auth testing) ──────────────────────────────────────────
INSERT INTO tenants (name, email, plan, countries, active)
VALUES ('Climate Intelligence Dev', 'dev@climateintel.br', 'starter', ARRAY['BR'], true)
ON CONFLICT (email) DO NOTHING;
