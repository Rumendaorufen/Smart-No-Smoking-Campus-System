package org.example.webback.controller;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import org.example.webback.common.Result;
import org.example.webback.entity.Alarm;
import org.example.webback.entity.Device;
import org.example.webback.mapper.AlarmMapper;
import org.example.webback.mapper.DeviceMapper;
import org.example.webback.service.SystemMonitorService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.lang.management.ManagementFactory;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/system")
public class SystemController {

    @Autowired
    private SystemMonitorService systemMonitorService; // 注入刚才写的服务

    @Autowired
    private AlarmMapper alarmMapper;

    @Autowired
    private DeviceMapper deviceMapper;

    @GetMapping("/status")
    public Result getStatus() {
        // 1. 获取硬件信息 (直接读缓存，毫秒级响应)
        Map<String, Object> data = new HashMap<>(systemMonitorService.getSystemStatus());

        // 2. 获取业务数据 (今日报警、待审核)
        // 优化：MyBatis-Plus 的 selectCount 比 selectList 更快
        Long todayAlarms = alarmMapper.selectCount(new QueryWrapper<Alarm>()
                .apply("DATE(created_at) = {0}", LocalDate.now().toString()));

        Long pendingAudit = alarmMapper.selectCount(new QueryWrapper<Alarm>()
                .eq("audit_status", 0));

        // 获取 JVM 启动时间
        long uptime = ManagementFactory.getRuntimeMXBean().getUptime();
        // 计算启动时间字符串 (例如: 2023-10-27 10:00:00)
        long startTime = System.currentTimeMillis() - uptime;

        Map<String, Object> business = new HashMap<>();
        business.put("today_alarms", todayAlarms);
        business.put("pending_audit", pendingAudit);
        business.put("boot_time", cn.hutool.core.date.DateUtil.date(startTime).toString());

        // 3. 获取设备状态统计
        // Python 代码里还返回了设备列表，我们也加上
        business.put("devices", deviceMapper.selectList(null));

        data.put("business", business);

        // 保持 JSON 结构与前端 Monitor.vue 一致
        // 前端期待的结构: data.ram_percent, data.cpu 等
        // 我们在 Service 里存的是 Map，这里为了完全兼容 Python 的返回结构，做一下平铺处理
        Map<String, Object> memory = (Map<String, Object>) data.get("memory");
        if (memory != null) {
            data.put("ram_percent", memory.get("percent"));
            data.put("ram_used", memory.get("used"));
        }

        return Result.success(data);
    }
}