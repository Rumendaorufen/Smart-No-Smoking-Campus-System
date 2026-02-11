package org.example.webback.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.webback.entity.User;

@Mapper
public interface UserMapper extends BaseMapper<User> {
}