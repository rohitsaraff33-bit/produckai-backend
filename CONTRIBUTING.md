# Contributing to ProduckAI

Thank you for your interest in contributing to ProduckAI! This document provides guidelines and instructions for contributing to the project.

## 📧 Contact

- **Creator**: Rohit Saraf ([rohitsaraff33@gmail.com](mailto:rohitsaraff33@gmail.com))
- **GitHub Issues**: https://github.com/rohitsaraff33-bit/produckai-backend/issues

## 🎯 Vision

ProduckAI is built **for product managers, by product managers**. Our goal is to create a thriving open source community where builders enhance integrations, improve clustering algorithms, and share learnings so the entire PM community benefits.

## 🙏 How You Can Contribute

We especially welcome contributions in these areas:

### 🔌 Integration Enhancements
- New data sources (Linear, Notion, Intercom, Zendesk, etc.)
- Improved parsing for existing integrations (Slack threads, Jira comments)
- OAuth flow improvements
- Webhook support for real-time ingestion

### 🧠 ML & Clustering
- Alternative clustering algorithms (DBSCAN, Agglomerative, etc.)
- Multi-language embedding models
- Improved theme naming (using LLMs)
- Sentiment analysis enhancements
- Duplicate detection improvements

### 📊 Scoring & Analytics
- New VOC scoring dimensions
- Custom scoring formulas
- Advanced analytics (trend detection, churn prediction)
- A/B testing framework for scoring weights

### 🎨 Frontend & UX
- Web UI improvements (Next.js)
- Chrome extension features
- Mobile-friendly views
- Accessibility improvements

### 📚 Documentation
- Tutorial videos
- Integration guides
- Architecture deep-dives
- Translation to other languages

### 🧪 Testing & Quality
- Unit tests
- Integration tests
- Performance benchmarks
- Security audits

---

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/produckai-backend.git
cd produckai-backend

# Add upstream remote
git remote add upstream https://github.com/rohitsaraff33-bit/produckai-backend.git
```

### 2. Set Up Development Environment

```bash
# Copy environment file
cp .env.example .env

# Start services
make up

# Run migrations and seed data
make migrate
make seed
make cluster
```

### 3. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Follow these naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

---

## 🛠️ Development Workflow

### Make Your Changes

```bash
# Edit files in apps/api, apps/web, etc.
# Hot reload is enabled for both API and Web
```

### Run Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run in watch mode (TDD)
make test-watch
```

### Lint and Format

```bash
# Check linting
make lint

# Auto-format code
make format
```

### Test Locally

```bash
# Check API health
curl http://localhost:8000/healthz

# Open API docs
open http://localhost:8000/docs

# Test your changes in Web UI
open http://localhost:3000
```

### Commit Your Changes

```bash
git add .
git commit -m "feat: add Linear integration support"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test changes
- `chore:` - Build process or auxiliary tool changes

### Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Go to GitHub and create a Pull Request
```

---

## 📝 Pull Request Guidelines

### PR Checklist

Before submitting a PR, ensure:

- [ ] Code follows project style (Ruff + Black for Python, Prettier for TypeScript)
- [ ] All tests pass (`make test`)
- [ ] New features include tests
- [ ] Documentation is updated (if applicable)
- [ ] Commit messages follow Conventional Commits
- [ ] PR description clearly explains the change
- [ ] No secrets or credentials in code

### PR Template

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Tests pass
- [ ] Code is formatted
- [ ] Documentation updated
```

### Review Process

1. **Automated checks**: GitHub Actions run tests and linting
2. **Code review**: Maintainers review within 2-3 business days
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, maintainers will merge
5. **Release**: Changes included in next release

---

## 🏗️ Architecture Guidelines

### Backend (FastAPI)

**File structure:**
```
apps/api/
├── api/               # API routes
│   ├── themes.py     # /themes endpoints
│   ├── feedback.py   # /feedback endpoints
│   └── ...
├── services/          # Business logic
│   ├── clustering.py # Clustering pipeline
│   ├── insights.py   # Insight generation
│   └── ...
├── models/            # SQLAlchemy models
├── config.py          # Configuration
└── main.py            # FastAPI app
```

**Best practices:**
- Use Pydantic for request/response models
- Keep routes thin, logic in services
- Type hints everywhere (`mypy` enforced)
- Async/await for I/O operations
- Structured logging with `structlog`

### Frontend (Next.js)

**File structure:**
```
apps/web/
├── app/               # App Router pages
│   ├── page.tsx      # Home page
│   ├── themes/       # /themes pages
│   └── ...
├── components/        # React components
├── lib/               # Utilities
└── types/             # TypeScript types
```

**Best practices:**
- Use TypeScript for all files
- Tailwind CSS for styling
- Server components by default
- Client components only when needed (`"use client"`)
- Fetch data in Server Components or RSC

### Database Migrations

```bash
# Create migration after model changes
make migrate-create MSG="add sentiment column to feedback"

