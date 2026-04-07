-- database/seed_south_america_sources.sql
-- South America energy sources — Colombia, Argentina, Chile
-- Apply: docker compose exec postgres psql -U climate_intel -d climate_intel -f /seeds/seed_south_america_sources.sql
-- id omitted: PostgreSQL generates UUID. Conflict target is url (UNIQUE).

SET search_path TO climate;

INSERT INTO sources (url, name, feed_type, status, country_code, language, discovered_by, credibility_tier) VALUES

-- Colombia
('https://www.minenergia.gov.co/noticias', 'MinEnergia Colombia', 'html', 'active', 'CO', 'es', 'manual', 'high'),
('https://www1.upme.gov.co/Noticias', 'UPME Colombia', 'html', 'active', 'CO', 'es', 'manual', 'high'),
('https://news.google.com/rss/search?q=energia+colombia&hl=es&gl=CO&ceid=CO:es', 'Google News — Energia Colombia', 'google_news', 'active', 'CO', 'es', 'manual', 'medium'),
('https://www.energiaestrategica.com/feed/', 'Energía Estratégica', 'rss', 'active', 'CO', 'es', 'manual', 'high'),

-- Argentina
('https://www.argentina.gob.ar/noticias/secretaria-de-energia', 'Secretaría de Energía Argentina', 'html', 'active', 'AR', 'es', 'manual', 'high'),
('https://news.google.com/rss/search?q=energia+argentina&hl=es&gl=AR&ceid=AR:es', 'Google News — Energia Argentina', 'google_news', 'active', 'AR', 'es', 'manual', 'medium'),
('https://www.iapg.org.ar/noticias', 'IAPG Argentina', 'html', 'candidate', 'AR', 'es', 'manual', 'medium'),

-- Chile
('https://www.energia.gob.cl/noticias', 'Ministerio de Energía Chile', 'html', 'active', 'CL', 'es', 'manual', 'high'),
('https://www.cne.cl/noticias/', 'CNE Chile', 'html', 'active', 'CL', 'es', 'manual', 'high'),
('https://news.google.com/rss/search?q=energia+chile&hl=es&gl=CL&ceid=CL:es', 'Google News — Energia Chile', 'google_news', 'active', 'CL', 'es', 'manual', 'medium'),

-- BNAmericas — Latin America cross-country
('https://www.bnamericas.com/en/news/power', 'BNAmericas Power', 'html', 'active', 'BR', 'en', 'manual', 'medium')

ON CONFLICT (url) DO NOTHING;
