#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$(cd "$KIT_DIR/.." && pwd)"
APP_NAME="$(basename "$APP_DIR")"

ORCHESTRATOR_PROVIDER="${ORCHESTRATOR_PROVIDER:-codex}"
ORCHESTRATOR_MODEL="${ORCHESTRATOR_MODEL:-gpt-5.5}"
ORCHESTRATOR_EFFORT="${ORCHESTRATOR_EFFORT:-low}"

END_USER_PROVIDER="${END_USER_PROVIDER:-claude}"
END_USER_MODEL="${END_USER_MODEL:-haiku}"
END_USER_EFFORT="${END_USER_EFFORT:-medium}"

REQUIREMENTS_PROVIDER="${REQUIREMENTS_PROVIDER:-codex}"
REQUIREMENTS_MODEL="${REQUIREMENTS_MODEL:-gpt-5.5}"
REQUIREMENTS_EFFORT="${REQUIREMENTS_EFFORT:-high}"

ARCHITECT_PROVIDER="${ARCHITECT_PROVIDER:-claude}"
ARCHITECT_MODEL="${ARCHITECT_MODEL:-fable}"
ARCHITECT_EFFORT="${ARCHITECT_EFFORT:-xhigh}"

DEVELOPER1_PROVIDER="${DEVELOPER1_PROVIDER:-codex}"
DEVELOPER1_MODEL="${DEVELOPER1_MODEL:-gpt-5.5}"
DEVELOPER1_EFFORT="${DEVELOPER1_EFFORT:-high}"

DEVELOPER2_PROVIDER="${DEVELOPER2_PROVIDER:-claude}"
DEVELOPER2_MODEL="${DEVELOPER2_MODEL:-sonnet}"
DEVELOPER2_EFFORT="${DEVELOPER2_EFFORT:-high}"

DEVELOPER3_PROVIDER="${DEVELOPER3_PROVIDER:-claude}"
DEVELOPER3_MODEL="${DEVELOPER3_MODEL:-sonnet}"
DEVELOPER3_EFFORT="${DEVELOPER3_EFFORT:-high}"

REVIEWER1_PROVIDER="${REVIEWER1_PROVIDER:-codex}"
REVIEWER1_MODEL="${REVIEWER1_MODEL:-gpt-5.5}"
REVIEWER1_EFFORT="${REVIEWER1_EFFORT:-xhigh}"

REVIEWER2_PROVIDER="${REVIEWER2_PROVIDER:-claude}"
REVIEWER2_MODEL="${REVIEWER2_MODEL:-sonnet}"
REVIEWER2_EFFORT="${REVIEWER2_EFFORT:-high}"

REVIEWER3_PROVIDER="${REVIEWER3_PROVIDER:-claude}"
REVIEWER3_MODEL="${REVIEWER3_MODEL:-haiku}"
REVIEWER3_EFFORT="${REVIEWER3_EFFORT:-medium}"

