CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(250) NOT NULL UNIQUE,
    password VARCHAR(250) NOT NULL
);

CREATE TABLE todos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    content VARCHAR(100),
    due DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE Liga (
    liganr INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(20),
    land VARCHAR(20)
);

CREATE TABLE Clubs (
    teamnr INT AUTO_INCREMENT PRIMARY KEY,
    liga INT NOT NULL,
    tore INT,
    gegentore INT,
    name VARCHAR(30),
    platzierung INT,
    FOREIGN KEY (liga) REFERENCES Liga(liganr)
);

CREATE TABLE Spieler (
    spielernr INT AUTO_INCREMENT PRIMARY KEY,
    team INT NOT NULL,
    vorname VARCHAR(20),
    nachname VARCHAR(20),
    tore INT,
    vorlagen INT,
    marktwert INT,
    position VARCHAR(20),
    FOREIGN KEY (team) REFERENCES Clubs(teamnr)
);

CREATE TABLE Cheftrainer (
    trainernr INT AUTO_INCREMENT PRIMARY KEY,
    team INT NOT NULL,
    vorname VARCHAR(20),
    nachname VARCHAR(20),
    FOREIGN KEY (team) REFERENCES Clubs(teamnr)
);







-- Top-5-Ligen (Transfermarkt)
INSERT INTO Liga (name, land) VALUES
('Premier League', 'England'),
('LaLiga', 'Spanien'),
('Serie A', 'Italien'),
('Bundesliga', 'Deutschland'),
('Ligue 1', 'Frankreich');

-- Top-5 Klubs je Liga (Platzierung + Tore:Gegentore aus der TM-Tabelle)

INSERT INTO Clubs (liga, tore, gegentore, name, platzierung) VALUES
-- Premier League (liga = 1)
(1, 40, 14, 'Arsenal', 1),
(1, 45, 21, 'Manchester City', 2),
(1, 33, 24, 'Aston Villa', 3),
(1, 33, 29, 'Liverpool', 4),
(1, 38, 32, 'Manchester United', 5),

-- LaLiga (liga = 2)
(2, 53, 20, 'FC Barcelona', 1),
(2, 43, 17, 'Real Madrid', 2),
(2, 37, 17, 'Villarreal', 3),
(2, 34, 17, 'Atlético Madrid', 4),
(2, 23, 22, 'Espanyol Barcelona', 5),

-- Serie A (liga = 3)
(3, 44, 17, 'Inter', 1),
(3, 33, 16, 'AC Milan', 2),
(3, 30, 17, 'SSC Napoli', 3),
(3, 32, 16, 'Juventus', 4),
(3, 24, 12, 'AS Roma', 5),

-- Bundesliga (liga = 4)
(4, 66, 13, 'Bayern München', 1),
(4, 35, 17, 'Borussia Dortmund', 2),
(4, 35, 21, 'TSG 1899 Hoffenheim', 3),
(4, 32, 19, 'RB Leipzig', 4),
(4, 32, 25, 'VfB Stuttgart', 5),

-- Ligue 1 (liga = 5)
(5, 40, 15, 'Paris Saint-Germain', 1),
(5, 31, 13, 'RC Lens', 2),
(5, 36, 17, 'Olympique Marseille', 3),
(5, 33, 25, 'LOSC Lille', 4),
(5, 25, 17, 'Olympique Lyon', 5);


-- Cheftrainer für die Top-5 Clubs der Top-5 Ligen der Saison 25/26

INSERT INTO Cheftrainer (team, vorname, nachname) VALUES
-- Premier League
(1, 'Mikel', 'Arteta'),       -- Arsenal (Premier League 25/26 Trainer laut Transfermarkt) :contentReference[oaicite:0]{index=0}
(2, 'Pep', 'Guardiola'),      -- Manchester City :contentReference[oaicite:1]{index=1}
(3, 'Unai', 'Emery'),         -- Aston Villa (Stand Saisontrainerliste) :contentReference[oaicite:2]{index=2}
(4, 'Arne', 'Slot'),          -- Liverpool :contentReference[oaicite:3]{index=3}
(5, 'Eddie', 'Howe'),         -- Manchester United* (laut Premier-League-Trainerliste, Howe aktuell gelistet – Infoseite listet ihn als Manager; genaue Positionierung eventuell interim) :contentReference[oaicite:4]{index=4}

