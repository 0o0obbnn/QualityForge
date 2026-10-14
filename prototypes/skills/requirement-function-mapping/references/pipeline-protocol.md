# 流水线与断点续跑协议

统一入口覆盖 Markdown 发现、归一、类型化、校验和 HTML；提供需求评审时继续完成评审投影与测试设计输入编译。

```bash
python3 scripts/run_pipeline.py --source <需求.md> --out-dir <输出目录>
python3 scripts/run_pipeline.py --source <需求.md> --source-review <资料依赖评审.json> --out-dir <输出目录>
python3 scripts/run_pipeline.py --source <需求.md> --source-review <资料依赖评审.json> --review <六维需求评审.json> --out-dir <输出目录>
python3 scripts/run_pipeline.py --source <需求.md> --out-dir <输出目录> --resume
```

## 续跑不变量

- 每阶段指纹包含输入文件、执行脚本和命令参数的 SHA-256。
- 只有阶段状态为 `COMPLETED`、指纹一致、输出存在且输出哈希一致时才能复用。
- 源文件、资料依赖评审、六维需求评审、上游输出、脚本或参数任一变化，都必须从受影响阶段重新执行。
- `--from-stage` 只允许在全部前置输出存在时使用；它是人工指定边界，不冒充哈希验证。
- 校验失败写入 `pipeline-state.json` 并停止后续阶段。
- 默认流水线只处理正文及显式结构化资料，不调用 OCR，也不以图片处理状态阻塞正文图谱。明确要求视觉核验时在主链之外按可选视觉证据契约执行。
- 存在六维需求评审时，流水线默认使用 `--ready-only` 编译测试设计输入。包级评审未全部通过不停止已确认范围交付；待确认项保留在评审队列和完整图谱中。

可用阶段可通过 `scripts/run_pipeline.py --help` 和状态文件查看。`--through-stage` 用于停在指定门禁，`--from-stage` 用于从已确认边界继续。
