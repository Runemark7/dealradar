-- Seed data for local development
-- This file is automatically loaded after schema.sql in docker-compose

-- Insert sample posts
INSERT INTO posts (ad_id, title, price, description, location, category, company_ad, images, discovered_at)
VALUES
    ('TEST001', 'Gaming PC - RTX 3080, Ryzen 7', '6500 kr', 'Säljer min gaming-dator i mycket gott skick. RTX 3080, Ryzen 7 5800X, 32GB RAM, 1TB NVMe SSD. Perfekt för gaming och streaming.', 'Stockholm', '5021', false, '[]'::jsonb, NOW()),
    ('TEST002', 'MacBook Pro 2021 M1 Pro', '12000 kr', 'MacBook Pro 14" med M1 Pro chip, 16GB RAM, 512GB SSD. Knappt använd, kvitto finns.', 'Göteborg', '5021', false, '[]'::jsonb, NOW()),
    ('TEST003', 'Dell Ultrawide Monitor 34"', '3500 kr', 'Dell U3419W, 34 tum ultrawide, 3440x1440, 60Hz. Inga pixelfel, fungerar perfekt.', 'Malmö', '5020', false, '[]'::jsonb, NOW()),
    ('TEST004', 'iPhone 13 Pro 256GB', '7500 kr', 'iPhone 13 Pro i mycket fint skick. Sierra Blue, 256GB. Batteri hälsa 95%.', 'Uppsala', '5040', false, '[]'::jsonb, NOW()),
    ('TEST005', 'Gamingstol - DXRacer', '1200 kr', 'DXRacer Formula Series. Lite använd, inga skador. Bekväm och ergonomisk.', 'Linköping', '5020', false, '[]'::jsonb, NOW()),
    ('TEST006', 'Lenovo Legion Gaming Laptop', '8900 kr', 'Lenovo Legion 5 Pro, RTX 3070, Ryzen 7 5800H, 16GB RAM, 1TB SSD. 165Hz skärm.', 'Stockholm', '5021', false, '[]'::jsonb, NOW()),
    ('TEST007', 'Sony WH-1000XM4 Hörlurar', '1800 kr', 'Trådlösa noise-cancelling hörlurar. Mycket bra skick, alla tillbehör medföljer.', 'Göteborg', '5020', false, '[]'::jsonb, NOW()),
    ('TEST008', 'Apple Magic Keyboard', '600 kr', 'Apple Magic Keyboard med svenskt tangentbord. Perfekt skick.', 'Stockholm', '5020', false, '[]'::jsonb, NOW()),
    ('TEST009', 'Nintendo Switch OLED', '2500 kr', 'Nintendo Switch OLED modell, vit. Används sällan, mycket fint skick.', 'Malmö', '5060', false, '[]'::jsonb, NOW()),
    ('TEST010', 'Samsung Odyssey G7 27"', '4200 kr', '27 tum gaming monitor, 1440p, 240Hz, curved. Perfekt för competitive gaming.', 'Uppsala', '5020', false, '[]'::jsonb, NOW()),
    ('TEST011', 'iPad Air 2022 256GB', '5500 kr', 'iPad Air 5:e gen, M1 chip, 256GB, Space Gray. Som ny, har legat i låda.', 'Linköping', '5020', false, '[]'::jsonb, NOW()),
    ('TEST012', 'Logitech MX Master 3', '600 kr', 'Trådlös mus för produktivitet. Fungerar perfekt, säljer pga uppgradering.', 'Stockholm', '5020', false, '[]'::jsonb, NOW());

