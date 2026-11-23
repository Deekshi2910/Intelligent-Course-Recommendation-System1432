-- ============================================================================
-- Intelligent Course Recommendation System
-- Database Schema & Initial Knowledge Base Seeding
-- Database Name: intelligent_course_recommendation
-- ============================================================================

CREATE DATABASE IF NOT EXISTS `intelligent_course_recommendation`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `intelligent_course_recommendation`;

-- Drop existing tables in reverse dependency order if resetting
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `default_rules`;
DROP TABLE IF EXISTS `recommendation_history`;
DROP TABLE IF EXISTS `knowledge_rules`;
DROP TABLE IF EXISTS `course_prerequisites`;
DROP TABLE IF EXISTS `course_career_goals`;
DROP TABLE IF EXISTS `course_interests`;
DROP TABLE IF EXISTS `student_interests`;
DROP TABLE IF EXISTS `career_goals`;
DROP TABLE IF EXISTS `student_profiles`;
DROP TABLE IF EXISTS `courses`;
DROP TABLE IF EXISTS `interests`;
DROP TABLE IF EXISTS `users`;
SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------------------------------------------------------
-- 1. Table: users
-- Stores user authentication credentials and system role (student/admin).
-- ----------------------------------------------------------------------------
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('student', 'admin') NOT NULL DEFAULT 'student',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_users_role` (`role`),
    INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 2. Table: student_profiles
-- Stores academic and biographical data for enrolled students (1:1 with users).
-- ----------------------------------------------------------------------------
CREATE TABLE `student_profiles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `full_name` VARCHAR(100) NOT NULL,
    `roll_number` VARCHAR(30) NOT NULL UNIQUE,
    `department` VARCHAR(100) NOT NULL,
    `semester` INT NOT NULL,
    `cgpa` DECIMAL(4, 2) NOT NULL DEFAULT 0.00,
    `gender` VARCHAR(20) DEFAULT 'Prefer not to say',
    `profile_photo` VARCHAR(255) NULL DEFAULT NULL,
    `career_goal_id` INT NULL,
    CONSTRAINT `fk_student_user` FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_student_career_goal` FOREIGN KEY (`career_goal_id`)
        REFERENCES `career_goals` (`id`)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    INDEX `idx_student_cgpa` (`cgpa`),
    INDEX `idx_student_dept_sem` (`department`, `semester`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 3. Table: interests
-- Master catalogue of academic and professional interest areas.
-- ----------------------------------------------------------------------------
CREATE TABLE `interests` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `interest_name` VARCHAR(100) NOT NULL UNIQUE,
    INDEX `idx_interest_name` (`interest_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 4. Table: student_interests
-- Junction table mapping M:N relationships between students and interests.
-- ----------------------------------------------------------------------------
CREATE TABLE `student_interests` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `interest_id` INT NOT NULL,
    CONSTRAINT `fk_si_student` FOREIGN KEY (`student_id`)
        REFERENCES `student_profiles` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_si_interest` FOREIGN KEY (`interest_id`)
        REFERENCES `interests` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    UNIQUE KEY `uq_student_interest` (`student_id`, `interest_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 5. Table: career_goals
