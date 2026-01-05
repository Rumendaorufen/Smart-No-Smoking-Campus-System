-- 高校无烟校园智能监测系统数据库初始化脚本
-- 版本：V1.0
-- 创建日期：2025-12-31

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS `smart_campus_smoking` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `smart_campus_smoking`;

-- 创建设备表
CREATE TABLE IF NOT EXISTS `devices` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` VARCHAR(100) NOT NULL COMMENT '设备名称（如：走廊西侧）',
  `rtsp_url` VARCHAR(500) NOT NULL COMMENT '视频流地址',
  `area_config` JSON NULL COMMENT '扩展字段，存储 ROI 区域坐标',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='设备表';

-- 创建报警表
CREATE TABLE IF NOT EXISTS `alarms` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `camera_id` INT NOT NULL COMMENT '摄像头ID',
  `type` ENUM('SMOKING', 'FIRE') NOT NULL COMMENT '报警类型',
  `confidence` FLOAT NOT NULL COMMENT '置信度',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '报警时间',
  `video_url` VARCHAR(255) NOT NULL COMMENT '证据视频路径',
  `roi_url` VARCHAR(255) NOT NULL COMMENT '特写图路径',
  `audit_status` TINYINT NOT NULL DEFAULT 0 COMMENT '审核状态：0-待审核，1-确认，2-忽略',
  `auditor` VARCHAR(50) NULL COMMENT '审核人',
  `audit_time` DATETIME NULL COMMENT '审核时间',
  PRIMARY KEY (`id`),
  INDEX `idx_camera_id` (`camera_id` ASC),
  INDEX `idx_create_time` (`create_time` ASC),
  INDEX `idx_audit_status` (`audit_status` ASC),
  CONSTRAINT `fk_alarms_devices`
    FOREIGN KEY (`camera_id`)
    REFERENCES `devices` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报警记录表';

-- 插入测试数据
INSERT INTO `devices` (`name`, `rtsp_url`, `area_config`) VALUES
('走廊西侧', 'rtsp://admin:12345@192.168.1.101:554/stream1', NULL),
('图书馆入口', 'rtsp://admin:12345@192.168.1.102:554/stream1', NULL),
('食堂门口', 'rtsp://admin:12345@192.168.1.103:554/stream1', NULL);
