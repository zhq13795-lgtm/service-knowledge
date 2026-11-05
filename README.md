# Service Knowledge

客服场景的轻量知识检索与问答工具。导入业务说明后，可以查询相关资料，并通过回答中的引用编号查看原始片段。

## 功能

- 导入 UTF-8 编码的 Markdown / TXT 文件，自动切分并保存到 SQLite。
- 使用英文单词、中文双字片段分词和 BM25 评分检索相关内容。
- 从命中的资料中整理回答摘录，返回来源文件和片段位置；无匹配时提示补充资料。
- 自带虚构的退换货、配送及发票说明，首次运行自动载入。

## 运行

需要 Python 3.11+，无需数据库服务和 API Key。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000`，点击示例问题即可查询，也可以上传自己的文本资料。

接口文档：`http://127.0.0.1:8000/docs`。

知识库保存在 `.local/knowledge.db`，重启后保留。该目录、虚拟环境与环境配置均不提交到 Git。当前回答采用本地摘录方式，不调用生成模型；服务默认仅监听本机地址。

## 目录

```text
app/        文档存储、切分、检索和问答接口
web/        页面
samples/    虚构业务资料
tests/      基本功能检查
```

```powershell
python -m unittest discover -s tests
```