-- Industry career pathways and job profiles aligned with elective courses.
-- ----------------------------------------------------------------------------
CREATE TABLE `career_goals` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `goal_name` VARCHAR(100) NOT NULL UNIQUE,
    `description` TEXT,
    INDEX `idx_career_goal_name` (`goal_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 6. Table: courses
-- Elective course offerings, prerequisite requirements, and difficulty ratings.
-- ----------------------------------------------------------------------------
CREATE TABLE `courses` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `course_code` VARCHAR(20) NOT NULL UNIQUE,
    `course_name` VARCHAR(150) NOT NULL,
    `description` TEXT,
    `minimum_cgpa` DECIMAL(3, 2) DEFAULT 0.00,
    `difficulty_level` ENUM('Beginner', 'Intermediate', 'Advanced') NOT NULL DEFAULT 'Intermediate',
    `career_scope` TEXT,
    `prerequisites` TEXT,
    `is_active` BOOLEAN DEFAULT TRUE,
    INDEX `idx_course_code` (`course_code`),
    INDEX `idx_course_min_cgpa` (`minimum_cgpa`),
    INDEX `idx_course_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 7. Table: course_interests
-- Junction table mapping M:N relationships between courses and interests.
-- ----------------------------------------------------------------------------
CREATE TABLE `course_interests` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `course_id` INT NOT NULL,
    `interest_id` INT NOT NULL,
    CONSTRAINT `fk_ci_course` FOREIGN KEY (`course_id`)
        REFERENCES `courses` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_ci_interest` FOREIGN KEY (`interest_id`)
        REFERENCES `interests` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    UNIQUE KEY `uq_course_interest` (`course_id`, `interest_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 8. Table: course_career_goals
-- Junction table mapping M:N relationships between courses and career goals.
-- ----------------------------------------------------------------------------
CREATE TABLE `course_career_goals` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `course_id` INT NOT NULL,
    `career_goal_id` INT NOT NULL,
    CONSTRAINT `fk_ccg_course` FOREIGN KEY (`course_id`)
        REFERENCES `courses` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_ccg_career_goal` FOREIGN KEY (`career_goal_id`)
        REFERENCES `career_goals` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    UNIQUE KEY `uq_course_career_goal` (`course_id`, `career_goal_id`),
    INDEX `idx_ccg_course` (`course_id`),
    INDEX `idx_ccg_goal` (`career_goal_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 9. Table: course_prerequisites
-- Junction table mapping structured prerequisite dependencies between courses.
-- ----------------------------------------------------------------------------
CREATE TABLE `course_prerequisites` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `course_id` INT NOT NULL,
    `prerequisite_course_id` INT NOT NULL,
    CONSTRAINT `fk_cp_course` FOREIGN KEY (`course_id`)
        REFERENCES `courses` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_cp_prereq_course` FOREIGN KEY (`prerequisite_course_id`)
        REFERENCES `courses` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    UNIQUE KEY `uq_course_prerequisite` (`course_id`, `prerequisite_course_id`),
    INDEX `idx_cp_course` (`course_id`),
    INDEX `idx_cp_prereq` (`prerequisite_course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 10. Table: knowledge_rules
-- Rule-based reasoning knowledge base conditions for the AI inference engine.
-- ----------------------------------------------------------------------------
CREATE TABLE `knowledge_rules` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `rule_name` VARCHAR(100) NOT NULL,
    `conditions` JSON NOT NULL,
    `recommended_course_id` INT NOT NULL,
    `priority` INT NOT NULL DEFAULT 1,
    `is_active` BOOLEAN DEFAULT TRUE,
    CONSTRAINT `fk_kr_course` FOREIGN KEY (`recommended_course_id`)
        REFERENCES `courses` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    INDEX `idx_rule_priority` (`priority`),
    INDEX `idx_rule_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------------------
-- 9. Table: recommendation_history
-- Historical audit log of AI-generated course suggestions and explanations.
-- ----------------------------------------------------------------------------
CREATE TABLE `recommendation_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `recommended_course_id` INT NOT NULL,
    `recommendation_score` DECIMAL(5, 2) NOT NULL,
    `reasoning` TEXT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_rh_student` FOREIGN KEY (`student_id`)
        REFERENCES `student_profiles` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT `fk_rh_course` FOREIGN KEY (`recommended_course_id`)
        REFERENCES `courses` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    INDEX `idx_rh_student` (`student_id`),
    INDEX `idx_rh_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ----------------------------------------------------------------------------
-- 11. Table: default_rules
-- Non-monotonic default reasoning fallback heuristics (DR01-DR05).
-- ----------------------------------------------------------------------------
CREATE TABLE `default_rules` (
    `rule_code` VARCHAR(20) PRIMARY KEY,
    `rule_name` VARCHAR(100) NOT NULL,
    `fallback_strategy` VARCHAR(100) NOT NULL,
    `description` TEXT,
    `priority` INT DEFAULT 1,
    `is_active` BOOLEAN DEFAULT TRUE,
    `rationale` TEXT,
    `explanation_template` TEXT,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================================
-- SEED DATA
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Sample Interests
-- ----------------------------------------------------------------------------
INSERT INTO `interests` (`interest_name`) VALUES
    ('Machine Learning'),
    ('Artificial Intelligence'),
    ('Data Science & Analytics'),
    ('Big Data & Distributed Computing'),
    ('Cloud Infrastructure & DevOps'),
    ('Network Security & Cryptography'),
    ('Deep Learning & Neural Networks'),
    ('Natural Language Processing'),
    ('Data Mining & Predictive Modeling'),
    ('Software Engineering & Architecture'),
    ('Web Development'),
    ('Computer Vision');

-- ----------------------------------------------------------------------------
-- Sample Career Goals
-- ----------------------------------------------------------------------------
INSERT INTO `career_goals` (`goal_name`, `description`) VALUES
    ('Machine Learning Engineer', 'Designs and builds self-running artificial intelligence software to automate predictive models.'),
    ('Data Scientist', 'Analyzes raw data, builds statistical pipelines, and draws actionable insights using ML techniques.'),
    ('Cloud Solutions Architect', 'Oversees an organization cloud computing strategy, application architecture, and deployment.'),
    ('Cybersecurity Analyst', 'Protects computer networks, systems, and sensitive data from cyber threats and unauthorized access.'),
    ('Big Data Engineer', 'Designs, maintains, and optimizes scalable data pipelines and distributed storage architectures.'),
    ('AI Research Scientist', 'Conducts cutting-edge exploratory research into deep learning, cognitive computing, and robotics.'),
    ('NLP Specialist', 'Develops computational models for speech recognition, language synthesis, and semantic analysis.'),
    ('Enterprise Software Architect', 'Builds robust, high-performance distributed systems and business-critical software.');

-- ----------------------------------------------------------------------------
-- Sample Elective Courses
-- Required: Machine Learning, Artificial Intelligence, Big Data Analytics,
-- Cloud Computing, Cyber Security, Deep Learning, Data Mining, Natural Language Processing
-- ----------------------------------------------------------------------------
INSERT INTO `courses` (`course_code`, `course_name`, `description`, `minimum_cgpa`, `difficulty_level`, `career_scope`, `prerequisites`, `is_active`) VALUES
(
    'CS-401',
    'Machine Learning',
    'Foundational theory and algorithms of supervised and unsupervised learning, regression, classification, clustering, and model validation.',
    2.50,
    'Intermediate',
    'Machine Learning Engineer, Data Scientist, Quantitative Analyst',
    'Linear Algebra, Probability & Statistics, Python Programming',
    TRUE
),
(
    'CS-402',
    'Artificial Intelligence',
    'Search algorithms, heuristics, knowledge representation, propositional logic, game theory, and autonomous agent architectures.',
    2.00,
    'Intermediate',
    'AI Systems Developer, Robotics Engineer, Decision Systems Architect',
    'Data Structures & Algorithms, Discrete Mathematics',
    TRUE
),
(
    'CS-403',
    'Big Data Analytics',
    'Scalable processing of high-volume data streams using Hadoop, Spark, MapReduce, NoSQL databases, and distributed query engines.',
    2.50,
    'Advanced',
    'Big Data Engineer, Data Platform Architect, BI Systems Specialist',
    'Database Systems, Object-Oriented Programming, Operating Systems',
    TRUE
),
(
    'CS-404',
    'Cloud Computing',
    'Virtualization, containerization (Docker, Kubernetes), microservices architecture, serverless computing, and AWS/Azure cloud security.',
    2.00,
    'Intermediate',
    'Cloud Solutions Architect, DevOps Engineer, Site Reliability Engineer',
    'Computer Networks, Operating Systems',
    TRUE
),
(
    'CS-405',
    'Cyber Security',
    'Network defense, cryptographic protocols, penetration testing, threat modeling, digital forensics, and secure coding principles.',
    2.00,
    'Intermediate',
    'Cybersecurity Analyst, Information Security Officer, Security Auditor',
    'Computer Networks, Operating Systems',
    TRUE
),
(
    'CS-406',
    'Deep Learning',
    'Multi-layer perceptrons, convolutional neural networks (CNNs), recurrent neural networks (RNNs), transformers, and PyTorch/TensorFlow.',
    3.00,
    'Advanced',
    'Deep Learning Researcher, Computer Vision Engineer, Autonomous Vehicle Engineer',
    'Machine Learning (CS-401), Multivariable Calculus',
    TRUE
),
(
    'CS-407',
    'Data Mining',
    'Association rule mining, classification trees, anomaly detection, clustering algorithms, and knowledge discovery in enterprise databases.',
    2.20,
    'Intermediate',
    'Data Analyst, Business Intelligence Engineer, Predictive Modeler',
    'Database Management Systems, Basic Statistics',
    TRUE
),
(
    'CS-408',
    'Natural Language Processing',
    'Syntactic analysis, semantic parsing, transformer models (BERT, GPT), tokenization, sentiment analysis, and conversational AI agents.',
    2.80,
    'Advanced',
    'NLP Specialist, Conversational AI Engineer, Search Engine Relevance Engineer',
    'Machine Learning (CS-401), Python Programming',
    TRUE
);

-- ----------------------------------------------------------------------------
-- Map Course Interests (M:N)
-- ----------------------------------------------------------------------------
-- Machine Learning (CS-401)
INSERT INTO `course_interests` (`course_id`, `interest_id`)
SELECT c.id, i.id FROM `courses` c, `interests` i
WHERE c.course_code = 'CS-401' AND i.interest_name IN ('Machine Learning', 'Data Science & Analytics', 'Artificial Intelligence');

-- Artificial Intelligence (CS-402)
INSERT INTO `course_interests` (`course_id`, `interest_id`)
SELECT c.id, i.id FROM `courses` c, `interests` i
WHERE c.course_code = 'CS-402' AND i.interest_name IN ('Artificial Intelligence', 'Machine Learning');

-- Big Data Analytics (CS-403)
INSERT INTO `course_interests` (`course_id`, `interest_id`)
SELECT c.id, i.id FROM `courses` c, `interests` i
WHERE c.course_code = 'CS-403' AND i.interest_name IN ('Big Data & Distributed Computing', 'Data Science & Analytics', 'Cloud Infrastructure & DevOps');

-- Cloud Computing (CS-404)
INSERT INTO `course_interests` (`course_id`, `interest_id`)
SELECT c.id, i.id FROM `courses` c, `interests` i
WHERE c.course_code = 'CS-404' AND i.interest_name IN ('Cloud Infrastructure & DevOps', 'Software Engineering & Architecture');

-- Cyber Security (CS-405)
INSERT INTO `course_interests` (`course_id`, `interest_id`)
SELECT c.id, i.id FROM `courses` c, `interests` i
WHERE c.course_code = 'CS-405' AND i.interest_name IN ('Network Security & Cryptography');

-- Deep Learning (CS-406)
INSERT INTO `course_interests` (`course_id`, `interest_id`)
SELECT c.id, i.id FROM `courses` c, `interests` i
WHERE c.course_code = 'CS-406' AND i.interest_name IN ('Deep Learning & Neural Networks', 'Machine Learning', 'Computer Vision');

-- Data Mining (CS-407)
INSERT INTO `course_interests` (`course_id`, `interest_id`)
SELECT c.id, i.id FROM `courses` c, `interests` i
WHERE c.course_code = 'CS-407' AND i.interest_name IN ('Data Mining & Predictive Modeling', 'Data Science & Analytics');

-- Natural Language Processing (CS-408)
INSERT INTO `course_interests` (`course_id`, `interest_id`)
SELECT c.id, i.id FROM `courses` c, `interests` i
WHERE c.course_code = 'CS-408' AND i.interest_name IN ('Natural Language Processing', 'Artificial Intelligence', 'Deep Learning & Neural Networks');

-- ----------------------------------------------------------------------------
-- Initial Knowledge Rules for AI Inference Engine
-- ----------------------------------------------------------------------------
INSERT INTO `knowledge_rules` (`rule_name`, `conditions`, `recommended_course_id`, `priority`, `is_active`) VALUES
(
    'Rule_Deep_Learning_Eligibility',
    JSON_OBJECT(
        'min_cgpa', 3.00,
        'min_semester', 5,
        'required_interests', JSON_ARRAY('Deep Learning & Neural Networks', 'Machine Learning'),
        'preferred_career_goals', JSON_ARRAY('AI Research Scientist', 'Machine Learning Engineer'),
        'rationale', 'High CGPA student in advanced semesters with deep learning interest qualifies for CS-406 Deep Learning.'
    ),
    (SELECT id FROM `courses` WHERE course_code = 'CS-406'),
    10,
    TRUE
),
(
    'Rule_NLP_Specialization',
    JSON_OBJECT(
        'min_cgpa', 2.80,
        'min_semester', 5,
        'required_interests', JSON_ARRAY('Natural Language Processing', 'Artificial Intelligence'),
        'preferred_career_goals', JSON_ARRAY('NLP Specialist', 'AI Research Scientist'),
        'rationale', 'Student targeting language modeling and conversational AI recommended for CS-408 Natural Language Processing.'
    ),
    (SELECT id FROM `courses` WHERE course_code = 'CS-408'),
    9,
    TRUE
),
(
    'Rule_Machine_Learning_Core',
    JSON_OBJECT(
        'min_cgpa', 2.50,
        'min_semester', 4,
        'required_interests', JSON_ARRAY('Machine Learning', 'Data Science & Analytics'),
        'preferred_career_goals', JSON_ARRAY('Machine Learning Engineer', 'Data Scientist'),
        'rationale', 'Intermediate student with predictive analytics interest strongly recommended for CS-401 Machine Learning.'
    ),
    (SELECT id FROM `courses` WHERE course_code = 'CS-401'),
    8,
    TRUE
),
(
    'Rule_Big_Data_Analytics',
    JSON_OBJECT(
        'min_cgpa', 2.50,
        'min_semester', 5,
        'required_interests', JSON_ARRAY('Big Data & Distributed Computing', 'Data Science & Analytics'),
        'preferred_career_goals', JSON_ARRAY('Big Data Engineer', 'Data Scientist'),
        'rationale', 'Upper semester student keen on distributed data pipelines suited for CS-403 Big Data Analytics.'
    ),
    (SELECT id FROM `courses` WHERE course_code = 'CS-403'),
    7,
    TRUE
),
(
    'Rule_Cloud_Computing_DevOps',
    JSON_OBJECT(
        'min_cgpa', 2.00,
        'min_semester', 3,
        'required_interests', JSON_ARRAY('Cloud Infrastructure & DevOps', 'Software Engineering & Architecture'),
        'preferred_career_goals', JSON_ARRAY('Cloud Solutions Architect', 'Enterprise Software Architect'),
        'rationale', 'Student interested in infrastructure and systems engineering matches CS-404 Cloud Computing.'
    ),
    (SELECT id FROM `courses` WHERE course_code = 'CS-404'),
    6,
    TRUE
),
(
    'Rule_Cyber_Security_Defense',
    JSON_OBJECT(
        'min_cgpa', 2.00,
        'min_semester', 3,
        'required_interests', JSON_ARRAY('Network Security & Cryptography'),
        'preferred_career_goals', JSON_ARRAY('Cybersecurity Analyst'),
        'rationale', 'Student dedicated to security and network protection directed to CS-405 Cyber Security.'
    ),
    (SELECT id FROM `courses` WHERE course_code = 'CS-405'),
    6,
    TRUE
),
(
    'Rule_Data_Mining_Foundation',
    JSON_OBJECT(
        'min_cgpa', 2.20,
        'min_semester', 4,
        'required_interests', JSON_ARRAY('Data Mining & Predictive Modeling', 'Data Science & Analytics'),
        'preferred_career_goals', JSON_ARRAY('Data Scientist'),
        'rationale', 'Students pursuing statistical pattern recognition steered toward CS-407 Data Mining.'
    ),
    (SELECT id FROM `courses` WHERE course_code = 'CS-407'),
    5,
    TRUE
),
(
    'Rule_General_AI_Foundations',
    JSON_OBJECT(
        'min_cgpa', 2.00,
        'min_semester', 3,
        'required_interests', JSON_ARRAY('Artificial Intelligence'),
        'preferred_career_goals', JSON_ARRAY('AI Systems Developer', 'Machine Learning Engineer'),
        'rationale', 'Default reasoning rule recommending CS-402 Artificial Intelligence for introductory AI exploration.'
    ),
    (SELECT id FROM `courses` WHERE course_code = 'CS-402'),
    4,
    TRUE
);

-- ----------------------------------------------------------------------------
-- Canonical Default Reasoning Rules (DR01 - DR05)
-- ----------------------------------------------------------------------------
INSERT INTO `default_rules` (`rule_code`, `rule_name`, `fallback_strategy`, `description`, `priority`, `is_active`, `rationale`, `explanation_template`) VALUES
(
    'DR01',
    'Missing Career Goal Fallback',
    'interest_based',
    'IF career goal is missing AND student interests are available, THEN generate interest-based recommendations.',
    4,
    TRUE,
    'When career aspirations are undeclared, domain interest ontologies provide the strongest personal signal.',
    'Your career goal was not provided. Therefore, the system used your selected interests to identify suitable courses.'
),
(
    'DR02',
    'Missing Interests Fallback',
    'career_based',
    'IF student interests are missing AND career goal is available, THEN generate career-based recommendations.',
    3,
    TRUE,
    'When specific technical topics are undeclared, target career pathways define the required curriculum competencies.',
    'Your interests were not provided. Therefore, the system used your selected career goal to identify suitable courses.'
),
(
    'DR03',
    'Missing Interests and Career Goal',
    'general_foundational',
    'IF interests and career goal are both missing, THEN generate general foundational course recommendations.',
    2,
    TRUE,
    'When neither interests nor career goals are declared, recommend introductory breadth electives.',
    'Neither interests nor career goals were provided. These are general foundational recommendations and may not match your personal preferences.'
),
(
    'DR04',
    'Missing CGPA Academic Request',
    'request_academic_info',
    'IF CGPA is missing, THEN request academic information. Do not assume a CGPA value.',
    5,
    TRUE,
    'Academic eligibility requires explicit verification; never hallucinate or assume student GPA.',
    'Your CGPA is missing. Please provide your CGPA before eligibility can be confirmed.'
),
(
    'DR05',
    'Unknown Prerequisites Verification',
    'unverified_prerequisites',
    'IF prerequisite information is unavailable or unverified, THEN mark eligibility as unverified. Do not assume prerequisites are satisfied.',
    1,
    TRUE,
    'Course prerequisites represent hard academic dependencies and cannot be assumed without evidence.',
    'Prerequisite completion status is unverified. Prerequisites cannot be assumed to be satisfied.'
);
