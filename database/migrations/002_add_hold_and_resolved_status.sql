-- Adds the 'On Hold' and 'Resolved' ticket statuses to an existing database (fresh installs get them from schema.sql).
-- Run once in MySQL Workbench as root: the app user (helpdesk_app) cannot ALTER tables.
USE it_helpdesk;

ALTER TABLE tickets
  MODIFY status ENUM('Open','Assigned','In Progress','On Hold','Resolved','Closed') NOT NULL DEFAULT 'Open';
