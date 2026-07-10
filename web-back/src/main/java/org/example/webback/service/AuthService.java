package org.example.webback.service;

import cn.hutool.core.map.MapUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import org.example.webback.entity.User;
import org.example.webback.mapper.UserMapper;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;

@Service
public class AuthService {

    private final UserMapper userMapper;
    private final BCryptPasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public AuthService(UserMapper userMapper,
                       BCryptPasswordEncoder passwordEncoder,
                       JwtService jwtService) {
        this.userMapper = userMapper;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

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
        String token = jwtService.createToken(user.getId().longValue());
        user.setPassword(null);

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
