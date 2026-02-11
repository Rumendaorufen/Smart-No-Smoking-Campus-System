package org.example.webback.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.example.webback.entity.User;
import org.example.webback.mapper.UserMapper;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class UserService extends ServiceImpl<UserMapper, User> {

    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    /**
     * 判断是否是管理员
     */
    public boolean isAdmin(Long uid) {
        if (uid == null) return false;
        User user = this.getById(uid);
        return user != null && "admin".equals(user.getRole());
    }

    /**
     * 获取所有用户 (创建时间倒序)
     */
    public List<User> listAllUsers() {
        return this.list(new LambdaQueryWrapper<User>()
                .orderByDesc(User::getCreatedAt));
    }

    /**
     * 创建用户
     */
    public void createUser(User user) {
        // 1. 查重
        long count = this.count(new LambdaQueryWrapper<User>().eq(User::getUsername, user.getUsername()));
        if (count > 0) {
            throw new RuntimeException("账号已存在");
        }

        // 2. 密码加密
        if (StringUtils.hasText(user.getPassword())) {
            user.setPassword(passwordEncoder.encode(user.getPassword()));
        } else {
            throw new RuntimeException("密码不能为空");
        }

        user.setCreatedAt(LocalDateTime.now());
        // status 默认为 1 (正常)
        if (user.getStatus() == null) user.setStatus(1);

        this.save(user);
    }

    /**
     * 更新用户
     */
    public void updateUser(User form) {
        User user = this.getById(form.getId());
        if (user == null) throw new RuntimeException("用户不存在");

        // 更新角色和状态
        if (StringUtils.hasText(form.getRole())) user.setRole(form.getRole());
        if (form.getStatus() != null) user.setStatus(form.getStatus());

        // 更新密码 (只有输入了新密码才更新)
        if (StringUtils.hasText(form.getPassword())) {
            if (form.getPassword().length() < 5) {
                throw new RuntimeException("密码长度不能少于5位");
            }
            user.setPassword(passwordEncoder.encode(form.getPassword()));
        }

        this.updateById(user);
    }
}