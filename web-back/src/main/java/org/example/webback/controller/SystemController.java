package org.example.webback.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import org.example.webback.common.Result;
import org.example.webback.entity.Alarm;
import org.example.webback.mapper.AlarmMapper;
import org.example.webback.mapper.DeviceMapper;
import org.example.webback.service.SystemMonitorService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.lang.management.ManagementFactory;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/system")
public class SystemController {

    @Autowired
    private SystemMonitorService systemMonitorService;

    @Autowired
    private AlarmMapper alarmMapper;

    @Autowired
    private DeviceMapper deviceMapper;

    /**
     * 获取系统实时状态 (供前端每3秒轮询)
     */
    @GetMapping("/status")
    public Result getStatus() {
        Map<String, Object> data = new HashMap<>(systemMonitorService.getSystemStatus());

        // 业务数据
        Map<String, Object> business = new HashMap<>();
        business.put("todayAlarms", alarmMapper.selectCount(new QueryWrapper<Alarm>()
                .apply("DATE(created_at) = {0}", LocalDate.now().toString())));
        business.put("pendingAudit", alarmMapper.selectCount(new QueryWrapper<Alarm>()
                .eq("audit_status", 0)));

        long startTime = System.currentTimeMillis() - ManagementFactory.getRuntimeMXBean().getUptime();
        business.put("bootTime", cn.hutool.core.date.DateUtil.date(startTime).toString());

        // 设备列表 (用于控制矩阵)
        business.put("devices", deviceMapper.selectList(null));

        data.put("business", business);
        return Result.success(data);
    }

    /**
     * 🚀 解决按钮弹回的关键接口：同步数据库/内存中的状态
     * 对应前端: javaRequest.post('/system/control/global_ai_db', { enabled: ... })
     */
    @PostMapping("/control/global_ai_db")
    public Result syncAiStatus(@RequestBody Map<String, Object> body) {
        Boolean enabled = (Boolean) body.get("enabled");
        if (enabled != null) {
            systemMonitorService.updateGlobalAiStatus(enabled);
            return Result.success("状态已同步");
        }
        return Result.error(400, "参数错误");
    }
}