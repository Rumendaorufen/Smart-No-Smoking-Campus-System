/*
 AI read-only views for Smart No-Smoking Campus System

 Usage:
 1. Run db/init.sql first
 2. Then run this file to create AI-facing views

 Goal:
 - Give SQLDatabaseToolkit a cleaner, safer semantic layer
 - Reduce direct access to raw business tables
 - Keep existing schema untouched
*/

SET NAMES utf8mb4;

-- =========================================================
-- 1. Detailed alarm view
--    Best for: recent alarm list, filtered drill-down, audit Q&A
-- =========================================================
DROP VIEW IF EXISTS `ai_alarm_detail_view`;
CREATE VIEW `ai_alarm_detail_view` AS
SELECT
    a.id,
    a.camera_id AS device_id,
    d.name AS device_name,
    a.type AS alarm_type,
    a.confidence,
    a.created_at,
    DATE(a.created_at) AS alarm_date,
    HOUR(a.created_at) AS alarm_hour,
    a.video_url,
    a.roi_url,
    a.audit_status,
    CASE a.audit_status
        WHEN 0 THEN '待审核'
        WHEN 1 THEN '已确认'
        WHEN 2 THEN '误报'
        WHEN 9 THEN '已忽略'
        ELSE '未知'
    END AS audit_status_text,
    a.auditor_id,
    u.username AS auditor_name,
    a.audit_time,
    a.audit_remark,
    CASE
        WHEN a.audit_time IS NULL THEN NULL
        ELSE TIMESTAMPDIFF(MINUTE, a.created_at, a.audit_time)
    END AS audit_delay_minutes
FROM alarms a
LEFT JOIN devices d ON d.id = a.camera_id
LEFT JOIN users u ON u.id = a.auditor_id;

-- =========================================================
-- 2. Daily alarm stats view
--    Best for: trend questions like "最近7天报警趋势"
-- =========================================================
DROP VIEW IF EXISTS `ai_alarm_daily_stats_view`;
CREATE VIEW `ai_alarm_daily_stats_view` AS
SELECT
    DATE(a.created_at) AS stat_date,
    COUNT(*) AS total_alarms,
    SUM(CASE WHEN a.audit_status = 0 THEN 1 ELSE 0 END) AS pending_count,
    SUM(CASE WHEN a.audit_status = 1 THEN 1 ELSE 0 END) AS confirmed_count,
    SUM(CASE WHEN a.audit_status = 2 THEN 1 ELSE 0 END) AS false_positive_count,
    SUM(CASE WHEN a.audit_status = 9 THEN 1 ELSE 0 END) AS ignored_count,
    COUNT(DISTINCT a.camera_id) AS active_device_count,
    ROUND(AVG(a.confidence), 4) AS avg_confidence
FROM alarms a
GROUP BY DATE(a.created_at);

-- =========================================================
-- 3. Device ranking stats view
--    Best for: "哪个设备报警最多" / device leaderboard queries
-- =========================================================
DROP VIEW IF EXISTS `ai_device_alarm_rank_view`;
CREATE VIEW `ai_device_alarm_rank_view` AS
SELECT
    d.id AS device_id,
    d.name AS device_name,
    d.enabled,
    d.status AS device_status,
    COUNT(a.id) AS total_alarms,
    SUM(CASE WHEN a.audit_status = 0 THEN 1 ELSE 0 END) AS pending_count,
    SUM(CASE WHEN a.audit_status = 1 THEN 1 ELSE 0 END) AS confirmed_count,
    SUM(CASE WHEN a.audit_status = 2 THEN 1 ELSE 0 END) AS false_positive_count,
    SUM(CASE WHEN a.audit_status = 9 THEN 1 ELSE 0 END) AS ignored_count,
    ROUND(AVG(a.confidence), 4) AS avg_confidence,
    MAX(a.created_at) AS last_alarm_time,
    CASE
        WHEN COUNT(a.id) = 0 THEN 0
        ELSE ROUND(SUM(CASE WHEN a.audit_status = 1 THEN 1 ELSE 0 END) / COUNT(a.id), 4)
    END AS confirmed_rate,
    CASE
        WHEN COUNT(a.id) = 0 THEN 0
        ELSE ROUND(SUM(CASE WHEN a.audit_status = 2 THEN 1 ELSE 0 END) / COUNT(a.id), 4)
    END AS false_positive_rate
FROM devices d
LEFT JOIN alarms a ON a.camera_id = d.id
GROUP BY d.id, d.name, d.enabled, d.status;

-- =========================================================
-- 4. Auditor stats view
--    Best for: audit efficiency / reviewer workload questions
-- =========================================================
DROP VIEW IF EXISTS `ai_audit_stats_view`;
CREATE VIEW `ai_audit_stats_view` AS
SELECT
    u.id AS auditor_id,
    u.username AS auditor_name,
    u.role,
    COUNT(a.id) AS total_audited,
    SUM(CASE WHEN a.audit_status = 1 THEN 1 ELSE 0 END) AS confirmed_count,
    SUM(CASE WHEN a.audit_status = 2 THEN 1 ELSE 0 END) AS false_positive_count,
    SUM(CASE WHEN a.audit_status = 9 THEN 1 ELSE 0 END) AS ignored_count,
    ROUND(AVG(TIMESTAMPDIFF(MINUTE, a.created_at, a.audit_time)), 2) AS avg_audit_delay_minutes,
    MIN(a.audit_time) AS first_audit_time,
    MAX(a.audit_time) AS last_audit_time
FROM users u
LEFT JOIN alarms a
    ON a.auditor_id = u.id
   AND a.audit_time IS NOT NULL
GROUP BY u.id, u.username, u.role;
