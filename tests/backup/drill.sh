#!/usr/bin/env bash
# Backup and restore drill (REQ-DEV-OPS-002): lays out a copy of /opt/toads with the drill's compose file, takes
# snapshots on two "nights", rewinds to each (once from the off-server copy only), undoes a rewind and refuses a
# tampered snapshot. Needs Docker. CI runs it through tests/step_defs/test_dev_backup.py.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$(cd "$HERE/../.." && pwd)"
TMP="$(mktemp -d)"
ROOT="$TMP/toads"
COMPOSE=(docker compose -f "$ROOT/infra/docker-compose.prod.yml")

cleanup() {
	"${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
	rm -rf "$TMP"
}
trap cleanup EXIT

fail() { echo "drill: FAILED: $*" >&2; exit 1; }
step() { printf '\n== drill: %s\n' "$*"; }
sql() { "${COMPOSE[@]}" exec -T postgres psql -U toads -d "${2:-toads}" -qAt -c "$1"; }
expect_rows() { local got; got="$(sql 'SELECT string_agg(name, $$,$$ ORDER BY name) FROM members')"; [[ "$got" == "$1" ]] || fail "members are '$got', expected '$1'"; }
expect_config() { local got; got="$(cat "$ROOT/config/raid_days.yaml")"; [[ "$got" == "$1" ]] || fail "config is '$got', expected '$1'"; }
names() { find "$TMP/backups" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | grep -E '^[0-9]{4}-' | sort; }

step "laying out a server in $ROOT"
mkdir -p "$ROOT/scripts" "$ROOT/infra/certs" "$ROOT/config" "$ROOT/services/api" "$ROOT/services/worker"
cp "$SRC/scripts/backup.sh" "$SRC/scripts/backup-lib.sh" "$SRC/scripts/restore.sh" "$ROOT/scripts/"
mkdir -p "$ROOT/infra/backup" && cp "$SRC/infra/backup/Dockerfile" "$ROOT/infra/backup/"
cp "$HERE/compose.yml" "$ROOT/infra/docker-compose.prod.yml"
echo "TOADS_DOMAIN=drill.invalid" >"$ROOT/infra/.env"
printf '%s\n' "TOADS_DRILL_SETTING=night-one" "TOADS_DATABASE_URL=postgresql+psycopg://toads:drill-o'pw@postgres:5432/toads" \
	>"$ROOT/services/api/.env"
echo "tls /certs/fullchain.pem /certs/privkey.pem" >"$ROOT/infra/certs/tls.caddy"
echo "night: one" >"$ROOT/config/raid_days.yaml"
cat >"$ROOT/infra/.env.backup" <<SETTINGS
TOADS_BACKUP_DIR=$TMP/backups
TOADS_BACKUP_KEEP_LOCAL=2
RESTIC_REPOSITORY=$TMP/offsite
RESTIC_PASSWORD=drill-only-password
SETTINGS
git -C "$ROOT" init -q && git -C "$ROOT" -c user.name=drill -c user.email=drill@invalid commit -q --allow-empty -m drill

"${COMPOSE[@]}" up -d --wait postgres api worker scheduler web caddy
sql 'CREATE TABLE members (name text PRIMARY KEY)'
sql "INSERT INTO members VALUES ('ada')"
"${COMPOSE[@]}" exec -T caddy sh -c 'echo account > /data/acme.json'

step "night one"
"$ROOT/scripts/backup.sh" nightly
night1="$(names | tail -n 1)"
sleep 1

step "night two"
sql "INSERT INTO members VALUES ('bo')"
echo "night: two" >"$ROOT/config/raid_days.yaml"
sed -i 's/night-one/night-two/' "$ROOT/services/api/.env"
"$ROOT/scripts/backup.sh" nightly
night2="$(names | tail -n 1)"
[[ "$night1" != "$night2" ]] || fail "two nights share a name"
for f in hub.dump hub.toc files.tar.gz caddy_data.tar.gz MANIFEST SHA256SUMS; do
	[[ -s "$TMP/backups/$night2/$f" ]] || fail "$night2 has no $f"
