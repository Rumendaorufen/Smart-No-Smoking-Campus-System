package org.example.webback.service;

import cn.hutool.core.util.NumberUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import oshi.SystemInfo;
import oshi.hardware.CentralProcessor;
import oshi.hardware.GlobalMemory;
import oshi.hardware.HardwareAbstractionLayer;
import oshi.software.os.FileSystem;
import oshi.software.os.OSFileStore;
import oshi.software.os.OperatingSystem;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@EnableScheduling
public class SystemMonitorService {

    private final SystemInfo systemInfo = new SystemInfo();
    private final HardwareAbstractionLayer hardware = systemInfo.getHardware();
    private final OperatingSystem os = systemInfo.getOperatingSystem();

    // 核心：缓存系统状态
    private final Map<String, Object> systemCache = new ConcurrentHashMap<>();
    private long[] prevTicks = new long[CentralProcessor.TickType.values().length];

    // 🚀 关键：同步 AI 引擎状态（默认为开启）
    private boolean globalAiEnabled = true;

    public SystemMonitorService() {
        prevTicks = hardware.getProcessor().getSystemCpuLoadTicks();
        systemCache.put("cpu", 0.0);
        systemCache.put("global_ai", true);
    }

    // 🚀 供 Controller 调用，更新同步状态
    public void updateGlobalAiStatus(boolean enabled) {
        this.globalAiEnabled = enabled;
        systemCache.put("global_ai", enabled);
    }

    @Scheduled(fixedRate = 1000)
    public void refreshSystemStatus() {
        try {
            // 1. CPU
            CentralProcessor processor = hardware.getProcessor();
            double cpuLoad = processor.getSystemCpuLoadBetweenTicks(prevTicks) * 100;
            prevTicks = processor.getSystemCpuLoadTicks();

            // 2. 内存 (RAM)
            GlobalMemory memory = hardware.getMemory();
            long totalMem = memory.getTotal();
            long usedMem = totalMem - memory.getAvailable();

            // 3. 磁盘 (Disk)
            OSFileStore store = os.getFileSystem().getFileStores().get(0);
            long totalDisk = store.getTotalSpace();
            long freeDisk = store.getUsableSpace();

            // 4. GPU (静态获取名称，实时负载需 Python 辅助)
            Map<String, Object> gpuData = new HashMap<>();
            var graphicsCards = hardware.getGraphicsCards();
            if (!graphicsCards.isEmpty()) {
                gpuData.put("name", graphicsCards.get(0).getName());
                gpuData.put("memPercent", 0);
            }

            // 更新缓存 (平铺结构，方便前端直接读取)
            systemCache.put("cpu", NumberUtil.round(cpuLoad, 1).doubleValue());
            systemCache.put("ramPercent", NumberUtil.round((double) usedMem / totalMem * 100, 1).doubleValue());
            systemCache.put("ramUsed", NumberUtil.round(usedMem / 1024.0 / 1024.0 / 1024.0, 2).doubleValue());

            Map<String, Object> diskData = new HashMap<>();
            diskData.put("percent", NumberUtil.round((double)(totalDisk - freeDisk)/totalDisk * 100, 1).doubleValue());
            diskData.put("free", NumberUtil.round(freeDisk / 1024.0 / 1024.0 / 1024.0, 1).doubleValue());
            systemCache.put("disk", diskData);

            systemCache.put("gpu", gpuData);
            systemCache.put("global_ai", globalAiEnabled); // 🚀 确保同步到前端

        } catch (Exception e) {
            log.error("监控数据采集异常", e);
        }
    }

    public Map<String, Object> getSystemStatus() {
        return systemCache;
    }
}