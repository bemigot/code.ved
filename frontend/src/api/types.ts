export interface UserInfo {
  username: string;
  roles: string[];
}

export interface ScriptSummary {
  id: number;
  ordering_number: number;
  descriptive_name: string;
  major: number;
  minor: number;
  last_run_at: string | null;
  last_run_exit_code: number | null;
}

export interface VersionInfo {
  id: number;
  major: number;
  minor: number;
  committer: string;
  created_at: string;
  git_commit_hash: string;
  parent_script_id: number | null;
  parent_version_id: number | null;
}

export interface ExecutionResult {
  id: number;
  script_version_id: number;
  exit_code: number | null;
  stdout: string;
  stderr: string;
  started_at: string;
  finished_at: string | null;
  interpreter: string;
}

export interface ScriptDetail {
  id: number;
  ordering_number: number;
  descriptive_name: string;
  content: string;
  version: VersionInfo;
  last_execution: ExecutionResult | null;
}

export interface CompleteResponse {
  response_text: string;
  model_id: string;
  cost_usd: number;
}
