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

CREATE TABLE Spieler (
    spielernr INT AUTO_INCREMENT PRIMARY KEY,
    vorname VARCHAR(20),
    nachname VARCHAR(20),
    tore INT,
    vorlagen INT,
    marktwert INT,
    position VARCHAR(20),
    FOREIGN KEY (team) REFERENCES Club(teamnr)
    );


CREATE TABLE Clubs (
    teamnr INT AUTO_INCREMENT PRIMARY KEY,
    tore INT,
    gegentore INT,
    name VARCHAR(30),
    platzierung INT,
    FOREIGN KEY (liga) REFERENCES Liga(liganr)
    );

CREATE TABLE Cheftrainer (
    trainernr INT AUTO_INCREMENT PRIMARY KEY,
    vorname VARCHAR(20),
    nachname VARCHAR(20),
    FOREIGN KEY (team) REFERENCES Club(teamnr)
    );

CREATE TABLE Liga (
    liganr INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(20),
    land VARCHAR(20)
    );
    
Insert into Spieler (vorname, nachname, position, tore, vorlagen, marktwert, team) Values
('Vinicius', 'Junior', 'LF', 5, 7, '180 mio', 1)
('Michael', 'Olise', 'RF', 6, 12, '130 mio', 2)


Insert into Cheftrainer (vorname, nachname, team) Values
('Xabi', 'Alonso', 1)
('Vincent', 'Kompany', 2)

Insert into liga (name, land) Values
('Laliga', 'Spanien')
('Bundesliga', 'Deutschland')

INSERT INTO Clubs (tore, gegentore, name, platzierung) Values
(30. 20, "Real Madrid", 2)
(50, 15, "Bayern München", 1)
