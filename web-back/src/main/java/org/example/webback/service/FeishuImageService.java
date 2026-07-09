package org.example.webback.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Service
public class FeishuImageService {

    private static final Logger log = LoggerFactory.getLogger(FeishuImageService.class);
    private static final String UPLOAD_URL = "https://open.feishu.cn/open-apis/im/v1/images";

    @Autowired
    private FeishuTokenService tokenService;
    @Autowired
    private RestTemplate restTemplate;

    /**
     * 从公网 URL 下载截图并上传到飞书
     * @return image_key，失败返回 null
     */
    public String uploadImage(String imageUrl) {
        if (imageUrl == null || imageUrl.isBlank()) return null;

        try {
            String token = tokenService.getToken();

            // 1. 下载截图
            ResponseEntity<byte[]> downloadResp = restTemplate.exchange(
                    imageUrl, HttpMethod.GET, null, byte[].class);
            byte[] imageBytes = downloadResp.getBody();
            if (imageBytes == null || imageBytes.length == 0) {
                log.warn("截图下载为空: {}", imageUrl);
                return null;
            }

            // 2. 构建 multipart 请求上传飞书
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);
            headers.setBearerAuth(token);

            ByteArrayResource imageResource = new ByteArrayResource(imageBytes) {
                @Override
                public String getFilename() {
                    return "alarm_snapshot.jpg";
                }
            };

            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("image_type", "message");
            body.add("image", imageResource);

            HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

            ResponseEntity<Map> response = restTemplate.exchange(
                    UPLOAD_URL, HttpMethod.POST, requestEntity, Map.class);

            Map responseBody = response.getBody();
            if (responseBody != null && responseBody.get("data") instanceof Map) {
                Map data = (Map) responseBody.get("data");
                String imageKey = (String) data.get("image_key");
                log.debug("截图上传飞书成功, image_key: {}", imageKey);
                return imageKey;
            }

            log.warn("飞书图片上传响应异常: {}", responseBody);
            return null;
        } catch (Exception e) {
            log.warn("截图上传飞书失败: {}", e.getMessage());
            return null;
        }
    }
}
