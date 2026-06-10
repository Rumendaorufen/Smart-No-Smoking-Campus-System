package org.example.webback.service;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * 证据文件生命周期管理。
 * - 未确认/误报: 7 天后删除关联证据
 * - 已确认: 视频 90 天后删除，快照永久保留
 */
@Service
public class EvidenceCleanupService {

    private static final Logger log = LoggerFactory.getLogger(EvidenceCleanupService.class);
    private static final String EVIDENCE_DIR = "app/static/evidence";

    @Scheduled(cron = "0 0 3 * * ?")  // 每天凌晨 3 点
    public void cleanupEvidence() {
        log.info("🔍 开始执行证据清理任务...");

        // TODO: 实现 MyBatis 查询逻辑
        // 1. 查询 7 天前仍未确认的报警记录 (audit_status = 'pending' or 'dismissed')
        //    → 删除关联的 snapshot 和 video 文件
        //    → 标记数据库记录 evidence_deleted = 1
        //
        // 2. 查询 90 天前已确认的报警记录 (audit_status = 'confirmed')
        //    → 只删除 video 文件，保留 snapshot
        //    → 标记数据库记录 video_deleted = 1

        log.info("✅ 证据清理任务执行完毕");
    }
}
