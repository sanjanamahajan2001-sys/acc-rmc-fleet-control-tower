# Feature-Based Business Module Architecture

Every future business capability (e.g., ERP Import Workspace, Site Dashboard, Timeline Replay)
MUST be implemented as an isolated module under `src/modules/<module-name>/`.

## Standard Module Internal Directory Structure
```
modules/<module-name>/
├── api/          # Module-specific API endpoints & queries
├── components/   # Module-specific UI components & widgets
├── hooks/        # Module-specific custom React hooks
├── pages/        # Module-specific React router pages
├── routes/       # Module route definitions
├── store/        # Module-specific Zustand state slice
├── tests/        # Module-specific unit & component tests
└── types/        # Module-specific TypeScript declarations
```

## Module Governance Rules
1. **Zero Cross-Module Dependency**: A module MUST NEVER import directly from another module.
2. **Shared Assets**: Reusable components belong exclusively in `src/components/`.
3. **Isolated State**: Module Zustand stores must be self-contained slices.
