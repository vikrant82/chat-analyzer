import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

from services import chat_service
from clients.base_client import Message, User, Attachment

# Mock data for testing
MOCK_USER = User(id="U1", name="User One")
MOCK_MESSAGES_FLAT = [
    Message(id="M1", text="Hello", author=MOCK_USER, timestamp=datetime(2023, 1, 1, 12, 0, 0).isoformat(), thread_id=None, parent_id=None),
    Message(id="M2", text="This is a reply", author=MOCK_USER, timestamp=datetime(2023, 1, 1, 12, 1, 0).isoformat(), thread_id="T1", parent_id="M1"),
    Message(id="M3", text="This is another reply", author=MOCK_USER, timestamp=datetime(2023, 1, 1, 12, 2, 0).isoformat(), thread_id="T1", parent_id="M1"),
    Message(id="M4", text="A new message", author=MOCK_USER, timestamp=datetime(2023, 1, 1, 12, 3, 0).isoformat(), thread_id=None, parent_id=None),
]

MOCK_MESSAGES_THREADED = [
    Message(id="R1", text="Root 1", author=MOCK_USER, timestamp=datetime(2023, 1, 1, 12, 0, 0).isoformat(), thread_id=None, parent_id=None),
    Message(id="R1C1", text="Reply to Root 1", author=MOCK_USER, timestamp=datetime(2023, 1, 1, 12, 1, 0).isoformat(), thread_id=None, parent_id="R1"),
    Message(id="R1C1C1", text="Reply to R1C1", author=MOCK_USER, timestamp=datetime(2023, 1, 1, 12, 2, 0).isoformat(), thread_id=None, parent_id="R1C1"),
    Message(id="R2", text="Root 2", author=MOCK_USER, timestamp=datetime(2023, 1, 1, 12, 3, 0).isoformat(), thread_id=None, parent_id=None),
]

class TestChatServiceFormatting:

    def test_format_flat_conversation(self):
        formatted = chat_service._format_flat_conversation(MOCK_MESSAGES_FLAT, is_multimodal=False)
        assert len(formatted) == 1
        content = formatted[0]["content"]
        assert len(content) == 1
        text = content[0]["text"]

        assert "--- Thread Started ---" in text
        assert "--- Thread Ended ---" in text
        assert "[User One at 2023-01-01T12:00:00]: Hello" in text
        assert "    [User One at 2023-01-01T12:01:00]: This is a reply" in text
        assert "[User One at 2023-01-01T12:03:00]: A new message" in text

    def test_format_threaded_conversation(self):
        formatted = chat_service._format_threaded_conversation(MOCK_MESSAGES_THREADED, is_multimodal=False)
        assert len(formatted) == 1
        content = formatted[0]["content"]
        assert len(content) == 1
        text = content[0]["text"]

        assert "--- Thread Started ---" in text
        assert "[User One at 2023-01-01T12:00:00]:" in text
        assert "    [User One at 2023-01-01T12:01:00]:\n    | Reply to Root 1" in text
        assert "        [User One at 2023-01-01T12:02:00]:\n        | Reply to R1C1" in text
        assert "--- Thread Ended ---" in text
        assert "[User One at 2023-01-01T12:03:00]:" in text

    def test_format_messages_with_attachments_multimodal(self):
        messages = [
            Message(id="M1", text="Check out this image", author=MOCK_USER, timestamp=datetime(2023, 1, 1, 12, 0, 0).isoformat(),
                    attachments=[Attachment(mime_type="image/png", data="base64data")])
        ]
        formatted = chat_service._format_flat_conversation(messages, is_multimodal=True)
        content = formatted[0]["content"]
        assert len(content) > 1
        assert any(p["type"] == "image" for p in content)
        text_part = next(p for p in content if p["type"] == "text")
        assert "(Image #1: image/png; author=User One; at=2023-01-01T12:00:00)" in text_part["text"]

    def test_format_messages_with_attachments_non_multimodal(self):
        messages = [
            Message(id="M1", text="Check out this image", author=MOCK_USER, timestamp=datetime(2023, 1, 1, 12, 0, 0).isoformat(),
                    attachments=[Attachment(mime_type="image/png", data="base64data")])
        ]
        formatted = chat_service._format_flat_conversation(messages, is_multimodal=False)
        content = formatted[0]["content"]
        assert len(content) == 1
        assert all(p["type"] == "text" for p in content)
        text_part = content[0]
        assert "(Image #1: image/png; author=User One; at=2023-01-01T12:00:00)" in text_part["text"]


