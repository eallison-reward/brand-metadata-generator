# Contributing to Brand Metadata Generator

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Workflow

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-org/brand-metadata-generator.git
   cd brand-metadata-generator
   ```

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set Up Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```

4. **Make Changes**
   - Write code following the project style guide
   - Add tests for new functionality
   - Update documentation as needed

5. **Run Tests**
   ```bash
   # Run all tests
   pytest

   # Run specific test types
   pytest tests/unit -m unit
   pytest tests/property -m property
   pytest tests/integration -m integration
   ```

6. **Check Code Quality**
   ```bash
   # Format code
   black agents shared tests

   # Check linting
   flake8 agents shared

   # Type checking
   mypy agents shared
   ```

7. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `test:` Test additions or changes
   - `refactor:` Code refactoring
   - `chore:` Maintenance tasks

8. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and under 50 lines when possible
- Use meaningful variable names

### Example

```python
def calculate_confidence_score(
    narrative_variance: float,
    mccid_consistency: float,
    wallet_affected: bool
) -> float:
    """Calculate confidence score for brand metadata.
    
    Args:
        narrative_variance: Variance in narrative patterns (0.0-1.0)
        mccid_consistency: MCCID alignment score (0.0-1.0)
        wallet_affected: Whether payment wallets detected
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    base_score = (narrative_variance + mccid_consistency) / 2
    if wallet_affected:
        base_score *= 0.8
    return max(0.0, min(1.0, base_score))
```

## Testing Guidelines

### Unit Tests

- Test individual functions and classes
- Mock external dependencies (AWS services, other agents)
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`

```python
def test_calculate_confidence_score_with_wallet_reduces_score():
    """Test that wallet detection reduces confidence score."""
    score = calculate_confidence_score(0.9, 0.9, wallet_affected=True)
    assert score < 0.9
```

### Property-Based Tests

- Use Hypothesis for property-based testing
- Test universal properties that should hold for all inputs
- Run at least 100 examples per property

```python
from hypothesis import given, strategies as st

@given(
    variance=st.floats(min_value=0.0, max_value=1.0),
    consistency=st.floats(min_value=0.0, max_value=1.0)
)
def test_confidence_score_always_in_range(variance, consistency):
    """Property: Confidence score always between 0.0 and 1.0."""
    score = calculate_confidence_score(variance, consistency, False)
    assert 0.0 <= score <= 1.0
```

### Integration Tests

- Test end-to-end workflows
- Use test data in Athena
- Clean up resources after tests

## Documentation

- Update README.md for user-facing changes
- Update docstrings for code changes
- Add examples for new features
- Update design documents in `.kiro/specs/` if architecture changes

## Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Add description of changes to PR
4. Request review from at least one maintainer
5. Address review feedback
6. Maintainer will merge after approval

## Questions?

Open an issue or reach out to the maintainers.
