#!/usr/bin/env bash
# Takes a snapshot of everything the hub keeps (ADMIN_GUIDE.md section 13): the hub database (the analyzer's tables
# included), config/*.yaml, the .env files, infra/certs and Caddy's certificates. The snapshot is checked, kept on the
# server under TOADS_BACKUP_DIR, and copied off the server with restic, encrypted, when RESTIC_REPOSITORY is set in
# infra/.env.backup. The toads-backup timer runs it every night; run it by hand any time:
#
#   sudo -iu toads /opt/toads/scripts/backup.sh [label]     # label: nightly (the timer), manual (default), ...
#
# scripts/restore.sh puts a snapshot back. Everything sits in main() because a deploy may rewrite this file while it
# runs.
set -euo pipefail

NAME=""
WORK=""

main() {
	REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
	# shellcheck source=scripts/backup-lib.sh
	. "$REPO/scripts/backup-lib.sh"
	cd "$REPO"
	local label="${1:-manual}" dir
	if [[ ! "$label" =~ ^[a-z][a-z-]*$ ]]; then
		echo "backup: the label must be lower-case letters and dashes, got '$label'" >&2
		exit 64
	fi
	dir="$(backup_dir)"
	mkdir -p "$dir"
	chmod 700 "$dir"
	exec 8>"$dir/.lock"
	flock -n 8 || { echo "backup: another backup is running" >&2; exit 75; }

	NAME="$(date -u +%Y-%m-%dT%H%M%SZ)"
	[[ "$label" == nightly ]] || NAME="$NAME-$label"
	if [[ -e "$dir/$NAME" ]]; then
		echo "backup: $dir/$NAME already exists" >&2
		exit 73
	fi
	WORK="$dir/.partial-$NAME"
	trap finish EXIT
	mkdir -m 700 "$WORK"

	echo "backup: $NAME"
	dump_database "$WORK"
	copy_files "$WORK"
	copy_caddy_data "$WORK"
	write_manifest "$WORK" "$NAME" "$label"
	mv "$WORK" "$dir/$NAME"
	echo "backup: kept on this server in $dir/$NAME ($(du -sh "$dir/$NAME" | cut -f1))"

	if offsite_enabled; then
		copy_offsite "$dir/$NAME" "$NAME"
	else
		echo "backup: no off-server copy: RESTIC_REPOSITORY is empty in infra/.env.backup (ADMIN_GUIDE.md section 13)" >&2
	fi
	prune_local "$dir"
	echo "$NAME $(date -u +%FT%TZ) offsite=$(offsite_enabled && echo yes || echo no)" >"$dir/last-success"
	echo "backup: done"
}

# On failure: drop the half-written snapshot and say so where someone will see it.
# shellcheck disable=SC2329  # called by the EXIT trap
finish() {
	local status=$?
	[[ $status -eq 0 ]] && return 0
	[[ -n "$WORK" ]] && rm -rf "$WORK"
	echo "backup: FAILED (exit $status)" >&2
	alert "Toads backup ${NAME:-?} failed on $(hostname) (exit $status): see journalctl -u toads-backup"
}

# pg_dump's custom format (compressed, restorable table by table). `exec -T` keeps a TTY from corrupting the bytes.
dump_database() {
	local work="$1" tables
	compose exec -T postgres pg_dump -U toads -d toads -Fc >"$work/hub.dump"
	# Read the dump back: a truncated or unreadable file fails here, tonight, not on the day it is needed.
	compose exec -T postgres pg_restore --list <"$work/hub.dump" >"$work/hub.toc"
	tables="$(grep -c ' TABLE DATA ' "$work/hub.toc" || true)"
	if [[ "$tables" -eq 0 ]]; then
		echo "backup: the dump holds no table data" >&2
		return 1
	fi
	echo "backup: database dumped, $tables tables"
}

