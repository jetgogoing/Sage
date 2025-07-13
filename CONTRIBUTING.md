# Contributing to Sage MCP

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for our commit messages.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to the build process or auxiliary tools
- **perf**: A code change that improves performance

### Scopes

- **mcp**: MCP protocol related changes
- **memory**: Memory system changes
- **db**: Database related changes
- **api**: API endpoint changes
- **config**: Configuration changes
- **docker**: Docker/containerization changes

### Subject

- Use the imperative, present tense: "change" not "changed" nor "changes"
- Don't capitalize the first letter
- No dot (.) at the end
- Maximum 50 characters

### Body

- Use the imperative, present tense
- Include motivation for the change and contrast with previous behavior
- Wrap at 72 characters

### Examples

#### Simple feature
```
feat(memory): add intelligent context retrieval
```

#### Complex change with body
```
feat(mcp): implement auto-context injection for Claude Code

- Add request interceptor to analyze user queries
- Implement intelligent retrieval with neural reranking
- Add caching mechanism for performance optimization
- Support transparent memory access across projects

This enables Claude to automatically remember and use
relevant context from previous conversations without
explicit user commands.

Closes #42
```

#### Bug fix
```
fix(db): resolve connection pool exhaustion

The connection pool was not properly releasing connections
after failed transactions, leading to pool exhaustion under
high load.

- Add proper connection cleanup in error handlers
- Implement connection timeout and retry logic
- Add monitoring for pool health

Fixes #156
```

## Setting Up Git Hooks

To ensure your commits follow our guidelines:

```bash
# Copy the commit-msg hook
cp .githooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg

# Or use Git's core.hooksPath (Git 2.9+)
git config core.hooksPath .githooks
```

## Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings to all public functions and classes
- Keep functions focused and under 50 lines

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for >80% code coverage

## Pull Request Process

1. Fork the repository
2. Create your feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes using conventional commits
4. Push to your fork (`git push origin feat/amazing-feature`)
5. Open a Pull Request with a clear description

## Questions?

Feel free to open an issue for any questions about contributing.