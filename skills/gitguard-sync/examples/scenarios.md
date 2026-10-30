# 可观察场景

通过场景：feature 合入 develop：切到 develop 后明确来源，预览再 merge；push origin develop 单独授权。

拒绝场景：省略目标后按不可信 upstream 自动 push，或以 --force-with-lease 当作默认安全同步。

未知场景：缺少已确认规范、来源证据或真实远端观察时，输出具体 unknown/unverified，不伪造 PASS。

输出应至少包含仓库、规则修订、branch/HEAD、结论、证据层级和未完成项。
