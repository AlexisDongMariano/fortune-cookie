# Bash Basics — SRE Survival Kit

> You'll live in a terminal. These are the ~30 commands that cover 90% of daily SRE work.

---

## Navigation

```bash
pwd                  # where am I
cd /srv/fortune      # change dir
cd -                 # previous dir
ls -la               # list with hidden + long format
tree -L 2            # tree view, 2 levels deep (brew/apt install tree)
```

## Files

```bash
cat file.log                  # whole file
less file.log                 # pageable view  (q to quit, / to search)
head -50 file.log             # first 50 lines
tail -f /var/log/syslog       # follow a log live
wc -l file.log                # line count
cp src dst                    # copy
mv src dst                    # rename/move
rm file                       # delete (no undo!)
rm -rf dir/                   # delete dir recursively (DANGER)
mkdir -p a/b/c                # create nested dirs
```

## Search

```bash
grep -r "TODO" .                       # recursive search for "TODO"
grep -rn "TODO" .                      # with line numbers
grep -rin "error" /var/log             # case-insensitive
find . -name "*.py"                    # files by name
find . -type f -mtime -1               # modified in last 24h
```

## Text processing (the sharp tools)

```bash
echo "hello world" | awk '{print $2}'        # split fields, print 2nd
echo "foo:bar" | cut -d: -f2                  # cut by delimiter
sort file | uniq -c | sort -rn                # frequency count
sed -i 's/old/new/g' file                     # in-place replace
tr ',' '\n' < csv.txt                         # comma → newline
jq '.items[].name' data.json                  # JSON queries (install jq)
```

## Permissions

```bash
ls -la                         # look at the rwx columns
chmod +x script.sh             # make executable
chmod 600 ~/.ssh/id_ed25519    # ONLY owner can read/write (required for SSH keys)
chown ubuntu:ubuntu file       # change owner
```

Numbers: r=4, w=2, x=1. `644` = owner rw, group r, others r. `600` = owner rw, others nothing. Memorize those two.

## Processes

```bash
ps aux | grep uvicorn          # find a process
kill <pid>                     # polite shutdown (SIGTERM)
kill -9 <pid>                  # force (SIGKILL, last resort)
pkill -f uvicorn               # kill by name pattern
top                            # live process view
htop                           # prettier top (install separately)
```

## Networking

```bash
curl -v http://localhost:8000/healthz        # HTTP request with verbose output
curl -fsS -o /dev/null -w "%{http_code}\n" http://…    # just the status
ss -tlnp                       # what's listening on what port
dig example.com                # DNS lookup
nslookup example.com           # alt DNS
ping -c 4 8.8.8.8              # 4 pings
traceroute example.com         # network path
```

## systemd (Linux service manager)

```bash
sudo systemctl status fortune
sudo systemctl start fortune
sudo systemctl stop fortune
sudo systemctl restart fortune
sudo systemctl enable fortune      # start on boot
sudo systemctl disable fortune
sudo journalctl -u fortune -f      # logs (follow)
sudo journalctl -u fortune --since "1 hour ago"
```

## Redirection + pipes

```bash
cmd > file         # overwrite file with stdout
cmd >> file        # append
cmd 2> err.log     # stderr only
cmd > out 2>&1     # both streams to out
cmd | grep error   # pipe stdout into next command
cmd1 && cmd2       # run cmd2 only if cmd1 succeeded
cmd1 || cmd2       # run cmd2 only if cmd1 failed
cmd1; cmd2         # run sequentially no matter what
```

## Writing a safe script

```bash
#!/usr/bin/env bash
set -euo pipefail            # exit on error, unset var, or failed pipe

BASE="${1:-http://localhost:8000}"

if ! curl -fsS "$BASE/healthz" >/dev/null; then
    echo "API unhealthy" >&2
    exit 1
fi

echo "OK"
```

The `set -euo pipefail` line is mandatory. Without it, bash silently ignores errors and you ship broken scripts.

## SSH

```bash
ssh user@host
ssh -i ~/.ssh/key.pem user@host
ssh -L 3000:localhost:3000 user@host    # forward host:3000 to your localhost:3000
scp file.txt user@host:/path/           # copy up
scp user@host:/path/file.txt .          # copy down
ssh-copy-id user@host                   # add your key to target's authorized_keys
```

## Environment variables

```bash
export DATABASE_URL=sqlite:///./f.db    # set in this shell
env | grep DATABASE                     # see current
unset DATABASE_URL                      # remove
```

Persist them:
- Per-user: put `export ...` in `~/.bashrc` (or `~/.zshrc`).
- Per-project: a `.env` file + `source .env` (never commit it).

## Shortcuts that save hours

| Keys | What |
|------|------|
| `Ctrl+R` | Search your shell history (type a word, hit Enter) |
| `Ctrl+A` | Jump to start of line |
| `Ctrl+E` | Jump to end of line |
| `Ctrl+W` | Delete last word |
| `Ctrl+U` | Delete entire line |
| `Alt+.` | Insert last argument of previous command |
| `!!` | Previous command (`sudo !!` = run it with sudo) |
| `!$` | Last arg of previous command |
| `cd -` | Previous directory |

---

## Debugging a script

```bash
bash -x script.sh              # trace every expansion
set -x                         # turn on trace inside script
set +x                         # turn off
```

---

## Things junior people Google repeatedly (print this)

```bash
# Size of current dir
du -sh .

# Top 10 biggest dirs
du -ahx . | sort -rh | head -10

# Free disk space
df -h

# RAM usage
free -h

# CPU cores
nproc

# Watch a command every 2 seconds
watch -n 2 docker ps

# Timestamp on every line of a log
tail -f file.log | ts    # apt install moreutils
```
