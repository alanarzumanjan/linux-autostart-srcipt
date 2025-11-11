# Prompt: user@host dir branch time
parse_git_branch() { git rev-parse --abbrev-ref HEAD 2>/dev/null; }
parse_rel_path() {
  local p=$(pwd -P)
  if [[ "$p" == "$HOME" ]]; then
    echo ""
  elif [[ "$p" == $HOME/* ]]; then
    echo "${p/#$HOME\//}"
  else
    echo "$p"
  fi
}

PS1='\[\e[1;36m\]\u@\h\[\e[0m\]$(r=$(parse_rel_path); [ -n "$r" ] && echo " \e[0;37m$r")\[\e[33m\]$(b=$(parse_git_branch); [ -n "$b" ] && echo " ($b)")\[\e[0m\]\[\e[35m\] $(date +%H:%M)\[\e[0m\]\$ '

# Aliases (ls always colored)
alias ls='ls --color=auto'
alias ll='ls -lah --color=auto'
alias la='ls -A --color=auto'
alias l='ls --color=auto'
alias ..='cd ..'
alias ...='cd ../..'
alias grep='grep --color=auto'
alias editbash='nano ~/.bashrc && source ~/.bashrc && echo -e "\e[32mbashrc reloaded\e[0m"'
alias c='clear'
alias ga='git add .'

# History
HISTSIZE=50000
HISTFILESIZE=500000
HISTCONTROL=ignoredups:erasedups
shopt -s histappend 2>/dev/null
add_to_prompt_command() {
  case ";$PROMPT_COMMAND;" in *";$1;"*) : ;; *) PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND; }$1" ;; esac
}
__pc_hist_sync() { history -a; history -c; history -r; }
add_to_prompt_command __pc_hist_sync

# Arch package management
alias orphans='pacman -Qtdq'
alias search='pacman -Ss'
alias remove='sudo pacman -Rns'
alias clean='sudo pacman -Rns $(pacman -Qtdq 2>/dev/null) 2>/dev/null || true'
alias up='update'
alias download='sudo pacman -S'

# Docker alias
alias dockon='sudo systemctl start docker.socket docker.service && docker info --format "{{.ServerVersion}}" && echo "docker: up"'
alias dockoff='sudo systemctl stop docker.service docker.socket && echo "docker: down"'

# Status alias
alias vpnstatus='systemctl --user status protonvpn-autoconnect.service'

# Shut down
alias stop='sudo systemctl poweroff'

update() {
  local NO_AUR=0 CLEAN=0 FORCE=0
  while (( "$#" )); do
    case "$1" in
      --no-aur) NO_AUR=1 ;;
      --clean) CLEAN=1 ;;
      --force-refresh) FORCE=1 ;;
      *) echo -e "\e[31munknown option:\e[0m $1"; return 2 ;;
    esac
    shift
  done

  local pac_flags="-Syu --noconfirm"
  [[ $FORCE -eq 1 ]] && pac_flags="-Syyu --noconfirm"

  echo -e "\e[36m==> pacman update\e[0m"
  sudo pacman $pac_flags || { echo -e "\e[31mpacman failed\e[0m"; return 1; }

  if [ $NO_AUR -eq 0 ]; then
    if command -v paru >/dev/null 2>&1; then
      echo -e "\e[36m==> AUR update (paru)\e[0m"
      paru -Syu --noconfirm || echo -e "\e[31mAUR update failed\e[0m"
    elif command -v yay >/dev/null 2>&1; then
      echo -e "\e[36m==> AUR update (yay)\e[0m"
      yay -Syu --noconfirm || echo -e "\e[31mAUR update failed\e[0m"
    else
      echo -e "\e[33mAUR helper not found\e[0m"
    fi
  else
    echo -e "\e[33mAUR skipped\e[0m"
  fi

  if [ $CLEAN -eq 1 ]; then
    echo -e "\e[36m==> Cleaning orphans\e[0m"
    local orph
    orph=$(pacman -Qtdq 2>/dev/null || true)
    if [ -n "$orph" ]; then
      sudo pacman -Rns $orph --noconfirm
      echo -e "\e[32morphan packages removed\e[0m"
    else
      echo -e "\e[32mno orphans found\e[0m"
    fi
  fi

  echo -e "\e[32mupdate done\e[0m"
}

# Enable color for ls
eval "$(dircolors -b)"