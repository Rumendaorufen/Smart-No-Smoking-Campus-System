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

 Date: 11/02/2026 20:47:20
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

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
) ENGINE = InnoDB AUTO_INCREMENT = 147 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '报警记录表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of alarms
-- ----------------------------
INSERT INTO `alarms` VALUES (120, 41, 'SMOKING', 0.734863, '2026-01-24 17:34:03', 'static/evidence/alarm_p17_1769247242.mp4', 'static/evidence/snapshots/alarm_p17_1769247242.jpg', 1, 1, '2026-01-24 17:34:41', '');
INSERT INTO `alarms` VALUES (121, 41, 'SMOKING', 0.748535, '2026-01-24 17:47:06', 'static/evidence/alarm_p1_1769248025.mp4', 'static/evidence/snapshots/alarm_p1_1769248025.jpg', 0, NULL, NULL, NULL);
INSERT INTO `alarms` VALUES (122, 40, 'SMOKING', 0.794922, '2026-01-24 17:48:17', 'static/evidence/alarm_p9_1769248096.mp4', 'static/evidence/snapshots/alarm_p9_1769248096.jpg', 0, NULL, NULL, NULL);
INSERT INTO `alarms` VALUES (123, 40, 'SMOKING', 0.810059, '2026-01-24 17:48:26', 'static/evidence/alarm_p19_1769248106.mp4', 'static/evidence/snapshots/alarm_p19_1769248106.jpg', 0, NULL, NULL, NULL);
INSERT INTO `alarms` VALUES (124, 41, 'SMOKING', 0.751953, '2026-01-24 17:49:11', 'static/evidence/alarm_p73_1769248151.mp4', 'static/evidence/snapshots/alarm_p73_1769248151.jpg', 0, NULL, NULL, NULL);
INSERT INTO `alarms` VALUES (125, 41, 'SMOKING', 0.728516, '2026-01-24 17:56:37', 'static/evidence/alarm_p1_1769248596.mp4', 'static/evidence/snapshots/alarm_p1_1769248596.jpg', 1, 2, '2026-01-24 18:56:29', '');
INSERT INTO `alarms` VALUES (126, 40, 'SMOKING', 0.711426, '2026-01-24 17:56:37', 'static/evidence/alarm_p1_1769248596.mp4', 'static/evidence/snapshots/alarm_p1_1769248596.jpg', 0, NULL, NULL, NULL);
INSERT INTO `alarms` VALUES (127, 41, 'SMOKING', 0.645996, '2026-01-24 17:59:18', 'static/evidence/alarm_p208_1769248757.mp4', 'static/evidence/snapshots/alarm_p208_1769248757.jpg', 1, 2, '2026-01-24 18:56:27', '');
INSERT INTO `alarms` VALUES (128, 40, 'SMOKING', 0.693359, '2026-01-24 17:59:18', 'static/evidence/alarm_p208_1769248758.mp4', 'static/evidence/snapshots/alarm_p208_1769248758.jpg', 1, 2, '2026-01-24 18:56:28', '');
INSERT INTO `alarms` VALUES (129, 40, 'SMOKING', 0.65332, '2026-01-24 18:02:25', 'static/evidence/alarm_p386_1769248945.mp4', 'static/evidence/snapshots/alarm_p386_1769248945.jpg', 1, 2, '2026-01-24 18:56:25', '');
INSERT INTO `alarms` VALUES (130, 41, 'SMOKING', 0.614258, '2026-01-24 18:02:29', 'static/evidence/alarm_p386_1769248948.mp4', 'static/evidence/snapshots/alarm_p386_1769248948.jpg', 1, 2, '2026-01-24 18:54:23', '');
INSERT INTO `alarms` VALUES (131, 40, 'SMOKING', 0.74707, '2026-01-24 18:02:52', 'static/evidence/alarm_p386_1769248971.mp4', 'static/evidence/snapshots/alarm_p386_1769248971.jpg', 1, 2, '2026-01-24 18:54:21', '');
INSERT INTO `alarms` VALUES (132, 40, 'SMOKING', 0.788574, '2026-01-24 18:04:33', 'static/evidence/alarm_p536_1769249072.mp4', 'static/evidence/snapshots/alarm_p536_1769249072.jpg', 1, 2, '2026-01-24 18:54:20', '');
INSERT INTO `alarms` VALUES (133, 41, 'SMOKING', 0.615234, '2026-01-24 18:04:35', 'static/evidence/alarm_p536_1769249074.mp4', 'static/evidence/snapshots/alarm_p536_1769249074.jpg', 1, 2, '2026-01-24 18:54:19', '');
INSERT INTO `alarms` VALUES (134, 40, 'SMOKING', 0.779297, '2026-01-24 18:04:51', 'static/evidence/alarm_p636_1769249090.mp4', 'static/evidence/snapshots/alarm_p636_1769249090.jpg', 1, 2, '2026-01-24 18:54:16', '');
INSERT INTO `alarms` VALUES (135, 41, 'SMOKING', 0.742188, '2026-01-24 18:04:51', 'static/evidence/alarm_p636_1769249090.mp4', 'static/evidence/snapshots/alarm_p636_1769249090.jpg', 1, 2, '2026-01-24 18:54:17', '');
INSERT INTO `alarms` VALUES (136, 40, 'SMOKING', 0.637207, '2026-01-24 18:05:01', 'static/evidence/alarm_p663_1769249101.mp4', 'static/evidence/snapshots/alarm_p663_1769249101.jpg', 1, 2, '2026-01-24 18:54:08', '');
INSERT INTO `alarms` VALUES (137, 41, 'SMOKING', 0.70166, '2026-01-24 18:28:19', 'static/evidence/alarm_p1_1769250498.mp4', 'static/evidence/snapshots/alarm_p1_1769250498.jpg', 1, 2, '2026-01-24 18:54:05', '');
INSERT INTO `alarms` VALUES (138, 40, 'SMOKING', 0.643555, '2026-01-24 18:28:19', 'static/evidence/alarm_p1_1769250498.mp4', 'static/evidence/snapshots/alarm_p1_1769250498.jpg', 1, 2, '2026-01-24 18:54:07', '');
INSERT INTO `alarms` VALUES (139, 40, 'SMOKING', 0.711426, '2026-01-24 18:28:52', 'static/evidence/alarm_p190_1769250531.mp4', 'static/evidence/snapshots/alarm_p190_1769250531.jpg', 1, 2, '2026-01-24 18:54:02', '');
INSERT INTO `alarms` VALUES (140, 41, 'SMOKING', 0.644043, '2026-01-24 18:29:27', 'static/evidence/alarm_p190_1769250567.mp4', 'static/evidence/snapshots/alarm_p190_1769250567.jpg', 1, 2, '2026-01-24 18:54:03', '');
INSERT INTO `alarms` VALUES (141, 41, 'SMOKING', 0.696777, '2026-01-25 22:08:32', 'static/evidence/alarm_p1_1769350112.mp4', 'static/evidence/snapshots/alarm_p1_1769350112.jpg', 0, NULL, NULL, NULL);
INSERT INTO `alarms` VALUES (142, 41, 'SMOKING', 0.613281, '2026-01-25 22:17:20', 'static/evidence/alarm_p20_1769350639.mp4', 'static/evidence/snapshots/alarm_p20_1769350639.jpg', 0, NULL, NULL, NULL);
INSERT INTO `alarms` VALUES (143, 42, 'SMOKING', 0.628906, '2026-02-11 15:51:16', 'static/evidence/alarm_p17_1770796274.mp4', 'static/evidence/snapshots/alarm_p17_1770796274.jpg', 0, NULL, NULL, NULL);
INSERT INTO `alarms` VALUES (144, 42, 'SMOKING', 0.634277, '2026-02-11 15:54:37', 'static/evidence/alarm_p30_1770796476.mp4', 'static/evidence/snapshots/alarm_p30_1770796476.jpg', 0, NULL, NULL, NULL);
INSERT INTO `alarms` VALUES (145, 42, 'SMOKING', 0.650391, '2026-02-11 16:02:05', 'static/evidence/alarm_p76_1770796924.mp4', 'static/evidence/snapshots/alarm_p76_1770796924.jpg', 0, NULL, NULL, NULL);
INSERT INTO `alarms` VALUES (146, 42, 'SMOKING', 0.647949, '2026-02-11 16:28:54', 'static/evidence/alarm_p142_1770798533.mp4', 'static/evidence/snapshots/alarm_p142_1770798533.jpg', 0, NULL, NULL, NULL);

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
) ENGINE = InnoDB AUTO_INCREMENT = 43 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '设备表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of devices
-- ----------------------------
INSERT INTO `devices` VALUES (40, '手机1', 'rtsp://admin:admin@192.168.1.6:8554/live', NULL, '2026-01-15 20:39:24', '2026-02-11 19:59:35', 0, 0);
INSERT INTO `devices` VALUES (41, '手机2', 'rtsp://admin:admin@192.168.110.107:8554/live', NULL, '2026-01-18 11:03:38', '2026-02-11 19:59:35', 0, 0);
INSERT INTO `devices` VALUES (42, '一楼', 'rtsp://rtsp:12345678@192.168.110.208:554/av_stream/ch0', NULL, '2026-02-11 14:59:40', '2026-02-11 19:59:34', 0, 0);

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
INSERT INTO `users` VALUES (1, 'admin', 'scrypt:32768:8:1$mtJo5UaWhdv3TjhL$857f792fc1328aa696e276444a580cf4c88184f05321c5b085fa3a36d380fb127db28c68cab4917730f8664f4bc2001724528eb71b7588632b69aaffd7b6fb2d', 'admin', 1, '127.0.0.1', '2026-02-11 19:09:08', '2026-01-13 23:15:22');
INSERT INTO `users` VALUES (2, 'user_01', 'scrypt:32768:8:1$DOKUBO0znNRfB9Yx$30e2093550f3fb805d8aec8e89b29e4f6ddef2cdea4375271ca144af4f7052e2598ae7c66717cae484ed9a4b82075e4d83d36ffdff3754788b86aa726dad3df5', 'user', 1, '127.0.0.1', '2026-01-24 12:44:49', '2026-01-14 16:51:01');
INSERT INTO `users` VALUES (3, 'user_02', 'scrypt:32768:8:1$DOKUBO0znNRfB9Yx$30e2093550f3fb805d8aec8e89b29e4f6ddef2cdea4375271ca144af4f7052e2598ae7c66717cae484ed9a4b82075e4d83d36ffdff3754788b86aa726dad3df5', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (4, 'user_03', 'scrypt:32768:8:1$DOKUBO0znNRfB9Yx$30e2093550f3fb805d8aec8e89b29e4f6ddef2cdea4375271ca144af4f7052e2598ae7c66717cae484ed9a4b82075e4d83d36ffdff3754788b86aa726dad3df5', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (5, 'user_04', 'scrypt:32768:8:1$DOKUBO0znNRfB9Yx$30e2093550f3fb805d8aec8e89b29e4f6ddef2cdea4375271ca144af4f7052e2598ae7c66717cae484ed9a4b82075e4d83d36ffdff3754788b86aa726dad3df5', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (6, 'user_05', 'scrypt:32768:8:1$DOKUBO0znNRfB9Yx$30e2093550f3fb805d8aec8e89b29e4f6ddef2cdea4375271ca144af4f7052e2598ae7c66717cae484ed9a4b82075e4d83d36ffdff3754788b86aa726dad3df5', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (7, 'user_06', 'scrypt:32768:8:1$DOKUBO0znNRfB9Yx$30e2093550f3fb805d8aec8e89b29e4f6ddef2cdea4375271ca144af4f7052e2598ae7c66717cae484ed9a4b82075e4d83d36ffdff3754788b86aa726dad3df5', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (8, 'user_07', 'scrypt:32768:8:1$DOKUBO0znNRfB9Yx$30e2093550f3fb805d8aec8e89b29e4f6ddef2cdea4375271ca144af4f7052e2598ae7c66717cae484ed9a4b82075e4d83d36ffdff3754788b86aa726dad3df5', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (9, 'user_08', 'scrypt:32768:8:1$DOKUBO0znNRfB9Yx$30e2093550f3fb805d8aec8e89b29e4f6ddef2cdea4375271ca144af4f7052e2598ae7c66717cae484ed9a4b82075e4d83d36ffdff3754788b86aa726dad3df5', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (10, 'user_09', 'scrypt:32768:8:1$DOKUBO0znNRfB9Yx$30e2093550f3fb805d8aec8e89b29e4f6ddef2cdea4375271ca144af4f7052e2598ae7c66717cae484ed9a4b82075e4d83d36ffdff3754788b86aa726dad3df5', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');
INSERT INTO `users` VALUES (11, 'user_10', 'scrypt:32768:8:1$DOKUBO0znNRfB9Yx$30e2093550f3fb805d8aec8e89b29e4f6ddef2cdea4375271ca144af4f7052e2598ae7c66717cae484ed9a4b82075e4d83d36ffdff3754788b86aa726dad3df5', 'user', 1, '127.0.0.1', '2026-02-02 15:54:31', '2026-02-02 15:54:31');

SET FOREIGN_KEY_CHECKS = 1;
