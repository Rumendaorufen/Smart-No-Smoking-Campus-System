

# 📝 开发记录：大模型流式输出与格式化异常排查与修复

## 1. 背景与目标
在**智慧校园禁烟监控系统**的 AI 数据分析助手开发中，我们采用了 Vue3 + SpringBoot(或Flask) + LangChain 的架构，通过 Server-Sent Events (SSE) 实现大模型的打字机流式输出。
在联调过程中，遇到了一系列因**前端正则误伤、网络层断包、底层协议裁切以及 Python 异步生命周期**导致的极其隐蔽的 Bug。特此记录排查与修复过程。

---

## 2. 核心问题现象描述
1. **Markdown 表格解析失效**：后端返回的 Markdown 表格文本正常，但前端渲染成了纯文本（没有表格框线）。
2. **无序列表渲染失败（吞空格）**：AI 返回的 `- 文本`，在前端流式打字时变成了 `-文本`（丢失了中间的空格），导致 Markdown 无法将其识别为列表。并且**刷新页面（全量加载）后显示却正常**。
3. **后端控制台协程连环报错**：控制台频繁抛出 `RuntimeWarning: coroutine was never awaited`、`Task was destroyed` 以及 `WinError 6 句柄无效` 等异步崩溃错误。
4. **Flask 流式接口报空指针**：请求时直接报错 `TypeError: 'NoneType' object is not iterable`。

---

## 3. 问题根因分析与解决历程

### 阶段一：前端正则误伤导致 Markdown 失效
* **问题 1：表格变文本**
  * **根因**：原前端代码 `.replace(/^(\|)/gm, '\n\n$1')` 过于激进，在表格的**每一行**前面都强行插入了两个换行符，切断了表格内部的连续性，导致 markdown-it 无法解析。
  * **修复**：修改正则，仅在“上一行不是换行也不是表格线”的情况下添加前置空行：
    ```javascript
    text = text.replace(/([^\n|])\n\|/g, '$1\n\n|');
    ```
* **问题 2：列表空格被误删**
  * **根因**：原代码 `line.substring(5).replace(/^\s/, '')` 粗暴地去掉了每个数据块（Chunk）开头的所有空白字符，导致单独成块的“空格”被直接吞噬。
  * **初步修复**：精准切分数据头，仅去掉 `data:` 和紧跟的一个可选空格。
    ```javascript
    let content = line.replace(/^data:\s?/, '');
    ```

### 阶段二：SSE 网络断包导致的“字块丢失”
* **现象**：虽然修改了正则，但偶尔还是会出现丢空格的情况，依然是“刷新后就正常”。
* **根因**：TCP 网络传输或底层代理存在**拆包/半包**现象。大模型吐出的数据 `data: - \n\n` 可能被网络切成了 `data: -` 和 ` \n\n` 两个包。前端原逻辑拿到不完整的包（没有 `data:` 开头）就直接丢弃了。
* **修复**：在前端引入**数据缓冲池（Buffer）**。
  ```javascript
  let buffer = '';
  // 收到 value 后先追加到 buffer
  buffer += decoder.decode(value, { stream: true });
  // 按事件结束符拆分
  const events = buffer.split('\n\n');
  // 🌟 核心：将最后一块不完整的数据 pop 出来保留在 buffer 中等待下一次拼接
  buffer = events.pop() || ''; 
  // 遍历处理 events...
  ```

### 阶段三：网络协议层“尾随空格（Trailing Space）裁切”
* **现象**：加入了 Buffer 之后，极少数情况下的空格还是会丢失。
* **根因**：部分网络中间件（如 Nginx、WSGI 容器、浏览器底层机制）在处理纯文本流时，为了节省带宽，会自动**裁切每一行末尾的空白字符**。当 Python 发出 `data:  \n\n` 时，到达前端变成了 `data:\n\n`。
* **终极修复（占位符保护法）**：在后端将空格伪装起来，避开网络层的裁切，到达前端后再还原。
  * **Python 后端加密**：
    ```python
    safe_chunk = clean.replace('\n', '<<br>>').replace(' ', '<<sp>>')
    yield f"data: {safe_chunk}\n\n"
    ```
  * **Vue 前端解密**：
    ```javascript
    let content = line.replace(/^data:\s?/, '').replace(/<<br>>/g, '\n').replace(/<<sp>>/g, ' ');
    ```

### 阶段四：Python Asyncio 与 LangChain 整合踩坑
* **现象**：后端抛出 `NameError: name 'is_sql' is not defined` 以及各种 Asyncio 句柄崩溃。
* **根因**：
  1. 拦截 SQL 的逻辑变量未清理干净，导致程序触发异常。
  2. Python 异步机制中，`loop.shutdown_asyncgens()` 不能在正在运行的异步函数内部调用。如果发生异常，finally 块在异步上下文中强制销毁事件循环，引发了“连环爆炸”。
  3. Flask 接口报错是因为主函数在处理完异步线程后，忘记了 `return generate()` 将生成器暴露给 Flask。
* **修复**：
  * 彻底移除基于字符串的 `is_sql` 拦截，改用原生安全的 `if not event["data"]["chunk"].tool_call_chunks:` 拦截工具调用输出。
  * 将 `loop.shutdown_asyncgens()` 移到异步函数外层的普通 `finally` 块中。
  * 确保生成器工厂函数被正确 `return` 给 `stream_with_context`。

---

## 4. 架构经验与总结

1. **“刷新就好”是排查流式传输问题的黄金线索**：只要页面一刷新历史记录就正常，说明大模型产出的数据、数据库存储的数据 100% 没问题。所有的锅都在**传输过程（网络裁切/断包）**或**流式渲染前端逻辑（错位解析）**上。
2. **永远不要信任流式数据的完整性**：在前端处理 SSE 或 WebSocket 时，必须通过 Buffer 缓冲池思想应对 TCP 粘包/半包问题。
3. **保护脆弱的格式字符**：空格、换行等格式控制符在复杂的代理网络中极其容易被当作“无用字符”抹杀。使用自定义占位符（如 `<<sp>>`、`<<br>>`）进行传输，再在终端还原，是目前最稳妥的防御性编程策略。
4. **LangChain v2 事件流过滤**：在最新的 LangChain 工具调用体系中，过滤内部思考/工具执行（如 SQL 查询），应利用 `astream_events` 的事件类型（`on_tool_start`、`tool_call_chunks`），而不是通过正则或字符串去匹配 AI 的回答。