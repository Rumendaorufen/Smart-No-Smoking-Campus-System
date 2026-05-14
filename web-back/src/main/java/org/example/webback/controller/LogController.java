package org.example.webback.controller;

import org.example.webback.common.Result;
import org.example.webback.dto.VueLogDto;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/logs")
public class LogController {

    private static final Logger frontendLog = LoggerFactory.getLogger("FrontendLog");

    @PostMapping
    public Result<?> report(@RequestBody VueLogDto dto) {
        Map<String, Object> doc = new LinkedHashMap<>();
        doc.put("service", "web-vue");
        doc.put("level", dto.getLevel() != null ? dto.getLevel() : "ERROR");
        doc.put("message", dto.getMessage());
        doc.put("endpoint", dto.getEndpoint());
        doc.put("trace_id", dto.getTraceId());
        doc.put("user_id", dto.getUserId());
        doc.put("metadata", dto.getMetadata());
        doc.put("timestamp", Instant.now().toString());

        frontendLog.error(toJson(doc));
        return Result.success();
    }

    private String toJson(Map<String, Object> doc) {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, Object> e : doc.entrySet()) {
            if (!first) sb.append(",");
            first = false;
            sb.append("\"").append(e.getKey()).append("\":");
            if (e.getValue() instanceof String) {
                sb.append("\"").append(escapeJson((String) e.getValue())).append("\"");
            } else {
                sb.append(e.getValue());
            }
        }
        sb.append("}");
        return sb.toString();
    }

    private String escapeJson(String s) {
        return s.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}
