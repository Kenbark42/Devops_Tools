# Contributing to DevOps Toolkit

Thank you for considering contributing to DevOps Toolkit! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct. Please be respectful and considerate of others when contributing.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a branch** for your contribution
4. **Set up your development environment**

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

## Development Workflow

### Code Style

We follow the [Black](https://black.readthedocs.io/) code style for Python. The project uses the following tools to maintain code quality:

- **Black**: For code formatting
- **Flake8**: For linting
- **isort**: For import sorting
- **mypy**: For static type checking

Before submitting a pull request, ensure your code passes all style checks:

```bash
# Format code
black src tests

# Sort imports
isort src tests

# Lint code
flake8 src tests

# Type check
mypy src
```

### Running Tests

We use pytest for testing. Make sure to write tests for any new functionality and ensure all tests pass before submitting a pull request:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term
```

## Pull Request Process

1. **Update the documentation** if needed
2. **Ensure all tests pass** and add new tests as appropriate
3. **Update the changelog** with your changes
4. **Submit a pull request** to the main repository
5. **Address any feedback** from code reviews

## Adding New Features

When adding new features, please follow these guidelines:

1. **Start with an issue** to discuss the feature before implementation
2. **Keep the scope focused** to make review easier
3. **Follow existing patterns** in the codebase
4. **Document your code** with docstrings and comments
5. **Add unit tests** covering the new functionality

## Documentation

Please update documentation when making changes:

- Update docstrings for any modified functions, classes, or modules
- Update README.md or specific documentation files in the docs/ directory as needed
- Ensure examples in documentation work correctly

## Versioning

We follow [Semantic Versioning](https://semver.org/) for this project:

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

## Release Process

1. Update version number in `src/devops_toolkit/__init__.py`
2. Update the CHANGELOG.md file
3. Create a new tag with the version number
4. Push the tag to trigger the release workflow

## Need Help?

If you need help with anything related to contributing, please:

- Check existing issues for similar questions
- Open a new issue with your question
- Reach out to the maintainers

Thank you for contributing to DevOps Toolkit!