TESTER_PROVIDER="${TESTER_PROVIDER:-claude}"
TESTER_MODEL="${TESTER_MODEL:-haiku}"
TESTER_EFFORT="${TESTER_EFFORT:-medium}"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry run"
  echo "App name: $APP_NAME"
  echo "App directory: $APP_DIR"
  echo "Require cloned git repository: $APP_DIR/.git"
  echo "Create Herdr workspace: $APP_NAME"
  echo "Create Herdr tabs: orchestrator, end-user, requirements, architecture, developer-1, developer-2, developer-3, review-1, review-2, review-3, testing"
  echo "Create agents: Orchestrator, EndUser, Requirements, Architect, Developer1, Developer2, Developer3, Reviewer1, Reviewer2, Reviewer3, Tester"
  echo "Agent models:"
  echo "  Orchestrator: $ORCHESTRATOR_PROVIDER / $ORCHESTRATOR_MODEL / $ORCHESTRATOR_EFFORT"
  echo "  EndUser:      $END_USER_PROVIDER / $END_USER_MODEL / $END_USER_EFFORT"
  echo "  Requirements: $REQUIREMENTS_PROVIDER / $REQUIREMENTS_MODEL / $REQUIREMENTS_EFFORT"
  echo "  Architect:    $ARCHITECT_PROVIDER / $ARCHITECT_MODEL / $ARCHITECT_EFFORT"
  echo "  Developer1:   $DEVELOPER1_PROVIDER / $DEVELOPER1_MODEL / $DEVELOPER1_EFFORT"
  echo "  Developer2:   $DEVELOPER2_PROVIDER / $DEVELOPER2_MODEL / $DEVELOPER2_EFFORT"
  echo "  Developer3:   $DEVELOPER3_PROVIDER / $DEVELOPER3_MODEL / $DEVELOPER3_EFFORT"
  echo "  Reviewer1:    $REVIEWER1_PROVIDER / $REVIEWER1_MODEL / $REVIEWER1_EFFORT"
  echo "  Reviewer2:    $REVIEWER2_PROVIDER / $REVIEWER2_MODEL / $REVIEWER2_EFFORT"
  echo "  Reviewer3:    $REVIEWER3_PROVIDER / $REVIEWER3_MODEL / $REVIEWER3_EFFORT"
  echo "  Tester:       $TESTER_PROVIDER / $TESTER_MODEL / $TESTER_EFFORT"
  exit 0
fi

if [[ ! -d "$APP_DIR" ]]; then
  echo "App directory does not exist: $APP_DIR"
  exit 1
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "Expected a cloned git repository at: $APP_DIR"
  echo "Missing: $APP_DIR/.git"
  exit 1
fi

WORKSPACE_JSON="$(herdr workspace create --cwd "$APP_DIR" --label "$APP_NAME" --focus)"
WORKSPACE_ID="$(printf '%s\n' "$WORKSPACE_JSON" | sed -n 's/.*"workspace_id":"\([^"]*\)".*/\1/p')"

if [[ -z "$WORKSPACE_ID" ]]; then
  echo "Failed to parse workspace_id from: $WORKSPACE_JSON"
  exit 1
fi

ORCH_TAB_JSON="$(herdr tab create --workspace "$WORKSPACE_ID" --cwd "$APP_DIR" --label orchestrator --focus)"
END_USER_TAB_JSON="$(herdr tab create --workspace "$WORKSPACE_ID" --cwd "$APP_DIR" --label end-user --no-focus)"
REQ_TAB_JSON="$(herdr tab create --workspace "$WORKSPACE_ID" --cwd "$APP_DIR" --label requirements --no-focus)"
ARCH_TAB_JSON="$(herdr tab create --workspace "$WORKSPACE_ID" --cwd "$APP_DIR" --label architecture --no-focus)"
DEV1_TAB_JSON="$(herdr tab create --workspace "$WORKSPACE_ID" --cwd "$APP_DIR" --label developer-1 --no-focus)"
DEV2_TAB_JSON="$(herdr tab create --workspace "$WORKSPACE_ID" --cwd "$APP_DIR" --label developer-2 --no-focus)"
DEV3_TAB_JSON="$(herdr tab create --workspace "$WORKSPACE_ID" --cwd "$APP_DIR" --label developer-3 --no-focus)"
REVIEW1_TAB_JSON="$(herdr tab create --workspace "$WORKSPACE_ID" --cwd "$APP_DIR" --label review-1 --no-focus)"
REVIEW2_TAB_JSON="$(herdr tab create --workspace "$WORKSPACE_ID" --cwd "$APP_DIR" --label review-2 --no-focus)"
REVIEW3_TAB_JSON="$(herdr tab create --workspace "$WORKSPACE_ID" --cwd "$APP_DIR" --label review-3 --no-focus)"
TEST_TAB_JSON="$(herdr tab create --workspace "$WORKSPACE_ID" --cwd "$APP_DIR" --label testing --no-focus)"

tab_id() {
  printf '%s\n' "$1" | sed -n 's/.*"tab_id":"\([^"]*\)".*/\1/p'
}

send_prompt() {
  local agent="$1"
  local prompt_file="$2"
  herdr agent send "$agent" "$(cat "$prompt_file")"
}

start_agent() {
  local agent="$1"
  local tab_json="$2"
  local provider="$3"
  local model="$4"
  local effort="$5"
  local tab
  tab="$(tab_id "$tab_json")"

  case "$provider" in
    codex)
      herdr agent start "$agent" --cwd "$APP_DIR" --tab "$tab" --no-focus -- \
        codex --model "$model" -c "model_reasoning_effort=\"$effort\""
      ;;
    claude)
      herdr agent start "$agent" --cwd "$APP_DIR" --tab "$tab" --no-focus -- \
        claude --model "$model" --effort "$effort"
      ;;
    *)
      echo "Unsupported provider for $agent: $provider"
      exit 1
      ;;
  esac
}

