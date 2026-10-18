#!/usr/bin/env bash
# One-time setup of a fresh AlmaLinux 10 (or RHEL 10) server for the Toads hub (docs/deploy.md). Run as root:
#
#   curl -fsSL https://raw.githubusercontent.com/lgriffin/toads/main/scripts/server-setup.sh -o server-setup.sh
#   sudo bash server-setup.sh toads.example.com you@example.com
#
# Installs Docker CE, opens HTTP/HTTPS in firewalld with SELinux left enforcing, creates the `toads` user, clones the
# hub to /opt/toads, writes every env file with fresh generated secrets, and makes the SSH key GitHub deploys with.
# Safe to run again: it never replaces a secret that is already set. It does not start the site: the Discord and
# Warcraft Logs values only you have go in first (docs/deploy.md, step 5).
set -euo pipefail

REPO_URL=https://github.com/lgriffin/toads
APP=/opt/toads
APP_USER=toads

main() {
	local domain="${1:-}" email="${2:-}"
	if [[ $EUID -ne 0 ]]; then echo "Run as root (sudo bash $0 ...)." >&2; exit 1; fi
	if [[ ! "$domain" =~ ^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ || ! "$email" =~ ^[^@[:space:]]+@[^@[:space:]]+$ ]]; then
		echo "Usage: $0 <domain, e.g. toads.example.com> <email for Let's Encrypt>" >&2
		exit 64
	fi
	# shellcheck source=/dev/null
	. /etc/os-release
	if [[ "${VERSION_ID%%.*}" != 10 ]]; then
		echo "Warning: written for AlmaLinux 10; this is $PRETTY_NAME. Continuing in 5 seconds (Ctrl-C to stop)." >&2
		sleep 5
	fi

	step "Updating the system and installing base packages"
	dnf -y upgrade
	dnf -y install dnf-plugins-core git curl tar openssl firewalld policycoreutils-python-utils util-linux

	install_docker
	configure_firewall
	add_swap
	create_user
	clone_repo
	write_env_files "$domain" "$email"
	make_deploy_key "$domain"

	step "Done"
	echo "SELinux is $(getenforce). Next: fill in the Discord and Warcraft Logs values (docs/deploy.md, step 5), then"
	echo "start the site with:  sudo -iu $APP_USER $APP/scripts/deploy.sh"
}

step() { printf '\n==> %s\n' "$*"; }

install_docker() {
	step "Installing Docker CE"
	if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
		dnf -y remove docker docker-client docker-common docker-latest docker-engine podman-docker podman runc || true
		dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo 2>/dev/null ||
			dnf config-manager addrepo --from-repofile=https://download.docker.com/linux/rhel/docker-ce.repo
		dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
	fi
	if [[ ! -f /etc/docker/daemon.json ]]; then
		# selinux-enabled makes the compose file's `z` mount labels take effect; logs rotate instead of filling the disk.
		mkdir -p /etc/docker
		cat >/etc/docker/daemon.json <<'JSON'
{
  "selinux-enabled": true,
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "5" }
}
JSON
	else
		echo "/etc/docker/daemon.json exists; left as it is."
	fi
	systemctl enable --now docker
	systemctl restart docker
	docker compose version
}

configure_firewall() {
	step "Opening SSH, HTTP and HTTPS in firewalld"
	systemctl enable --now firewalld
	firewall-cmd --permanent --add-service=ssh --add-service=http --add-service=https
	firewall-cmd --permanent --add-port=443/udp  # HTTP/3
	firewall-cmd --reload
	# Docker publishes container ports itself, around firewalld; the production compose publishes only 80 and 443.
}

add_swap() {
	local mem_mb
	mem_mb=$(awk '/MemTotal/ {print int($2 / 1024)}' /proc/meminfo)
	if [[ -z "$(swapon --show)" && $mem_mb -lt 4096 ]]; then
		step "Adding 2 GB of swap (${mem_mb} MB RAM; image builds need the headroom)"
		fallocate -l 2G /swapfile
		chmod 600 /swapfile
		mkswap /swapfile
		restorecon /swapfile || true
		swapon /swapfile
		grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap defaults 0 0' >>/etc/fstab
	fi
}

create_user() {
	step "Creating the $APP_USER user"
	id "$APP_USER" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$APP_USER"
	# The docker group is root-equivalent on this server: only the deploy key and admins log in as this user.
	usermod -aG docker "$APP_USER"
}

clone_repo() {
	step "Cloning $REPO_URL to $APP"
	if [[ ! -d "$APP/.git" ]]; then
		install -d -o "$APP_USER" -g "$APP_USER" "$APP"
		sudo -u "$APP_USER" git clone "$REPO_URL" "$APP"
	else
		sudo -u "$APP_USER" git -C "$APP" fetch --quiet origin main
	fi
}

# Print the value of KEY in FILE (empty if missing).
env_get() { grep -m1 "^$2=" "$1" | cut -d= -f2- || true; }

# Set KEY=VALUE in FILE, replacing the line if there is one. Values are never passed through sed, so any
# character is safe.
env_set() {
	local file=$1 key=$2 value=$3
	if grep -q "^$key=" "$file"; then
		KEY=$key VALUE=$value awk 'index($0, ENVIRON["KEY"] "=") == 1 { print ENVIRON["KEY"] "=" ENVIRON["VALUE"]; next } { print }' \
			"$file" >"$file.tmp"
		cat "$file.tmp" >"$file"
		rm -f "$file.tmp"
	else
		printf '%s=%s\n' "$key" "$value" >>"$file"
	fi
}