# The git-ignored files a fresh checkout would not bring back. They hold secrets, so the snapshot folder is 0700 and
# the off-server copy is encrypted.
copy_files() {
	local work="$1" files=() f
	shopt -s nullglob
	for f in config/*.yaml infra/.env services/*/.env services/*/.env.* infra/certs/*; do
		[[ "$f" == *.example || "$f" == */.gitkeep ]] && continue
		[[ -f "$REPO/$f" ]] && files+=("$f")
	done
	shopt -u nullglob
	if [[ ${#files[@]} -eq 0 ]]; then
		tar -czf "$work/files.tar.gz" -T /dev/null
	else
		tar -C "$REPO" -czf "$work/files.tar.gz" "${files[@]}"
	fi
	echo "backup: ${#files[@]} config, env and certificate files"
}

# Caddy's Let's Encrypt account and certificates. Only a rebuilt server needs them (Caddy would otherwise ask Let's
# Encrypt again, which limits how often it may); a rewind leaves them alone.
copy_caddy_data() {
	local work="$1"
	if [[ -z "$(compose ps -q --status running caddy 2>/dev/null)" ]]; then
		echo "backup: caddy is not running; its certificates are not in this snapshot" >&2
		return 0
	fi
	compose exec -T caddy tar -C /data -czf - . >"$work/caddy_data.tar.gz"
}

write_manifest() {
	local work="$1" name="$2" label="$3" commit
	commit="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo unknown)"
	cat >"$work/MANIFEST" <<-EOF
		name=$name
		label=$label
		created=$(date -u +%FT%TZ)
		host=$(hostname)
		commit=$commit
	EOF
	local sums=(hub.dump hub.toc files.tar.gz MANIFEST)
	[[ -f "$work/caddy_data.tar.gz" ]] && sums+=(caddy_data.tar.gz)
	(cd "$work" && sha256sum "${sums[@]}" >SHA256SUMS)
}

# restic encrypts on the server, so the object store only ever holds ciphertext. Every snapshot is backed up from the
# same path (/snapshot) so restic deduplicates between nights; its tag is the snapshot's name. Every snapshot of the
# last TOADS_BACKUP_KEEP_DAYS days is kept (a manual one never pushes out that day's nightly), then one a week and
# one a month.
copy_offsite() {
	local path="$1" name="$2"
	RESTIC_EXTRA_MOUNTS=(-v "$path:/snapshot:ro,z")
	if ! restic cat config >/dev/null 2>&1; then
		echo "backup: creating the restic repository"
		restic init
	fi
	restic backup --quiet --host toads --tag toads --tag "$name" /snapshot
	RESTIC_EXTRA_MOUNTS=()
	restic forget --quiet --host toads --tag toads --prune \
		--keep-within "$(setting TOADS_BACKUP_KEEP_DAYS 14)d" \
		--keep-weekly "$(setting TOADS_BACKUP_KEEP_WEEKLY 8)" \
		--keep-monthly "$(setting TOADS_BACKUP_KEEP_MONTHLY 12)"
	restic check --quiet
	echo "backup: copied off the server to $(setting RESTIC_REPOSITORY | sed -E 's#^(s3:https?://[^/]+/).*#\1...#')"
}

# Keep the newest TOADS_BACKUP_KEEP_LOCAL nightly snapshots here; labelled ones (manual, pre-restore) for 30 days.
prune_local() {
	local dir="$1" keep old
	keep="$(setting TOADS_BACKUP_KEEP_LOCAL 14)"
	while read -r old; do
		[[ -n "$old" ]] && rm -rf "${dir:?}/$old" && echo "backup: removed $old from this server"
	done < <(local_names | grep -E "$NIGHTLY_NAME" | head -n "-$keep")
	find "$dir" -mindepth 1 -maxdepth 1 -type d -name '*Z-*' -mtime +30 -exec rm -rf {} +
	find "$dir" -mindepth 1 -maxdepth 1 -type d -name '.partial-*' -mmin +360 -exec rm -rf {} +
	find "$dir" -mindepth 1 -maxdepth 1 -type d -name '.restore-*' -mmin +360 -exec rm -rf {} +
}

main "$@"
exit
