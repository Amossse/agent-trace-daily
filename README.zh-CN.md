# Agent 执行轨迹日报

[English](README.md)

一个汇总 Agent 昨日执行记录的 Skill，包含任务、项目变更、文件访问和产出候选，并保留完整的可观察事件序列。采集脚本只读选定的本地日志，Agent 根据证据整理日报，不执行日志里的命令。

安装器会立即告知 Agent：需要创建每日定时任务，默认按用户选定时区每天上午 11:00 运行，用户可以改时间。仅打印指令不代表定时任务已创建，必须由宿主定时工具创建并读回确认。手动复制 Skill 目录的宿主，需要首次调用完成引导。

## 安装

需要 Python 3.11 及以上版本。Windows 使用 IANA 时区时可能需要安装 `tzdata`；固定偏移量 `+08:00` 不需要该依赖，但不适用于夏令时地区的自动切换。

```sh
git clone https://github.com/Amossse/agent-trace-daily.git
cd agent-trace-daily
python scripts/trace_daily.py install --agent codex --timezone Asia/Shanghai
```

Claude Code 使用 `--agent claude`。改成上午 09:30，添加 `--time 09:30`。安装器默认选择对应宿主的本地会话目录，不扫描整台机器。多个来源可以重复指定 `--source`，其他 Agent 可使用通用 JSONL 格式。

默认日报仅含匿名标识和结构信息，隐藏任务原文、路径和参数。若要查看可读的任务与结果摘要，用户可明确添加 `--include-text`；这些脱敏预览仍可能包含隐私或内部信息，只适合保存在本机，不能直接公开。

安装后将输出的 `agent_instruction` 告知 Agent，或发送：

```text
使用 agent-trace-daily，按已安装的 LOCAL_SETUP.md 创建每日定时任务。
默认按配置时区每天上午 11:00 运行，汇总昨日执行轨迹。
先检查是否已有同一任务，创建后读回确认实际时间、时区和下次运行。
日志和日报只保存在本机，不上传，不创建重复定时任务。
```

宿主没有持久定时能力时，必须明确报告待创建，并给出手动运行命令。本项目不会偷偷修改系统 cron、安装后台服务或声称所有 Agent 都有安装钩子。

## 先跑一个虚构示例

```sh
python scripts/trace_daily.py report --source jsonl:examples/demo.jsonl \
  --timezone Asia/Shanghai --date 2026-10-06 \
  --output-dir ../trace-demo-output --include-text
```

示例应得到两个任务、七个事件、一个工作目录项目、两个明确文件路径和一次失败工具调用。JSON 与中文 Markdown 输出到指定目录，不能写入开源仓库或 Skill 目录。重复生成默认拒绝覆盖，审查后才可使用 `--replace`。

安装后，日报任务运行已安装的脚本，并传入本地配置：

```sh
python /path/to/installed/agent-trace-daily/scripts/trace_daily.py report \
  --config /path/to/private/config.json --date yesterday
```

“昨日”每次按配置时区重新计算，范围为昨天零点至今天零点，包含开始、不包含结束。跨午夜任务按事件时间统计，不能只查文件名里带昨天日期的会话。夏令时切换日可能有 23 或 25 小时。

## 日报中的证据边界

任务包含用户请求和 Agent 自述，后者不能当作已验证完成。项目以工作目录作为标识，未自动验证 Git 根目录。明确的写入调用及对应成功结果，可以确认该操作；shell 成功退出不能证明某个文件发生变更。

文件访问统计明确记录的 Read、Edit、Write 和补丁路径。复杂 shell、JS 包装工具内部的文件操作可能无法还原，会列为覆盖边界。沉淀包含显式导出的产出事件和确认写入的文件候选，不凭文件名猜测长期记忆已保存。

首版支持 Codex、Claude Code 本地 JSONL，以及其他 Agent 的通用导出格式。只覆盖已配置且可读取的记录，不能保证所有 Agent 的全部真实行为。缺失、损坏、未知格式、孤立结果和扫描上限会列出；没有记录不等于没有执行。原始思考、工具输出和完整对话不复制进日报，详情可按本地证据行定位。

## 修改时间与停止

```sh
python /path/to/installed/scripts/trace_daily.py schedule \
  --config /path/to/private/config.json --time 09:30
```

这条命令更新期望时间并输出 Agent 指令，不会自行修改宿主定时任务。让 Agent 更新原有任务，读回确认后记录实际 ID。修改时区可用 `--timezone`。暂停或停止通过宿主定时工具处理对应任务，不删除历史日报或执行记录。

## 隐私、限制与贡献

默认本地状态目录为 `~/.agent-trace-daily`，可通过 `--state-dir` 修改；旧安装和配置不会覆盖。文件在 POSIX 系统以 0600 创建，新建私有目录为 0700；Windows 依赖目录 ACL。符号链接路径会被拒绝，需要使用物理路径。

默认扫描上限为 256 MiB、10,000 个文件、每行 2 MiB，超限必须报告缺口。前两项可以通过明确参数提高，逐文件缓冲可能占用较多内存。文本预览最多 1,000 个字符，脱敏不能保证识别全部秘密。JSON 与 Markdown 分别原子写入，并非跨文件事务；I/O 失败可能只留下其中一个文件。

脚本不调用模型、不联网、不修改项目，也不清理历史。Agent 宿主和模型提供方仍可能处理其读取的内容，使用真实记录前需检查相应隐私设置。不要把真实日志、日报或配置作为开源问题附件。

```sh
python -m unittest discover -s tests -v
```

测试只用虚构数据与临时目录。详见 [验证记录](VALIDATION.md)、[安全说明](SECURITY.md)、[贡献说明](CONTRIBUTING.md)、[更新记录](CHANGELOG.md)和 [MIT 许可证](LICENSE)。中英文推广文案在 [LAUNCH.md](LAUNCH.md)，未代发。

扫描先按文件更新时间排序，在所有来源间优先读取近期更新的日志；更新时间仅决定预算分配顺序，不排除旧会话，事件仍按时间戳筛选。覆盖信息区分当日解析缺口和整个扫描的读取、预算缺口，并记录扫描文件数和字节数。functions.exec 内的工具名称仅作为静态引用展示，不证明执行、成功或文件操作。

增量日报在 reports 同级的 cache 目录保存仅本人可读的检查点：来源身份、字节和行位置、规范化事件及待匹配调用。结构模式不保存任务原文或工具参数；开启文本后只保存有长度限制的尽力脱敏预览。每次校验历史前缀哈希，追加日志仅解析新字节；截断、替换、前缀改写、缓存损坏或解析器版本变化时重新解析该文件。未结束的最后一行等追加完整后重试。首次扫描仍受预算限制，可能不完整；后续运行可以继续。历史报告不覆盖。--no-cache 可关闭缓存。前缀校验仍读取历史数据，报告单独统计校验字节，不计入新增解析预算。缓存不会上传，也不会改写来源日志。

证据分层：observation 是日志直接记录的事件或结果；claim 是 Agent 自述；inference 是静态工具引用或产出候选；unknown 是未确认结果。这些标签不代表业务目标已经完成。设计借鉴 [REA 的证据分层和快照复用](https://github.com/morluto/rea/blob/main/docs/cli.md)，未引入 REA 运行依赖，也不启用进程采集或重放历史命令。
