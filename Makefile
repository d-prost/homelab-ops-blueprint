.PHONY: validate ci lab-proof public-safety syntax

validate:
	bash scripts/validate-repository.sh

ci:
	HOMELAB_STRICT_VALIDATION=1 bash scripts/validate-repository.sh

lab-proof:
	HOMELAB_LAB_ROLLBACK_TEST=1 bash tests/test-lab-rollback.sh

public-safety:
	python3 scripts/check-public-safety.py

syntax:
	bash -n scripts/*.sh tests/*.sh
	python3 -c "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in sorted(Path('scripts').glob('*.py'))]; print('Python syntax validation passed.')"
