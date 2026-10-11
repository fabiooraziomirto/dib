#!/usr/bin/env bash
# netem_watch2.sh (watcher v2; PREPARED, NOT RUN; to be installed by the USER in /usr/local/lib/dib-netem/ next to the unchanged
# netem_common.sh / netem_apply.sh / netem_show.sh and started ONCE with sudo, in tmux; everything after that is requested without sudo).
#
# Same guard as v1 (netem_watch.sh): the only containers touched are the 11 of the compose project dibtnsm, by label AND by exact
# name, pid > 1 (netem_common.sh); docker is used only as `ps --filter label=...` and `inspect -f ... <expected name>`; namespaces are
# entered only as `nsenter -t <pid> -n tc qdisc (show|replace|del) dev eth0 ...` (replace/del through netem_apply.sh, show here).
#
# What v2 adds. A request file DIR/profile.request is read at every poll. Accepted content is compared for EXACT equality with a CLOSED
# list and nothing else: lan | regional | wan | degraded | restore | partition:site-N (N one digit 0..9, validated against the expected
# names), each optionally followed by `+fast` (poll 0.1 s instead of 0.5 s, for B2). The content is never interpolated into a command,
# never eval'd, never used as a path. The file must be a regular file (symlinks and every other type are rejected), owned by --owner,
# with a single hard link, at most 128 bytes. Anything else is rejected and logged.
#   * state = (BASE profile, partition site or none). lan/regional/wan/degraded set the BASE and clear the partition; `restore` re-applies
#     the CURRENT BASE (it does not delete netem unless the base is lan); partition:site-N applies loss 100% on the egress of that site
#     only (as `netem_apply.sh partition N`) and keeps every other container at the base.
#   * every application ends by writing DIR/profile.applied: request, trigger (request|recreate), UTC time with milliseconds, base,
#     partition, current poll, number of containers, and for EVERY container its `tc qdisc show dev eth0` output (read only). It is
#     the check done by hand with netem_show.sh until now.
#   * the cluster is recreated by run.py: a new signature (ids, names, pids, as in v1) re-applies the current state.
#   * a request that arrives while no container exists is acknowledged (profile.applied with `containers: 0`) and applied when the
#     cluster appears.
#   * DIR/watch2.heartbeat is refreshed every ~2 s (pid, epoch ms, state): the driver uses it to see that the watcher is alive.
#   * DIR/watch2.log records every request, accepted or rejected, with a UTC time (rejected content is logged escaped).
#   * runs ALWAYS under `timeout` (the script re-executes itself under `timeout --max-seconds`, default 9 h, also when the user already
#     wrapped it). On SIGINT/SIGTERM/HUP, on the deadline, or when DIR/STOP exists, it restores lan on the validated containers (netem_apply.sh
#     lan); if that fails it prints the ATTENZIONE warning on stderr and exits 1. With no container left there is nothing to remove.
# Children: `timeout --foreground` signals only this shell, so the exit path kills its own background sleep; a SIGKILL after --kill-after cannot be handled.
# Files in DIR written by root (profile.applied, watch2.log, watch2.heartbeat) are created with mktemp (O_EXCL) and moved into place
# with `mv -fT`, so a symlink planted by the owner at the final name is replaced, never followed.
# TRUST: profile.applied (like watch2.log and watch2.heartbeat) is evidence written by root, but it lives in a directory owned by --owner, who can
# delete or replace any file in it (a symlink or a forged record included). It is a consistency check against faults (wrong profile, partial
# cluster, dead watcher), NOT an authentication of what root applied; the authoritative check stays `sudo netem_show.sh` and the RTT probe of the driver.
# Until the first request is accepted nothing is applied (a fresh cluster has no qdisc). A stale profile.request present at start is ignored. A STOP file present at start makes the script refuse to start.
#
# Usage: sudo timeout 9h bash netem_watch2.sh --dir /home/ubuntu/dib_tnsm/m67 --owner ubuntu [--poll 0.5] [--fast-poll 0.1] [--max-seconds 32400]
#        bash netem_watch2.sh --dry-run --dir D --owner U      prints what it would do; applies nothing, writes nothing
set -uo pipefail
export LC_ALL=C
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/netem_common.sh"
APPLY="$HERE/netem_apply.sh"
ORIG_ARGS=("$@")
DIR=""; OWNER=""; POLL_BASE=0.5; POLL_FAST=0.1; MAX_S=32400; DRY=0
while [[ ${1:-} == --* ]]; do
  case $1 in
    --dry-run) DRY=1; shift;;
    --dir) DIR=${2:-}; shift 2 || die "--dir needs a value";;
    --owner) OWNER=${2:-}; shift 2 || die "--owner needs a value";;
    --poll) POLL_BASE=${2:-}; shift 2 || die "--poll needs a value";;
    --fast-poll) POLL_FAST=${2:-}; shift 2 || die "--fast-poll needs a value";;
    --max-seconds) MAX_S=${2:-}; shift 2 || die "--max-seconds needs a value";;
    *) die "unknown option $1";;
  esac
