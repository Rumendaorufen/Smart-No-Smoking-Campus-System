package org.example.webback.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.webback.entity.Device;
import org.example.webback.mapper.DeviceMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.CompletableFuture;

@Service
public class DeviceService extends ServiceImpl<DeviceMapper, Device> {

    private static final Logger log = LoggerFactory.getLogger(DeviceService.class);

    @Autowired
    private RestTemplate restTemplate;

    /**
     * 1. 获取所有设备 (前端通常 5-10秒 轮询一次即可)
     */
    public List<Device> listAllDevices() {
        return this.list(new LambdaQueryWrapper<Device>()
                .orderByDesc(Device::getId));
    }

    /**
     * 2. 添加设备
     */
    public void addDevice(Device device) {
        long count = this.count(new LambdaQueryWrapper<Device>().eq(Device::getName, device.getName()));
        if (count > 0) throw new RuntimeException("设备名称已存在");

        device.setStatus(0);
        device.setEnabled(true);
        device.setCreatedAt(LocalDateTime.now());
        this.save(device);
    }

    /**
     * 3. 更新设备：通知 Python 停用或重连
     */
    public void updateDevice(Integer id, Device form) {
        Device device = this.baseMapper.selectById(id);
        if (device == null) throw new RuntimeException("设备不存在");

        boolean needsSync = false;

        if (form.getName() != null) device.setName(form.getName());

        // 1. 修改 RTSP 地址逻辑
        if (form.getRtspUrl() != null && !form.getRtspUrl().equals(device.getRtspUrl())) {
            device.setRtspUrl(form.getRtspUrl());
            device.setStatus(0);
            needsSync = true;
        }

        // 2. 启停状态变更联动 (核心改动) 🚀
        if (form.getEnabled() != null && !form.getEnabled().equals(device.getEnabled())) {
            device.setEnabled(form.getEnabled());
            // 如果设置为停用，强制将 status 设为 0（离线）
            if (!form.getEnabled()) {
                device.setStatus(0);
            }
            needsSync = true;
        }

        device.setUpdatedAt(LocalDateTime.now());
        this.updateById(device);

        // 异步通知 Python
        if (needsSync) {
            CompletableFuture.runAsync(this::notifyPythonSync);
        }
    }

    /**
     * 4. 接收 Python 通知（核心：Java 不再主动 Ping，只管收信）
     */
    public void syncDeviceStatus(Integer id, Integer status) {
        // 🚀 快速检查，减少不必要的数据库交互
        Device device = this.baseMapper.selectById(id);
        if (device == null || device.getStatus().equals(status)) return;

        device.setStatus(status);
        device.setUpdatedAt(LocalDateTime.now());
        this.baseMapper.updateById(device);
        log.info("📡 设备 {} 状态同步为: {}", id, status == 1 ? "在线" : "离线");
    }

    /**
     * 5. 移除“主动探测”逻辑 (checkAndUpdateStatus 方法已废弃)
     * 现在的 status 检查直接读数据库字段即可。
     */
    public int getDeviceStatus(Integer id) {
        Device device = this.baseMapper.selectById(id);
        return device != null ? device.getStatus() : 0;
    }

    private void notifyPythonSync() {
        try {
            // 设置一个短超时，防止 Python 挂掉时 Java 线程卡死
            // 如果你的 RestTemplate 没有配置超时，建议在这里临时处理
            String url = "http://localhost:5000/api/v1/monitor/sync";
            restTemplate.postForEntity(url, null, String.class);
            log.info("🔔 已成功同步状态至 Python 引擎");
        } catch (Exception e) {
            // 仅仅记录警告，不要抛出异常影响 Java 端的业务逻辑
            log.warn("⚠️ 无法连接到 Python 引擎 (可能未启动): {}", e.getMessage());
        }
    }
}