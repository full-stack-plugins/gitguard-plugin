# 工作流 JSON 契约

schema_version 固定 1.0.0，profile 为模型标识，revision 为递增正整数。顶层恰为 schema_version/profile/revision/roles/primary_remote/merge_method/commit_message_pattern/collaboration；未知字段与类型错误拒绝。

roles 为角色对象，字段恰为 name/pattern/required/allow_commit/create_from/merge_into。name 与 pattern 二选一，required 仅用于固定长期角色，布尔值必须是 JSON true/false；关系引用存在角色。Git 本身名称校验也需要通过。pattern 使用受限全匹配正则，不接受 lookaround、反向引用、量词分组和计数重复；最多一个单原子无界重复；不能用复杂正则阻塞门禁。

merge_method 为 merge/no-ff/ff-only/squash；首版执行拒绝自动 squash，需要独立提交方案。primary_remote 是明确远端名称；collaboration shared/fork 不代表外发授权。commit_message_pattern 可为 null；启用时需要完整消息。

候选例外通过角色/命名/关系正常修订并显式 activate，不支持临时免检参数。模板见本目录 profiles/。模板是起点，需要与项目历史、发布方式和用户约定核对。既有契约不被模板自动取代。
