# AI Test Platform PRD - Workspace 模块

> 来源：对话记录第 582-647 行（原文第三章节）

## 功能目标

建立AI测试上下文。

## 功能列表

```
Workspace
├ 创建空间
├ 系统信息
├ 技术栈信息
├ 环境配置
├ 测试范围
├ AI上下文
└ 知识概览
```

## 创建Workspace

输入：

基础信息
- 系统名称
- 系统地址
- 描述
- 负责人

技术信息
- 前端: React/Vue
- 后端: Spring/FastAPI
- 数据库: MySQL/PostgreSQL
- 接口: REST/gRPC

AI初始化

AI执行：
- 扫描系统
- 解析接口
- 建立知识图谱
- 生成测试建议