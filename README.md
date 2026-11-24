联邦元数据过期了还在用，一份被替换过的元数据把单点登录指向了别人的地址：签名只覆盖密钥描述符而实体标识可被替换；有效期只比较起始时间导致过期元数据仍可使用；有效期偏移在两端各加一次使窗口被放大一倍；实体标识用前缀比较导致相似标识互相命中；刷新判定只看缓存是否存在而不看到期时间；写入不检查实体标识重复导致后写覆盖先写；淘汰不清理索引导致失效实体仍可被查到；淘汰只删主记录导致密钥描述符仍残留；批量校验复用缓存实体导致第二个请求沿用第一个请求的实体；签名比较使用普通等号。meta/_impl.py 是核心，tests/test_metadata.py 15个红。要修的是：按上面的顺序把 10 个缺陷逐个修掉。

## 运行方式

在仓库根目录执行：

```
python -m pytest tests -q
```

初始状态应恰好得到 `15 failed`，0 error，且 15 个失败全部由 `NotImplementedError` 引起。实现完成后应得到 `15 passed`。测试只用标准库，不联网，不需要安装包。

## 任务字段

| 字段 | 取值 |
| --- | --- |
| 所属领域 | 安全 |
| 子方向 | 漏洞检测与攻防 |
| 任务类型 | Bugfix |
| 语言/框架 | Python 3, pytest |
| 环境可复现等级 | 无外部依赖 |

## 数据字段表

| 对象 | 字段 | 类型 | 约定 |
| --- | --- | --- | --- |
| metadata | entity_id | str | 实体标识，必须逐字符精确匹配 |
| metadata | valid_from | int | 生效时刻，Unix 秒 |
| metadata | valid_until | int | 失效时刻，Unix 秒 |
| metadata | keys | list | 密钥描述符列表，签名必须覆盖整个列表 |
| metadata | endpoints | dict | 至少含 sso 端点 |
| metadata | signature | dict | 含 covered 与 value |
| key descriptor | key_id | str | 密钥描述符标识，用于建立索引 |
| key descriptor | use | str | signing 或 encryption |
| key descriptor | value | str | 证书或密钥材料 |
| signature | covered | list[str] | 必须同时包含 entity_id 与 keys |
| signature | value | str | 小写十六进制 HMAC-SHA256 摘要 |
| store | entities | dict | entity_id 到 metadata 的主记录 |
| store | keys | dict | entity_id 到 key_id 到描述符的映射 |
| store | index | dict | key_id 到 entity_id 的索引 |
| cached | metadata | dict | 缓存中的元数据 |
| cached | fetched_at | int | 缓存抓取时刻，Unix 秒 |
| policy | skew | int | 只放宽生效下界的时钟偏移，单位秒 |
| policy | refresh_before | int | 距 valid_until 小于等于该值时必须刷新 |
| policy | max_age | int | 缓存年龄大于等于该值时必须刷新 |
| request | request_id | str | 批量校验结果的键 |
| request | metadata | str | JSON 文本形式的元数据 |
| request | expected_entity_id | str | 本请求期望的实体标识 |
| request | key | bytes | 本请求的验签密钥 |

## 关键语义

有效期判定用闭区间：下界取 valid_from 减一次 skew，上界保持 valid_until 不变，再判断 now 是否落在区间内。skew 只放宽生效下界，不得同时扩张失效上界，尤其不得让已过期元数据继续可用。

签名负载固定为 entity_id 与 keys 两个字段组成的紧凑 JSON，键排序，UTF-8 编码，使用 HMAC-SHA256 与小写十六进制摘要。covered 必须同时声明 entity_id 与 keys，任一项缺失即判否；签名值必须用 `hmac.compare_digest` 做定时安全比较，普通等号不满足要求。

实体标识只做精确相等判断，区分大小写，不允许前缀、后缀、包含或 URL 规范化命中。写入时实体标识重复必须拒绝，且不得留下部分密钥或索引记录。淘汰必须同时删除主记录、密钥描述符与索引，并返回实际淘汰数量。批量校验的每个请求独立解析、独立验签，不得复用前一个请求的实体。

## 门面布局

```
sec-saml-metadata/
  README.md
  conftest.py
  meta/__init__.py
  meta/_impl.py
  meta/api.py
  tests/test_metadata.py
```

`meta/_impl.py` 是唯一实现文件，恰好包含 8 个函数桩，且全部 `raise NotImplementedError`。`meta/api.py` 只从 `_impl` 再导出；`meta/__init__.py` 只从 `meta.api` 再导出；测试只通过公开接口调用这 8 个函数。根目录 `conftest.py` 把仓库根加入 `sys.path`，因此从仓库根运行 pytest 时不需要安装包。

`tests/test_metadata.py` 不可修改。15 个测试中，10 个以 defect 命名的测试按题面顺序分别锁定 10 个缺陷，另外 5 个覆盖合法元数据通过、过期元数据被拒、实体标识不符被拒、重复写入被拒、批量结果与单独校验一致。验收以文件中现有的 15 个测试为准。