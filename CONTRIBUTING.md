# Contributing to NEXUS

Thank you for your interest in contributing to NEXUS! This document provides guidelines for contributing.

## How to Contribute

### Reporting Issues
- Use GitHub Issues to report bugs or suggest features
- Include steps to reproduce for bug reports
- Provide environment details (OS, Docker version, Python version)

### Pull Requests
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Test your changes
5. Submit a Pull Request

### Development Setup
1. Clone the repo and follow the Quick Start in README
2. All MCP servers are in `nexus/services/mcp-servers/`
3. Domain Builder engine is in `nexus/core/domain-builder/`
4. Indexing pipeline is in `nexus/services/indexing/`

### Adding a New MCP Server
1. Create `nexus/services/mcp-servers/your-server/server.py`
2. Use `FastMCP` from the MCP SDK
3. Register in OpenClaw MCP bridge config
4. Update documentation

### Creating a New Framework
1. Add to `nexus/core/domain-builder/frameworks.md`
2. Define: target process type, methodology, question directions, skill.md structure guide
3. Test with Domain Builder Phase 1 + Phase 3

### Code Style
- Python 3.11+
- Follow existing patterns in the codebase
- Use type hints where practical

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
