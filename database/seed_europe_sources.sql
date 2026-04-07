SET search_path TO climate;

INSERT INTO sources (id, url, name, feed_type, status, country_code, language, discovered_by, credibility_tier) VALUES

-- Germany
('src-de-bmwk',          'https://www.bmwk.de/Navigation/EN/Press/press-releases.html', 'BMWK Germany (English)', 'html', 'active', 'DE', 'en', 'manual', 'high'),
('src-de-cleanenergy',   'https://www.cleanenergywire.org/rss.xml', 'Clean Energy Wire', 'rss', 'active', 'DE', 'en', 'manual', 'high'),
('src-de-energiewende',  'https://news.google.com/rss/search?q=energiewende&hl=de&gl=DE&ceid=DE:de', 'Google News — Energiewende', 'google_news', 'active', 'DE', 'de', 'manual', 'medium'),
('src-de-policy-gnews',  'https://news.google.com/rss/search?q=german+energy+policy&hl=en&gl=DE&ceid=DE:en', 'Google News — German Energy Policy', 'google_news', 'active', 'DE', 'en', 'manual', 'medium'),
('src-de-euractiv',      'https://www.euractiv.com/feed/', 'Euractiv', 'rss', 'active', 'DE', 'en', 'manual', 'high'),

-- United Kingdom
('src-gb-desnz',         'https://www.gov.uk/government/organisations/department-for-energy-security-and-net-zero.atom', 'UK DESNZ', 'atom', 'active', 'GB', 'en', 'manual', 'high'),
('src-gb-policy-gnews',  'https://news.google.com/rss/search?q=uk+energy+policy&hl=en-GB&gl=GB&ceid=GB:en', 'Google News — UK Energy Policy', 'google_news', 'active', 'GB', 'en', 'manual', 'medium'),
('src-gb-carbon-brief',  'https://www.carbonbrief.org/feed/', 'Carbon Brief', 'rss', 'active', 'GB', 'en', 'manual', 'high'),

-- Spain
('src-es-miteco',        'https://www.miteco.gob.es/es/prensa/notas-de-prensa/', 'MITECO Spain', 'html', 'active', 'ES', 'es', 'manual', 'high'),
('src-es-energia-gnews', 'https://news.google.com/rss/search?q=politica+energetica+espana&hl=es&gl=ES&ceid=ES:es', 'Google News — Política Energética España', 'google_news', 'active', 'ES', 'es', 'manual', 'medium'),

-- France
('src-fr-mte',           'https://www.ecologie.gouv.fr/actualites', 'Ministère Transition Écologique France', 'html', 'active', 'FR', 'fr', 'manual', 'high'),
('src-fr-energia-gnews', 'https://news.google.com/rss/search?q=politique+energetique+france&hl=fr&gl=FR&ceid=FR:fr', 'Google News — Politique Énergétique France', 'google_news', 'active', 'FR', 'fr', 'manual', 'medium')

ON CONFLICT (id) DO NOTHING;
