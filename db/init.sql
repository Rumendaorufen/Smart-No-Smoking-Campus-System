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

 Date: 17/01/2026 01:08:06
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
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '报警时间',
  `video_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '证据视频路径',
  `roi_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '特写图路径',
  `audit_status` tinyint NOT NULL DEFAULT 0 COMMENT '审核状态：0-待审核，1-确认，2-忽略',
  `auditor` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT '审核人',
  `audit_time` datetime NULL DEFAULT NULL COMMENT '审核时间',
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_camera_id`(`camera_id` ASC) USING BTREE,
  INDEX `idx_create_time`(`create_time` ASC) USING BTREE,
  INDEX `idx_audit_status`(`audit_status` ASC) USING BTREE,
  CONSTRAINT `fk_alarms_devices` FOREIGN KEY (`camera_id`) REFERENCES `devices` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE = InnoDB AUTO_INCREMENT = 101 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '报警记录表' ROW_FORMAT = Dynamic;

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
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 41 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '设备表' ROW_FORMAT = Dynamic;

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
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '用户表' ROW_FORMAT = DYNAMIC;

SET FOREIGN_KEY_CHECKS = 1;
