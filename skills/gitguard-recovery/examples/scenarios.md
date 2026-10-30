# 可观察场景

通过场景：feature/wrong 的单父提交复制到 feature/right，原引用保持不变；明确后续错误分支处理需另授权。

拒绝场景：reset --hard 清掉用户修改、强推重写别人历史，或网络超时后重复 cherry-pick。

未知场景：缺少已确认规范、来源证据或真实远端观察时，输出具体 unknown/unverified，不伪造 PASS。

输出应至少包含仓库、规则修订、branch/HEAD、结论、证据层级和未完成项。
