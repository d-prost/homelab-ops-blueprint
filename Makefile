.PHONY: validate lab-proof

validate:
	./scripts/validate-repository.sh

lab-proof:
	HOMELAB_LAB_ROLLBACK_TEST=1 ./tests/test-lab-rollback.sh
