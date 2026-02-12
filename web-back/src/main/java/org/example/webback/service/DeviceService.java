package org.example.webback.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.webback.entity.Device;
import org.example.webback.mapper.DeviceMapper;
import org.springframework.stereotype.Service;

import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URI;
import java.time.LocalDateTime;
import java.util.List;

@Service
public class DeviceService extends ServiceImpl<DeviceMapper, Device> {

    /**
     * 获取所有设备 (ID 倒序)
     */
    public List<Device> listAllDevices() {
        return this.list(new LambdaQueryWrapper<Device>()
                .orderByDesc(Device::getId));
    }

    /**
     * 添加设备
     */
    public void addDevice(Device device) {
        long count = this.count(new LambdaQueryWrapper<Device>().eq(Device::getName, device.getName()));
        if (count > 0) throw new RuntimeException("设备名称已存在");

        device.setStatus(0); // 默认离线
        device.setEnabled(true);
        device.setCreatedAt(LocalDateTime.now());
        this.save(device);
    }

    /**
     * 更新设备
     */
    public void updateDevice(Integer id, Device form) {
        Device device = this.getById(id);
        if (device == null) throw new RuntimeException("设备不存在");

        if (form.getName() != null) device.setName(form.getName());

        // 如果修改了 RTSP 地址，重置状态
        if (form.getRtspUrl() != null && !form.getRtspUrl().equals(device.getRtspUrl())) {
            device.setRtspUrl(form.getRtspUrl());
            device.setStatus(0);
        }

        if (form.getEnabled() != null) device.setEnabled(form.getEnabled());

        device.setUpdatedAt(LocalDateTime.now());
        this.updateById(device);
    }

    /**
     * 检测并更新在线状态
     */
    public int checkAndUpdateStatus(Integer deviceId) {
        Device device = this.getById(deviceId);
        if (device == null) throw new RuntimeException("设备不存在");

        if (!device.getEnabled()) return 0; // 已停用则视为离线

        boolean isOnline = checkSocketConnect(device.getRtspUrl());

        device.setStatus(isOnline ? 1 : 0);
        this.updateById(device);

        return device.getStatus();
    }

    // 辅助方法：Socket 连接测试
    private boolean checkSocketConnect(String url) {
        try {
            // 简单解析 rtsp://admin:pass@192.168.1.1:554/stream
            URI uri = URI.create(url);
            String host = uri.getHost();
            int port = uri.getPort() == -1 ? 554 : uri.getPort();

            if (host == null) return false;

            try (Socket socket = new Socket()) {
                // 2秒超时，避免卡顿
                socket.connect(new InetSocketAddress(host, port), 2000);
                return true;
            }
        } catch (Exception e) {
            return false;
        }
    }

    /**
     * 接收外部（Python）通知，直接更新设备在线状态
     * 这种方式比 Socket 探测更准确，因为 Python 是真正连接流的一方
     */
    public void syncDeviceStatus(Integer id, Integer status) {
        Device device = this.getById(id);
        if (device == null) return;

        // 如果状态没变，就不更新数据库，节省性能
        if (device.getStatus().equals(status)) return;

        device.setStatus(status);
        device.setUpdatedAt(LocalDateTime.now());
        this.updateById(device);
    }
}