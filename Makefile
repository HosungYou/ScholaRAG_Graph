.PHONY: verify-env test-backend-core test-backend-full test-frontend-core test-frontend-e2e test-frontend-visual test-all-core

BACKEND_DIR := backend
FRONTEND_DIR := frontend
BACKEND_PYTEST := $(BACKEND_DIR)/venv/bin/pytest

verify-env:
	@echo "Repository: $$(pwd)"
	@echo "Backend pytest: $(BACKEND_PYTEST)"
	@$(BACKEND_PYTEST) --version
	@echo "Frontend node: $$(cd $(FRONTEND_DIR) && node -v)"
	@echo "Frontend npm:  $$(cd $(FRONTEND_DIR) && npm -v)"

test-backend-core:
	$(BACKEND_PYTEST) -q \
		$(BACKEND_DIR)/tests/test_entity_resolution.py \
		$(BACKEND_DIR)/tests/test_agents.py \
		$(BACKEND_DIR)/tests/test_importer.py \
		$(BACKEND_DIR)/tests/test_api_contracts.py \
		$(BACKEND_DIR)/tests/test_integrations.py

test-backend-full:
	$(BACKEND_PYTEST) -q $(BACKEND_DIR)/tests

test-frontend-core:
	cd $(FRONTEND_DIR) && npm run type-check && npm run test -- __tests__/lib/api.test.ts __tests__/hooks/useGraphStore.test.ts __tests__/components/graph/Graph3D.test.tsx __tests__/components/import/ImportProgress.test.tsx __tests__/components/graph/GapPanel.test.tsx __tests__/components/graph/GapPanel.snapshot.test.tsx __tests__/components/import/ImportProgress.snapshot.test.tsx __tests__/components/graph/Graph3D.snapshot.test.tsx __tests__/components/graph/KnowledgeGraph3D.snapshot.test.tsx --runInBand

test-frontend-e2e:
	cd $(FRONTEND_DIR) && npx playwright test -c playwright.config.ts e2e/graph-interactions.spec.ts

test-frontend-visual:
	cd $(FRONTEND_DIR) && npx playwright test -c playwright.config.ts e2e/visual-regression.spec.ts

test-all-core: test-backend-core test-frontend-core
