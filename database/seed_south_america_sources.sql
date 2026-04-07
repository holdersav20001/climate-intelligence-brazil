SET search_path TO climate;

INSERT INTO sources (id, url, name, feed_type, status, country_code, language, discovered_by, credibility_tier) VALUES

-- Colombia
('src-co-minenergia',    'https://www.minenergia.gov.co/noticias', 'MinEnergia Colombia', 'html', 'active', 'CO', 'es', 'manual', 'high'),
('src-co-upme',          'https://www1.upme.gov.co/Noticias', 'UPME Colombia', 'html', 'active', 'CO', 'es', 'manual', 'high'),
('src-co-energia-gnews', 'https://news.google.com/rss/search?q=energia+colombia&hl=es&gl=CO&ceid=CO:es', 'Google News — Energia Colombia', 'google_news', 'active', 'CO', 'es', 'manual', 'medium'),
('src-co-estrategica',   'https://www.energiaestrategica.com/feed/', 'Energía Estratégica', 'rss', 'active', 'CO', 'es', 'manual', 'high'),

-- Argentina
('src-ar-secenergia',    'https://www.argentina.gob.ar/noticias/secretaria-de-energia', 'Secretaría de Energía Argentina', 'html', 'active', 'AR', 'es', 'manual', 'high'),
('src-ar-energia-gnews', 'https://news.google.com/rss/search?q=energia+argentina&hl=es&gl=AR&ceid=AR:es', 'Google News — Energia Argentina', 'google_news', 'active', 'AR', 'es', 'manual', 'medium'),
('src-ar-iapg',          'https://www.iapg.org.ar/noticias', 'IAPG Argentina', 'html', 'candidate', 'AR', 'es', 'manual', 'medium'),
('src-ar-estrategica',   'https://www.energiaestrategica.com/feed/', 'Energía Estratégica (AR)', 'rss', 'active', 'AR', 'es', 'manual', 'high'),

-- Chile
('src-cl-minenergia',    'https://www.energia.gob.cl/noticias', 'Ministerio de Energía Chile', 'html', 'active', 'CL', 'es', 'manual', 'high'),
('src-cl-cne',           'https://www.cne.cl/noticias/', 'CNE Chile', 'html', 'active', 'CL', 'es', 'manual', 'high'),
('src-cl-energia-gnews', 'https://news.google.com/rss/search?q=energia+chile&hl=es&gl=CL&ceid=CL:es', 'Google News — Energia Chile', 'google_news', 'active', 'CL', 'es', 'manual', 'medium'),
('src-cl-estrategica',   'https://www.energiaestrategica.com/feed/', 'Energía Estratégica (CL)', 'rss', 'active', 'CL', 'es', 'manual', 'high'),

-- BNAmericas — Latin America cross-country
('src-latam-bnamericas',  'https://www.bnamericas.com/en/news/power', 'BNAmericas Power', 'html', 'active', 'BR', 'en', 'manual', 'medium')

ON CONFLICT (id) DO NOTHING;
