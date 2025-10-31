"""
In this file, we define the class for handling chat
interactions and tool function definitions for ApolloAgent.

Author: Alberto Barrago
License: BSD 3-Clause License - 2025
"""

import uuid
from typing import Any
import ollama

from apollo.config.instructions import get_available_tools
from apollo.config.const import Constant
from apollo.service.tool.format import format_duration_ns
from apollo.service.session import save_user_history_to_json


class ApolloCore:
    """
    Handles chat interactions and tool function definitions for ApolloAgent.

    This class encapsulates the core chat logic, including LLM interactions,
    tool calls using Ollama's function calling API, and managing chat history.
    """

    def __init__(self):
        """
        Initializes the ApolloAgentChat instance.
        """
        self.session_id: str | None = None
        self.permanent_history: list[dict] = []
        self.chat_history: list[dict] = []
        self._chat_in_progress: bool = False
        self.tool_executor = None
        self.ollama_client = ollama.AsyncClient(host=Constant.ollama_host)

    async def process_llm_response(
        self, llm_response
    ) -> tuple[dict | None, list | None, str | None, int | None]:
        """
        Process the response from the LLM, extracting message, tool calls, and content.

        Args:
            llm_response: The response from the LLM.

        Returns:
            A tuple of (a message, tool_calls, content).
        """
        message = llm_response.get("message")
        total_duration = llm_response.get("total_duration", 0)
        if not message:
            print("[WARNING] LLM response missing 'message' field.")
            self.chat_history.append(
                {
                    "role": "assistant",
                    "content": "[Error: Empty message received from LLM]",
                }
            )
            return None, None, None, None

        if isinstance(message, dict):
            tool_calls = message.get("tool_calls")
            content = message.get("content")
        else:
            tool_calls = getattr(message, "tool_calls", None)
            content = getattr(message, "content", None)

        self.chat_history.append(message)
        return message, tool_calls, content, total_duration

    async def _handle_tool_calls(self, tool_calls, iterations, recent_tool_calls):
        """
        Handle tool calls from the LLM.

        Args:
            tool_calls: The tool calls from the LLM.
            iterations: The current iteration-count.
            recent_tool_calls: The recent tool calls for loop detection.

        Returns:
            A tuple of (results, current_tool_calls) where
            results is a response dict if a loop is detected,
            or None if processing should continue,
            and current_tool_calls is a list of function names.
        """
        if not isinstance(tool_calls, list):
            print(
                f"[ERROR] Received non-list 'tool_calls' from LLM Message. "
                f"Type: {type(tool_calls)}. Value: {tool_calls}"
            )
            return {
                "error": f"Received unexpected tool_calls format from LLM: {tool_calls}"
            }, None

        current_tool_calls = []
        for tool_call in tool_calls:
            if hasattr(tool_call, "function"):
                func_name = getattr(tool_call.function, "name", "unknown")
            elif isinstance(tool_call, dict) and "function" in tool_call:
                func_name = tool_call["function"].get("name", "unknown")
            else:
                func_name = "unknown"
            current_tool_calls.append(func_name)

        if (
            iterations > Constant.max_chat_iterations
            and current_tool_calls == recent_tool_calls
        ):
            print("[WARNING] Detected repeated tool call pattern, breaking loop")
            loop_detected_msg = Constant.error_loop_detected
            self.permanent_history.append(
                {"role": "assistant", "content": loop_detected_msg}
            )
            return {"response": loop_detected_msg}, current_tool_calls

        tool_outputs = []
        for tool_call in tool_calls:
            try:
                tool_result = await self._execute_tool(tool_call)

            except RuntimeError as e:
                tool_result = f"[ERROR] Exception during tool execution: {str(e)}"

            tool_outputs.append(
                {
                    "role": "tool",
                    "tool_call_id": getattr(
                        tool_call, "id", tool_call.get("id", "N/A")
                    ),
                    "content": str(tool_result),
                }
            )

        self.chat_history.extend(tool_outputs)
        return None, current_tool_calls

    async def _get_llm_response_from_ollama(self):
        """
        Fetches the LLM response from Ollama, adding a system message if needed.
        """

        llm_response_stream = await self.ollama_client.chat(
            model=Constant.llm_model,
            messages=self.chat_history,
            tools=get_available_tools(),
            stream=True,
            options={},
        )

        return llm_response_stream

    async def handle_request(
        self, text: str
    ) -> None | dict[str, str] | dict[str, Any | None]:
        """
        Responds to the user's message, handling potential tool calls and multi-turn interactions.

        Args:
            text: The user's message.

        Returns:
            Response from the chat model or error information.
        """
        if self._chat_in_progress:
            print("[WARNING] Chat already in progress, ignoring concurrent request")
            return {"error": Constant.error_chat_in_progress}

        self._chat_in_progress = True

        try:
            self._initialize_chat_session(text)  # Init session and update chat history

            iterations = 0
            recent_tool_calls = []

            return await self.start_iterations(iterations, recent_tool_calls)

        except RuntimeError as e:
            error_message = f"[ERROR] RuntimeError during chat processing: {e}"
            print(error_message)
            return {"error": error_message}
        except IOError as e:
            error_message = f"[ERROR] An unexpected error occurred: {str(e)}"
            print(error_message)
            return {"error": error_message}
        finally:
            self._chat_in_progress = False

    async def start_iterations(self, iterations, recent_tool_calls):
        """
        Executes several iterations of interaction with a language model (LLM) and processes
        the result.
        """

        while iterations < Constant.max_chat_iterations:
            try:
                llm_response_stream = await self._get_llm_response_from_ollama()
            except RuntimeError as e:
                return {
                    "error": f"Failed to get response from language model: {str(e)}"
                }

            full_response_message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [],
            }
            accumulated_content = ""
            final_tool_calls = None
            total_duration = 0

            async for chunk in llm_response_stream:
                # Process each chunk
                # This part needs careful adaptation based on ollama client's streaming format
                chunk_message = chunk.get("message", {})
                chunk_content = chunk_message.get("content", "")
                chunk_tool_calls = chunk_message.get("tool_calls")

                if chunk_content:
                    accumulated_content += chunk_content

                if chunk_tool_calls:
                    if final_tool_calls is None:
                        final_tool_calls = []
                    final_tool_calls.extend(chunk_tool_calls)

                if chunk.get("done"):
                    total_duration = chunk.get("total_duration", 0)
                    if chunk_message:
                        full_response_message = chunk_message
                    break

            if not full_response_message.get("content") and accumulated_content:
                full_response_message["content"] = accumulated_content
            if final_tool_calls and not full_response_message.get("tool_calls"):
                full_response_message["tool_calls"] = final_tool_calls

            simulated_llm_response_for_processing = {
                "message": full_response_message,
                "total_duration": total_duration,
            }

            (message_obj, tool_calls, content, duration_val) = (
                await self.process_llm_response(simulated_llm_response_for_processing)
            )
            duration_str = format_duration_ns(duration_val)

            if message_obj and message_obj.get("role"):
                save_user_history_to_json(
                    message=message_obj.get("content"), role=message_obj.get("role")
                )
            elif content:
                save_user_history_to_json(message=content, role="assistant")

            if message_obj is None:
                return {"response": Constant.error_empty_llm_message}

            if content and not tool_calls:
                self.permanent_history.append({"role": "assistant", "content": content})
                return {"response": f"[{duration_str}] {content}"}

            if tool_calls:
                result, current_tool_calls = await self._handle_tool_calls(
                    tool_calls, iterations, recent_tool_calls
                )
                print(f"\n[{duration_str}], Tools used: {current_tool_calls}\n")
                if result:
                    return result
                recent_tool_calls = current_tool_calls
                iterations += 1
                continue

            return {
                "response": f"[{duration_str}] No content or tools were provided in the response."
            }

        timeout_message = Constant.error_max_iterations.format(
            max_iterations=Constant.max_chat_iterations
        )
        self.permanent_history.append({"role": "assistant", "content": timeout_message})
        return {"Max iterations reached: ": timeout_message}

    async def _execute_tool(self, tool_call: dict) -> Any:
        """Execute a tool call using the associated tool executors execute_tool method."""
        if not self.tool_executor:
            return Constant.error_no_agent

        try:
            return await self.tool_executor.execute_tool(tool_call)
        except RuntimeError as e:
            return f"[ERROR] Exception during tool execution: {str(e)}"

    def set_tool_executor(self, tool_executor):
        """Associate this chat instance with a ToolExecutor instance."""
        self.tool_executor = tool_executor

    def _initialize_chat_session(self, text: str):
        """Initializes the session and updates chat history."""
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
            print(f"[INFO] New chat session: {self.session_id}")

        last_message = self.permanent_history[-1] if self.permanent_history else None

        if (
            not last_message
            or last_message.get("role") != "user"
            or last_message.get("content") != text
        ):
            self.permanent_history.append({"role": "user", "content": text})
            self.chat_history = self.permanent_history.copy()
        else:
            self.chat_history = self.permanent_history.copy()
            print(f"Chat History {self.chat_history}")
