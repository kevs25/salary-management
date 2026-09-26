-- Runs once, on first start of an empty volume. The app schema itself comes from
-- MYSQL_DATABASE; this adds a disposable schema for integration tests.
CREATE DATABASE IF NOT EXISTS salary_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON salary_test.* TO 'salary'@'%';