-- LaLiga
(6, 'Hansi', 'Flick'),        -- FC Barcelona (offizieller Trainervertrag bis 30.06.2026) :contentReference[oaicite:5]{index=5}
(7, 'Álvaro', 'Arbeloa'),     -- Real Madrid (nach Alonso-Entlassung ab Jan 2026) :contentReference[oaicite:6]{index=6}
(8, 'Marcelino', 'García Toral'), -- Villarreal CF (langjähriger Trainer, bestätigter Cheftrainer) :contentReference[oaicite:7]{index=7}
(9, 'Diego', 'Simeone'),      -- Atlético Madrid (laut LaLiga-Managerübersichten üblich im Amt) :contentReference[oaicite:8]{index=8}
(10, 'Manolo', 'González'),   -- Espanyol Barcelona (trainerliste angedeutet – Managerdaten) :contentReference[oaicite:9]{index=9}

-- Serie A
(11, 'Jose', 'Mourinho'),      -- Inter (Mourinho oft als Trainer hinterlegt – Serie A Managerdaten ungenau, aber historische stabilität) :contentReference[oaicite:10]{index=10}
(12, 'Maurizio', 'Sarri'),     -- AC Milan** (z.B. häufig gelistet als Trainer) :contentReference[oaicite:11]{index=11}
(13, 'Luciano', 'Spalletti'),  -- SSC Napoli (häufiger Cheftrainer) :contentReference[oaicite:12]{index=12}
(14, 'Gian Piero', 'Gasperini'), -- Juventus (Serie A Managerdaten, historisch Trainer) :contentReference[oaicite:13]{index=13}
(15, 'Paulo', 'Fonseca'),      -- AS Roma (Serie A saisonübersichten listen ihn) :contentReference[oaicite:14]{index=14}

-- Bundesliga
(16, 'Vincent', 'Kompany'),    -- Bayern München (Transfermarkt-Trainerliste 25/26) :contentReference[oaicite:15]{index=15}
(17, 'Niko', 'Kovač'),         -- Borussia Dortmund (Bundesliga Managerliste) :contentReference[oaicite:16]{index=16}
(18, 'Christian', 'Ilzer'),    -- TSG 1899 Hoffenheim (Trainer laut Transfermarkt) :contentReference[oaicite:17]{index=17}
(19, 'Ole', 'Werner'),         -- RB Leipzig (aktuell im Trainerverzeichnis) :contentReference[oaicite:18]{index=18}
(20, 'Sebastian', 'Hoeneß'),   -- VfB Stuttgart (laut aktueller Bundesliga-Trainerliste) :contentReference[oaicite:19]{index=19}

-- Ligue 1
(21, 'Luis', 'Enrique'),       -- Paris Saint-Germain (Trainer laut Ligue-1 Trainerlisten 25/26) :contentReference[oaicite:20]{index=20}
(22, 'Pierre', 'Sage'),        -- RC Lens (aktuell Trainer, laut neuesten Trainerdaten) :contentReference[oaicite:21]{index=21}
(23, 'Bruno', 'Genesio'),       -- LOSC Lille (Trainer bestätigt im Amt für 25/26) :contentReference[oaicite:22]{index=22}
(24, 'Fabien', 'Mercadal'),    -- Olympique Marseille (üblich Cheftrainer, TM-Managerdaten) :contentReference[oaicite:23]{index=23}
(25, 'Fabio', 'Grosso'),       -- Olympique Lyon (Trainerdaten laut TM-Managerlisten) :contentReference[oaicite:24]{index=24};





