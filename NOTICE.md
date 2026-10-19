# Notice

本仓库是 Instruct-Particulate 项目的适配器和本地补丁发布包。

## Upstream

官方 Space：

- https://huggingface.co/spaces/rayli/instruct-particulate

本仓库不包含官方 Space 的完整源码和模型权重。组员应从上游获取官方 Space，并遵守其源码、第三方组件和模型的许可证。

## Third-party components

官方 Space 中包含 PartField 等第三方组件。当前上游目录中的 `partfield/LICENSE` 为 NVIDIA License，涉及该组件时必须保留原许可证和版权声明，并遵守其非商业研究/教育使用限制。

## Local changes

本仓库新增或维护的主要内容是：

- OpenAI-compatible vision relay；
- 官方 `app.py` 的 relay 和 query batch 配置补丁；
- Structure JSON 输出适配器及校验代码；
- 本地部署说明和测试。

本仓库不授权重新分发不属于本仓库的上游代码或权重，也不包含任何 API Key。
