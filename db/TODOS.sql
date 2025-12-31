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
    Spielernr INT AUTO_INCREMENT PRIMARY KEY,
    vorname VARCHAR(20),
    nachname VARCHAR(20),
    Tore INT,
    Vorlagen INT,
    Marktwert INT,
    Position VARCHAR(20),
    Einsatzzeit INT,
    FOREIGN KEY (team) REFERENCES Club(teamnr)
    
CREATE TABLE Clubs (
   teamnr INT AUTO_INCREMENT PRIMARY KEY,
    Tore INT,
    Gegentore INT,
    Name VARCHAR(30),

CREATE TABLE Cheftrainer (
    Trainernr INT AUTO_INCREMENT PRIMARY KEY,
    Titel INT,
    Vorname VARCHAR(20),
    Nachname VARCHAR(20),
    FOREIGN KEY (team) REFERENCES Club(teamnr)

CREATE TABLE Liga (
    liganr INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(20),
    Land VARCHAR(20),
    
