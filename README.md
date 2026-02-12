# 100orange 内存修改器

使用 PySide6 + PyQt-Fluent-Widgets 的 Windows 游戏内存修改器示例。

## 运行方式

1. 安装依赖
2. 运行主程序

## 功能

- 进程检测与附加
- 实时读取并显示数值
- 修改数值并写入
- 快捷键操作
- 偏移配置
- 多语言（语言文件单独放在 i18n/）

## 多语言

- 语言文件：i18n/zh-CN.json、i18n/en-US.json
- 可在“设置”页切换语言（即时生效）
- 也可直接在 config.json 中修改：language

## 快捷键

- Ctrl+Alt+A：附加/分离进程
- Ctrl+Alt+R：刷新读取
- Ctrl+Alt+1：写入骰子效果
- Ctrl+Alt+2：写入骰子点数
- Ctrl+Alt+3：写入回合数量
