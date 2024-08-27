.PHONY: run debug backup clean clean-logs clean-data clean-conversations

run:
	@ENV_FOR_DYNACONF=prod python src/bot.py

debug: clean
	@ENV_FOR_DYNACONF=dev python src/bot.py

backup:
	@timestamp=$$(date +%Y%m%d) && \
	mkdir -p backup/$$timestamp && \
	cp -r data backup/$$timestamp/. && \
	cp -r logs/bot.log backup/$$timestamp/. && \
	cp -r backup/$$timestamp/* backup/.

clean: clean-logs clean-data

clean-logs:
	@rm -rf logs

clean-data:
	@rm -rf data

clean-conversations:
	@rm -f data/db_conversations
