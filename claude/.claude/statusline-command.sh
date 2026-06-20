#!/usr/bin/env bash
# Claude Code statusLine — continuous left Powerline, Blue PSL 10K palette
# All segments left-to-right with ▶ separators, pi blue-psl-10k order:
#   [ 🍎 path ] ▶ [ git ] ▶ [ 💰 cost ] ▶ [ ⏱️ 5h ] ▶ [ 📅 7d ] ▶ [ 📊 ↓r ↑w ] ▶ [ cache% ] ▶ [ ctx% ] ▶ [ 🧠 effort ] ▶ [ 🤖 model ]

input=$(cat)

# ── Data extraction ────────────────────────────────────────────────────────────
cwd=$(echo "$input"      | jq -r '.workspace.current_dir // .cwd // ""')
display_path="${cwd/#$HOME/~}"
IFS='/' read -ra _p <<< "$display_path"
_n=${#_p[@]}
[ "$_n" -gt 2 ] && display_path=".../${_p[$((_n-2))]}/${_p[$((_n-1))]}"

model=$(echo "$input"    | jq -r '.model.display_name // .model.id // ""')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
cost_usd=$(echo "$input" | jq -r '.cost.total_cost_usd // empty')
rl_5h=$(echo "$input"    | jq -r '.rate_limits.five_hour.used_percentage // empty')
rl_7d=$(echo "$input"    | jq -r '.rate_limits.seven_day.used_percentage // empty')
cache_r=$(echo "$input"  | jq -r '.context_window.current_usage.cache_read_input_tokens // 0')
cache_w=$(echo "$input"  | jq -r '.context_window.current_usage.cache_creation_input_tokens // 0')
input_tk=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // 0')
output_tk=$(echo "$input"| jq -r '.context_window.current_usage.output_tokens // 0')
effort_lvl=$(echo "$input"| jq -r '.effort.level // empty')
fast_mode=$(echo "$input" | jq -r '.fast_mode // false')

read_tokens=$(( input_tk + cache_r ))
write_tokens=$(( output_tk + cache_w ))
total_input=$(( input_tk + cache_r ))
cache_hit_pct=0
[ "$total_input" -gt 0 ] && cache_hit_pct=$(( cache_r * 100 / total_input ))

# ── OS icon (Nerd Fonts, UTF-8 bytes — bash 3.2 compatible) ───────────────────
case "$(uname)" in
  Darwin) OS_ICON=$'\xef\x85\xb9' ;;  # U+F179
  Linux)  OS_ICON=$'\xef\x85\xbc' ;;  # U+F17C
  *)      OS_ICON="" ;;
esac

# ── Git status ─────────────────────────────────────────────────────────────────
git_branch="" git_status="" git_ahead=0 git_behind=0
if [ -n "$cwd" ] && git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git_branch=$(git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null \
               || git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
  git -C "$cwd" diff --no-ext-diff --quiet --cached 2>/dev/null || git_status+="+"
  git -C "$cwd" diff --no-ext-diff --quiet           2>/dev/null || git_status+="!"
  [ -n "$(git -C "$cwd" ls-files --others --exclude-standard 2>/dev/null)" ] && git_status+="?"
  upstream=$(git -C "$cwd" rev-parse --abbrev-ref @{upstream} 2>/dev/null)
  if [ -n "$upstream" ] && [ "$upstream" != "HEAD" ]; then
    ab=$(git -C "$cwd" rev-list --count --left-right @{upstream}...HEAD 2>/dev/null)
    [ -n "$ab" ] && git_behind=$(echo "$ab" | awk '{print $1}') \
                 && git_ahead=$(echo "$ab" | awk '{print $2}')
    git_behind=${git_behind:-0}
    git_ahead=${git_ahead:-0}
  fi
fi

# ── Powerline right arrow (U+E0B0) ────────────────────────────────────────────
PL_R=$'\xee\x82\xb0'

# ── Blue PSL 10K palette ───────────────────────────────────────────────────────
P_BASE="#eff1f5"
P_PATH_BLUE="#3465a4"
P_GREEN="#40a02b"
P_YELLOW="#df8e1d"
P_ORANGE="#fe640b"
P_RED="#d20f39"
P_MAROON="#e64553"
P_SKY="#04a5e5"
P_TEAL="#179299"
P_BLUE="#1e66f5"
P_MUTED="#6c6f85"

# ── ANSI helpers (24-bit true colour) ─────────────────────────────────────────
fgc() { local h="${1#'#'}"; printf '\033[38;2;%d;%d;%dm' "$((16#${h:0:2}))" "$((16#${h:2:2}))" "$((16#${h:4:2}))"; }
bgc() { local h="${1#'#'}"; printf '\033[48;2;%d;%d;%dm' "$((16#${h:0:2}))" "$((16#${h:2:2}))" "$((16#${h:4:2}))"; }
RESET=$'\033[0m'

# ── Helpers ────────────────────────────────────────────────────────────────────
fmt_k() {
  local n=$1
  [ "$n" -ge 1000000 ] && { printf "%.1fM" "$(echo "scale=1; $n/1000000" | bc)"; return; }
  [ "$n" -ge 1000 ]    && { printf "%.1fk" "$(echo "scale=1; $n/1000" | bc)"; return; }
  printf "%d" "$n"
}

ctx_color() { local v=$1
  [ "$v" -ge 90 ] && echo "$P_RED"    && return
  [ "$v" -ge 80 ] && echo "$P_ORANGE" && return
  [ "$v" -ge 50 ] && echo "$P_YELLOW" && return
  echo "$P_GREEN"; }

threshold_color() { local v=$1
  [ "$v" -ge 80 ] && echo "$P_RED"    && return
  [ "$v" -ge 50 ] && echo "$P_YELLOW" && return
  echo "$P_GREEN"; }

effort_color() {
  case "$1" in
    high)   echo "$P_SKY" ;;
    medium) echo "$P_TEAL" ;;
    low)    echo "$P_BLUE" ;;
    *)      echo "$P_MUTED" ;;
  esac
}

