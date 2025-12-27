.PHONY: up down test logs etl clean

up:
	docker-compose up -d api

down:
	docker-compose down

test:
	docker-compose exec api pytest tests/ -v

logs:
	docker-compose logs -f api

etl:
	docker-compose run --rm etl

clean:
	docker-compose down -v
	docker system prune -f
