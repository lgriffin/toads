# restic with rclone beside it, so RESTIC_REPOSITORY can name an rclone remote such as Google Drive
# (rclone:gdrive:toads-backups). scripts/backup-lib.sh builds it on the server the first time it is needed.
FROM rclone/rclone:1.71.1 AS rclone

FROM restic/restic:0.18.0
COPY --from=rclone /usr/local/bin/rclone /usr/local/bin/rclone
