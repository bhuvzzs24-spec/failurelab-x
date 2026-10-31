CREATE TABLE demo_transactions (
 role VARCHAR(20) NOT NULL, key VARCHAR(100) NOT NULL,
 status VARCHAR(30) NOT NULL, amount INTEGER NOT NULL, quantity INTEGER NOT NULL,
 PRIMARY KEY(role,key)
);

CREATE TABLE demo_stock (sku VARCHAR(40) PRIMARY KEY, available INTEGER NOT NULL CHECK (available >= 0));
INSERT INTO demo_stock(sku,available) VALUES ('demo-sku',100);