done
[[ $# == 0 ]] || die "unexpected argument '$1' (the profile is requested through the request file)"
for p in "$POLL_BASE" "$POLL_FAST"; do
  [[ $p =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk "BEGIN{exit !($p >= 0.05)}" || die "bad poll interval '$p' (seconds, >= 0.05)"
done
[[ $MAX_S =~ ^[0-9]+$ && $MAX_S -ge 1 ]] || die "bad --max-seconds '$MAX_S'"
[[ -n $DIR && -n $OWNER ]] || die "usage: $0 [--dry-run] --dir DIR --owner USER [--poll S] [--fast-poll S] [--max-seconds N]"
[[ $DRY == 1 || $EUID == 0 ]] || die "must run as root (sudo)"
OWNER_UID=$(id -u -- "$OWNER" 2>/dev/null) || die "unknown owner '$OWNER'"
[[ -L $DIR ]] && die "$DIR is a symlink"
[[ -d $DIR ]] || die "$DIR is not a directory"
read -r d_uid d_mode <<< "$(stat -c '%u %a' -- "$DIR")"
[[ $d_uid == "$OWNER_UID" ]] || die "directory $DIR is owned by uid $d_uid, not by owner $OWNER ($OWNER_UID)"
(( (8#$d_mode & 8#022) == 0 )) || die "directory $DIR (mode $d_mode) is writable by group/other"
[[ -e $DIR/STOP || -L $DIR/STOP ]] && die "$DIR/STOP exists: remove it first"

ts() { date -u +%FT%T.%3NZ; }
if [[ $DRY == 1 ]]; then
  echo "netem_watch2 (dry run): dir=$DIR owner=$OWNER($OWNER_UID) poll=$POLL_BASE fast-poll=$POLL_FAST max=${MAX_S}s"
  echo "closed list: lan regional wan degraded restore partition:site-0..9 (each optionally +fast)"
  echo "containers of project $PROJECT right now (by name):"
  docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.Names}}' | sort | sed 's/^/  /'
  for pr in lan regional wan degraded; do bash "$APPLY" --dry-run "$pr" || true; done
  bash "$APPLY" --dry-run partition 3 || true
  exit 0
fi

# ---- always under timeout (it re-executes itself once)
if [[ -z ${NETEM_WATCH2_INNER:-} ]]; then
  export NETEM_WATCH2_INNER=1
  exec timeout --foreground --preserve-status --signal=TERM --kill-after=30 "$MAX_S" bash "$0" "${ORIG_ARGS[@]}"
fi

# ---- logging (all root-written files: mktemp + mv -T, never `>` on a name the owner can point elsewhere)
LOG=()
atomic_write() {  # dest content
  local tmp
  tmp=$(mktemp "$DIR/.w2.XXXXXX") || return 1
  printf '%s' "$2" > "$tmp" && chmod 644 "$tmp" && mv -fT -- "$tmp" "$1" || { rm -f -- "$tmp"; return 1; }
}
flush_log() {
  (( ${#LOG[@]} > 20000 )) && LOG=("${LOG[@]:10000}")
  atomic_write "$DIR/watch2.log" "$(printf '%s\n' "${LOG[@]}")"$'\n' || echo "$(ts) netem_watch: cannot write watch2.log" >&2
}
say()  { local l; l="$(ts) netem_watch: $*"; echo "$l"; LOG+=("$l"); flush_log; }
warn() { local l; l="$(ts) netem_watch: $*"; echo "$l" >&2; LOG+=("$l"); flush_log; }

# ---- state
BASE=lan; PART=""; CUR_REQ="(none)"; POLL_CUR=$POLL_BASE
PEND=0; P_BASE=""; P_PART=""; P_REQ=""; P_POLL=""
UNW_TRIGGER=""; unw_fails=0; last_sig=""; TOUCHED=0; fails=0; last_req_sig=""; last_hb=0

heartbeat() {  # state
  local now
  printf -v now '%(%s)T' -1
  [[ $1 == stopped ]] || (( now - last_hb >= 2 )) || return 0
  last_hb=$now
  atomic_write "$DIR/watch2.heartbeat" "pid: $$
utc: $(ts)
epoch_ms: $(date +%s%3N)
state: $1
base: $BASE
partition: ${PART:-none}
poll_s: $POLL_CUR
" || true
}

signature() {  # as v1: "<id> <name>" lines, then "pid <name> <pid>" for the expected names only; non-zero if docker fails
  local psout id n pids i
  local -a names=()
  psout=$(docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.ID}} {{.Names}}' | sort) || return 1
  while read -r id n; do
    [[ -n ${n:-} && $n =~ $EXPECTED_RE ]] && names+=("$n")
  done <<< "$psout"
  echo "$psout"
  if (( ${#names[@]} )); then
    pids=$(docker inspect -f '{{.State.Pid}}' "${names[@]}") || return 1
    i=0
    while read -r id; do echo "pid ${names[$i]} $id"; i=$((i + 1)); done <<< "$pids"
  fi
}

# ---- request file
REQ_WHY=""; REQ_VAL=""; REQ_BASE=""; REQ_PART=""; REQ_FAST=0
esc() { printf '%q' "${1:0:64}"; }
read_request() {  # sets REQ_* ; returns 0 accepted, 1 rejected (REQ_WHY)
  local f="$DIR/profile.request" uid size nlink content v n had_nl=0
  REQ_WHY=""; REQ_VAL=""; REQ_BASE=""; REQ_PART=""; REQ_FAST=0
  if [[ -L $f ]]; then REQ_WHY="symlink"; return 1; fi
  if [[ ! -f $f ]]; then REQ_WHY="not a regular file"; return 1; fi
  read -r uid size nlink <<< "$(stat -c '%u %s %h' -- "$f")"
  if [[ $uid != "$OWNER_UID" ]]; then REQ_WHY="owner uid $uid, expected $OWNER_UID"; return 1; fi
  if (( nlink != 1 )); then REQ_WHY="file has $nlink hard links"; return 1; fi
  if (( size > 128 )); then REQ_WHY="size $size bytes > 128"; return 1; fi
  content=$(timeout 2 head -c 129 -- "$f"; printf x); content=${content%x}
  if [[ $content == *$'\n' ]]; then content=${content%$'\n'}; had_nl=1; fi
  if (( ${#content} + had_nl != size )); then REQ_WHY="content differs from the file size (NUL bytes or file changed while reading): $(esc "$content")"; return 1; fi
  v=$content
  if [[ $v == *+fast ]]; then REQ_FAST=1; v=${v%+fast}; fi
  case $v in
    lan|regional|wan|degraded) REQ_BASE=$v; REQ_PART="";;
    restore) REQ_BASE=$BASE; REQ_PART="";;
    partition:site-[0-9]) n=${v: -1}
      if [[ "$PROJECT-site-$n-1" =~ $EXPECTED_RE ]]; then REQ_BASE=$BASE; REQ_PART=$n
      else REQ_WHY="site $n is not an expected container: $(esc "$content")"; return 1; fi;;
    *) REQ_WHY="not in the closed list: $(esc "$content")"; return 1;;
  esac
  REQ_VAL=$content
  return 0
}
check_request() {
  local sig
  [[ -e $DIR/profile.request || -L $DIR/profile.request ]] || { last_req_sig=""; return 0; }
  sig=$(stat -c '%i %.9Y %.9Z %s %F' -- "$DIR/profile.request" 2>/dev/null) || return 0
  [[ $sig != "$last_req_sig" ]] || return 0
  last_req_sig=$sig
  if read_request; then
    say "request accepted: $REQ_VAL"
    PEND=1; P_BASE=$REQ_BASE; P_PART=$REQ_PART; P_REQ=$REQ_VAL
    if (( REQ_FAST )); then P_POLL=$POLL_FAST; else P_POLL=$POLL_BASE; fi
    fails=0
  else
    say "request rejected: $REQ_WHY"
  fi
}

# ---- application
label() { if [[ -n $2 ]]; then echo "$1+partition:site-$2"; else echo "$1"; fi; }
write_applied() {  # trigger request poll entries(text)
  atomic_write "$DIR/profile.applied" "format: netem_watch2/1
request: $CUR_REQ
trigger: $1
applied_utc: $(ts)
epoch_ms: $(date +%s%3N)
base: $BASE
partition: ${PART:-none}
poll_s: $POLL_CUR
containers: $2
$3"
}
collect_show() {  # prints sections; non-zero on any failure
  local entries name pid out
  entries=$(list_project) || return 1
  while read -r name pid; do
    out=$(nsenter -t "$pid" -n tc qdisc show dev eth0) || { echo "cannot read the qdisc of $name" >&2; return 1; }
    printf '== %s pid %s\n%s\n' "$name" "$pid" "$out"
  done <<< "$entries"
}
try_apply() {  # trigger ; uses BASE/PART/CUR_REQ/POLL_CUR already set to the CANDIDATE state; returns 0 on success
  local trigger=$1 psout n shown
  psout=$(docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.Names}}') || return 1
  if [[ -z $psout ]]; then
    write_applied "$trigger" 0 "note: no container of project $PROJECT; the state is applied when the cluster appears" || return 1
    return 0
  fi
  bash "$APPLY" "$BASE" >/dev/null || return 1
  if [[ -n $PART ]]; then
    list_project | awk -v n="$PROJECT-site-$PART-1" '$1==n{f=1} END{exit !f}' || { echo "partition site-$PART: container not present" >&2; return 1; }
    bash "$APPLY" partition "$PART" >/dev/null || return 1
  fi
  shown=$(collect_show) || return 1
  n=$(grep -c '^== ' <<< "$shown")
  if ! write_applied "$trigger" "$n" "$shown"; then
    # the netem state IS in place: retry only the write (a failed write must never re-run the application)
    UNW_TRIGGER=$trigger; unw_fails=0
    warn "profile.applied NOT written (netem applied; the write is retried every poll)"
  fi
}
retry_write() {  # re-reads the qdisc (read only) and writes the record again
  local shown n
  if shown=$(collect_show) && n=$(grep -c '^== ' <<< "$shown") && write_applied "$UNW_TRIGGER" "$n" "$shown"; then
    say "profile.applied written after $((unw_fails + 1)) failed attempt(s)"; UNW_TRIGGER=""
  else
    unw_fails=$((unw_fails + 1))
    if (( unw_fails % 20 == 0 )); then warn "profile.applied NOT written (attempt $unw_fails)"; fi
  fi
}

cleanup() {  # reason
  local rc=0 psout
  trap '' INT TERM HUP
  kill $(jobs -p) 2>/dev/null; wait 2>/dev/null   # `timeout --foreground` signals only this shell: do not leave the background sleep behind
  say "stopping ($1), restoring lan on the dibtnsm containers"
  if ! psout=$(docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.Names}}'); then
    rc=1
  elif [[ -n $psout ]]; then
    bash "$APPLY" lan >/dev/null || rc=1
  fi
  if (( rc )); then
    warn "ATTENZIONE: pulizia netem NON riuscita, verifica con netem_show.sh"
  else
    say "cleanup done"
    [[ $1 == STOP ]] && rm -f -- "$DIR/STOP"
  fi
  BASE=lan; PART=""
  heartbeat stopped
  exit $rc
}
trap 'cleanup signal' INT TERM HUP

if [[ -e $DIR/profile.request || -L $DIR/profile.request ]]; then
  last_req_sig=$(stat -c '%i %.9Y %.9Z %s %F' -- "$DIR/profile.request" 2>/dev/null || true)
  say "profile.request present at start: stale, ignored"
fi
say "watching: dir=$DIR owner=$OWNER poll=${POLL_BASE}s fast-poll=${POLL_FAST}s max=${MAX_S}s (STOP file or Ctrl-C to stop and clean)"
heartbeat running
while true; do
  if [[ -e $DIR/STOP || -L $DIR/STOP ]]; then cleanup STOP; fi
  heartbeat running
  check_request
  [[ -z $UNW_TRIGGER ]] || retry_write
  cur=$(signature) || cur=""
  if (( PEND )); then
    # candidate state; committed only if the application succeeded (a failed apply is retried at the next poll)
    s_base=$BASE; s_part=$PART; s_req=$CUR_REQ; s_poll=$POLL_CUR
    BASE=$P_BASE; PART=$P_PART; CUR_REQ=$P_REQ; POLL_CUR=$P_POLL
    t0=$(date +%s.%N)
    if try_apply request; then
      PEND=0; fails=0; TOUCHED=1
      [[ -n $cur ]] && last_sig=$cur
      say "applied $(label "$BASE" "$PART") ($(awk "BEGIN{printf \"%.3f\", $(date +%s.%N) - $t0}") s)"
    else
      BASE=$s_base; PART=$s_part; CUR_REQ=$s_req; POLL_CUR=$s_poll
      fails=$((fails + 1))
      if (( fails == 1 || fails % 20 == 0 )); then warn "apply FAILED (attempt $fails) for request $P_REQ, retrying every ${POLL_CUR}s"; fi
    fi
  elif [[ -n $cur && $cur != "$last_sig" ]] && (( ! TOUCHED )); then
    last_sig=$cur   # no request accepted yet: a fresh cluster has no qdisc, nothing to re-apply
  elif [[ -n $cur && $cur != "$last_sig" ]]; then
    (( fails )) || say "containers changed -> applying $(label "$BASE" "$PART")"
    t0=$(date +%s.%N)
    if try_apply recreate; then
      last_sig=$cur; fails=0
      say "applied $(label "$BASE" "$PART") ($(awk "BEGIN{printf \"%.3f\", $(date +%s.%N) - $t0}") s)"
    else
      fails=$((fails + 1))
      if (( fails == 1 || fails % 20 == 0 )); then warn "apply FAILED (attempt $fails), retrying every ${POLL_CUR}s"; fi
    fi
  fi
  sleep "$POLL_CUR" & wait $! || true
done