done
tar -tzf "$TMP/backups/$night2/files.tar.gz" | grep -qx 'infra/certs/tls.caddy' || fail "certs are not in the snapshot"
listed="$("$ROOT/scripts/restore.sh" list)"
echo "$listed"
[[ "$(grep -c "$night2" <<<"$listed")" == 2 ]] || fail "list does not show $night2 both here and off the server"

step "the day after: a change to rewind"
sql "INSERT INTO members VALUES ('cy')"
echo "night: three" >"$ROOT/config/raid_days.yaml"

step "rewind to night one"
"$ROOT/scripts/restore.sh" "$night1" --yes
expect_rows "ada"
expect_config "night: one"
grep -q night-two "$ROOT/services/api/.env" || fail ".env was rewound without --with-env"
[[ "$(sql 'SELECT count(*) FROM members' toads_previous)" == 3 ]] || fail "toads_previous does not hold the replaced database"
names | grep -q -- '-pre-restore$' || fail "no pre-restore snapshot was taken"
[[ -n "$("${COMPOSE[@]}" ps -q --status running api)" ]] || fail "the API was not started again"

step "undo the rewind"
"$ROOT/scripts/restore.sh" undo
expect_rows "ada,bo,cy"

step "rewind to night two from the off-server copy alone, with its .env files"
rm -rf "${TMP:?}/backups/$night2"
"$ROOT/scripts/restore.sh" "$night2" --offsite --with-env --yes
expect_rows "ada,bo"
expect_config "night: two"
grep -q night-two "$ROOT/services/api/.env" || fail ".env was not put back with --with-env"

step "a tampered snapshot is refused and nothing changes"
echo tampered >>"$TMP/backups/$night1/hub.dump"
if "$ROOT/scripts/restore.sh" "$night1" --yes; then fail "a tampered snapshot was restored"; fi
expect_rows "ada,bo"

step "a snapshot whose migration fails is rolled back and the hub keeps serving"
sql 'CREATE TABLE poison (x int)'
"$ROOT/scripts/backup.sh" poisoned
sql 'DROP TABLE poison'
if "$ROOT/scripts/restore.sh" "$(names | grep -- '-poisoned$')" --db-only --yes; then fail "a failed migration was not reported"; fi
expect_rows "ada,bo"
[[ -n "$("${COMPOSE[@]}" ps -q --status running api)" ]] || fail "the API was not started again after the rollback"

step "a rebuilt server: an empty database and no local snapshots, restored from the off-server copy"
"${COMPOSE[@]}" down -v >/dev/null 2>&1
rm -rf "${TMP:?}/backups"
"$ROOT/scripts/restore.sh" "$night2" --offsite --with-env --yes
expect_rows "ada,bo"
[[ "$(sql "SELECT rolpassword IS NOT NULL FROM pg_authid WHERE rolname = 'toads'")" == t ]] ||
	fail "the database password was not set from the restored TOADS_DATABASE_URL"
[[ "$("${COMPOSE[@]}" exec -T caddy cat /data/acme.json)" == account ]] || fail "Caddy's certificates were not put back"

step "an rclone destination, the way Google Drive is reached"
# rclone's local backend stands in for Drive; the repository sits in the cache folder restic's container mounts.
cat >>"$ROOT/infra/.env.backup" <<SETTINGS
RESTIC_REPOSITORY=rclone:drill:/cache/rclone-repo
RCLONE_CONFIG_DRILL_TYPE=local
SETTINGS
"$ROOT/scripts/backup.sh" nightly
rclone_night="$(names | grep -E 'Z$' | tail -n 1)"
[[ "$("$ROOT/scripts/restore.sh" list)" == *"rclone:drill"*"$rclone_night"* ]] || fail "list does not show the rclone repository"
rm -rf "${TMP:?}/backups/$rclone_night"
"$ROOT/scripts/restore.sh" "$rclone_night" --offsite --db-only --yes
expect_rows "ada,bo"
sleep 1

step "retention"
"$ROOT/scripts/backup.sh" nightly
sleep 1
"$ROOT/scripts/backup.sh" nightly
[[ "$(names | grep -cE 'Z$')" -le 2 ]] || fail "more than TOADS_BACKUP_KEEP_LOCAL nightly snapshots are kept: $(names | tr '\n' ' ')"

printf '\n== drill: passed\n'