@pytest.mark.asyncio
class TestProcessChatRequest:

    @pytest.fixture
    def mock_dependencies(self, mocker):
        mocker.patch('services.chat_service.auth_service.get_token_for_user', return_value="test_token")
        mock_get_client = mocker.patch('services.chat_service.get_client')
        mock_chat_client = AsyncMock()
        mock_get_client.return_value = mock_chat_client
        
        mock_llm_manager = MagicMock()
        mock_llm_manager.is_multimodal.return_value = False
        mock_llm_manager.call_conversational = AsyncMock(return_value=self.mock_stream())

        return mock_chat_client, mock_llm_manager

    async def mock_stream(self):
        yield "response chunk"

    async def _consume_stream(self, stream):
        return [item async for item in stream]

    async def test_process_chat_request_cache_hit(self, mocker, mock_dependencies):
        mock_chat_client, mock_llm_manager = mock_dependencies
        
        req = chat_service.ChatMessage(
            chatId="C1", modelName="test_model", provider="test_provider",
            startDate="2023-01-01", endDate="2023-01-01",
            enableCaching=True, conversation=[]
        )
        
        cache_key = f"test_token_{req.chatId}_{req.startDate}_{req.endDate}"
        chat_service.message_cache[cache_key] = '[{"role": "user", "content": [{"type": "text", "text": "cached"}]}]'

        stream = await chat_service.process_chat_request(req, "user1", "backend", mock_llm_manager)
        await self._consume_stream(stream)
        
        # Check that get_messages was NOT called
        mock_chat_client.get_messages.assert_not_called()
        
        # Check that LLM was called with cached data
        mock_llm_manager.call_conversational.assert_called_once()
        args, _ = mock_llm_manager.call_conversational.call_args
        assert args[3][0]['content'][0]['text'] == 'cached'

        # Clean up cache
        del chat_service.message_cache[cache_key]

    async def test_process_chat_request_cache_miss(self, mocker, mock_dependencies):
        mock_chat_client, mock_llm_manager = mock_dependencies
        # Mock datetime.now() to ensure is_historical_date is True
        mock_now = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mocker.patch('services.chat_service.datetime', new_callable=lambda: mock_now)
        
        mock_chat_client.get_messages.return_value = [
            Message(id="M1", text="Fresh message", author=MOCK_USER, timestamp=datetime.now().isoformat())
        ]
        
        req = chat_service.ChatMessage(
            chatId="C1", modelName="test_model", provider="test_provider",
            startDate="2023-01-01", endDate="2023-01-01",
            enableCaching=True, conversation=[]
        )

        stream_generator = await chat_service.process_chat_request(req, "user1", "backend", mock_llm_manager)
        await self._consume_stream(stream_generator)
        
        mock_chat_client.get_messages.assert_called_once()
        mock_llm_manager.call_conversational.assert_called_once()
        
        # Check that the result is stored in cache
        cache_key = f"test_token_{req.chatId}_{req.startDate}_{req.endDate}"
        assert cache_key in chat_service.message_cache

        del chat_service.message_cache[cache_key]

    async def test_process_chat_request_no_messages(self, mock_dependencies):
        mock_chat_client, mock_llm_manager = mock_dependencies
        mock_chat_client.get_messages.return_value = []

        req = chat_service.ChatMessage(
            chatId="C1", modelName="test_model", provider="test_provider",
            startDate="2023-01-01", endDate="2023-01-01",
            enableCaching=False, conversation=[]
        )

        stream = await chat_service.process_chat_request(req, "user1", "backend", mock_llm_manager)
        
        result = await self._consume_stream(stream)
        assert "No messages found" in result[0]


class TestChatServiceUtils:
    def test_clear_chat_cache(self):
        chat_service.message_cache["token1_key1"] = "data1"
        chat_service.message_cache["token1_key2"] = "data2"
        chat_service.message_cache["token2_key1"] = "data3"

        chat_service.clear_chat_cache("token1")

        assert "token1_key1" not in chat_service.message_cache
        assert "token1_key2" not in chat_service.message_cache
        assert "token2_key1" in chat_service.message_cache