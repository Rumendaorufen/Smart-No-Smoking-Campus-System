package org.example.webback.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.webback.entity.Alarm;
import org.example.webback.mapper.AlarmMapper;
import org.example.webback.mapper.DeviceMapper;
import org.example.webback.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.io.File;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class AlarmService extends ServiceImpl<AlarmMapper, Alarm> {

    @Autowired
    private DeviceMapper deviceMapper;
    @Autowired
    private UserMapper userMapper;

    private void fillExtraInfo(IPage<Alarm> page) {
        List<Alarm> records = page.getRecords();
        if (CollectionUtils.isEmpty(records)) return;

        // 收集 ID 并过滤 null
        Set<Integer> cameraIds = records.stream()
                .map(Alarm::getCameraId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());

        Set<Integer> auditorIds = records.stream()
                .map(Alarm::getAuditorId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());

        // 🚀 修复点：显式转换 ID 类型以匹配 Map 的 Key
        Map<Integer, String> deviceMap = new HashMap<>();
        if (!cameraIds.isEmpty()) {
            deviceMapper.selectBatchIds(cameraIds).forEach(d -> {
                deviceMap.put(d.getId().intValue(), d.getName());
            });
        }

        Map<Integer, String> userMap = new HashMap<>();
        if (!auditorIds.isEmpty()) {
            userMapper.selectBatchIds(auditorIds).forEach(u -> {
                userMap.put(u.getId().intValue(), u.getUsername());
            });
        }

        records.forEach(alarm -> {
            alarm.setDeviceName(deviceMap.getOrDefault(alarm.getCameraId(), "未知位置"));
            alarm.setAuditorName(userMap.getOrDefault(alarm.getAuditorId(), "系统"));
        });
    }

    public IPage<Alarm> getPendingAlarms(Integer page, Integer pageSize) {
        Page<Alarm> pageParam = new Page<>(page, pageSize);
        IPage<Alarm> result = this.page(pageParam, new LambdaQueryWrapper<Alarm>()
                .eq(Alarm::getAuditStatus, 0)
                .orderByDesc(Alarm::getCreatedAt));
        fillExtraInfo(result);
        return result;
    }

    @Transactional(rollbackFor = Exception.class)
    public void auditAlarm(Long id, Integer status, String remark, Integer userId) {
        Alarm alarm = this.getById(id);
        if (alarm == null) throw new RuntimeException("记录不存在");
        alarm.setAuditStatus(status);
        alarm.setAuditRemark(remark);
        alarm.setAuditorId(userId);
        alarm.setAuditTime(LocalDateTime.now());
        this.updateById(alarm);
    }

    public IPage<Alarm> getArchivedAlarms(Integer page, Integer pageSize,
                                          Integer deviceId, Integer status,
                                          String startTime, String endTime) {
        Page<Alarm> pageParam = new Page<>(page, pageSize);
        LambdaQueryWrapper<Alarm> query = new LambdaQueryWrapper<>();
        query.ne(Alarm::getAuditStatus, 0);
        if (deviceId != null) query.eq(Alarm::getCameraId, deviceId);
        if (status != null) query.eq(Alarm::getAuditStatus, status);
        if (StringUtils.hasText(startTime) && StringUtils.hasText(endTime)) {
            query.between(Alarm::getCreatedAt, startTime, endTime);
        }
        query.orderByDesc(Alarm::getCreatedAt);
        IPage<Alarm> result = this.page(pageParam, query);
        fillExtraInfo(result);
        return result;
    }

    @Transactional(rollbackFor = Exception.class)
    public void removeAlarmWithFile(Long id) {
        Alarm alarm = this.getById(id);
        if (alarm == null) return;
        deletePhysicalFile(alarm.getRoiUrl());
        deletePhysicalFile(alarm.getVideoUrl());
        this.removeById(id);
    }

    private void deletePhysicalFile(String relPath) {
        if (!StringUtils.hasText(relPath)) return;
        try {
            String projectDir = System.getProperty("user.dir");
            String safePath = relPath.startsWith("/") ? relPath.substring(1) : relPath;
            File file = new File(projectDir, safePath);
            if (file.exists()) file.delete();
        } catch (Exception e) {
            // ✅ 修复点：改用简单的标准错误打印，避免不兼容的 log 库调用
            System.err.println("文件删除失败: " + e.getMessage());
        }
    }

    // 在 AlarmService 类中添加

    /**
     * 将 AI 引擎的数据持久化到数据库
     */
    @Transactional(rollbackFor = Exception.class)
    public void saveInternalAlarm(Integer deviceId, String type, Double confidence,
                                  String snapshotUrl, String videoUrl) {
        Alarm alarm = new Alarm();

        // 映射关系
        alarm.setCameraId(deviceId);           // 对应数据库 camera_id
        alarm.setType(type);                   // 对应数据库 type (SMOKING)
        alarm.setConfidence((double) confidence.floatValue()); // 转换为 float
        alarm.setRoiUrl(snapshotUrl);          // 对应数据库 roi_url
        alarm.setVideoUrl(videoUrl);           // 对应数据库 video_url

        // 初始状态
        alarm.setAuditStatus(0);               // 0-待审核
        alarm.setCreatedAt(LocalDateTime.now());

        // 执行插入 (MyBatis Plus 提供的方法)
        this.save(alarm);
    }
}