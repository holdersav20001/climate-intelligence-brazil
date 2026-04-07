-- database/seed_europe_sources.sql
-- Europe energy sources — Germany, UK, Spain, France
-- Apply: docker compose exec postgres psql -U climate_intel -d climate_intel -f /seeds/seed_europe_sources.sql
-- id omitted: PostgreSQL generates UUID. Conflict target is url (UNIQUE).

SET search_path TO climate;

INSERT INTO sources (url, name, feed_type, status, country_code, language, discovered_by, credibility_tier) VALUES

-- Germany
('https://www.bmwk.de/Navigation/EN/Press/press-releases.html', 'BMWK Germany (English)', 'html', 'active', 'DE', 'en', 'manual', 'high'),
('https://www.cleanenergywire.org/rss.xml', 'Clean Energy Wire', 'rss', 'active', 'DE', 'en', 'manual', 'high'),
('https://news.google.com/rss/search?q=energiewende&hl=de&gl=DE&ceid=DE:de', 'Google News — Energiewende', 'google_news', 'active', 'DE', 'de', 'manual', 'medium'),
('https://news.google.com/rss/search?q=german+energy+policy&hl=en&gl=DE&ceid=DE:en', 'Google News — German Energy Policy', 'google_news', 'active', 'DE', 'en', 'manual', 'medium'),
('https://www.euractiv.com/feed/', 'Euractiv', 'rss', 'active', 'DE', 'en', 'manual', 'high'),

-- United Kingdom
('https://www.gov.uk/government/organisations/department-for-energy-security-and-net-zero.atom', 'UK DESNZ', 'atom', 'active', 'GB', 'en', 'manual', 'high'),
('https://news.google.com/rss/search?q=uk+energy+policy&hl=en-GB&gl=GB&ceid=GB:en', 'Google News — UK Energy Policy', 'google_news', 'active', 'GB', 'en', 'manual', 'medium'),
('https://www.carbonbrief.org/feed/', 'Carbon Brief', 'rss', 'active', 'GB', 'en', 'manual', 'high'),

-- Spain
('https://www.miteco.gob.es/es/prensa/notas-de-prensa/', 'MITECO Spain', 'html', 'active', 'ES', 'es', 'manual', 'high'),
('https://news.google.com/rss/search?q=politica+energetica+espana&hl=es&gl=ES&ceid=ES:es', 'Google News — Política Energética España', 'google_news', 'active', 'ES', 'es', 'manual', 'medium'),

-- France
('https://www.ecologie.gouv.fr/actualites', 'Ministère Transition Écologique France', 'html', 'active', 'FR', 'fr', 'manual', 'high'),
('https://news.google.com/rss/search?q=politique+energetique+france&hl=fr&gl=FR&ceid=FR:fr', 'Google News — Politique Énergétique France', 'google_news', 'active', 'FR', 'fr', 'manual', 'medium')

ON CONFLICT (url) DO NOTHING;
