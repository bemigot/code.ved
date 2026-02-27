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
