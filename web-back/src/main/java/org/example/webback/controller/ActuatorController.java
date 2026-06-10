package org.example.webback.controller;

import org.example.webback.service.SystemMonitorService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

/**
 * Exposes /actuator/health and /actuator/metrics for the copilot-back alert engine.
 * Does not require Spring Boot Actuator dependency.
 */
@RestController
public class ActuatorController {

    @Autowired
    private SystemMonitorService systemMonitorService;

    @GetMapping("/actuator/health")
    public Map<String, Object> health() {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "UP");
        result.put("service", "web-back");
        return result;
    }

    @GetMapping("/actuator/metrics")
    public Map<String, Object> metrics() {
        Map<String, Object> sys = systemMonitorService.getSystemStatus();
        Map<String, Object> result = new HashMap<>();
        result.put("cpu", Map.of("percent", sys.getOrDefault("cpu", 0)));
        result.put("memory", Map.of("percent", sys.getOrDefault("ramPercent", 0),
                                    "used_gb", sys.getOrDefault("ramUsed", 0)));
        result.put("disk", sys.getOrDefault("disk", Map.of()));
        result.put("gpu", sys.getOrDefault("gpu", Map.of()));
        return result;
    }
}
