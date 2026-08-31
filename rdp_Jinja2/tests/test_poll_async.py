import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from poll_async import async_poll_logs

class MockConsole:
    def print(self, *args, **kwargs):
        pass
    def status(self, *args, **kwargs):
        return MagicMock()

@pytest.mark.asyncio
@patch('asyncio.create_subprocess_exec')
async def test_async_poll_logs_timeout(mock_exec):
    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b'null\n', b''))
    mock_exec.return_value = mock_proc
    
    console = MockConsole()
    with patch('asyncio.sleep', new_callable=AsyncMock):
        await async_poll_logs('.', 'testrepo', 'testuser', 'pass', console)
        
    assert mock_exec.call_count == 15

@pytest.mark.asyncio
@patch('asyncio.create_subprocess_exec')
async def test_async_poll_logs_success(mock_exec):
    mock_proc1 = MagicMock()
    mock_proc1.communicate = AsyncMock(return_value=(b'123456\n', b''))
    
    mock_proc2 = MagicMock()
    mock_proc2.communicate = AsyncMock(return_value=(b'Connect using tcp://a.pinggy.io:1234\nUsername: runner\n', b''))
    
    mock_exec.side_effect = [mock_proc1, mock_proc2]
    
    console = MockConsole()
    with patch('asyncio.sleep', new_callable=AsyncMock):
        await async_poll_logs('.', 'testrepo', 'testuser', 'pass', console)
        
    assert mock_exec.call_count == 2
