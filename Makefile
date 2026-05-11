.PHONY: build push build-task push-task setup run clean login stop-all

BASE_IMAGE = lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench:v6
TASK_IMAGE = lily-tcr.tencentcloudcr.com/terminalbench/terminal-bench-task:v1

login:
	docker login lily-tcr.tencentcloudcr.com --username 100000881922 --password-stdin < .tcr-password

build:
	docker build -t $(BASE_IMAGE) .

push:
	docker push $(BASE_IMAGE)

build-task:
	docker build -t $(TASK_IMAGE) -f Dockerfile .

push-task:
	docker push $(TASK_IMAGE)

build-push: build push build-task push-task

setup:
	pip install -r requirements.txt

run:
	cd src && python3 -u run_bench.py

stop-all:
	cd src && python3 sandbox_manager.py stop-all

clean:
	cd src && python3 sandbox_manager.py cleanup
