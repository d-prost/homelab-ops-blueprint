.PHONY: validate ci lab-proof idempotency-proof acceptance-proof interruption-proof stale-marker-proof ssh-interruption-proof public-safety syntax

validate:
	bash scripts/validate-repository.sh

ci:
	HOMELAB_STRICT_VALIDATION=1 bash scripts/validate-repository.sh

lab-proof:
	HOMELAB_LAB_ROLLBACK_TEST=1 bash tests/test-lab-rollback.sh

idempotency-proof:
	HOMELAB_LAB_IDEMPOTENCY_TEST=1 bash tests/test-lab-idempotency.sh

acceptance-proof:
	HOMELAB_LAB_ACCEPTANCE_FAILURE_TEST=1 bash tests/test-lab-acceptance-persistence.sh

interruption-proof:
	HOMELAB_LAB_INTERRUPTION_TEST=1 bash tests/test-lab-interruption-recovery.sh

stale-marker-proof:
	HOMELAB_LAB_STALE_MARKER_PROOF=1 bash tests/test-lab-stale-accepted-marker.sh

ssh-interruption-proof:
	HOMELAB_SSH_INTERRUPTION_TEST=1 bash tests/test-ssh-session-interruption.sh

public-safety:
	python3 scripts/check-public-safety.py

syntax:
	bash -n scripts/*.sh tests/*.sh
	python3 -c "from pathlib import Path; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in sorted(Path('scripts').glob('*.py'))]; print('Python syntax validation passed.')"
