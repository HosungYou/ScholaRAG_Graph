# Contributing to ScholaRAG_Graph

Thank you for your interest in contributing to ScholaRAG_Graph! This document provides guidelines and instructions for contributing.

## 🌟 Ways to Contribute

- **Bug Reports**: Found a bug? Open an issue with detailed reproduction steps
- **Feature Requests**: Have an idea? We'd love to hear it
- **Code Contributions**: Submit a pull request
- **Documentation**: Help improve our docs
- **Testing**: Add tests or improve test coverage

## 🚀 Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/ScholaRAG_Graph.git
cd ScholaRAG_Graph
```

### 2. Set Up Development Environment

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

**Frontend:**
```bash
cd frontend
npm install
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number
```

## 📝 Code Style

### Python (Backend)

We use the following tools:
- **Black**: Code formatting
- **Ruff**: Linting
- **MyPy**: Type checking

```bash
# Format code
black .

# Lint
ruff check .

# Type check
mypy .
```

### TypeScript (Frontend)

We use:
- **ESLint**: Linting
- **Prettier**: Formatting

```bash
npm run lint
npm run format
```

## ✅ Testing

### Backend Tests

```bash
cd backend
pytest --cov=. --cov-report=html
```

### Frontend Tests

```bash
cd frontend
npm run test
```

### Before Submitting

1. Ensure all tests pass
2. Add tests for new features
3. Update documentation if needed
4. Run linters and formatters

## 📤 Pull Request Process

1. **Update your branch** with the latest main:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Push your changes**:
   ```bash
   git push origin your-branch-name
   ```

3. **Open a Pull Request** on GitHub with:
   - Clear title describing the change
   - Description of what and why
   - Link to related issue (if any)
   - Screenshots for UI changes

4. **Address Review Comments** promptly

## 🏗️ Project Structure

```
ScholaRAG_Graph/
├── backend/                 # FastAPI Backend
│   ├── agents/             # Multi-Agent System (6 agents)
│   ├── graph/              # Graph Storage & Processing
│   │   ├── entity_extractor.py    # LLM-based concept extraction
│   │   ├── gap_detector.py        # InfraNodus-style gap detection
│   │   └── relationship_builder.py # Semantic relationship building
│   ├── importers/          # Data Import
│   ├── llm/                # Multi-Provider LLM
│   ├── routers/            # API Routes
│   └── tests/              # Backend Tests
├── frontend/               # Next.js Frontend
│   ├── app/                # App Router Pages
│   └── components/         # React Components
│       └── graph/          # Graph Visualization
└── database/               # PostgreSQL Schema
```

## 🎯 Priority Areas

We especially welcome contributions in these areas:

### High Priority
- [ ] Test coverage improvement (target: 80%+)
- [ ] API documentation (OpenAPI)
- [ ] Error handling standardization
- [ ] Performance optimization

### Medium Priority
- [ ] Zotero/Mendeley integration
- [ ] PRISMA diagram auto-generation
- [ ] Mobile responsiveness

### Low Priority
- [ ] Real-time collaboration
- [ ] Living review support
- [ ] Enterprise SSO

## 📜 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Keep discussions on-topic

## 💬 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and community chat
- **Email**: [Contact maintainer]

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to ScholaRAG_Graph! 🎉
