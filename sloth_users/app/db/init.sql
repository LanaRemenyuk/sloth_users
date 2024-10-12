CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    rating FLOAT DEFAULT 0,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS passwords (
    user_id UUID REFERENCES users(id),
    hashed_pass TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_timestamp
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE OR REPLACE PROCEDURE create_user_procedure(
    p_username TEXT,
    p_email TEXT,
    p_hashed_pass TEXT,
    p_phone TEXT,
    p_is_verified BOOLEAN,
    p_rating FLOAT,
    p_role TEXT,
    OUT p_user_id UUID
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO users (username, email, phone, is_verified, rating, role)
    VALUES (p_username, p_email, p_phone, p_is_verified, p_rating, p_role)
    RETURNING id INTO p_user_id;

    INSERT INTO passwords (user_id, hashed_pass, created_at, updated_at)
    VALUES (p_user_id, p_hashed_pass, NOW(), NOW());
END;
$$;

CREATE OR REPLACE FUNCTION get_user_by_id(_user_id UUID)
RETURNS TABLE(id UUID, username TEXT, email TEXT, hashed_pass TEXT, phone TEXT, is_verified BOOLEAN, rating FLOAT, role TEXT, created_at TIMESTAMP, updated_at TIMESTAMP) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        users.id, 
        users.username, 
        users.email, 
        passwords.hashed_pass,
        users.phone,
        users.is_verified, 
        users.rating, 
        users.role, 
        users.created_at, 
        users.updated_at
    FROM users
    LEFT JOIN passwords ON users.id = passwords.user_id
    WHERE users.id = _user_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_all_users()
RETURNS TABLE(id UUID, username TEXT, email TEXT, hashed_pass TEXT, phone TEXT, is_verified BOOLEAN, rating FLOAT, role TEXT, created_at TIMESTAMP, updated_at TIMESTAMP) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (users.id) 
        users.id AS id, 
        users.username, 
        users.email, 
        passwords.hashed_pass,  
        users.phone,
        users.is_verified, 
        users.rating, 
        users.role, 
        users.created_at, 
        users.updated_at
    FROM users
    LEFT JOIN passwords ON users.id = passwords.user_id
    ORDER BY users.id, passwords.created_at DESC;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE PROCEDURE update_user_procedure(
    _user_id UUID,
    _username TEXT DEFAULT NULL,
    _email TEXT DEFAULT NULL,
    _phone TEXT DEFAULT NULL,
    _is_verified BOOLEAN DEFAULT NULL,
    _rating FLOAT DEFAULT NULL,
    _role TEXT DEFAULT NULL,
    _hashed_pass TEXT DEFAULT NULL
) 
LANGUAGE plpgsql AS $$ 
DECLARE 
    _sql TEXT := 'UPDATE users SET '; 
    _fields TEXT := '';
    _param_count INT := 1; 
BEGIN 
    -- Обновление полей пользователя
    IF _username IS NOT NULL THEN 
        _fields := _fields || format('username = $%s, ', _param_count); 
        _param_count := _param_count + 1; 
    END IF; 

    IF _email IS NOT NULL THEN 
        _fields := _fields || format('email = $%s, ', _param_count); 
        _param_count := _param_count + 1; 
    END IF; 

    IF _phone IS NOT NULL THEN 
        _fields := _fields || format('phone = $%s, ', _param_count); 
        _param_count := _param_count + 1; 
    END IF; 

    IF _is_verified IS NOT NULL THEN 
        _fields := _fields || format('is_verified = $%s, ', _param_count); 
        _param_count := _param_count + 1; 
    END IF; 

    IF _rating IS NOT NULL THEN 
        _fields := _fields || format('rating = $%s, ', _param_count); 
        _param_count := _param_count + 1; 
    END IF; 

    IF _role IS NOT NULL THEN 
        _fields := _fields || format('role = $%s, ', _param_count); 
        _param_count := _param_count + 1; 
    END IF; 

    IF char_length(_fields) > 0 THEN
        _fields := left(_fields, char_length(_fields) - 2); -- Удаляем последнюю запятую
        _sql := _sql || _fields || format(' WHERE id = $%s', _param_count); 

        -- Выполняем обновление пользователя
        EXECUTE _sql USING _username, _email, _phone, _is_verified, _rating, _role, _user_id;
    END IF; 
    
    -- Добавляем новый пароль, если он предоставлен
    IF _hashed_pass IS NOT NULL THEN
        INSERT INTO passwords (user_id, hashed_pass, created_at, updated_at)
        VALUES (_user_id, _hashed_pass, NOW(), NOW());
    END IF;
END; 
$$;

CREATE OR REPLACE FUNCTION delete_user_by_id(_user_id UUID) RETURNS VOID AS $$
BEGIN
    DELETE FROM passwords WHERE user_id = _user_id;
    DELETE FROM users WHERE id = _user_id;
END;
$$ LANGUAGE plpgsql;

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);