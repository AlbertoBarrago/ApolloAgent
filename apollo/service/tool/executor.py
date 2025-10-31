"""
Tool execution for the ApolloAgent.

This module contains the ToolExecutor class, which is responsible for
executing tool and handling tool calls from the LLM.

Author: Alberto Barrago
License: BSD 3-Clause License - 2025
"""

import inspect
import json

from typing import Any, Dict, Callable

def _format_tool_result(result) -> str:
    """
    Format the tool execution result into a string that can be sent to LLM.

    Args:
        result: The raw result from tool execution

    Returns:
        Formatted string representation of the result
    """

    if result is None:
        return "Tool executed successfully with no return value."

    # If it's already a string, return it
    if isinstance(result, str):
        return result

    # If it's a list of dicts (like wiki_search results), format nicely
    if isinstance(result, list):
        if all(isinstance(item, dict) for item in result):
            # Format as readable text for wiki results
            formatted = []
            for i, item in enumerate(result, 1):
                if "error" in item:
                    formatted.append(f"Error: {item.get('error')}")
                else:
                    formatted.append(
                        f"{i}. {item.get('title', 'No title')}\n"
                        f"   URL: {item.get('url', 'No URL')}\n"
                        f"   Snippet: {item.get('snippet', 'No snippet')}\n"
                    )
            return "\n".join(formatted)

        # Generic list, convert to JSON
        return json.dumps(result, indent=2, ensure_ascii=False)

    # If it's a dict, convert to JSON
    if isinstance(result, dict):
        return json.dumps(result, indent=2, ensure_ascii=False)

    # For other types, convert to string
    try:
        return str(result)
    except Exception:
        return f"[Result type: {type(result).__name__}]"


class ToolExecutor:
    """
    ToolExecutor is responsible for executing tools and handling tool calls from the LLM.
    It provides a unified interface for tool execution, resolving the circular dependency
    between ApolloAgent and ApolloAgentChat.
    """

    def __init__(self, workspace_path: str = None):
        """
        Initialize the ToolExecutor with a workspace path.

        Args:
            workspace_path: The root path of the workspace to operate on.
        """
        self.workspace_path = workspace_path
        self.available_functions = {}
        self.last_edit_file = None
        self.last_edit_content = None

    def register_function(self, name: str, func: Callable) -> None:
        """
        Register a function to be available for tool execution.

        Args:
            name: The name of the function.
            func: The function to register.
        """
        self.available_functions[name] = func

    def register_functions(self, functions: Dict[str, Callable]) -> None:
        """
        Register multiple functions to be available for tool execution.

        Args:
            functions: A dictionary mapping function names to functions.
        """
        self.available_functions.update(functions)

    async def execute_tool(self, tool_call) -> Any:
        """
        Execute a tool function call (from LLM) with validated arguments

        Args:
            tool_call: The tool call from the LLM.

        Returns:
            The result of the tool execution (properly formatted as string).
        """

        def filter_valid_args(valid_func, args_dict):
            valid_params = valid_func.__code__.co_varnames[
                : valid_func.__code__.co_argcount
            ]
            return {k: v for k, v in args_dict.items() if k in valid_params}

        # Parse tool call
        try:
            if hasattr(tool_call, "function"):
                func_name = getattr(tool_call.function, "name", None)
                raw_args = getattr(tool_call.function, "arguments", {})
            elif isinstance(tool_call, dict) and "function" in tool_call:
                func_name = tool_call["function"].get("name")
                raw_args = tool_call["function"].get("arguments", {})
            else:
                return "[ERROR] Invalid tool_call format or missing 'function'."

            if not func_name:
                return "[ERROR] Function name not provided in tool call."

            # Parse arguments
            if isinstance(raw_args, str):
                arguments_dict = __import__("json").loads(raw_args)
            elif isinstance(raw_args, dict):
                arguments_dict = raw_args
            else:
                return f"[ERROR] Unsupported arguments type: {type(raw_args)}"

            if not isinstance(arguments_dict, dict):
                return "[ERROR] Parsed arguments are not a dictionary."

        except Exception as e:
            return f"[ERROR] Failed to parse tool call: {e}"

        # Get function
        func = self.available_functions.get(func_name)
        if not func:
            return f"[ERROR] Function '{func_name}' not found."

        # Filter and prepare arguments
        filtered_args = filter_valid_args(func, arguments_dict)

        sig = inspect.signature(func)
        params = sig.parameters

        args_to_pass = filtered_args.copy()

        if "agent" in params:
            args_to_pass["agent"] = self

        # Execute function
        try:
            if inspect.iscoroutinefunction(func):
                result = await func(**args_to_pass)
            else:
                result = func(**args_to_pass)

            return _format_tool_result(result)

        except Exception as e:
            return f"[ERROR] Failed to execute tool: {e}"
