package org.example.webback.service;

import cn.hutool.core.map.MapUtil;
import cn.hutool.jwt.JWT;
import cn.hutool.jwt.JWTUtil;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.util.Map;

@Service
public class JwtService {

    private final byte[] signingKey;

    public JwtService(@Value("${jwt.secret}") String secret) {
        if (secret == null || secret.length() < 32) {
            throw new IllegalArgumentException("jwt.secret must contain at least 32 characters");
        }
        this.signingKey = secret.getBytes(StandardCharsets.UTF_8);
    }

    public String createToken(Long userId) {
        Map<String, Object> payload = MapUtil.of("uid", userId);
        return JWTUtil.createToken(payload, signingKey);
    }

    public Long verifyAndGetUserId(String token) {
        if (!JWTUtil.verify(token, signingKey)) {
            throw new IllegalArgumentException("invalid JWT signature");
        }
        JWT jwt = JWTUtil.parseToken(token);
        Object uid = jwt.getPayload("uid");
        if (uid == null) {
            throw new IllegalArgumentException("JWT uid is missing");
        }
        return Long.valueOf(uid.toString());
    }
}
