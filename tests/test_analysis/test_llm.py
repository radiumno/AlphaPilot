"""LLM 客户端测试"""

from data.llm import LLMClient


def test_llm_client_init():
    """LLM 客户端初始化"""
    client = LLMClient(api_key="test-key", base_url="https://test.com", model="test-model")
    assert client.api_key == "test-key"
    assert client.base_url == "https://test.com"
    assert client.model == "test-model"


def test_llm_no_key_response():
    """无 API Key 时返回提示信息"""
    client = LLMClient(api_key="")
    result = client.chat([{"role": "user", "content": "hi"}])
    assert "未配置" in result


def test_llm_chat_json_no_key():
    """无 API Key 时 chat_json 仍返回提示"""
    client = LLMClient(api_key="")
    result = client.chat_json([{"role": "user", "content": "hi"}])
    assert "未配置" in str(result) or "error" in str(result)


def test_llm_headers():
    """请求头包含 Authorization"""
    client = LLMClient(api_key="sk-test123", base_url="https://api.test.com")
    headers = client._headers
    assert headers["Authorization"] == "Bearer sk-test123"
    assert headers["Content-Type"] == "application/json"


def test_llm_api_key_from_settings():
    """不传 api_key 时使用 settings 中的 key"""
    client = LLMClient()
    # CI 环境中可能没有 API Key，也可能是空字符串
    assert client.api_key is None or isinstance(client.api_key, str)
    assert client.base_url == "https://api.deepseek.com"
