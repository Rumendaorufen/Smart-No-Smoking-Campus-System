package org.example.webback.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.webback.entity.AiConversation;

/**
 * AI 对话列表 Mapper 接口
 */
@Mapper
public interface AiConversationMapper extends BaseMapper<AiConversation> {
    // 继承 BaseMapper 即可，基础的 insert, selectById, deleteById 已经自动生成了
}