# KEY's value in FILE, after generating one with CMD if it is still the example's placeholder.
secret() {
	local file=$1 key=$2 cmd=$3 value
	value=$(env_get "$file" "$key")
	if [[ -z "$value" || "$value" == replace-me ]]; then
		value=$(eval "$cmd")
		env_set "$file" "$key" "$value"
	fi
	printf '%s' "$value"
}

write_env_files() {
	local domain=$1 email=$2
	step "Writing env files (existing secrets are kept)"
	local infra=$APP/infra/.env api=$APP/services/api/.env worker=$APP/services/worker/.env
	local bot=$APP/services/bot/.env bank=$APP/services/bot/.env.bank
	[[ -f $infra ]] || cp "$APP/infra/.env.example" "$infra"
	[[ -f $api ]] || cp "$APP/services/api/.env.example" "$api"
	[[ -f $worker ]] || cp "$APP/services/worker/.env.example" "$worker"
	[[ -f $bot ]] || cp "$APP/services/bot/.env.example" "$bot"
	if [[ ! -f $bank ]]; then
		cp "$APP/services/bot/.env.example" "$bank"
		env_set "$bank" TOADS_BOT_SPEC bank
	fi
	local name
	for name in raid_days community raid_sheets; do
		[[ -f $APP/config/$name.yaml ]] || cp "$APP/config/$name.example.yaml" "$APP/config/$name.yaml"
	done

	env_set "$infra" TOADS_DOMAIN "$domain"
	env_set "$infra" TOADS_ACME_EMAIL "$email"
	env_set "$api" TOADS_PUBLIC_BASE_URL "https://$domain"
	env_set "$api" TOADS_DISCORD_REDIRECT_URI "https://$domain/auth/callback"
	# The dev stack's fake Discord; without these two lines the API talks to the real one.
	sed -i '/^TOADS_DISCORD_AUTHORIZE_URL=/d; /^TOADS_DISCORD_API_BASE=/d' "$api"
	# The guild bank stays off (its routes answer 503) until ToadsBank runs next to the hub (docs/bank.md).
	if [[ "$(env_get "$api" TOADS_BANK_URL)" == *fake-bank* ]]; then
		env_set "$api" TOADS_BANK_URL ""
		env_set "$api" TOADS_BANK_SERVICE_TOKEN ""
	fi

	local pg hub creds bankbot url
	pg=$(secret "$infra" TOADS_POSTGRES_PASSWORD 'openssl rand -hex 24')
	url="postgresql+psycopg://toads:$pg@postgres:5432/toads"
	env_set "$api" TOADS_DATABASE_URL "$url"
	env_set "$worker" TOADS_DATABASE_URL "$url"
	hub=$(secret "$api" TOADS_HUB_SERVICE_TOKEN 'openssl rand -hex 32')
	for f in "$worker" "$bot" "$bank"; do env_set "$f" TOADS_HUB_SERVICE_TOKEN "$hub"; done
	creds=$(secret "$api" TOADS_CREDENTIALS_KEYS "openssl rand -base64 32 | tr '+/' '-_'")
	env_set "$worker" TOADS_CREDENTIALS_KEYS "$creds"
	bankbot=$(secret "$api" TOADS_BANK_BOT_TOKEN 'openssl rand -hex 32')
	env_set "$bank" TOADS_BANK_BOT_TOKEN "$bankbot"

	chown "$APP_USER:$APP_USER" "$infra" "$api" "$worker" "$bot" "$bank" "$APP"/config/*.yaml
	chmod 600 "$infra" "$api" "$worker" "$bot" "$bank"
}

make_deploy_key() {
	local domain=$1 home key=/root/toads-deploy-key ip
	home=$(getent passwd "$APP_USER" | cut -d: -f6)
	step "Setting up the GitHub deploy key"
	install -d -m 700 -o "$APP_USER" -g "$APP_USER" "$home/.ssh"
	touch "$home/.ssh/authorized_keys"
	if ! grep -q 'toads-deploy$' "$home/.ssh/authorized_keys"; then
		[[ -f $key ]] || ssh-keygen -q -t ed25519 -N '' -C toads-deploy -f "$key"
		# The key can only run the deploy script: no shell, no forwarding.
		printf 'command="%s/scripts/deploy.sh",restrict %s\n' "$APP" "$(cat "$key.pub")" >>"$home/.ssh/authorized_keys"
	fi
	chown -R "$APP_USER:$APP_USER" "$home/.ssh"
	chmod 600 "$home/.ssh/authorized_keys"
	restorecon -R "$home/.ssh" || true

	ip=$(hostname -I | awk '{print $1}')
	echo "GitHub secrets for the production environment (docs/deploy.md, step 7):"
	echo "  DEPLOY_HOST         $domain"
	echo "  DEPLOY_USER         $APP_USER"
	echo "  DEPLOY_KNOWN_HOSTS  these two lines:"
	awk -v d="$domain" -v i="$ip" '{ print "    " d " " $1 " " $2; print "    " i " " $1 " " $2 }' /etc/ssh/ssh_host_ed25519_key.pub
	if [[ -f $key ]]; then
		echo "  DEPLOY_SSH_KEY      the whole of: sudo cat $key"
		echo "                      then delete it from the server: sudo rm $key $key.pub"
	fi
}

main "$@"
exit
