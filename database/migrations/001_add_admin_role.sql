-- Adds the 'admin' role to an existing database (fresh installs get it from schema.sql).
-- Run once in MySQL Workbench as root: the app user (helpdesk_app) cannot ALTER tables.
USE it_helpdesk;

ALTER TABLE users
  MODIFY role ENUM('employee','it_team','admin') NOT NULL DEFAULT 'employee';
