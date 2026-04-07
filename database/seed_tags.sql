-- Core tag taxonomy for the Climate Intelligence Platform
-- Apply via: docker compose exec postgres psql -U climate_intel -d climate_intel -f /docker-entrypoint-initdb.d/seed_tags.sql
-- Or: docker compose exec postgres psql -U climate_intel -d climate_intel < database/seed_tags.sql

SET search_path TO climate;

INSERT INTO tags (slug, label, category) VALUES
  -- Fossil fuel sectors
  ('coal',          'Coal',                'sector'),
  ('gas',           'Natural Gas',         'sector'),
  ('oil',           'Oil / Petroleum',     'sector'),
  ('lng',           'LNG',                 'sector'),
  ('pre-sal',       'Pre-Sal',             'sector'),
  -- Renewable sectors
  ('solar',         'Solar Energy',        'sector'),
  ('wind',          'Wind Energy',         'sector'),
  ('hydro',         'Hydropower',          'sector'),
  ('hydrogen',      'Green Hydrogen',      'sector'),
  ('biomass',       'Biomass / Ethanol',   'sector'),
  ('storage',       'Energy Storage',      'sector'),
  ('offshore-wind', 'Offshore Wind',       'sector'),
  -- Policy & governance
  ('ndc',           'NDC / Climate Target','policy'),
  ('regulation',    'Regulation',          'policy'),
  ('auction',       'Energy Auction',      'policy'),
  ('licensing',     'Licensing',           'policy'),
  ('climate-finance','Climate Finance',    'policy'),
  ('transition',    'Energy Transition',   'policy'),
  -- Key events
  ('cop30',         'COP30 Belem',         'event'),
  ('cop29',         'COP29',               'event'),
  -- Key actors
  ('petrobras',     'Petrobras',           'actor'),
  ('bndes',         'BNDES',               'actor'),
  ('aneel',         'ANEEL',               'actor'),
  ('anp',           'ANP',                 'actor'),
  ('mme',           'MME',                 'actor'),
  ('ibama',         'IBAMA',               'actor'),
  -- Geography / social
  ('indigenous',    'Indigenous Territory','policy'),
  ('amazon',        'Amazon / Amazonia',   'geography')
ON CONFLICT (slug) DO NOTHING;
