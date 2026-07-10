/*
 Navicat Premium Data Transfer

 Source Server         : localhost_3308
 Source Server Type    : MySQL
 Source Server Version : 80034 (8.0.34)
 Source Host           : localhost:3308
 Source Schema         : smart_campus_smoking

 Target Server Type    : MySQL
 Target Server Version : 80034 (8.0.34)
 File Encoding         : 65001

 Date: 08/05/2026 09:33:39
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ai_chat_history
-- ----------------------------
DROP TABLE IF EXISTS `ai_chat_history`;
CREATE TABLE `ai_chat_history`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `session_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '对应 conversation_id',
  `message` json NOT NULL COMMENT '存储消息角色(role)和内容(content)的JSON',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_session`(`session_id` ASC) USING BTREE,
  INDEX `idx_session_time`(`session_id` ASC, `created_at` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 145 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ai_chat_history
-- ----------------------------

-- ----------------------------
-- Table structure for ai_conversations
-- ----------------------------
DROP TABLE IF EXISTS `ai_conversations`;
CREATE TABLE `ai_conversations`  (
  `id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '会话全局唯一ID',
  `user_id` int NOT NULL COMMENT '所属用户',
  `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT '新对话' COMMENT '会话标题（AI可随后根据内容更新）',
  `is_deleted` tinyint NULL DEFAULT 0 COMMENT '逻辑删除标识',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_user_list`(`user_id` ASC, `is_deleted` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of ai_conversations
-- ----------------------------

-- ----------------------------
-- Table structure for alarms
-- ----------------------------
DROP TABLE IF EXISTS `alarms`;
CREATE TABLE `alarms`  (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `camera_id` int NOT NULL COMMENT '摄像头ID',
  `type` enum('SMOKING','FIRE') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '报警类型',
  `confidence` float NOT NULL COMMENT '置信度',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '报警时间',
  `video_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '证据视频路径',
  `roi_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '特写图路径',
  `audit_status` tinyint NOT NULL DEFAULT 0 COMMENT '状态: 0-待审核, 1-已确认(违规), 2-误报(加入负样本), 9-已忽略',
  `auditor_id` int NULL DEFAULT NULL COMMENT '审核人ID (关联users.id)',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  `audit_remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '审核备注/驳回原因',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_camera_id`(`camera_id` ASC) USING BTREE,
  INDEX `idx_create_time`(`created_at` ASC) USING BTREE,
  INDEX `idx_audit_status`(`audit_status` ASC) USING BTREE,
  INDEX `fk_alarms_users`(`auditor_id` ASC) USING BTREE,
  CONSTRAINT `fk_alarms_devices` FOREIGN KEY (`camera_id`) REFERENCES `devices` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_alarms_users` FOREIGN KEY (`auditor_id`) REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 301 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '报警记录表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of alarms
-- ----------------------------

-- ----------------------------
-- Table structure for devices
-- ----------------------------
DROP TABLE IF EXISTS `devices`;
CREATE TABLE `devices`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '设备名称（如：走廊西侧）',
  `rtsp_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '视频流地址',
  `area_config` json NULL COMMENT '扩展字段，存储 ROI 区域坐标',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `status` int NULL DEFAULT 1,
  `enabled` tinyint(1) NULL DEFAULT 1,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 48 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '设备表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of devices
-- ----------------------------

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '用户主键',
  `username` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '登录账号',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '加密后的密码',
  `role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'user' COMMENT '角色: admin-管理员, user-普通用户',
  `status` tinyint NOT NULL DEFAULT 1 COMMENT '状态: 1-启用, 0-禁用',
  `last_login_ip` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '最后登录IP',
  `last_login_time` datetime NULL DEFAULT NULL COMMENT '最后登录时间',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_username`(`username` ASC) USING BTREE COMMENT '账号唯一索引'
) ENGINE = InnoDB AUTO_INCREMENT = 12 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '用户表' ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Records of users
-- ----------------------------

-- ----------------------------
-- View structure for ai_alarm_daily_stats_view
-- ----------------------------
DROP VIEW IF EXISTS `ai_alarm_daily_stats_view`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `ai_alarm_daily_stats_view` AS select cast(`a`.`created_at` as date) AS `stat_date`,count(0) AS `total_alarms`,sum((case when (`a`.`audit_status` = 0) then 1 else 0 end)) AS `pending_count`,sum((case when (`a`.`audit_status` = 1) then 1 else 0 end)) AS `confirmed_count`,sum((case when (`a`.`audit_status` = 2) then 1 else 0 end)) AS `false_positive_count`,sum((case when (`a`.`audit_status` = 9) then 1 else 0 end)) AS `ignored_count`,count(distinct `a`.`camera_id`) AS `active_device_count`,round(avg(`a`.`confidence`),4) AS `avg_confidence` from `alarms` `a` group by cast(`a`.`created_at` as date);

-- ----------------------------
-- View structure for ai_alarm_detail_view
-- ----------------------------
DROP VIEW IF EXISTS `ai_alarm_detail_view`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `ai_alarm_detail_view` AS select `a`.`id` AS `id`,`a`.`camera_id` AS `device_id`,`d`.`name` AS `device_name`,`a`.`type` AS `alarm_type`,`a`.`confidence` AS `confidence`,`a`.`created_at` AS `created_at`,cast(`a`.`created_at` as date) AS `alarm_date`,hour(`a`.`created_at`) AS `alarm_hour`,`a`.`video_url` AS `video_url`,`a`.`roi_url` AS `roi_url`,`a`.`audit_status` AS `audit_status`,(case `a`.`audit_status` when 0 then '待审核' when 1 then '已确认' when 2 then '误报' when 9 then '已忽略' else '未知' end) AS `audit_status_text`,`a`.`auditor_id` AS `auditor_id`,`u`.`username` AS `auditor_name`,`a`.`audit_time` AS `audit_time`,`a`.`audit_remark` AS `audit_remark`,(case when (`a`.`audit_time` is null) then NULL else timestampdiff(MINUTE,`a`.`created_at`,`a`.`audit_time`) end) AS `audit_delay_minutes` from ((`alarms` `a` left join `devices` `d` on((`d`.`id` = `a`.`camera_id`))) left join `users` `u` on((`u`.`id` = `a`.`auditor_id`)));

-- ----------------------------
-- View structure for ai_audit_stats_view
-- ----------------------------
DROP VIEW IF EXISTS `ai_audit_stats_view`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `ai_audit_stats_view` AS select `u`.`id` AS `auditor_id`,`u`.`username` AS `auditor_name`,`u`.`role` AS `role`,count(`a`.`id`) AS `total_audited`,sum((case when (`a`.`audit_status` = 1) then 1 else 0 end)) AS `confirmed_count`,sum((case when (`a`.`audit_status` = 2) then 1 else 0 end)) AS `false_positive_count`,sum((case when (`a`.`audit_status` = 9) then 1 else 0 end)) AS `ignored_count`,round(avg(timestampdiff(MINUTE,`a`.`created_at`,`a`.`audit_time`)),2) AS `avg_audit_delay_minutes`,min(`a`.`audit_time`) AS `first_audit_time`,max(`a`.`audit_time`) AS `last_audit_time` from (`users` `u` left join `alarms` `a` on(((`a`.`auditor_id` = `u`.`id`) and (`a`.`audit_time` is not null)))) group by `u`.`id`,`u`.`username`,`u`.`role`;

-- ----------------------------
-- View structure for ai_device_alarm_rank_view
-- ----------------------------
DROP VIEW IF EXISTS `ai_device_alarm_rank_view`;
CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `ai_device_alarm_rank_view` AS select `d`.`id` AS `device_id`,`d`.`name` AS `device_name`,`d`.`enabled` AS `enabled`,`d`.`status` AS `device_status`,count(`a`.`id`) AS `total_alarms`,sum((case when (`a`.`audit_status` = 0) then 1 else 0 end)) AS `pending_count`,sum((case when (`a`.`audit_status` = 1) then 1 else 0 end)) AS `confirmed_count`,sum((case when (`a`.`audit_status` = 2) then 1 else 0 end)) AS `false_positive_count`,sum((case when (`a`.`audit_status` = 9) then 1 else 0 end)) AS `ignored_count`,round(avg(`a`.`confidence`),4) AS `avg_confidence`,max(`a`.`created_at`) AS `last_alarm_time`,(case when (count(`a`.`id`) = 0) then 0 else round((sum((case when (`a`.`audit_status` = 1) then 1 else 0 end)) / count(`a`.`id`)),4) end) AS `confirmed_rate`,(case when (count(`a`.`id`) = 0) then 0 else round((sum((case when (`a`.`audit_status` = 2) then 1 else 0 end)) / count(`a`.`id`)),4) end) AS `false_positive_rate` from (`devices` `d` left join `alarms` `a` on((`a`.`camera_id` = `d`.`id`))) group by `d`.`id`,`d`.`name`,`d`.`enabled`,`d`.`status`;

SET FOREIGN_KEY_CHECKS = 1;
