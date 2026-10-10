# netem_common.sh: shared guard of netem_apply.sh, netem_watch.sh and netem_show.sh (sourced, never run).
# The only containers these scripts may ever act on are the 11 of the compose project "dibtnsm":
#   (1) selection: `docker ps --filter label=com.docker.compose.project=dibtnsm` (the ONLY docker ps form used);
#   (2) per container: its label com.docker.compose.project must be exactly "dibtnsm" AND its name must be
#       one of the expected names (dibtnsm-evidence-1, dibtnsm-site-0-1 ... dibtnsm-site-9-1);
#   (3) its pid must be a number > 1.
# Any anomaly aborts the WHOLE script BEFORE any namespace is touched (nothing is applied partially).
# docker commands used: `docker ps --filter ...` and `docker inspect -f <label|pid> <expected name>`. Nothing else
# (no network, exec, run, rm, kill). Namespaces are entered only with `nsenter -t <pid> -n tc qdisc ...`.
PROJECT=dibtnsm
EXPECTED_RE='^dibtnsm-(evidence|site-[0-9])-1$'
NODE_N_EXPECTED=11
export PATH="$PATH:/snap/bin"   # appended: /usr/bin/docker is enough for ps/inspect; tests put fakes first

die() { echo "${0##*/}: $*" >&2; exit 1; }

# Prints "name pid" for every container of the project, validated; exits the calling script on any anomaly.
list_project() {
  local names n label pid
  names=$(docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.Names}}' | sort) || die "docker ps failed"
  [[ -n $names ]] || die "no running container in project $PROJECT"
  while read -r n; do
    [[ $n =~ $EXPECTED_RE ]] || die "unexpected container name '$n' in project $PROJECT: nothing applied"
    label=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$n") || die "inspect failed for $n"
    [[ $label == "$PROJECT" ]] || die "container $n has project label '$label', not '$PROJECT': nothing applied"
    pid=$(docker inspect -f '{{.State.Pid}}' "$n") || die "inspect failed for $n"
    [[ $pid =~ ^[0-9]+$ && $pid -gt 1 ]] || die "bad pid '$pid' for $n: nothing applied"
    printf '%s %s\n' "$n" "$pid"
  done <<< "$names"
}

# Loads the validated list into ENTRIES (a plain assignment: a failure in list_project aborts the script here).
load_entries() { ENTRIES=$(list_project) || exit 1; }
