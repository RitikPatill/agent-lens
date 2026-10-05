.PHONY: dev lint format test install demo

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

demo:
	@echo "Demo target available in M7 — run 'python examples/research_assistant.py' after make install"
