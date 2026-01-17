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



INSERT INTO LigCREATE TABLE users (
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





INSERT INTO Liga (name, land) Values
('Premier League', 'England'),
('LaLiga', 'Spanien'),
('Bundesliga', 'Deutschland');

INSERT INTO Clubs (liga, tore, gegentore, name, platzierung) Values
(2, 50, 20, 'Real Madrid', 2),
(3, 66, 13, 'Bayern München', 1);

INSERT INTO Cheftrainer (team, vorname, nachname) Values
(2, 'Vincent', 'Kompany');

INSERT INTO Spieler (team, vorname, nachname, tore, vorlagen, marktwert, position) Values
(2, 'Manuel', 'Neuer', 0, 0, 5000000, 'Torwart');
