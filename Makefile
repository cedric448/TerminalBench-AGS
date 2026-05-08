.PHONY: build push setup run clean login

IMAGE = lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:latest

login:
	docker login lily-tcr.tencentcloudcr.com --username 100000881922 --password-stdin < .tcr-password

build:
	docker build -t $(IMAGE) .

push:
	docker push $(IMAGE)

build-push: build push

setup:
	pip install -r requirements.txt

run:
	cd src && python run_bench.py

clean:
	cd src && python -c "from sandbox_manager import cleanup; cleanup()"
