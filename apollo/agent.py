"""
ApolloAgent is a custom AI agent that implements various functions for code assistance.

This is the main module for the ApolloAgent agent.
The functions chat_terminal and execute_tool are responsible
for the chat mode and tool execution, respectively.

Author: Alberto Barrago
License: BSD 3-Clause License - 2025
"""

import os

from apollo.service.session import save_user_history_to_json
from apollo.tools.search import (
    codebase_search,
    file_search,
    grep_search,
)
from apollo.tools.core import ApolloCore
from apollo.tools.files import list_dir, delete_file, create_file, edit_file, remove_dir
from apollo.service.tool.executor import ToolExecutor
from apollo.config.const import Constant
from apollo.tools.web import web_search, wiki_search


class ApolloAgent:
    """
    ApolloAgent is a custom AI agent that implements various functions for code assistance.
    """

    def __init__(self, workspace_path: str = None):
        """
        Initialize the ApolloAgent with a workspace path.

        Args:
            workspace_path: The root path of the workspace to operate on.
                            Defaults to the current working directory if None.
        """
        self.workspace_path = workspace_path or os.getcwd()

        # Initialize the tool executor
        self.tool_executor = ToolExecutor(self.workspace_path)

        # Initialize the chat agent
        self.chat_agent = ApolloCore()
        self.chat_agent.set_tool_executor(self.tool_executor)

        # Register functions with the tool executor
        self.tool_executor.register_functions(
            {
                # File operations (core functionality)
                "create_file": create_file,
                "edit_file": edit_file,
                "list_dir": list_dir,
                "delete_file": delete_file,
                "remove_dir": remove_dir,
                # Search operations (by increasing scope/complexity)
                "file_search": file_search,
                "grep_search": grep_search,
                "codebase_search": codebase_search,
                # External information sources
                "web_search": web_search,
                "wiki_search": wiki_search,
            }
        )

    async def execute_tool(self, tool_call):
        """
        Execute a tool function call (from LLM) with
        validated arguments and secure redirection.

        This method is now a wrapper around the ToolExecutor's
        execute_tool method for backward compatibility.
        """
        return await self.tool_executor.execute_tool(tool_call)

    @staticmethod
    async def chat_terminal():
        """Start a Chat Session in the terminal."""
        print(Constant.apollo_welcome)
        workspace_cabled = Constant.workspace_cabled

        if not os.path.exists(workspace_cabled) and workspace_cabled != "exit":
            os.makedirs(workspace_cabled)
        if workspace_cabled == "exit":
            return

        agent = ApolloAgent(workspace_path=workspace_cabled)
        print(
            "🌟 Welcome to ApolloAgent Chat Mode!"
            "\n > Type 'exit' to end the conversation."
            "\n > Now in BETA MODE the workspace is set to:",
            os.path.abspath(workspace_cabled),
        )

        while True:
            try:
                user_input = input("\n> You: ")
                if user_input.lower() == "exit":
                    break
                save_user_history_to_json(message=user_input, role="user")

                prompt = (
                    f"Follow this instructions:{Constant.prompt_reinforcement_dev_v2}"
                    f" The command is: ${user_input}"
                )
                # The magic begin
                response = await agent.chat_agent.handle_request(prompt)

                if response and isinstance(response, dict) and "response" in response:
                    print(f"\n🤖 {response['response']}")
                elif response and isinstance(response, dict) and "error" in response:
                    print(f"🤖 Apollo (Error): {response['error']}")
                else:
                    print(f"🤖 Apollo (Unexpected Response Format): {response}")

            except EOFError:
                print("\nExiting chat.")
                break
            except KeyboardInterrupt:
                print("\nExiting chat.")
                break