# Review migration file in infra/alembic/versions/

# Apply migration
make migrate
```

### Adding New Integrations

1. Create connector in `apps/api/services/ingestion/extractors/`
2. Implement `BaseExtractor` interface
3. Add demo data in `samples/`
4. Add tests in `apps/api/tests/`
5. Update `.env.example` with required env vars
6. Add documentation in README and INSTALLATION.md

**Example:**
```python
# apps/api/services/ingestion/extractors/linear.py
from .base import BaseExtractor, IngestionResult

class LinearExtractor(BaseExtractor):
    async def extract(self) -> IngestionResult:
        # Implementation
        pass
```

---

## 🧪 Testing Guidelines

### Unit Tests

```python
# apps/api/tests/test_scoring.py
def test_calculate_theme_score():
    score = calculate_theme_score(
        frequency=10,
        acv=50000,
        sentiment=-0.5,
        segment="enterprise"
    )
    assert 0 <= score <= 100
```

### Integration Tests

```python
# apps/api/tests/test_api.py
async def test_create_feedback(client):
    response = await client.post("/feedback", json={
        "text": "Need SSO support",
        "customer_name": "Acme Corp",
        "source": "slack"
    })
    assert response.status_code == 201
```

### Running Specific Tests

```bash
# Run specific test file
docker compose exec api pytest apps/api/tests/test_scoring.py

# Run specific test
docker compose exec api pytest apps/api/tests/test_scoring.py::test_calculate_theme_score

# Run with verbose output
docker compose exec api pytest -v
```

---

## 🐛 Reporting Bugs

### Before Reporting

1. **Search existing issues**: https://github.com/rohitsaraff33-bit/produckai-backend/issues
2. **Check documentation**: [README.md](README.md), [INSTALLATION.md](INSTALLATION.md)
3. **Verify it's reproducible**: Try on a clean installation

### Bug Report Template

```markdown
## Describe the Bug
Clear description of what went wrong

## To Reproduce
Steps to reproduce:
1. Start services with `make up`
2. Run `make cluster`
3. Check logs with `make logs-worker`
4. See error: "..."

## Expected Behavior
What you expected to happen

## Environment
- OS: macOS 14.5
- Docker version: 24.0.6
- Python version: 3.11.5
- Browser (if UI bug): Chrome 120

## Logs
```
Paste relevant logs here
```

## Screenshots
If applicable, add screenshots
```

---

## 💡 Requesting Features

### Feature Request Template

```markdown
## Feature Description
What feature would you like to see?

## Use Case
Why is this feature needed? How will it be used?

## Proposed Solution
Your ideas on how this could be implemented

## Alternatives Considered
Other approaches you've thought about

## Additional Context
Screenshots, mockups, examples from other tools
```

---

## 🔐 Security

If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Email rohitsaraff33@gmail.com with details
3. We'll respond within 48 hours
4. See [SECURITY.md](SECURITY.md) for full policy

---

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of background or identity.

### Expected Behavior

- Be respectful and considerate
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Trolling or inflammatory remarks
- Personal attacks or insults
- Publishing others' private information

### Enforcement

Violations can be reported to rohitsaraff33@gmail.com. All reports will be reviewed confidentially.

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## 🎉 Recognition

Contributors will be:
- Listed in the project's README
- Mentioned in release notes
- Eligible for "Top Contributor" badge
- Invited to join the maintainers team (if interested)

---

## 🤝 Join the Community

- **GitHub Discussions**: https://github.com/rohitsaraff33-bit/produckai-backend/discussions
- **Email**: rohitsaraff33@gmail.com

We can't wait to see what you build! 🚀

---

**Thank you for helping make product management better for everyone!**
