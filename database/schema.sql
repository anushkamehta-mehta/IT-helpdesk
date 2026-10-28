-- IT Helpdesk schema (reference copy; mirrors api/app/models).
-- Run in MySQL Workbench. Create a dedicated app user separately (see README).
CREATE DATABASE IF NOT EXISTS it_helpdesk CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE it_helpdesk;

CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  full_name     VARCHAR(100) NOT NULL,
  email         VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('employee','it_team','admin') NOT NULL DEFAULT 'employee',
  is_active     TINYINT(1) NOT NULL DEFAULT 1,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS categories (
  id   INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS tickets (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  title            VARCHAR(200) NOT NULL,
  description      TEXT NOT NULL,
  category_id      INT NOT NULL,
  priority         ENUM('Low','Medium','High') NOT NULL DEFAULT 'Medium',
  status           ENUM('Open','Assigned','In Progress','Closed') NOT NULL DEFAULT 'Open',
  created_by       INT NOT NULL,
  assigned_to      INT NULL,
  resolution_notes TEXT NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  closed_at        DATETIME NULL,
  INDEX idx_tickets_status (status),
  INDEX idx_tickets_created_by (created_by),
  INDEX idx_tickets_assigned_to (assigned_to),
  CONSTRAINT fk_tickets_category FOREIGN KEY (category_id) REFERENCES categories(id),
  CONSTRAINT fk_tickets_creator  FOREIGN KEY (created_by)  REFERENCES users(id),
  CONSTRAINT fk_tickets_assignee FOREIGN KEY (assigned_to) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS comments (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  ticket_id  INT NOT NULL,
  author_id  INT NOT NULL,
  body       TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_comments_ticket (ticket_id),
  CONSTRAINT fk_comments_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
  CONSTRAINT fk_comments_author FOREIGN KEY (author_id) REFERENCES users(id)
) ENGINE=InnoDB;

-- Starter categories (no users or passwords are seeded here)
INSERT IGNORE INTO categories (name) VALUES
  ('Hardware'), ('Software'), ('Network'), ('Email'), ('Access / Accounts'), ('Other');
