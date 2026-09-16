-- ================================================================
-- Migration Patch for healthcare_db
-- Run this in MySQL Workbench or MySQL CLI:
-- mysql -u root -p healthcare_db < migration_patch.sql
-- ================================================================

USE healthcare_db;

-- 1. Ensure columns exist in `appointments`
ALTER TABLE appointments 
ADD COLUMN IF NOT EXISTS patient_id INT DEFAULT NULL AFTER id,
ADD COLUMN IF NOT EXISTS patient_name VARCHAR(100) DEFAULT NULL AFTER patient_id,
ADD COLUMN IF NOT EXISTS predicted_duration INT DEFAULT 15 AFTER visit_type;

-- 2. Ensure `phone` column exists in `patients`
ALTER TABLE patients
ADD COLUMN IF NOT EXISTS phone VARCHAR(20) DEFAULT NULL AFTER age;

-- 3. Populate missing default values if any
UPDATE appointments SET predicted_duration = 15 WHERE predicted_duration IS NULL;

-- 4. Verify changes
DESCRIBE appointments;
DESCRIBE patients;
