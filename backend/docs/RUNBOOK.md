# AURA Operations Runbook

## Database Backups & Restore
We use `pg_dump` for logical backups and `WAL-G` for continuous archiving and point-in-time recovery (PITR).

### Backup
```bash
# Logical backup
pg_dump -h $PGHOST -U $PGUSER $PGDATABASE -F c -f /backups/aura_$(date +%Y%m%d).dump
```

### Restore Drill
1. Spin up an isolated restore environment.
2. `pg_restore -d $PGDATABASE -c /backups/aura_<date>.dump`
3. Verify `alembic current` matches the target state.
4. Verify data via sampling `organizations` and `users`.

## Alert Responses
- **Error Budget Exceeded**: Halt non-critical LLM jobs. Scale up LLM caching.
- **P95 Latency > 1000ms**: Check DB pool saturation. Check PgBouncer stats.
- **Queue Lag**: Increase ARQ worker count or scale vertically. Check Redis memory.
- **Auth-failure Spikes**: Investigate potential credential stuffing or IDOR attempts.

## Retention
- Runs and traces older than 30 days are automatically deleted unless `legal_hold=true`.
- Run `python scripts/retention.py` manually if emergency cleanup is needed.
