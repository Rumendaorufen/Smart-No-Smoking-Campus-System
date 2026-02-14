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
import org.springframework.beans.factory.annotation.Value;
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

    @Value("${app.python-static-path}") // 🚀 注入刚才配置的路径
    private String pythonStaticPath;

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

        // 1. 先删除物理文件
        deletePhysicalFile(alarm.getRoiUrl());
        deletePhysicalFile(alarm.getVideoUrl());

        // 2. 再删除数据库记录
        this.removeById(id);
        System.out.println("✅ 记录 ID:" + id + " 及其关联物理文件已清理");
    }

    private void deletePhysicalFile(String webPath) {
        if (!StringUtils.hasText(webPath)) return;

        try {
            // webPath 示例: "/static/evidence/snapshots/alarm_xxx.jpg"
            // 我们需要去掉开头的 "/" 并拼接到 Python 的 app 目录下
            String relativePath = webPath.startsWith("/") ? webPath.substring(1) : webPath;

            // 构造绝对路径
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