-- Insert evaluations for the posts
INSERT INTO evaluations (ad_id, status, value_score, evaluation_notes, notification_message, estimated_market_value, specs, evaluated_at)
VALUES
    ('TEST001', 'completed', 9.2,
     'Mycket bra pris för specifikationerna. RTX 3080 och Ryzen 7 5800X är kraftfulla komponenter som normalt kostar betydligt mer. 32GB RAM är generöst. Prisvärt köp för gaming-entusiaster.',
     '🔥 Excellent deal! High-end gaming PC at 35% below market value',
     '10,000 kr',
     '{"CPU": "Ryzen 7 5800X", "GPU": "RTX 3080", "RAM": "32GB", "Storage": "1TB NVMe SSD"}'::jsonb,
     NOW()),

    ('TEST002', 'completed', 7.5,
     'MacBook Pro M1 Pro är en fantastisk maskin men priset är bara marginellt under marknadsvärdet. Fortfarande ett bra köp med tanke på prestanda och kvalitet.',
     'Good deal on M1 Pro MacBook, slightly below market price',
     '13,500 kr',
     '{"Model": "MacBook Pro 14\"", "Processor": "M1 Pro", "RAM": "16GB", "Storage": "512GB SSD", "Year": "2021"}'::jsonb,
     NOW()),

    ('TEST003', 'completed', 8.5,
     'Utmärkt pris för en Dell Ultrawide. U3419W är en populär modell med bra färgåtergivning. 3500 kr är cirka 30% under normalpriset för denna monitor.',
     '💰 Great price! Dell Ultrawide 30% cheaper than usual',
     '5,000 kr',
     '{"Brand": "Dell", "Model": "U3419W", "Size": "34 inch", "Resolution": "3440x1440", "Refresh Rate": "60Hz"}'::jsonb,
     NOW()),

    ('TEST004', 'completed', 8.0,
     'iPhone 13 Pro 256GB för 7500 kr är ett konkurrenskraftigt pris. Batteri hälsa på 95% är bra. Sierra Blue är en efterfrågad färg.',
     'Solid deal on iPhone 13 Pro with good battery health',
     '8,500 kr',
     '{"Model": "iPhone 13 Pro", "Color": "Sierra Blue", "Storage": "256GB", "Battery Health": "95%"}'::jsonb,
     NOW()),

    ('TEST005', 'completed', 6.5,
     'DXRacer Formula för 1200 kr är okej men inte fantastiskt. Begagnade gamingstolar har varierande skick och komfort är subjektivt.',
     'Decent price for used gaming chair',
     '1,500 kr',
     '{"Brand": "DXRacer", "Series": "Formula", "Condition": "Lite använd"}'::jsonb,
     NOW()),

    ('TEST006', 'completed', 9.0,
     'Legion 5 Pro med RTX 3070 för 8900 kr är ett riktigt fynd! Denna laptop kostar normalt 12,000-14,000 kr ny. Perfekt för gaming och kreativt arbete.',
     '🎯 Excellent value! Gaming laptop 40% below retail price',
     '13,000 kr',
     '{"Model": "Lenovo Legion 5 Pro", "GPU": "RTX 3070", "CPU": "Ryzen 7 5800H", "RAM": "16GB", "Storage": "1TB SSD", "Display": "165Hz"}'::jsonb,
     NOW()),

    ('TEST007', 'completed', 8.3,
     'Sony WH-1000XM4 för 1800 kr är ett bra pris. Dessa hörlurar är högst rankade för noise-cancelling och ljudkvalitet. Nypris ligger på 3000-3500 kr.',
     'Great deal on premium noise-cancelling headphones',
     '2,500 kr',
     '{"Brand": "Sony", "Model": "WH-1000XM4", "Type": "Trådlösa, Noise-cancelling"}'::jsonb,
     NOW()),

    ('TEST008', 'completed', 5.0,
     'Apple Magic Keyboard för 600 kr är marknadspris. Inget speciellt fynd men inte heller dåligt. Bra om man behöver just detta tangentbord.',
     'Fair price for Apple Magic Keyboard',
     '700 kr',
     '{"Brand": "Apple", "Model": "Magic Keyboard", "Layout": "Svenskt"}'::jsonb,
     NOW()),

    ('TEST009', 'completed', 7.8,
     'Nintendo Switch OLED för 2500 kr är under marknadspris. OLED-modellen är populär och håller sitt värde bra. Bra köp för Switch-fans.',
     'Good price on Switch OLED, below market value',
     '3,000 kr',
     '{"Model": "Nintendo Switch OLED", "Color": "Vit", "Condition": "Mycket fint skick"}'::jsonb,
     NOW()),

    ('TEST010', 'completed', 8.7,
     'Samsung Odyssey G7 för 4200 kr är mycket bra pris. 240Hz och 1440p gör den perfekt för competitive gaming. Nypris ligger kring 6000-7000 kr.',
     '🎮 Excellent gaming monitor deal! 40% off retail',
     '6,500 kr',
     '{"Brand": "Samsung", "Model": "Odyssey G7", "Size": "27 inch", "Resolution": "1440p", "Refresh Rate": "240Hz", "Type": "Curved"}'::jsonb,
     NOW()),

    ('TEST011', 'completed', 6.8,
     'iPad Air 2022 för 5500 kr är OK pris men inte exceptionellt. M1-chippet är kraftfullt men priset är bara lite under nypriser med kampanjer.',
     'Decent price for iPad Air M1, slightly below retail',
     '6,200 kr',
     '{"Model": "iPad Air 5", "Processor": "M1", "Storage": "256GB", "Color": "Space Gray", "Year": "2022"}'::jsonb,
     NOW()),

    ('TEST012', 'completed', 7.0,
     'Logitech MX Master 3 för 600 kr är ett bra pris för denna populära mus. Nypris ligger på 1000-1200 kr. Bra köp för kontorsarbete.',
     'Good deal on premium productivity mouse',
     '900 kr',
     '{"Brand": "Logitech", "Model": "MX Master 3", "Type": "Trådlös"}'::jsonb,
     NOW());

-- Show summary
SELECT
    COUNT(*) as total_posts,
    (SELECT COUNT(*) FROM evaluations WHERE status = 'completed') as evaluated_posts,
    (SELECT COUNT(*) FROM evaluations WHERE value_score >= 8) as high_value_deals
FROM posts;
