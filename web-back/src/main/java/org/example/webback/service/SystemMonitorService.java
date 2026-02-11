package org.example.webback.service;

import cn.hutool.core.util.NumberUtil;
import lombok.Data;
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

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@EnableScheduling // 开启定时任务
public class SystemMonitorService {

    private final SystemInfo systemInfo = new SystemInfo();
    private final HardwareAbstractionLayer hardware = systemInfo.getHardware();
    private final OperatingSystem os = systemInfo.getOperatingSystem();

    // 缓存最新的系统状态 (线程安全)
    private final Map<String, Object> systemCache = new ConcurrentHashMap<>();

    // 保留上一次的 CPU 滴答数，用于计算差值
    private long[] prevTicks = new long[CentralProcessor.TickType.values().length];

    /**
     * 初始化
     */
    public SystemMonitorService() {
        // 初始化 CPU 滴答数
        prevTicks = hardware.getProcessor().getSystemCpuLoadTicks();
        // 初始化缓存结构
        systemCache.put("cpu", 0.0);
        systemCache.put("memory", new HashMap<>());
        systemCache.put("gpu", new HashMap<>());
        systemCache.put("disk", new HashMap<>());
    }

    /**
     * 🚀 核心任务：每秒执行一次 (fixedRate = 1000ms)
     * 对应 Python 代码中的 monitor_task while True 循环
     */
    @Scheduled(fixedRate = 1000)
    public void refreshSystemStatus() {
        try {
            // 1. CPU 使用率
            CentralProcessor processor = hardware.getProcessor();
            // 计算自上次更新以来的负载 (这种方式不会阻塞线程)
            double cpuLoad = processor.getSystemCpuLoadBetweenTicks(prevTicks) * 100;
            prevTicks = processor.getSystemCpuLoadTicks(); // 更新滴答数

            // 2. 内存使用
            GlobalMemory memory = hardware.getMemory();
            long totalMem = memory.getTotal();
            long availableMem = memory.getAvailable();
            long usedMem = totalMem - availableMem;

            Map<String, Object> memData = new HashMap<>();
            memData.put("total", formatGb(totalMem));
            memData.put("used", formatGb(usedMem));
            memData.put("free", formatGb(availableMem));
            memData.put("percent", NumberUtil.round((double) usedMem / totalMem * 100, 1).doubleValue());

            // 3. 磁盘使用 (只获取项目所在的磁盘)
            FileSystem fileSystem = os.getFileSystem();
            List<OSFileStore> fileStores = fileSystem.getFileStores();
            // 简单起见，我们取第一个主要磁盘，或者你可以遍历求和
            OSFileStore store = fileStores.isEmpty() ? null : fileStores.get(0);

            Map<String, Object> diskData = new HashMap<>();
            if (store != null) {
                long totalSpace = store.getTotalSpace();
                long usableSpace = store.getUsableSpace();
                long usedSpace = totalSpace - usableSpace;

                diskData.put("total", formatGb(totalSpace));
                diskData.put("used", formatGb(usedSpace));
                diskData.put("free", formatGb(usableSpace));
                diskData.put("percent", NumberUtil.round((double) usedSpace / totalSpace * 100, 1).doubleValue());
            }

            // 4. GPU 信息 (Java OSHI 获取 N卡 实时使用率比较难，这里做个静态展示)
            // 如果必须获取实时 GPU，建议让 Python 通过 HTTP 传给 Java，或者 Java 调用 nvidia-smi 命令行
            Map<String, Object> gpuData = new HashMap<>();
            var graphicsCards = hardware.getGraphicsCards();
            if (!graphicsCards.isEmpty()) {
                var card = graphicsCards.get(0);
                gpuData.put("name", card.getName());
                gpuData.put("vram", formatGb(card.getVRam()));
                gpuData.put("percent", 0); // OSHI 无法获取实时 GPU 负载
            } else {
                gpuData.put("name", "无独立显卡");
                gpuData.put("percent", 0);
            }

            // 更新缓存
            systemCache.put("cpu", NumberUtil.round(cpuLoad, 1).doubleValue());
            systemCache.put("memory", memData);
            systemCache.put("disk", diskData);
            systemCache.put("gpu", gpuData);

            // log.info("系统状态已更新: CPU={}%, RAM={}%", cpuLoad, memData.get("percent"));

        } catch (Exception e) {
            log.error("获取硬件信息失败", e);
        }
    }

    /**
     * 对外提供获取缓存的方法
     */
    public Map<String, Object> getSystemStatus() {
        return systemCache;
    }

    // 辅助：转 GB
    private double formatGb(long bytes) {
        return NumberUtil.round(bytes / 1024.0 / 1024.0 / 1024.0, 2).doubleValue();
    }
}