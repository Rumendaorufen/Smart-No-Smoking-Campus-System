package org.example.webback.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class AlarmReportDTO {
    @JsonProperty("deviceId") // 🚀 告诉 Jackson：JSON 里的 deviceId 映射到这个变量
    private Integer cameraId;

    private String type;
    private Float confidence;

    @JsonProperty("snapshotUrl") // 确保与 Python 端的字段名完全一致
    private String snapshotUrl;

    private String videoUrl;
    private String description;
}