package org.example.webback.service;

import cn.hutool.core.map.MapUtil;
import cn.hutool.jwt.JWTUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.example.webback.entity.User;
import org.example.webback.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;

@Service
public class AuthService {

    @Autowired
    private UserMapper userMapper;

    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();
    // 密钥 (实际开发请放入 application.yml)
    private static final byte[] JWT_KEY = "your_secret_key".getBytes();

    /**
     * 登录逻辑
     */
    public Map<String, Object> login(String username, String password, String ip) {
        // 1. 查用户
        User user = userMapper.selectOne(new LambdaQueryWrapper<User>()
                .eq(User::getUsername, username));

        if (user == null) {
            throw new RuntimeException("账号不存在");
        }

        // 2. 校验密码 (如果你是刚从 Python 迁移，且旧密码是明文/旧算法，这里可能需要兼容)
        // 这里假设是新用户或已重置为 BCrypt 密码
        if (!passwordEncoder.matches(password, user.getPassword())) {
            throw new RuntimeException("密码错误");
        }

        // 3. 校验状态
        if (user.getStatus() != null && user.getStatus() != 1) {
            throw new RuntimeException("账号已被禁用");
        }

        // 4. 更新登录信息
        user.setLastLoginIp(ip);
        user.setLastLoginTime(LocalDateTime.now());
        userMapper.updateById(user);

        // 5. 生成 Token
        String token = JWTUtil.createToken(MapUtil.of("uid", user.getId()), JWT_KEY);

        return MapUtil.builder(new java.util.HashMap<String, Object>())
                .put("token", token)
                .put("userInfo", user)
                .build();
    }

    /**
     * 获取当前用户信息
     */
    public User getCurrentUser(Long uid) {
        User user = userMapper.selectById(uid);
        if (user == null) throw new RuntimeException("用户不存在");
        user.setPassword(null); // 不返回密码
        return user;
    }
}