.PHONY: dev lint format test install install-all demo

install-all:
	py -3.11 -m pip install -e "sdk/[dev]" -q
	py -3.11 -m pip install -e "server/[dev]" -q
	cd dashboard && npm install --silent

dev:
	@echo "Run 'uv run agentlens serve' (not yet implemented)"

lint:
	uv run ruff check sdk/ server/ examples/
	cd dashboard && npm run lint

format:
	uv run ruff format sdk/ server/ examples/
	cd dashboard && npm run format

test:
	uv run pytest sdk/tests/ server/tests/ -v

install:
	uv pip install -e "sdk/[dev]" -e "server/[dev]"
	cd dashboard && npm install

demo: ## Start collector + dashboard, run example, print URL for GIF recording
	@bash scripts/record_demo.sh