start_agent Orchestrator "$ORCH_TAB_JSON" "$ORCHESTRATOR_PROVIDER" "$ORCHESTRATOR_MODEL" "$ORCHESTRATOR_EFFORT"
start_agent EndUser "$END_USER_TAB_JSON" "$END_USER_PROVIDER" "$END_USER_MODEL" "$END_USER_EFFORT"
start_agent Requirements "$REQ_TAB_JSON" "$REQUIREMENTS_PROVIDER" "$REQUIREMENTS_MODEL" "$REQUIREMENTS_EFFORT"
start_agent Architect "$ARCH_TAB_JSON" "$ARCHITECT_PROVIDER" "$ARCHITECT_MODEL" "$ARCHITECT_EFFORT"
start_agent Developer1 "$DEV1_TAB_JSON" "$DEVELOPER1_PROVIDER" "$DEVELOPER1_MODEL" "$DEVELOPER1_EFFORT"
start_agent Developer2 "$DEV2_TAB_JSON" "$DEVELOPER2_PROVIDER" "$DEVELOPER2_MODEL" "$DEVELOPER2_EFFORT"
start_agent Developer3 "$DEV3_TAB_JSON" "$DEVELOPER3_PROVIDER" "$DEVELOPER3_MODEL" "$DEVELOPER3_EFFORT"
start_agent Reviewer1 "$REVIEW1_TAB_JSON" "$REVIEWER1_PROVIDER" "$REVIEWER1_MODEL" "$REVIEWER1_EFFORT"
start_agent Reviewer2 "$REVIEW2_TAB_JSON" "$REVIEWER2_PROVIDER" "$REVIEWER2_MODEL" "$REVIEWER2_EFFORT"
start_agent Reviewer3 "$REVIEW3_TAB_JSON" "$REVIEWER3_PROVIDER" "$REVIEWER3_MODEL" "$REVIEWER3_EFFORT"
start_agent Tester "$TEST_TAB_JSON" "$TESTER_PROVIDER" "$TESTER_MODEL" "$TESTER_EFFORT"

send_prompt Orchestrator "$KIT_DIR/prompts/orchestrator.md"
send_prompt EndUser "$KIT_DIR/prompts/end_user.md"
send_prompt Requirements "$KIT_DIR/prompts/requirements.md"
send_prompt Architect "$KIT_DIR/prompts/architect.md"
send_prompt Developer1 "$KIT_DIR/prompts/developer1.md"
send_prompt Developer2 "$KIT_DIR/prompts/developer2.md"
send_prompt Developer3 "$KIT_DIR/prompts/developer3.md"
send_prompt Reviewer1 "$KIT_DIR/prompts/reviewer.md"
send_prompt Reviewer2 "$KIT_DIR/prompts/reviewer2.md"
send_prompt Reviewer3 "$KIT_DIR/prompts/reviewer3.md"
send_prompt Tester "$KIT_DIR/prompts/tester.md"

echo "Created Herdr workspace: $APP_NAME ($WORKSPACE_ID)"
echo "App directory: $APP_DIR"
echo "Tabs and agents are ready."
