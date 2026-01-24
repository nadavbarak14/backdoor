# Documentation

## Purpose

This directory contains all project documentation for the Basketball Analytics Platform beyond code-level documentation.

## Contents

| File/Directory | Description |
|----------------|-------------|
| `architecture.md` | System architecture and design decisions |
| `api/` | API reference documentation |
| `models/` | Data model documentation and ERD |

## Documentation Types

### Code Documentation (in source files)
- Module docstrings
- Function/method docstrings
- Class docstrings
- Inline comments (sparingly)

### Folder Documentation (README.md files)
- Every folder has a README.md
- Explains purpose, contents, usage
- See `CLAUDE.md` for template

### Technical Documentation (this folder)
- Architecture decisions
- API reference
- Data models
- Deployment guides

## API Documentation

The API is documented in multiple ways:

1. **OpenAPI/Swagger** - Auto-generated at `/docs`
2. **ReDoc** - Alternative view at `/redoc`
3. **Manual docs** - In `docs/api/` for detailed guides

## Related Documentation

- [Development Guidelines](../CLAUDE.md)
- [Project README](../README.md)
