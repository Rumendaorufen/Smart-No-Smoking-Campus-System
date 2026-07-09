package org.example.webback.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.webback.entity.Alarm;
import org.example.webback.entity.Device;
import org.example.webback.mapper.AlarmMapper;
import org.example.webback.mapper.DeviceMapper;
import org.example.webback.mapper.UserMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.io.File;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

@Service
public class AlarmService extends ServiceImpl<AlarmMapper, Alarm> {

    private static final Logger log = LoggerFactory.getLogger(AlarmService.class);

    @Autowired
    private DeviceMapper deviceMapper;
    @Autowired
    private UserMapper userMapper;

    @Autowired
    private FeishuNotificationService feishuNotificationService;
    @Autowired
    private DeviceService deviceService;

    @Value("${app.python-static-path}")
    private String pythonStaticPath;

    private void fillExtraInfo(IPage<Alarm> page) {
        List<Alarm> records = page.getRecords();
        if (CollectionUtils.isEmpty(records)) return;

        Set<Integer> cameraIds = records.stream()
                .map(Alarm::getCameraId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());

        Set<Integer> auditorIds = records.stream()
                .map(Alarm::getAuditorId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());

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
        System.out.println("✅ 记录 ID:" + id + " 及其关联物理文件已清理");
    }

    private void deletePhysicalFile(String webPath) {
        if (!StringUtils.hasText(webPath)) return;

        try {
            String relativePath = webPath.startsWith("/") ? webPath.substring(1) : webPath;
            File file = new File(pythonStaticPath, relativePath);

            if (file.exists()) {
                boolean success = file.delete();
                if (success) {
                    System.out.println("🗑️ 已删除物理文件: " + file.getAbsolutePath());
                } else {
                    System.err.println("⚠️ 文件存在但删除失败(可能被占用): " + file.getAbsolutePath());
                }
            } else {
                System.err.println("❓ 未找到物理文件，跳过删除: " + file.getAbsolutePath());
            }
        } catch (Exception e) {
            System.err.println("❌ 物理删除异常: " + e.getMessage());
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public void saveInternalAlarm(Integer deviceId, String type, Double confidence,
                                  String snapshotUrl, String videoUrl) {
        Alarm alarm = new Alarm();

        alarm.setCameraId(deviceId);
        alarm.setType(type);
        alarm.setConfidence((double) confidence.floatValue());
        alarm.setRoiUrl(snapshotUrl);
        alarm.setVideoUrl(videoUrl);

        alarm.setAuditStatus(0);
        alarm.setCreatedAt(LocalDateTime.now());

        this.save(alarm);

        // 事务提交后异步发送飞书通知
        TransactionSynchronizationManager.registerSynchronization(
            new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    String deviceName = "未知";
                    try {
                        Device device = deviceService.getById(deviceId);
                        if (device != null) {
                            deviceName = device.getName();
                        }
                    } catch (Exception e) {
                        log.warn("获取设备名称失败: {}", e.getMessage());
                    }

                    final String name = deviceName;
                    CompletableFuture.runAsync(() ->
                        feishuNotificationService.notifyAlarm(alarm, name));
                }
            });
    }
}
