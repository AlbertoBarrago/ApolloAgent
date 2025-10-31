# ApolloAgent

ApolloAgent is a custom AI agent that implements various functions for code assistance.

[![PyPI version](https://img.shields.io/pypi/v/apollo-agent)](https://pypi.org/appo-agent)
[![Black Code Formatter](https://github.com/AlbertoBarrago/ApolloAgent/actions/workflows/black.yml/badge.svg)](https://github.com/AlbertoBarrago/ApolloAgent/actions/workflows/black.yml)

> "_ApolloAgent is a versatile PoC showcasing how AI-driven tools can simplify coding tasks and enhance productivity._"

ApolloAgent provides the following functionality:

- **Web Search**: Get info from duck duck.
- **Wiki Search**: Get info from Wikipedia.
- **Grep Search**: Perform fast, text-based regex searches within files or directories.
- **File Search**: (Broken for now) Locate files quickly using fuzzy matching on file paths.
- **File Operations**: Delete and edit files directly through the agent.
- **Session**: Each session is stored in a separate file inside the chat_sessions folder 


## Conversation example 

```text
> You: Howdy who are you?

🤖 [9 seconds, 98 ms] Ciao! I'm Apollo, your AI pair-programming assistant. I'm from Cagliari, Italy, and my creator is Alberto Barrago. How can I help you today? What's on your mind?

> You: what's the Cagliari weather today?                                                       

[11 seconds, 98 ms], Tools used: ['web_search']


🤖 [19 seconds, 651 ms] The current weather in Cagliari is partly cloudy with a high of 23°C (73°F) and a low of 17°C (63°F). There is no precipitation expected today. However, there may be some scattered showers in the evening.

Here's a summary of the weather forecast for the next 10 days:

* Today: Partly cloudy with a high of 23°C (73°F) and a low of 17°C (63°F)
* Tomorrow: Sunny with a high of 25°C (77°F) and a low of 18°C (64°F)
* Wednesday: Mostly sunny with a high of 27°C (81°F) and a low of 20°C (68°F)
* Thursday: Partly cloudy with a high of 24°C (75°F) and a low of 19°C (66°F)
* Friday: Scattered showers with a high of 22°C (72°F) and a low of 17°C (63°F)

It's recommended to pack light clothing for the next few days, but also bring an umbrella in case of scattered showers.

Please note that this is just a summary of the weather forecast, and you should check the latest updates before making any plans.
```

## Installation

Ensure you have Python 3.10+ installed.

```bash
# Clone the repository
git clone https://github.com/albertobarrago/ApolloAgent.git

# Navigate to the project directory
cd ApolloAgent

# Install dependencies
pip install -r requirements.txt
```

If no `requirements.txt` is included, install dependencies manually as needed.

## Usage

To start ApolloAgent, run:

```bash
python main.py
```

### Tool: `list_dir`

Lists all files and subdirectories within a specified directory path, relative to the workspace root. This is useful for exploring the project structure and discovering files.

### Tool: `grep_search`

Performs a fast, text-based search for an exact string or regular expression pattern within files. This is highly effective for locating specific function names, variable declarations, or log messages when the exact text is known.

### Tool: `file_search`

Find files by performing a fuzzy search against their paths. This is useful when you know a part of the filename or path but are unsure of the exact location or spelling.

### Tool: `delete_file`

Permanently deletes a file from the workspace.

### Tool: `create_file`

Create a new file with a variety of granular operations. Always provide a clear explanation for the modification.

### Tool: `edit_file`

Modifies an existing one with a variety of granular operations. It is critical to first inspect the file's content to ensure the edit is appropriate. Always provide a clear explanation for the modification.

### Tool: `remove_dir`

Recursively and permanently removes a directory and all of its contents. This action is irreversible.

### Tool: `web_search`

Search the web to find up-to-date information on a given topic. This tool is best used for general knowledge, current events, or technical information not present in the local codebase or Wikipedia.

### Tool: `wiki_search`

Search Wikipedia for encyclopedic information on a topic. This is best for historical events, scientific concepts, or detailed biographies.

### Tool: `codebase_search` (the coolest one! for now...)

The `codebase_search` tool is designed to help you find relevant code snippets within the project's codebase based on a natural language query. It's particularly useful when you're looking for code related to a specific concept or functionality but don't know the exact file names or precise syntax.

### How it Works

Internally, `codebase_search` takes your natural language query and processes it to extract significant keywords. It then searches through the files in the workspace (respecting specified `included_extensions` like `.py`, `.js`, `.md`, etc.) to find files that contain **all** of these extracted keywords. This approach aims to provide more relevant results than a simple substring match of the entire query.

### When to Use

Use `codebase_search` when:

*   You want to understand how a particular feature is implemented.
*   You're looking for code related to a general concept (e.g., "error handling," "user authentication").
*   You remember what a piece of code does but not where it is or its exact variable/function names.

### Parameters

When the ApolloAgent decides to use this tool, it will invoke it with the following parameter:

*   `query` (string): Your natural language search query. For example:
    *   `"how are database connections managed"`
    *   `"find the main configuration settings"`
    *   `"show me code related to payment processing"`

### Return Value

The `codebase_search` tool returns a JSON object. This object will always contain `query`, `results`, and `error` keys.

*   `query` (string): The original natural language query you provided.
*   `results` (array of objects): A list of found items.
    *   If matches are found, each object in the array represents a distinct match and includes the following fields:
        *   `file_path` (string): The path to the file where the keywords were found, relative to the workspace root.
        *   `content_snippet` (string): A preview of the file's content (up to the first 500 characters).
        *   `relevance_score` (number): A score indicating the relevance. (Note: This is currently a fixed value for keyword matches but is designed for future semantic enhancements).
    *   If no matches are found (but no error occurred), this will be an empty list (`[]`).
*   `error` (string | null):
    *   If the search operation encounters an issue (e.g., an invalid workspace path, permission errors), this field will contain a descriptive error message (string). In such cases, the `results` list will typically be empty.
    *   If the search completes successfully (even if no items are found), this field will be `null`.

**Example JSON Response (Success with results):**

### Docker (docker-compose)
**Pull the LLM model into Ollama**:
    Ensure the required LLM model (e.g., `llama3.1`) is available in your Ollama container before running ApolloAgent.
    * First, start just the Ollama service:
        ```bash
        docker compose up -d ollama
        ```
    * Then, execute the pull command inside the running Ollama container:
        ```bash
        docker exec -it ollama ollama pull llama3.1
        ```
    * Wait for the download to complete.

1. **Start all services**:
    From your project root (where `docker-compose.yml` is located), run:
    ```bash
    docker compose up -d
    ```
    This command builds your `apolloagent` image, creates the Docker network, and starts both Ollama and ApolloAgent in detached mode.

2. **Interact with ApolloAgent**:
    To access the interactive chat terminal of ApolloAgent:
    ```bash
    docker attach apollo-agent
    ```
    You can detach from the terminal by pressing `Ctrl+C`.

3. **Stop and Clean Up**:
    To stop and remove all services defined in your `docker-compose.yml` file:
    ```bash
    docker compose down
    ```

## License

ApolloAgent is licensed under the BSD 3-Clause License. See the `LICENSE` file for more details.

## Contributing

We welcome contributions to ApolloAgent! If you'd like to help:
- Report bugs or suggest new features via [GitHub Issues](https://github.com/AlbertoBarrago/Apollo-Agent/issues).
- Submit pull requests for enhancements or changes.

### Getting Started with Contributions

1. **Pick an Area**: Choose one of the areas above that interests you.
2. **Create an Issue**: Describe what you plan to implement or improve.
3. **Fork and Clone**: Fork the repository and clone it locally.
4. **Implement Changes**: Make your changes following the project's coding style.
5. **Add Tests**: Write tests for your new functionality.
6. **Submit a PR**: Create a pull request with a clear description of your changes.

We're particularly interested in contributions that make ApolloAgent more robust, user-friendly, and versatile as a coding assistant.
