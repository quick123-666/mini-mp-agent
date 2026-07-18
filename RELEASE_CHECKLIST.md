# Release 收尾指南

仓库地址: https://github.com/quick123-666/mini-mp-agent

> 这份指南是 v1.0.1 发布时的可手点步骤清单。完成后可删除本文件。

---

## 1. 粘贴 Release notes（2 min）

1. 打开 https://github.com/quick123-666/mini-mp-agent/releases/new
2. **Choose a tag**: 选择已有 tag `v1.0.1`
3. **Release title**: `v1.0.1 — wiki method-tree classification`
4. **Description**: 粘贴 `RELEASE_NOTES_v1.0.1.md` 的全文（不含本指南内容）
5. 勾上 **Set as the latest release**
6. 点 **Publish release**

---

## 2. 加 topics（30 秒）

打开 https://github.com/quick123-666/mini-mp-agent 右上 ⚙️ About → topics 字段，输入（建议前 5 个）：

- `single-agent`
- `pwr-loop`
- `karpathy-wiki`
- `asyncio`
- `zero-deps`

可选追加：`llm-wiki` `wiki-classification` `methods-tree`

---

## 3. About 描述（30 秒）

紧邻 topics 的 Description 字段填入（单行 ≤350 字）：

`single-agent multi-role PWR Loop with Karpathy LLM Wiki — 5 modes, 18-method work tree, stdlib-only, 307 tests`

Website 留空，勾选 **Include in the homepage**。

---

## 4. 等 CI 跑通后贴 badge（1 min）

打开 https://github.com/quick123-666/mini-mp-agent/actions 等待 `tests` workflow ✅

复制此 markdown 片段到 `README.md` 顶部（标题正下方）：

```markdown
[![tests](https://github.com/quick123-666/mini-mp-agent/actions/workflows/test.yml/badge.svg)](https://github.com/quick123-666/mini-mp-agent/actions/workflows/test.yml)
```
