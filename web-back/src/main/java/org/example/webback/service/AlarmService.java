package org.example.webback.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.webback.entity.Alarm;
import org.example.webback.mapper.AlarmMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.io.File;
import java.time.LocalDateTime;

@Service
public class AlarmService extends ServiceImpl<AlarmMapper, Alarm> {

    /**
     * 获取待审核列表
     */
    public IPage<Alarm> getPendingAlarms(Integer page, Integer pageSize) {
        Page<Alarm> pageParam = new Page<>(page, pageSize);
        return this.page(pageParam, new LambdaQueryWrapper<Alarm>()
                .eq(Alarm::getAuditStatus, 0)
                .orderByDesc(Alarm::getCreatedAt));
    }

    /**
     * 审核报警
     */
    public void auditAlarm(Long id, Integer status, String remark, Integer userId) {
        Alarm alarm = this.getById(id);
        if (alarm == null) throw new RuntimeException("记录不存在");

        if (status != 1 && status != 2 && status != 9) {
            throw new RuntimeException("无效的状态码");
        }

        alarm.setAuditStatus(status);
        alarm.setAuditRemark(remark);
        alarm.setAuditorId(userId);
        alarm.setAuditTime(LocalDateTime.now());

        this.updateById(alarm);
    }

    /**
     * 历史档案查询 (多条件)
     */
    public IPage<Alarm> getArchivedAlarms(Integer page, Integer pageSize,
                                          Integer deviceId, Integer status,
                                          String startTime, String endTime) {

        Page<Alarm> pageParam = new Page<>(page, pageSize);
        LambdaQueryWrapper<Alarm> query = new LambdaQueryWrapper<>();

        // 排除待审核的
        query.ne(Alarm::getAuditStatus, 0);

        if (deviceId != null) {
            query.eq(Alarm::getCameraId, deviceId);
        }
        if (status != null) {
            query.eq(Alarm::getAuditStatus, status);
        }
        if (StringUtils.hasText(startTime) && StringUtils.hasText(endTime)) {
            query.between(Alarm::getCreatedAt, startTime, endTime);
        }

        query.orderByDesc(Alarm::getCreatedAt);
        return this.page(pageParam, query);
    }

    /**
     * 删除报警 (包含文件)
     */
    @Transactional(rollbackFor = Exception.class)
    public void removeAlarmWithFile(Long id) {
        Alarm alarm = this.getById(id);
        if (alarm == null) throw new RuntimeException("记录不存在");

        // 1. 删除物理文件
        deletePhysicalFile(alarm.getRoiUrl());
        deletePhysicalFile(alarm.getVideoUrl());

        // 2. 删除数据库记录
        this.removeById(id);
    }

    // 辅助：删除文件
    private void deletePhysicalFile(String relPath) {
        if (!StringUtils.hasText(relPath)) return;
        try {
            // 注意：这里需要定位到 Python 项目的根目录或者静态资源目录
            // 假设你的 SpringBoot 和 Python 项目在同一级目录下，或者你知道绝对路径
            // 这里暂且使用 user.dir (项目根目录) 作为演示
            String projectDir = System.getProperty("user.dir");

            // 去掉路径开头的 / (例如 /static/evidence/...)
            String safePath = relPath.startsWith("/") ? relPath.substring(1) : relPath;

            File file = new File(projectDir, safePath);
            if (file.exists()) {
                file.delete();
                System.out.println("🗑️ 已物理删除: " + safePath);
            }
        } catch (Exception e) {
            System.err.println("文件删除失败: " + e.getMessage());
        }
    }
}