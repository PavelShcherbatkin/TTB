create table if not exists users
(
    my_id int not null primary key,
    first_name text,
    second_name text,
    oauth_token text, 
    oauth_token_secret text
);

alter table users
    owner to postgres;

create unique index if not exists users_id_uindex
    on users (my_id);
