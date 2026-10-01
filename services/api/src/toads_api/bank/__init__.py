"""The guild bank: the hub's adapter to ToadsBank (docs/bank.md). ToadsBank owns the bank's data and rules; the hub
signs members in, decides who reaches which route, calls toadsbank-api for them and turns ToadsBank's events into
Discord messages through the bank bot."""
