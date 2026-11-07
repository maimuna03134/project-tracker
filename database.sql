-- ============================================================
-- database.sql : MySQL database + 8 ta table (khali, kono mock data nai)
-- 8 ta table = amader 3NF normalization er final table
-- ============================================================

DROP DATABASE IF EXISTS project_tracker;
CREATE DATABASE project_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE project_tracker;

-- 1) USER
CREATE TABLE users (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(100) NOT NULL,
  email      VARCHAR(150) NOT NULL UNIQUE,
  password   VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2) PROFILE (role: student / teacher)
CREATE TABLE profiles (
  id      INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  role    ENUM('student','teacher') NOT NULL DEFAULT 'student',
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3) PROJECT
CREATE TABLE projects (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  title       VARCHAR(200) NOT NULL,
  description TEXT NOT NULL,
  deadline    DATE NOT NULL,
  created_by  INT NOT NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- 4) PROJECT_MEMBER (kon project e kon student ache)
CREATE TABLE project_members (
  project_id INT NOT NULL,
  user_id    INT NOT NULL,
  PRIMARY KEY (project_id, user_id),
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE
);

-- 5) TASK
CREATE TABLE tasks (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  project_id  INT NOT NULL,
  title       VARCHAR(200) NOT NULL,
  description TEXT,
  priority    ENUM('low','medium','high') NOT NULL DEFAULT 'medium',
  status      ENUM('todo','doing','done')  NOT NULL DEFAULT 'todo',
  due_date    DATE NULL,
  assigned_to INT NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id)  REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (assigned_to) REFERENCES users(id)    ON DELETE SET NULL
);

-- 6) COMMENT
CREATE TABLE comments (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  project_id INT NOT NULL,
  user_id    INT NOT NULL,
  text       TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE
);

-- 7) ATTACHMENT (file er naam; asol file static/uploads folder e thake)
CREATE TABLE attachments (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  project_id  INT NOT NULL,
  file_name   VARCHAR(255) NOT NULL,
  uploaded_by INT NOT NULL,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id)  REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (uploaded_by) REFERENCES users(id)    ON DELETE CASCADE
);

-- 8) FEEDBACK (teacher er feedback + marks)
CREATE TABLE feedbacks (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  project_id INT NOT NULL,
  teacher_id INT NOT NULL,
  text       TEXT NOT NULL,
  marks      INT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (teacher_id) REFERENCES users(id)    ON DELETE CASCADE
);