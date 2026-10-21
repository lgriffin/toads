#!/usr/bin/env bash
# Turns on the nightly backup on the production server (ADMIN_GUIDE.md section 13). Run as root, once:
#
#   sudo bash /opt/toads/scripts/backup-install.sh
#
# Writes infra/.env.backup (with a generated RESTIC_PASSWORD) unless it exists, makes the snapshot folder, installs
# and starts the toads-backup timer, then takes a first snapshot to show it works (--no-run skips that, for a server
# whose site is not running yet). Safe to run again: it never replaces a setting that is already there.
set -euo pipefail

APP=/opt/toads
APP_USER=toads

main() {
	local run=true
	[[ "${1:-}" == --no-run ]] && run=false
	if [[ $EUID -ne 0 ]]; then echo "Run as root (sudo bash $0)." >&2; exit 1; fi
	local settings=$APP/infra/.env.backup dir

	if [[ ! -f $settings ]]; then
		install -m 600 -o "$APP_USER" -g "$APP_USER" "$APP/infra/.env.backup.example" "$settings"
	fi
	if grep -q '^RESTIC_PASSWORD=replace-me$' "$settings"; then
		local password
		password="$(openssl rand -base64 33 | tr -d '/+=\n')"
		sed -i "s|^RESTIC_PASSWORD=replace-me$|RESTIC_PASSWORD=$password|" "$settings"
		echo "Generated RESTIC_PASSWORD in $settings. Copy it into your password manager now:"
		echo "  sudo grep RESTIC_PASSWORD $settings"
	fi
	chmod 600 "$settings"
	chown "$APP_USER:$APP_USER" "$settings"

	dir="$(sed -n 's/^TOADS_BACKUP_DIR=//p' "$settings" | tail -n 1)"
	dir="${dir:-/var/backups/toads}"
	install -d -m 700 -o "$APP_USER" -g "$APP_USER" "$dir"

	install -m 644 "$APP/infra/systemd/toads-backup.service" "$APP/infra/systemd/toads-backup.timer" /etc/systemd/system/
	command -v restorecon >/dev/null && restorecon /etc/systemd/system/toads-backup.service /etc/systemd/system/toads-backup.timer
	systemctl daemon-reload
	systemctl enable --now toads-backup.timer
	sudo -u "$APP_USER" docker build -q -t "$(sed -n 's/^RESTIC_IMAGE=//p' "$APP/scripts/backup-lib.sh")" \
		"$APP/infra/backup" >/dev/null

	if [[ "$run" == true ]]; then
		echo "Taking a first snapshot (journalctl -u toads-backup shows the details)..."
		if systemctl start toads-backup.service; then
			echo "First snapshot done: sudo -iu $APP_USER $APP/scripts/restore.sh list"
		else
			echo "The first snapshot failed: sudo journalctl -u toads-backup -n 50" >&2
			exit 1
		fi
	fi
	systemctl list-timers toads-backup.timer --no-pager
	if ! grep -Eq '^RESTIC_REPOSITORY=.+' "$settings"; then
		echo "Snapshots stay on this server until RESTIC_REPOSITORY is set in $settings (ADMIN_GUIDE.md section 13)."
	fi
}

main "$@"