# ── Segment renderer (all left, ▶ separators) ──────────────────────────────────
D=$'\x01'

render_left() {
  local segs_var="$1[@]" out="" prev_color=""
  for seg in "${!segs_var}"; do
    local sc="${seg%%${D}*}" st="${seg#*${D}}"
    if [ -z "$prev_color" ]; then
      out+="$(bgc "$sc")$(fgc "$P_BASE")${st}"
    else
      out+="$(bgc "$sc")$(fgc "$prev_color")${PL_R}$(fgc "$P_BASE")${st}"
    fi
    prev_color="$sc"
  done
  [ -n "$prev_color" ] && out+="${RESET}$(fgc "$prev_color")${PL_R}${RESET}" || out+="${RESET}"
  printf '%s' "$out"
}

# ── Build segments (left to right, pi order) ───────────────────────────────────
segs=()

# [ 🍎 path ]
segs+=("${P_PATH_BLUE}${D} ${OS_ICON} ${display_path} ")

# [ git branch [+!?] [↓N/↑N] ]
if [ -n "$git_branch" ]; then
  if [ "$git_ahead" -gt 0 ] && [ "$git_behind" -gt 0 ]; then
    gbg="$P_MAROON"
  elif [ "$git_ahead" -gt 0 ]; then
    gbg="$P_SKY"
  elif [ -n "$git_status" ]; then
    gbg="$P_YELLOW"
  else
    gbg="$P_GREEN"
  fi
  git_text=" $git_branch"
  [ -n "$git_status" ] && git_text+=" $git_status"
  ab=""
  [ "$git_behind" -gt 0 ] && ab+="↓${git_behind}"
  [ "$git_ahead"  -gt 0 ] && { [ -n "$ab" ] && ab+="/"; ab+="↑${git_ahead}"; }
  [ -n "$ab" ] && git_text+=" $ab"
  git_text+=" "
  segs+=("${gbg}${D}${git_text}")
fi

# [ 💰 cost ]
if [ -n "$cost_usd" ] && awk "BEGIN{exit !($cost_usd > 0)}" 2>/dev/null; then
  cost_fmt=$(printf '%.4f' "$cost_usd")
  segs+=("${P_ORANGE}${D} 💰 \$$cost_fmt ")
fi

# [ ⏱️ 5h ] [ 📅 7d ]
if [ -n "$rl_5h" ]; then
  v=$(printf '%.0f' "$rl_5h")
  segs+=("$(threshold_color "$v")${D} ⏱️  ${v}% ")
fi
if [ -n "$rl_7d" ]; then
  v=$(printf '%.0f' "$rl_7d")
  segs+=("$(threshold_color "$v")${D} 📅 ${v}% ")
fi

# [ 📊 ↓read ↑write ]
if [ "$read_tokens" -gt 0 ] || [ "$write_tokens" -gt 0 ]; then
  segs+=("${P_TEAL}${D} 📊 ↓$(fmt_k "$read_tokens") ↑$(fmt_k "$write_tokens") ")
fi

# [ cache X% ]
if [ "$cache_hit_pct" -gt 0 ]; then
  segs+=("${P_GREEN}${D} cache ${cache_hit_pct}% ")
fi

# [ ctx X% ]
if [ -n "$used_pct" ]; then
  v=$(printf '%.0f' "$used_pct")
  segs+=("$(ctx_color "$v")${D} ctx ${v}% ")
fi

# [ 🧠 effort ] — immediately left of model
if [ -n "$effort_lvl" ]; then
  effort_bg=$(effort_color "$effort_lvl")
  if [ "$fast_mode" = "true" ]; then
    segs+=("${effort_bg}${D} 🧠 fast ")
  else
    segs+=("${effort_bg}${D} 🧠 ${effort_lvl} ")
  fi
fi

# [ 🤖 model ] — rightmost
[ -n "$model" ] && segs+=("${P_BLUE}${D} 🤖 $model ")

# ── Render ─────────────────────────────────────────────────────────────────────
render_left segs
