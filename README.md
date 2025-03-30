## Typogen

将 Windows 显示字体替换为任何字体

## 原理

将字体的属性信息修改为微软雅黑 (Microsoft YaHei)，微软雅黑 UI (Microsoft YaHei UI)，宋体，新宋体 (SimSun) 来欺骗 Windows

## 用法

安装依赖

```
pip install -r requirements.txt
```

准备一份目标字体文件，应该包含至少 3 种字重

- **Light**.ttf
- **Regular**.ttf
- **Bold**.ttf

将以上 3 个文件复制到 Input 目录

运行脚本

```
python app.py
```

脚本会首先会备份目前的字体文件到 Backup 目录

待运行结束后，如无错误发生，你会在 Output 目录下看见转换成果。共有 5 个文件

```
msyh.ttc
msyhbd.ttc
msyhl.ttc
simsun.ttc
simsunb.ttf
```

进入 Windows 设置 - 系统 - 恢复 - 高级启动，立即重新启动

进入高级选项 - 命令提示符，运行

```
xcopy <Output> C:\Windows\Fonts
```

选择全部覆盖，然后重新启动电脑

默认显示字体应该被替换为你自定义的字体

如果需要恢复为默认字体，则是运行

```
xcopy <Backup> C:\Windows\Fonts
```

