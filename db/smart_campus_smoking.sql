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
INSERT INTO `ai_chat_history` VALUES (141, '5c24598e805349129814709eb69a66d8', '{\"data\": {\"id\": null, \"name\": null, \"type\": \"human\", \"content\": \"最近一周的报警趋势\", \"example\": false, \"additional_kwargs\": {}, \"response_metadata\": {}}, \"type\": \"human\"}', '2026-04-23 21:56:37');
INSERT INTO `ai_chat_history` VALUES (142, '5c24598e805349129814709eb69a66d8', '{\"data\": {\"id\": null, \"name\": null, \"type\": \"ai\", \"content\": \"最近一周的报警趋势显示整体报警数量较低，仅在4月22日和23日有少量报警记录。\\n\\n**数据概览**：\\n\\n| 日期 | 报警总数 | 已确认 | 误报 | 待处理 |\\n| :--- | :---: | :---: | :---: | :---: |\\n| 2026-04-23 | **1** | 0 | 0 | 1 |\\n| 2026-04-22 | **2** | 1 | 0 | 1 |\\n\\n**趋势分析**：\\n- 报警活动集中在最近两天，此前5天无报警记录\\n- 已确认的报警占比为 **33.3%**（3起报警中1起已确认）\\n- 待处理报警占比为 **66.7%**，需关注审核进度\\n- 未出现误报，设备检测准确率表现良好\", \"example\": false, \"tool_calls\": [], \"usage_metadata\": null, \"additional_kwargs\": {}, \"response_metadata\": {}, \"invalid_tool_calls\": []}, \"type\": \"ai\"}', '2026-04-23 21:56:37');
INSERT INTO `ai_chat_history` VALUES (143, '5c24598e805349129814709eb69a66d8', '{\"data\": {\"id\": null, \"name\": null, \"type\": \"human\", \"content\": \"昨天情况\", \"example\": false, \"additional_kwargs\": {}, \"response_metadata\": {}}, \"type\": \"human\"}', '2026-04-23 22:04:48');
INSERT INTO `ai_chat_history` VALUES (144, '5c24598e805349129814709eb69a66d8', '{\"data\": {\"id\": null, \"name\": null, \"type\": \"ai\", \"content\": \"昨天（2026-04-22）共发生 **2** 起报警，其中 **1** 起已确认、**1** 起待处理，无漏报和误报。\\n\\n**数据详情**：\\n\\n| 指标 | 数值 |\\n| :--- | :---: |\\n| 报警总数 | **2** |\\n| 已确认 | **1** |\\n| 待处理 | **1** |\\n| 误报 | **0** |\\n| 已忽略 | **0** |\\n| 活跃设备数 | **1** |\\n| 平均置信度 | **0.72** |\\n\\n**情况分析**：\\n- 确认率为 **50%**，仍有1起报警待审核\\n- 未出现误报，设备检测准确性良好\\n- 平均置信度为 **0.72**，处于中等水平\\n- 建议尽快完成待处理报警的审核工作\", \"example\": false, \"tool_calls\": [], \"usage_metadata\": null, \"additional_kwargs\": {}, \"response_metadata\": {}, \"invalid_tool_calls\": []}, \"type\": \"ai\"}', '2026-04-23 22:04:48');

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
INSERT INTO `ai_conversations` VALUES ('0325ae909b4e4788899aab676be06b4f', 1, '你好', 1, '2026-04-23 19:57:06', '2026-04-23 20:55:50');
INSERT INTO `ai_conversations` VALUES ('0a40c78980384bc2a2a8367019016a98', 1, '今日未处理数', 1, '2026-04-23 21:00:28', '2026-04-23 21:55:56');
INSERT INTO `ai_conversations` VALUES ('205a634b70d8476d84b185f7801e5729', 1, '你好', 1, '2026-04-23 18:31:00', '2026-04-23 18:33:17');
INSERT INTO `ai_conversations` VALUES ('35d7120046964bfc9787a5282a48b5ef', 1, '你好', 1, '2026-04-23 18:33:18', '2026-04-23 20:55:51');
INSERT INTO `ai_conversations` VALUES ('50cad2351ed14a8db237c42eb11deced', 1, '昨天情况', 1, '2026-04-23 21:41:31', '2026-04-23 21:55:53');
INSERT INTO `ai_conversations` VALUES ('5c24598e805349129814709eb69a66d8', 1, '最近一周的报警趋势', 0, '2026-04-23 21:55:57', '2026-04-23 21:55:57');
INSERT INTO `ai_conversations` VALUES ('6b5538decbef4a2c9ac6ab6c3e8eb6a7', 1, '今日未处理数', 1, '2026-04-23 21:14:07', '2026-04-23 21:55:54');
INSERT INTO `ai_conversations` VALUES ('94274cbfb4454ac69882c5b90351729b', 1, '你好', 1, '2026-04-23 18:28:08', '2026-04-23 18:31:05');
INSERT INTO `ai_conversations` VALUES ('adbd51b360db459f8483711a0c7fd79c', 1, '你好', 1, '2026-04-23 20:08:36', '2026-04-23 20:55:47');
INSERT INTO `ai_conversations` VALUES ('b3cfe450060b4d438de7de0285245791', 1, '你好', 1, '2026-04-23 18:05:41', '2026-04-23 18:21:41');
INSERT INTO `ai_conversations` VALUES ('bf221b471d784aa9b6d37c7d67f6b85d', 1, '你好', 1, '2026-04-23 18:13:08', '2026-04-23 18:21:42');
INSERT INTO `ai_conversations` VALUES ('c97998f7993b473b9cc06961eff02450', 1, '你好', 1, '2026-04-23 18:15:07', '2026-04-23 18:21:38');
INSERT INTO `ai_conversations` VALUES ('eff358f2686b4554b64257e3704ea9f0', 1, '你好', 1, '2026-04-23 18:21:43', '2026-04-23 18:28:07');

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
INSERT INTO `alarms` VALUES (295, 46, 'SMOKING', 0.76, '2026-03-04 21:47:02', 'static/evidence/alarm_cam46__p9_1772632022.mp4', 'static/evidence/snapshots/alarm_cam46__p9_1772632022.jpg', 1, 1, '2026-04-22 13:18:23', '');
INSERT INTO `alarms` VALUES (296, 46, 'SMOKING', 0.71, '2026-03-04 22:09:59', 'static/evidence/alarm_cam46__p20_1772633399.mp4', 'static/evidence/snapshots/alarm_cam46__p20_1772633399.jpg', 1, 1, '2026-04-22 13:18:21', '');
INSERT INTO `alarms` VALUES (297, 46, 'SMOKING', 0.72, '2026-03-04 22:25:11', 'static/evidence/alarm_cam46__p1_1772634310.mp4', 'static/evidence/snapshots/alarm_cam46__p1_1772634310.jpg', 1, 1, '2026-04-22 13:18:24', '');
INSERT INTO `alarms` VALUES (298, 46, 'SMOKING', 0.72, '2026-04-22 13:17:33', 'static/evidence/alarm_cam46__p16_1776835052.mp4', 'static/evidence/snapshots/alarm_cam46__p16_1776835052.jpg', 1, 1, '2026-04-22 13:18:26', '');
INSERT INTO `alarms` VALUES (299, 46, 'SMOKING', 0.71, '2026-04-22 13:23:06', 'static/evidence/alarm_cam46__p50_1776835386.mp4', 'static/evidence/snapshots/alarm_cam46__p50_1776835386.jpg', 0, NULL, NULL, NULL);
INSERT INTO `alarms` VALUES (300, 47, 'SMOKING', 0.74, '2026-04-23 21:00:10', 'static/evidence/alarm_cam47__p1_1776949209.mp4', 'static/evidence/snapshots/alarm_cam47__p1_1776949209.jpg', 0, NULL, NULL, NULL);

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
INSERT INTO `devices` VALUES (46, '手机', 'rtsp://admin:admin@192.168.217.134:8554/live', NULL, '2026-03-04 21:46:26', '2026-04-22 13:23:55', 0, 0);
INSERT INTO `devices` VALUES (47, '宿舍', 'rtsp://admin:admin@192.168.217.48:8554/live', NULL, '2026-04-23 20:59:47', '2026-04-23 22:09:54', 0, 0);

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
INSERT INTO `users` VALUES (1, 'admin', '$2a$10$51qmfkswHTqgnF3nMWgBiOeTcCmEsxN8Ub01P.q34GhMDvckUD6vW', 'admin', 1, '0:0:0:0:0:0:0:1', '2026-04-23 20:13:16', '2026-01-13 23:15:22');
INSERT INTO `users` VALUES (2, 'user_01', '$2a$10$51qmfkswHTqgnF3nMWgBiOeTcCmEsxN8Ub01P.q34GhMDvckUD6vW', 'user', 1, '0:0:0:0:0:0:0:1', '2026-04-23 20:12:11', '2026-01-14 16:51:01');
INSERT INTO `users` VALUES (3, 'user_02', '$2a$10$51qmfkswHTqgnF3nMWgBiOeTcCmEsxN8Ub01P.q34GhMDvckUD6vW', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (4, 'user_03', '$2a$10$51qmfkswHTqgnF3nMWgBiOeTcCmEsxN8Ub01P.q34GhMDvckUD6vW', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (5, 'user_04', '$2a$10$51qmfkswHTqgnF3nMWgBiOeTcCmEsxN8Ub01P.q34GhMDvckUD6vW', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (6, 'user_05', '$2a$10$51qmfkswHTqgnF3nMWgBiOeTcCmEsxN8Ub01P.q34GhMDvckUD6vW', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (7, 'user_06', '$2a$10$51qmfkswHTqgnF3nMWgBiOeTcCmEsxN8Ub01P.q34GhMDvckUD6vW', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (8, 'user_07', '$2a$10$51qmfkswHTqgnF3nMWgBiOeTcCmEsxN8Ub01P.q34GhMDvckUD6vW', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (9, 'user_08', '$2a$10$51qmfkswHTqgnF3nMWgBiOeTcCmEsxN8Ub01P.q34GhMDvckUD6vW', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (10, 'user_09', '$2a$10$51qmfkswHTqgnF3nMWgBiOeTcCmEsxN8Ub01P.q34GhMDvckUD6vW', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (11, 'user_10', '$2a$10$51qmfkswHTqgnF3nMWgBiOeTcCmEsxN8Ub01P.q34GhMDvckUD6vW', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');

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
