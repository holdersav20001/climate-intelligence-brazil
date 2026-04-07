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
  ('amazon',        'Amazon / Amazonia',   'geography'),
  -- Broad sectors (spec-required)
  ('energy',        'Energy',              'sector'),
  ('forest',        'Forests / Deforestation', 'sector'),
  ('agriculture',   'Agriculture / Land Use',  'sector'),
  ('water',         'Water Resources',     'sector'),
  -- Additional policy slugs (spec-required)
  ('carbon-market', 'Carbon Market',       'policy'),
  ('net-zero',      'Net Zero',            'policy'),
  ('just-transition','Just Transition',    'policy'),
  ('loss-damage',   'Loss & Damage',       'policy'),
  ('adaptation',    'Climate Adaptation',  'policy'),
  -- Additional events (spec-required)
  ('unfccc',        'UNFCCC',              'event'),
  ('g20',           'G20',                 'event'),
  ('bilateral',     'Bilateral Agreement', 'event'),
  -- Broad actor types (spec-required)
  ('government',    'Government',          'actor'),
  ('ngo',           'NGO / Civil Society', 'actor'),
  ('business',      'Business / Industry', 'actor'),
  ('finance',       'Finance / Investment','actor'),
  -- Additional geographies (spec-required)
  ('cerrado',       'Cerrado',             'geography'),
  ('atlantic-forest','Atlantic Forest',    'geography'),
  ('pantanal',      'Pantanal',            'geography'),
  ('brazil',        'Brazil',              'geography'),
  ('latam',         'Latin America',       'geography'),
  ('global',        'Global',              'geography')
ON CONFLICT (slug) DO NOTHING;
