CREATE TABLE IF NOT EXISTS settings (
    last_update timestamp with time zone
);

CREATE TABLE IF NOT EXISTS songs (
    id varchar(50) NOT NULL,
    title varchar(200) NOT NULL,
    request_id varchar(50) NOT NULL,
    PRIMARY KEY(id)
);


CREATE TABLE IF NOT EXISTS favorites (
    cid varchar(50) NOT NULL,
    song_id varchar(50) NOT NULL,
    CONSTRAINT fk_song
      FOREIGN KEY(song_id) 
        REFERENCES songs(id)
        ON DELETE CASCADE
);